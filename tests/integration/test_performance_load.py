"""
Performance and Load Testing for Slack Trading Bot

This module provides comprehensive performance and load testing scenarios
including concurrent user workflows, high-load scenarios, stress testing,
and performance benchmarking with detailed metrics collection and analysis.
"""

import asyncio
import pytest
import time
import statistics
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Tuple, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import concurrent.futures
import threading
import psutil
import gc

# Import application components
from listeners.commands import CommandHandler, CommandType
from listeners.actions import ActionHandler, ActionType
from services.service_container import ServiceContainer
from models.user import User, UserRole, Permission
from models.trade import Trade, TradeType, TradeStatus

# Test utilities
from tests.fixtures.slack_payloads import (
    create_slash_command_payload,
    create_button_action_payload,
    create_modal_submission_payload
)
from tests.fixtures.test_data import create_bulk_test_data, create_test_user
from tests.utils.mock_services import (
    MockSlackClient,
    MockDatabaseService,
    MockMarketDataService,
    MockRiskAnalysisService,
    MockTradingAPIService
)


class PerformanceMetrics:
    """
    Performance metrics collection and analysis.
    
    Tracks response times, throughput, resource usage, and error rates
    for comprehensive performance analysis.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
        self.concurrent_operations = 0
        self.max_concurrent_operations = 0
        self.operation_details = []
    
    def start_operation(self, operation_type: str, operation_id: str = None) -> str:
        """Start tracking an operation."""
        if operation_id is None:
            operation_id = str(uuid.uuid4())
        
        self.concurrent_operations += 1
        self.max_concurrent_operations = max(self.max_concurrent_operations, self.concurrent_operations)
        
        operation = {
            'id': operation_id,
            'type': operation_type,
            'start_time': time.time(),
            'end_time': None,
            'duration': None,
            'success': None,
            'error': None
        }
        
        self.operation_details.append(operation)
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, error: str = None):
        """End tracking an operation."""
        end_time = time.time()
        
        # Find the operation
        operation = next((op for op in self.operation_details if op['id'] == operation_id), None)
        if operation:
            operation['end_time'] = end_time
            operation['duration'] = end_time - operation['start_time']
            operation['success'] = success
            operation['error'] = error
            
            self.response_times.append(operation['duration'])
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
        
        self.concurrent_operations -= 1
    
    def record_system_metrics(self):
        """Record current system resource usage."""
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.response_times:
            return {'error': 'No operations recorded'}
        
        total_operations = len(self.response_times)
        total_time = (self.end_time or time.time()) - (self.start_time or time.time())
        
        return {
            'total_operations': total_operations,
            'successful_operations': self.success_count,
            'failed_operations': self.error_count,
            'success_rate': (self.success_count / total_operations) * 100 if total_operations > 0 else 0,
            'total_duration': total_time,
            'throughput_ops_per_second': total_operations / total_time if total_time > 0 else 0,
            'response_times': {
                'min': min(self.response_times),
                'max': max(self.response_times),
                'mean': statistics.mean(self.response_times),
                'median': statistics.median(self.response_times),
                'p95': self._percentile(self.response_times, 95),
                'p99': self._percentile(self.response_times, 99)
            },
            'concurrency': {
                'max_concurrent_operations': self.max_concurrent_operations
            },
            'resource_usage': {
                'memory_mb': {
                    'min': min(self.memory_usage) if self.memory_usage else 0,
                    'max': max(self.memory_usage) if self.memory_usage else 0,
                    'mean': statistics.mean(self.memory_usage) if self.memory_usage else 0
                },
                'cpu_percent': {
                    'min': min(self.cpu_usage) if self.cpu_usage else 0,
                    'max': max(self.cpu_usage) if self.cpu_usage else 0,
                    'mean': statistics.mean(self.cpu_usage) if self.cpu_usage else 0
                }
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestPerformanceAndLoad:
    """
    Comprehensive performance and load testing suite.
    
    Tests system performance under various load conditions including
    concurrent users, high-frequency operations, stress testing,
    and resource utilization analysis.
    """
    
    @pytest.fixture
    async def service_container(self):
        """Create optimized service container for performance testing."""
        container = ServiceContainer()
        
        # Use mock services with minimal delays
        container._auth_service = AsyncMock()
        container._database_service = MockDatabaseService()
        container._market_data_service = MockMarketDataService()
        container._risk_analysis_service = MockRiskAnalysisService()
        container._trading_api_service = MockTradingAPIService()
        
        # Configure for performance testing
        container._market_data_service.set_response_delay(0.01)  # 10ms delay
        container._risk_analysis_service.set_response_delay(0.05)  # 50ms delay
        container._trading_api_service.set_response_delay(0.02)  # 20ms delay
        
        return container
    
    @pytest.fixture
    def performance_metrics(self):
        """Create performance metrics tracker."""
        return PerformanceMetrics()
    
    @pytest.fixture
    def bulk_test_data(self):
        """Create bulk test data for load testing."""
        return create_bulk_test_data(
            num_users=50,
            num_trades_per_user=10,
            num_positions_per_user=5
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_command_processing(self, service_container, performance_metrics, bulk_test_data):
        """
        Test concurrent command processing performance.
        
        Simulates multiple users executing /trade commands simultaneously
        to test system performance under concurrent load.
        """
        users = bulk_test_data['users'][:20]  # Use 20 users for concurrency test
        mock_slack_client = MockSlackClient()
        
        # Setup authentication
        def mock_auth(slack_user_id, *args, **kwargs):
            user = next((u for u in users if u.slack_user_id == slack_user_id), users[0])
            return user, MagicMock(session_id=f'session_{slack_user_id}')
        
        service_container._auth_service.authenticate_slack_user.side_effect = mock_auth
        service_container._auth_service.authorize_channel_access.return_value = True
        
        # Initialize command handler
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        
        # Define concurrent command execution
        async def execute_command(user: User, symbol: str) -> Tuple[bool, float, str]:
            """Execute a single command and return results."""
            operation_id = performance_metrics.start_operation('command_processing', f'cmd_{user.user_id}')
            
            try:
                command_payload = create_slash_command_payload(
                    command='/trade',
                    user_id=user.slack_user_id,
                    channel_id='C1234567890',
                    text=f'{symbol} 100 BUY'
                )
                
                start_time = time.time()
                
                await command_handler.process_command(
                    CommandType.TRADE,
                    command_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                
                duration = time.time() - start_time
                performance_metrics.end_operation(operation_id, True)
                return True, duration, None
                
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                performance_metrics.end_operation(operation_id, False, str(e))
                return False, duration, str(e)
        
        # Execute concurrent commands
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        
        performance_metrics.start_time = time.time()
        
        # Create tasks for concurrent execution
        tasks = []
        for i, user in enumerate(users):
            symbol = symbols[i % len(symbols)]
            task = execute_command(user, symbol)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        performance_metrics.end_time = time.time()
        
        # Analyze results
        successful_commands = sum(1 for result in results if isinstance(result, tuple) and result[0])
        failed_commands = len(results) - successful_commands
        
        response_times = [result[1] for result in results if isinstance(result, tuple)]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Performance assertions
        assert successful_commands >= len(users) * 0.95, f"Success rate too low: {successful_commands}/{len(users)}"
        assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time:.3f}s"
        assert max(response_times) < 5.0, f"Max response time too high: {max(response_times):.3f}s"
        
        # Verify all users got their modals
        assert mock_slack_client.views_open.call_count >= successful_commands * 0.9
        
        print(f"\nConcurrent Command Processing Results:")
        print(f"Users: {len(users)}")
        print(f"Successful commands: {successful_commands}")
        print(f"Failed commands: {failed_commands}")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Max response time: {max(response_times):.3f}s")
        print(f"Min response time: {min(response_times):.3f}s")
    
    @pytest.mark.asyncio
    async def test_high_frequency_operations(self, service_container, performance_metrics):
        """
        Test high-frequency operation performance.
        
        Simulates rapid-fire operations from a single user to test
        system performance under high-frequency load.
        """
        test_user = create_test_user(role=UserRole.EXECUTION_TRADER)
        mock_slack_client = MockSlackClient()
        
        # Setup services
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='high_freq_session')
        )
        service_container._auth_service.authorize_channel_access.return_value = True
        
        # Initialize handlers
        action_handler = ActionHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service,
            service_container._risk_analysis_service,
            service_container._trading_api_service
        )
        
        # Define high-frequency operation
        async def rapid_market_data_request(symbol: str, request_id: int) -> Tuple[bool, float]:
            """Execute rapid market data request."""
            operation_id = performance_metrics.start_operation('market_data', f'md_{request_id}')
            
            try:
                market_data_payload = create_button_action_payload(
                    action_id='get_market_data',
                    user_id=test_user.slack_user_id,
                    view_id=f'V{request_id:010d}',
                    state_values={
                        'symbol_input': {'symbol': {'value': symbol}}
                    }
                )
                
                start_time = time.time()
                
                await action_handler.process_action(
                    ActionType.GET_MARKET_DATA,
                    market_data_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                
                duration = time.time() - start_time
                performance_metrics.end_operation(operation_id, True)
                return True, duration
                
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                performance_metrics.end_operation(operation_id, False, str(e))
                return False, duration
        
        # Execute high-frequency operations
        num_operations = 100
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        
        performance_metrics.start_time = time.time()
        
        # Execute operations in batches to simulate high frequency
        batch_size = 10
        all_results = []
        
        for batch_start in range(0, num_operations, batch_size):
            batch_tasks = []
            
            for i in range(batch_start, min(batch_start + batch_size, num_operations)):
                symbol = symbols[i % len(symbols)]
                task = rapid_market_data_request(symbol, i)
                batch_tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)
            
            # Small delay between batches to simulate realistic usage
            await asyncio.sleep(0.01)
        
        performance_metrics.end_time = time.time()
        
        # Analyze results
        successful_ops = sum(1 for result in all_results if isinstance(result, tuple) and result[0])
        response_times = [result[1] for result in all_results if isinstance(result, tuple)]
        
        total_time = performance_metrics.end_time - performance_metrics.start_time
        throughput = num_operations / total_time
        
        # Performance assertions
        assert successful_ops >= num_operations * 0.95, f"Success rate too low: {successful_ops}/{num_operations}"
        assert throughput >= 20, f"Throughput too low: {throughput:.1f} ops/sec"
        assert statistics.mean(response_times) < 0.5, f"Average response time too high: {statistics.mean(response_times):.3f}s"
        
        print(f"\nHigh-Frequency Operations Results:")
        print(f"Total operations: {num_operations}")
        print(f"Successful operations: {successful_ops}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Throughput: {throughput:.1f} ops/sec")
        print(f"Average response time: {statistics.mean(response_times):.3f}s")
        print(f"95th percentile: {performance_metrics._percentile(response_times, 95):.3f}s")
    
    @pytest.mark.asyncio
    async def test_stress_testing_limits(self, service_container, performance_metrics):
        """
        Test system behavior under extreme stress conditions.
        
        Pushes the system to its limits with maximum concurrent operations,
        large payloads, and resource exhaustion scenarios.
        """
        # Create many test users
        users = [create_test_user(user_id=f'stress_user_{i:03d}') for i in range(100)]
        mock_slack_client = MockSlackClient()
        
        # Setup authentication
        def mock_auth(slack_user_id, *args, **kwargs):
            user = next((u for u in users if u.slack_user_id == slack_user_id), users[0])
            return user, MagicMock(session_id=f'stress_session_{slack_user_id}')
        
        service_container._auth_service.authenticate_slack_user.side_effect = mock_auth
        service_container._auth_service.authorize_channel_access.return_value = True
        
        # Initialize handlers
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        
        action_handler = ActionHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service,
            service_container._risk_analysis_service,
            service_container._trading_api_service
        )
        
        # Define stress test operation
        async def stress_operation(user: User, operation_id: int) -> Dict[str, Any]:
            """Execute a complete trade workflow under stress."""
            op_id = performance_metrics.start_operation('stress_workflow', f'stress_{operation_id}')
            
            try:
                # Step 1: Command processing
                command_payload = create_slash_command_payload(
                    command='/trade',
                    user_id=user.slack_user_id,
                    channel_id='C1234567890',
                    text='AAPL 100 BUY'
                )
                
                await command_handler.process_command(
                    CommandType.TRADE,
                    command_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                
                # Step 2: Market data request
                market_data_payload = create_button_action_payload(
                    action_id='get_market_data',
                    user_id=user.slack_user_id,
                    view_id=f'V{operation_id:010d}',
                    state_values={'symbol_input': {'symbol': {'value': 'AAPL'}}}
                )
                
                await action_handler.process_action(
                    ActionType.GET_MARKET_DATA,
                    market_data_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                
                # Step 3: Risk analysis
                risk_payload = create_button_action_payload(
                    action_id='analyze_risk',
                    user_id=user.slack_user_id,
                    view_id=f'V{operation_id:010d}',
                    state_values={
                        'symbol_input': {'symbol': {'value': 'AAPL'}},
                        'quantity_input': {'quantity': {'value': '100'}},
                        'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                        'price_input': {'price': {'value': '150.00'}}
                    }
                )
                
                await action_handler.process_action(
                    ActionType.ANALYZE_RISK,
                    risk_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                
                # Step 4: Trade submission
                trade_payload = create_modal_submission_payload(
                    callback_id='trade_modal',
                    user_id=user.slack_user_id,
                    view_id=f'V{operation_id:010d}',
                    state_values={
                        'symbol_input': {'symbol': {'value': 'AAPL'}},
                        'quantity_input': {'quantity': {'value': '100'}},
                        'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                        'price_input': {'price': {'value': '150.00'}}
                    }
                )
                
                await action_handler.process_action(
                    ActionType.SUBMIT_TRADE,
                    trade_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                
                performance_metrics.end_operation(op_id, True)
                return {'success': True, 'user_id': user.user_id, 'operation_id': operation_id}
                
            except Exception as e:
                performance_metrics.end_operation(op_id, False, str(e))
                return {'success': False, 'user_id': user.user_id, 'operation_id': operation_id, 'error': str(e)}
        
        # Execute stress test
        num_operations = 50  # Reduced for stress test
        performance_metrics.start_time = time.time()
        
        # Monitor system resources during stress test
        async def monitor_resources():
            """Monitor system resources during stress test."""
            while performance_metrics.concurrent_operations > 0:
                performance_metrics.record_system_metrics()
                await asyncio.sleep(0.1)
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(monitor_resources())
        
        # Execute stress operations
        tasks = []
        for i in range(num_operations):
            user = users[i % len(users)]
            task = stress_operation(user, i)
            tasks.append(task)
        
        # Execute with limited concurrency to avoid overwhelming the system
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent operations
        
        async def limited_stress_operation(user: User, operation_id: int):
            async with semaphore:
                return await stress_operation(user, operation_id)
        
        limited_tasks = [limited_stress_operation(users[i % len(users)], i) for i in range(num_operations)]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        performance_metrics.end_time = time.time()
        
        # Stop resource monitoring
        monitor_task.cancel()
        
        # Analyze stress test results
        successful_ops = sum(1 for result in results if isinstance(result, dict) and result.get('success'))
        failed_ops = len(results) - successful_ops
        
        summary = performance_metrics.get_summary()
        
        # Stress test assertions (more lenient than normal performance tests)
        assert successful_ops >= num_operations * 0.8, f"Success rate too low under stress: {successful_ops}/{num_operations}"
        assert summary['response_times']['mean'] < 10.0, f"Average response time too high under stress: {summary['response_times']['mean']:.3f}s"
        
        print(f"\nStress Test Results:")
        print(f"Total operations: {num_operations}")
        print(f"Successful operations: {successful_ops}")
        print(f"Failed operations: {failed_ops}")
        print(f"Success rate: {(successful_ops/num_operations)*100:.1f}%")
        print(f"Average response time: {summary['response_times']['mean']:.3f}s")
        print(f"95th percentile: {summary['response_times']['p95']:.3f}s")
        print(f"Max concurrent operations: {summary['concurrency']['max_concurrent_operations']}")
        print(f"Peak memory usage: {summary['resource_usage']['memory_mb']['max']:.1f} MB")
        print(f"Peak CPU usage: {summary['resource_usage']['cpu_percent']['max']:.1f}%")
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, service_container, performance_metrics):
        """
        Test for memory leaks during extended operation.
        
        Runs operations repeatedly and monitors memory usage to detect
        potential memory leaks or resource accumulation issues.
        """
        test_user = create_test_user()
        mock_slack_client = MockSlackClient()
        
        # Setup services
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='memory_test_session')
        )
        service_container._auth_service.authorize_channel_access.return_value = True
        
        # Initialize command handler
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        
        # Record initial memory usage
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_samples = [initial_memory]
        
        # Run operations in cycles
        num_cycles = 10
        operations_per_cycle = 20
        
        for cycle in range(num_cycles):
            # Execute operations
            for op in range(operations_per_cycle):
                command_payload = create_slash_command_payload(
                    command='/trade',
                    user_id=test_user.slack_user_id,
                    channel_id='C1234567890',
                    text=f'AAPL {(op+1)*10} BUY'
                )
                
                await command_handler.process_command(
                    CommandType.TRADE,
                    command_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
            
            # Force garbage collection
            gc.collect()
            
            # Record memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)
            
            # Small delay between cycles
            await asyncio.sleep(0.1)
        
        # Analyze memory usage trend
        memory_growth = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)
        avg_memory = statistics.mean(memory_samples)
        
        # Calculate memory growth rate
        if len(memory_samples) > 1:
            # Linear regression to detect trend
            x_values = list(range(len(memory_samples)))
            y_values = memory_samples
            
            n = len(memory_samples)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            memory_growth_rate = slope  # MB per cycle
        else:
            memory_growth_rate = 0
        
        # Memory leak assertions
        assert memory_growth < 50, f"Excessive memory growth detected: {memory_growth:.1f} MB"
        assert memory_growth_rate < 2, f"High memory growth rate: {memory_growth_rate:.2f} MB/cycle"
        assert max_memory < initial_memory + 100, f"Peak memory usage too high: {max_memory:.1f} MB"
        
        print(f"\nMemory Leak Detection Results:")
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Final memory: {memory_samples[-1]:.1f} MB")
        print(f"Memory growth: {memory_growth:.1f} MB")
        print(f"Memory growth rate: {memory_growth_rate:.2f} MB/cycle")
        print(f"Peak memory: {max_memory:.1f} MB")
        print(f"Average memory: {avg_memory:.1f} MB")
        print(f"Total operations: {num_cycles * operations_per_cycle}")
    
    @pytest.mark.asyncio
    async def test_database_performance_scaling(self, service_container, performance_metrics):
        """
        Test database performance under increasing load.
        
        Tests database operations with increasing data volumes and
        concurrent access patterns to identify scaling bottlenecks.
        """
        # Use real mock database service for this test
        db_service = MockDatabaseService()
        
        # Pre-populate database with test data
        bulk_data = create_bulk_test_data(
            num_users=20,
            num_trades_per_user=50,
            num_positions_per_user=10
        )
        
        # Insert bulk data
        for user in bulk_data['users']:
            await db_service.create_user(user)
        
        for trade in bulk_data['trades']:
            await db_service.log_trade(trade)
        
        for position in bulk_data['positions']:
            await db_service.update_position(
                position.user_id,
                position.symbol,
                position.quantity,
                position.average_cost,
                f"trade_{uuid.uuid4().hex[:8]}"
            )
        
        # Test database operations with increasing load
        async def database_operation_test(operation_type: str, num_operations: int) -> Dict[str, Any]:
            """Test specific database operation performance."""
            operation_times = []
            
            for i in range(num_operations):
                start_time = time.time()
                
                try:
                    if operation_type == 'get_user':
                        user = bulk_data['users'][i % len(bulk_data['users'])]
                        await db_service.get_user(user.user_id)
                    
                    elif operation_type == 'get_user_trades':
                        user = bulk_data['users'][i % len(bulk_data['users'])]
                        await db_service.get_user_trades(user.user_id, limit=10)
                    
                    elif operation_type == 'get_user_positions':
                        user = bulk_data['users'][i % len(bulk_data['users'])]
                        await db_service.get_user_positions(user.user_id)
                    
                    elif operation_type == 'log_trade':
                        user = bulk_data['users'][i % len(bulk_data['users'])]
                        from tests.fixtures.test_data import create_test_trade
                        trade = create_test_trade(
                            symbol='TEST',
                            quantity=100,
                            user_id=user.user_id,
                            trade_id=f"perf_trade_{i}"
                        )
                        await db_service.log_trade(trade)
                    
                    operation_times.append(time.time() - start_time)
                    
                except Exception as e:
                    # Record failed operation time
                    operation_times.append(time.time() - start_time)
            
            return {
                'operation_type': operation_type,
                'num_operations': num_operations,
                'total_time': sum(operation_times),
                'avg_time': statistics.mean(operation_times),
                'min_time': min(operation_times),
                'max_time': max(operation_times),
                'p95_time': performance_metrics._percentile(operation_times, 95)
            }
        
        # Test different operation types with increasing load
        operation_types = ['get_user', 'get_user_trades', 'get_user_positions', 'log_trade']
        load_levels = [10, 50, 100, 200]
        
        results = {}
        
        for operation_type in operation_types:
            results[operation_type] = {}
            
            for load_level in load_levels:
                result = await database_operation_test(operation_type, load_level)
                results[operation_type][load_level] = result
                
                # Performance assertions based on operation type
                if operation_type in ['get_user', 'get_user_positions']:
                    assert result['avg_time'] < 0.1, f"{operation_type} too slow at {load_level} ops: {result['avg_time']:.3f}s"
                elif operation_type == 'get_user_trades':
                    assert result['avg_time'] < 0.2, f"{operation_type} too slow at {load_level} ops: {result['avg_time']:.3f}s"
                elif operation_type == 'log_trade':
                    assert result['avg_time'] < 0.15, f"{operation_type} too slow at {load_level} ops: {result['avg_time']:.3f}s"
        
        # Print performance scaling results
        print(f"\nDatabase Performance Scaling Results:")
        for operation_type, load_results in results.items():
            print(f"\n{operation_type.upper()}:")
            for load_level, result in load_results.items():
                print(f"  {load_level:3d} ops: avg={result['avg_time']*1000:6.1f}ms, "
                      f"p95={result['p95_time']*1000:6.1f}ms, max={result['max_time']*1000:6.1f}ms")


if __name__ == '__main__':
    # Run performance tests
    pytest.main([__file__, '-v', '--asyncio-mode=auto', '-s'])