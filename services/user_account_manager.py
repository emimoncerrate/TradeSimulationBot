"""
User Account Manager for Multi-Alpaca Account Assignment

This service manages the assignment of users to specific Alpaca accounts,
allowing for isolated portfolios and account management.
"""

import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AccountAssignmentStrategy(Enum):
    """Strategies for assigning users to accounts."""
    ROUND_ROBIN = "round_robin"  # Distribute users evenly
    LEAST_LOADED = "least_loaded"  # Assign to account with fewest users
    MANUAL = "manual"  # Manual assignment only
    DEPARTMENT_BASED = "department"  # Assign based on user department


@dataclass
class UserAccountAssignment:
    """User to account assignment record."""
    user_id: str
    account_id: str
    assigned_at: datetime
    assigned_by: str
    assignment_reason: str
    is_active: bool = True


class UserAccountManager:
    """
    Manages user assignments to Alpaca accounts.
    
    Features:
    - Automatic user assignment strategies
    - Manual account assignment
    - Department-based assignment
    - Load balancing across accounts
    - Assignment history tracking
    """
    
    def __init__(self, database_service=None):
        self.database_service = database_service
        self.assignments: Dict[str, UserAccountAssignment] = {}
        self.assignment_strategy = AccountAssignmentStrategy.LEAST_LOADED
        
        # Load existing assignments from database on startup
        self._load_assignments_sync()
        
        logger.info("UserAccountManager initialized")
    
    async def assign_user_to_account(self, user_id: str, account_id: str, 
                                   assigned_by: str = "system", 
                                   reason: str = "auto_assignment") -> bool:
        """
        Assign a user to a specific Alpaca account.
        
        Args:
            user_id: User identifier
            account_id: Alpaca account identifier
            assigned_by: Who made the assignment
            reason: Reason for assignment
            
        Returns:
            bool: True if assignment successful
        """
        try:
            assignment = UserAccountAssignment(
                user_id=user_id,
                account_id=account_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by=assigned_by,
                assignment_reason=reason
            )
            
            self.assignments[user_id] = assignment
            
            # Store in database if available
            if self.database_service:
                await self._store_assignment_in_database(assignment)
            
            logger.info(f"✅ User {user_id} assigned to account {account_id} by {assigned_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign user {user_id} to account {account_id}: {e}")
            return False
    
    def get_user_account(self, user_id: str) -> Optional[str]:
        """
        Get the account ID assigned to a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional[str]: Account ID if assigned, None otherwise
        """
        assignment = self.assignments.get(user_id)
        if assignment and assignment.is_active:
            return assignment.account_id
        return None
    
    async def auto_assign_user(self, user_id: str, available_accounts: List[str], 
                             user_department: Optional[str] = None) -> Optional[str]:
        """
        Automatically assign a user to an account based on strategy.
        
        Args:
            user_id: User identifier
            available_accounts: List of available account IDs
            user_department: User's department (for department-based assignment)
            
        Returns:
            Optional[str]: Assigned account ID
        """
        if not available_accounts:
            logger.warning("No available accounts for auto-assignment")
            return None
        
        # Check if user already has an assignment
        existing_account = self.get_user_account(user_id)
        if existing_account and existing_account in available_accounts:
            logger.info(f"User {user_id} already assigned to {existing_account}")
            return existing_account
        
        # Apply assignment strategy
        if self.assignment_strategy == AccountAssignmentStrategy.DEPARTMENT_BASED:
            account_id = self._assign_by_department(user_department, available_accounts)
        elif self.assignment_strategy == AccountAssignmentStrategy.ROUND_ROBIN:
            account_id = self._assign_round_robin(available_accounts)
        elif self.assignment_strategy == AccountAssignmentStrategy.LEAST_LOADED:
            account_id = self._assign_least_loaded(available_accounts)
        else:
            # Default to first available account
            account_id = available_accounts[0]
        
        if account_id:
            success = await self.assign_user_to_account(
                user_id, account_id, "system", f"auto_{self.assignment_strategy.value}"
            )
            return account_id if success else None
        
        return None
    
    def _assign_by_department(self, department: Optional[str], 
                            available_accounts: List[str]) -> Optional[str]:
        """
        Assign user based on department.
        
        Department mapping:
        - Trading/Execution -> Primary account
        - Research/Analysis -> Account 1
        - Portfolio Management -> Account 2
        - Other -> Least loaded account
        """
        if not department:
            return self._assign_least_loaded(available_accounts)
        
        department_mapping = {
            'trading': 'primary',
            'execution': 'primary',
            'research': 'account_1',
            'analysis': 'account_1',
            'portfolio': 'account_2',
            'management': 'account_2'
        }
        
        preferred_account = None
        for dept_key, account_id in department_mapping.items():
            if dept_key.lower() in department.lower():
                preferred_account = account_id
                break
        
        if preferred_account and preferred_account in available_accounts:
            return preferred_account
        
        # Fallback to least loaded
        return self._assign_least_loaded(available_accounts)
    
    def _assign_round_robin(self, available_accounts: List[str]) -> str:
        """
        Assign user using round-robin strategy.
        """
        # Count assignments per account
        account_counts = {account_id: 0 for account_id in available_accounts}
        
        for assignment in self.assignments.values():
            if assignment.is_active and assignment.account_id in account_counts:
                account_counts[assignment.account_id] += 1
        
        # Find account with minimum assignments
        return min(account_counts.keys(), key=lambda x: account_counts[x])
    
    def _assign_least_loaded(self, available_accounts: List[str]) -> str:
        """
        Assign user to the least loaded account.
        """
        return self._assign_round_robin(available_accounts)  # Same logic
    
    async def reassign_user(self, user_id: str, new_account_id: str, 
                          assigned_by: str, reason: str) -> bool:
        """
        Reassign a user to a different account.
        
        Args:
            user_id: User identifier
            new_account_id: New account ID
            assigned_by: Who made the reassignment
            reason: Reason for reassignment
            
        Returns:
            bool: True if reassignment successful
        """
        # Deactivate old assignment
        old_assignment = self.assignments.get(user_id)
        if old_assignment:
            old_assignment.is_active = False
            logger.info(f"Deactivated old assignment: {user_id} -> {old_assignment.account_id}")
        
        # Create new assignment
        return await self.assign_user_to_account(
            user_id, new_account_id, assigned_by, f"reassignment: {reason}"
        )
    
    def get_account_users(self, account_id: str) -> List[str]:
        """
        Get all users assigned to a specific account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List[str]: List of user IDs assigned to the account
        """
        return [
            assignment.user_id
            for assignment in self.assignments.values()
            if assignment.account_id == account_id and assignment.is_active
        ]
    
    def get_assignment_stats(self) -> Dict[str, Any]:
        """
        Get statistics about user assignments.
        
        Returns:
            Dict[str, Any]: Assignment statistics
        """
        active_assignments = [
            assignment for assignment in self.assignments.values()
            if assignment.is_active
        ]
        
        account_counts = {}
        for assignment in active_assignments:
            account_counts[assignment.account_id] = account_counts.get(assignment.account_id, 0) + 1
        
        return {
            'total_assignments': len(active_assignments),
            'accounts_in_use': len(account_counts),
            'account_distribution': account_counts,
            'assignment_strategy': self.assignment_strategy.value
        }
    
    async def _store_assignment_in_database(self, assignment: UserAccountAssignment) -> None:
        """
        Store assignment in database for persistence.
        
        Args:
            assignment: Assignment to store
        """
        try:
            # Simple file-based persistence for now
            import json
            import os
            
            assignments_file = "user_assignments.json"
            
            # Load existing assignments
            assignments_data = {}
            if os.path.exists(assignments_file):
                try:
                    with open(assignments_file, 'r') as f:
                        assignments_data = json.load(f)
                except:
                    assignments_data = {}
            
            # Add/update assignment
            assignments_data[assignment.user_id] = {
                'user_id': assignment.user_id,
                'account_id': assignment.account_id,
                'assigned_at': assignment.assigned_at.isoformat(),
                'assigned_by': assignment.assigned_by,
                'assignment_reason': assignment.assignment_reason,
                'is_active': assignment.is_active
            }
            
            # Save to file
            with open(assignments_file, 'w') as f:
                json.dump(assignments_data, f, indent=2)
            
            logger.info(f"Assignment stored in database: {assignment.user_id} -> {assignment.account_id}")
        except Exception as e:
            logger.error(f"Failed to store assignment in database: {e}")
    
    async def load_assignments_from_database(self) -> None:
        """
        Load existing assignments from database.
        """
        try:
            import json
            import os
            
            assignments_file = "user_assignments.json"
            
            if os.path.exists(assignments_file):
                with open(assignments_file, 'r') as f:
                    assignments_data = json.load(f)
                
                for user_id, data in assignments_data.items():
                    assignment = UserAccountAssignment(
                        user_id=data['user_id'],
                        account_id=data['account_id'],
                        assigned_at=datetime.fromisoformat(data['assigned_at']),
                        assigned_by=data['assigned_by'],
                        assignment_reason=data['assignment_reason'],
                        is_active=data['is_active']
                    )
                    self.assignments[assignment.user_id] = assignment
                
                logger.info(f"User assignments loaded from database: {len(assignments_data)} assignments")
            else:
                logger.info("No existing assignments file found")
        except Exception as e:
            logger.error(f"Failed to load assignments from database: {e}")
    
    def _load_assignments_sync(self) -> None:
        """
        Load existing assignments synchronously.
        """
        try:
            import json
            import os
            
            assignments_file = "user_assignments.json"
            
            if os.path.exists(assignments_file):
                with open(assignments_file, 'r') as f:
                    assignments_data = json.load(f)
                
                for user_id, data in assignments_data.items():
                    assignment = UserAccountAssignment(
                        user_id=data['user_id'],
                        account_id=data['account_id'],
                        assigned_at=datetime.fromisoformat(data['assigned_at']),
                        assigned_by=data['assigned_by'],
                        assignment_reason=data['assignment_reason'],
                        is_active=data['is_active']
                    )
                    self.assignments[assignment.user_id] = assignment
                
                logger.info(f"User assignments loaded: {len(assignments_data)} assignments")
            else:
                logger.info("No existing assignments file found")
        except Exception as e:
            logger.error(f"Failed to load assignments: {e}")
    
    def set_assignment_strategy(self, strategy: AccountAssignmentStrategy) -> None:
        """
        Set the assignment strategy.
        
        Args:
            strategy: Assignment strategy to use
        """
        self.assignment_strategy = strategy
        logger.info(f"Assignment strategy set to: {strategy.value}")