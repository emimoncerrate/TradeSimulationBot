"""
Comprehensive AI-powered risk analysis service for Jain Global Slack Trading Bot.

This module provides sophisticated risk assessment capabilities using Amazon Bedrock Claude
for trade analysis, portfolio impact evaluation, and compliance checking. It implements
advanced prompt engineering for financial risk analysis and provides comprehensive
risk scoring and recommendations.

The service integrates with portfolio data, market conditions, and regulatory requirements
to provide actionable risk insights for trading decisions.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
from prometheus_client import Counter, Histogram, Gauge
import structlog

from config.settings import get_config
from models.trade import Trade
from models.portfolio import Portfolio, Position
from services.market_data import MarketQuote, get_market_data_service


class RiskAnalysisError(Exception):
    """Custom exception for risk analysis service errors."""
    
    def __init__(self, message: str, trade_id: str = None, error_code: str = None):
        self.message = message
        self.trade_id = trade_id
        self.error_code = error_code
        super().__init__(self.message)


class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Risk analysis categories."""
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    MARKET_CONDITIONS = "market_conditions"
    POSITION_SIZE = "position_size"
    CORRELATION = "correlation"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"


@dataclass
class RiskFactor:
    """Individual risk factor assessment."""
    category: RiskCategory
    level: RiskLevel
    score: float  # 0.0 to 1.0
    description: str
    impact: str
    recommendation: str
    confidence: float = 1.0  # AI confidence in assessment
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert risk factor to dictionary."""
        return {
            'category': self.category.value,
            'level': self.level.value,
            'score': self.score,
            'description': self.description,
            'impact': self.impact,
            'recommendation': self.recommendation,
            'confidence': self.confidence
        }


@dataclass
class RiskAnalysis:
    """Comprehensive risk analysis result."""
    trade_id: str
    symbol: str
    trade_type: str
    quantity: int
    price: Decimal
    
    # Overall risk assessment
    overall_risk_level: RiskLevel
    overall_risk_score: float  # 0.0 to 1.0
    
    # Individual risk factors
    risk_factors: List[RiskFactor] = field(default_factory=list)
    
    # Analysis metadata
    analysis_summary: str = ""
    portfolio_impact: str = ""
    market_context: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    # Technical details
    generated_at: datetime = field(default_factory=datetime.utcnow)
    analysis_duration_ms: Optional[float] = None
    model_used: str = "claude-3-sonnet"
    confidence_score: float = 1.0
    
    # Compliance and regulatory
    regulatory_flags: List[str] = field(default_factory=list)
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    
    def __post_init__(self):
        """Validate analysis data after initialization."""
        if not (0.0 <= self.overall_risk_score <= 1.0):
            raise ValueError(f"Risk score must be between 0.0 and 1.0: {self.overall_risk_score}")
        
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0: {self.confidence_score}")
    
    @property
    def is_high_risk(self) -> bool:
        """Check if trade is considered high risk."""
        return self.overall_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    @property
    def requires_confirmation(self) -> bool:
        """Check if trade requires additional confirmation."""
        return self.is_high_risk or self.requires_approval
    
    def get_risk_factors_by_category(self, category: RiskCategory) -> List[RiskFactor]:
        """Get risk factors for a specific category."""
        return [rf for rf in self.risk_factors if rf.category == category]
    
    def get_high_risk_factors(self) -> List[RiskFactor]:
        """Get all high and critical risk factors."""
        return [rf for rf in self.risk_factors if rf.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for serialization."""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'quantity': self.quantity,
            'price': float(self.price),
            'overall_risk_level': self.overall_risk_level.value,
            'overall_risk_score': self.overall_risk_score,
            'risk_factors': [rf.to_dict() for rf in self.risk_factors],
            'analysis_summary': self.analysis_summary,
            'portfolio_impact': self.portfolio_impact,
            'market_context': self.market_context,
            'recommendations': self.recommendations,
            'generated_at': self.generated_at.isoformat(),
            'analysis_duration_ms': self.analysis_duration_ms,
            'model_used': self.model_used,
            'confidence_score': self.confidence_score,
            'regulatory_flags': self.regulatory_flags,
            'requires_approval': self.requires_approval,
            'approval_reason': self.approval_reason,
            'is_high_risk': self.is_high_risk,
            'requires_confirmation': self.requires_confirmation
        }


class PromptTemplate:
    """Risk analysis prompt templates for different scenarios."""
    
    BASE_ANALYSIS_PROMPT = """
You are a sophisticated financial risk analyst for Jain Global, an investment management firm. 
Analyze the following trade proposal and provide a comprehensive risk assessment.

TRADE DETAILS:
- Symbol: {symbol}
- Trade Type: {trade_type}
- Quantity: {quantity:,}
- Price: ${price}
- Total Value: ${total_value:,.2f}

CURRENT PORTFOLIO:
{portfolio_summary}

MARKET DATA:
{market_data}

ANALYSIS REQUIREMENTS:
1. Assess overall risk level (LOW, MEDIUM, HIGH, CRITICAL)
2. Identify specific risk factors across categories:
   - Concentration risk
   - Volatility risk
   - Liquidity risk
   - Market conditions
   - Position sizing
   - Correlation risk
   - Regulatory considerations
3. Evaluate portfolio impact
4. Provide actionable recommendations
5. Flag any regulatory or compliance concerns

Respond in JSON format with the following structure:
{{
    "overall_risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "overall_risk_score": 0.0-1.0,
    "analysis_summary": "Brief summary of key findings",
    "portfolio_impact": "Description of how this trade affects the portfolio",
    "market_context": "Current market conditions relevant to this trade",
    "risk_factors": [
        {{
            "category": "concentration|volatility|liquidity|market_conditions|position_size|correlation|regulatory|operational",
            "level": "LOW|MEDIUM|HIGH|CRITICAL",
            "score": 0.0-1.0,
            "description": "What the risk is",
            "impact": "Potential impact if risk materializes",
            "recommendation": "How to mitigate this risk",
            "confidence": 0.0-1.0
        }}
    ],
    "recommendations": ["List of actionable recommendations"],
    "regulatory_flags": ["Any regulatory or compliance concerns"],
    "requires_approval": true/false,
    "approval_reason": "Why approval is needed (if applicable)",
    "confidence_score": 0.0-1.0
}}

Be thorough but concise. Focus on actionable insights and material risks.
"""

    CONCENTRATION_ANALYSIS_PROMPT = """
Analyze concentration risk for this trade:

CURRENT POSITIONS IN {symbol}:
{current_position}

PROPOSED TRADE:
{trade_details}

PORTFOLIO COMPOSITION:
{portfolio_breakdown}

Assess:
1. Single-name concentration after trade
2. Sector/industry concentration
3. Geographic concentration
4. Correlation with existing positions

Provide specific concentration metrics and thresholds.
"""

    VOLATILITY_ANALYSIS_PROMPT = """
Analyze volatility risk for {symbol}:

HISTORICAL VOLATILITY:
{volatility_data}

MARKET CONDITIONS:
{market_conditions}

POSITION SIZE:
{position_details}

Assess:
1. Historical volatility patterns
2. Implied volatility levels
3. VaR impact on portfolio
4. Stress test scenarios

Provide quantitative risk metrics where possible.
"""


class RiskAnalysisService:
    """
    Comprehensive AI-powered risk analysis service.
    
    Provides sophisticated risk assessment using Amazon Bedrock Claude for trade analysis,
    portfolio impact evaluation, and compliance checking. Implements advanced caching,
    error handling, and fallback mechanisms for high availability.
    """
    
    def __init__(self, market_data_service=None):
        """Initialize risk analysis service with configuration and dependencies."""
        self.config = get_config()
        self.logger = structlog.get_logger(__name__)
        self.market_data_service = market_data_service
        
        # Initialize AWS Bedrock client
        self.bedrock_client: Optional[boto3.client] = None
        self.is_mock_mode = False
        
        # Initialize caching
        self.analysis_cache: Dict[str, Tuple[RiskAnalysis, datetime]] = {}
        
        # Metrics
        self.analysis_counter = Counter(
            'risk_analysis_requests_total',
            'Total risk analysis requests',
            ['risk_level', 'status']
        )
        self.analysis_duration = Histogram(
            'risk_analysis_duration_seconds',
            'Risk analysis duration',
            ['analysis_type']
        )
        self.cache_hit_counter = Counter(
            'risk_analysis_cache_hits_total',
            'Cache hits for risk analysis'
        )
        self.ai_error_counter = Counter(
            'risk_analysis_ai_errors_total',
            'AI service errors by type',
            ['error_type']
        )
        
        # Risk thresholds and configuration
        self.risk_thresholds = {
            'concentration_limit': 0.10,  # 10% max single position
            'sector_limit': 0.25,  # 25% max sector exposure
            'volatility_threshold': 0.30,  # 30% annualized volatility
            'liquidity_threshold': 1000000,  # $1M daily volume minimum
            'position_size_limit': 0.05  # 5% max single trade of portfolio
        }
        
        self.logger.info("RiskAnalysisService initialized",
                        model_id=self.config.aws.bedrock_model_id,
                        region=self.config.aws.region)
    
    async def initialize(self) -> None:
        """Initialize async resources and AWS clients."""
        try:
            # Check if we should use mock mode for development
            # Use mock mode if: in development AND (no AWS creds OR placeholder AWS creds)
            aws_key = os.getenv('AWS_ACCESS_KEY_ID', '')
            is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
            has_placeholder_aws = aws_key in ['', 'mock-access-key-id', 'your-aws-access-key']
            
            if is_development and has_placeholder_aws:
                self.logger.info("RiskAnalysisService initialized in MOCK MODE for development")
                self.is_mock_mode = True
                return
            
            # Initialize Bedrock client
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.config.aws.region
            )
            
            # Skip Bedrock connectivity test for now - model access needs to be enabled
            self.logger.info("Skipping Bedrock connectivity test - model access needs to be enabled")
            
            self.logger.info("RiskAnalysisService initialization complete")
            
        except Exception as e:
            # If connection fails in development, fall back to mock mode
            if is_development:
                self.logger.warning(f"Failed to connect to AWS Bedrock, falling back to mock mode: {e}")
                self.is_mock_mode = True
            else:
                # In production, fail loudly
                self.logger.error("Failed to initialize RiskAnalysisService", error=str(e))
                raise e
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.analysis_cache.clear()
        self.logger.info("RiskAnalysisService cleanup complete") 
   
    async def analyze_trade_risk(
        self, 
        trade: Trade, 
        portfolio: Portfolio, 
        market_quote: Optional[MarketQuote] = None,
        use_cache: bool = True
    ) -> RiskAnalysis:
        """
        Perform comprehensive risk analysis for a proposed trade.
        
        Args:
            trade: Trade object to analyze
            portfolio: Current portfolio state
            market_quote: Current market data (optional, will fetch if not provided)
            use_cache: Whether to use cached analysis if available
            
        Returns:
            RiskAnalysis: Comprehensive risk assessment
            
        Raises:
            Exception: If analysis fails after retries
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(trade, portfolio)
        
        # Check cache first if enabled
        if use_cache:
            cached_analysis = self._get_cached_analysis(cache_key)
            if cached_analysis:
                self.cache_hit_counter.inc()
                self.logger.debug("Cache hit for risk analysis", trade_id=trade.trade_id)
                return cached_analysis
        
        try:
            # Fetch market data if not provided
            if market_quote is None:
                market_data_service = await get_market_data_service()
                market_quote = await market_data_service.get_quote(trade.symbol)
            
            # Perform comprehensive analysis
            analysis = await self._perform_comprehensive_analysis(trade, portfolio, market_quote)
            
            # Calculate analysis duration
            analysis.analysis_duration_ms = (time.time() - start_time) * 1000
            
            # Cache the result
            self._cache_analysis(cache_key, analysis)
            
            # Update metrics
            self.analysis_counter.labels(
                risk_level=analysis.overall_risk_level.value,
                status='success'
            ).inc()
            self.analysis_duration.labels(analysis_type='comprehensive').observe(time.time() - start_time)
            
            self.logger.info("Risk analysis completed",
                           trade_id=trade.trade_id,
                           symbol=trade.symbol,
                           risk_level=analysis.overall_risk_level.value,
                           risk_score=analysis.overall_risk_score,
                           duration_ms=analysis.analysis_duration_ms)
            
            return analysis
            
        except Exception as e:
            self.ai_error_counter.labels(error_type=type(e).__name__).inc()
            self.analysis_counter.labels(risk_level='unknown', status='error').inc()
            self.logger.error("Risk analysis failed", 
                            trade_id=trade.trade_id, 
                            error=str(e))
            
            # Return fallback analysis for critical system availability
            return self._create_fallback_analysis(trade, str(e))
    
    async def analyze_portfolio_impact(
        self, 
        trade: Trade, 
        portfolio: Portfolio
    ) -> Dict[str, Any]:
        """
        Analyze the impact of a trade on portfolio composition and risk metrics.
        
        Args:
            trade: Proposed trade
            portfolio: Current portfolio
            
        Returns:
            Dict containing portfolio impact analysis
        """
        try:
            # Calculate position changes
            current_position = portfolio.get_position(trade.symbol)
            new_quantity = (current_position.quantity if current_position else 0) + trade.quantity
            
            # Calculate portfolio metrics before and after
            current_value = portfolio.total_value
            trade_value = trade.quantity * trade.price
            new_portfolio_value = current_value + trade_value
            
            # Calculate concentration metrics
            position_concentration = abs(new_quantity * trade.price) / new_portfolio_value
            
            # Analyze sector/industry impact
            sector_impact = await self._analyze_sector_impact(trade, portfolio)
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_portfolio_risk_metrics(trade, portfolio)
            
            impact_analysis = {
                'position_changes': {
                    'symbol': trade.symbol,
                    'current_quantity': current_position.quantity if current_position else 0,
                    'new_quantity': new_quantity,
                    'quantity_change': trade.quantity,
                    'current_value': float(current_position.current_value) if current_position else 0.0,
                    'new_position_value': float(new_quantity * trade.price),
                    'value_change': float(trade_value)
                },
                'portfolio_metrics': {
                    'current_portfolio_value': float(current_value),
                    'new_portfolio_value': float(new_portfolio_value),
                    'trade_percentage': float(abs(trade_value) / current_value * 100),
                    'position_concentration': float(position_concentration * 100)
                },
                'sector_impact': sector_impact,
                'risk_metrics': risk_metrics,
                'concentration_flags': self._check_concentration_limits(position_concentration)
            }
            
            self.logger.debug("Portfolio impact analysis completed",
                            trade_id=trade.trade_id,
                            position_concentration=position_concentration)
            
            return impact_analysis
            
        except Exception as e:
            self.logger.error("Portfolio impact analysis failed", 
                            trade_id=trade.trade_id, 
                            error=str(e))
            return {'error': str(e), 'analysis_available': False}
    
    async def get_risk_recommendations(
        self, 
        analysis: RiskAnalysis, 
        user_role: str = "trader"
    ) -> List[str]:
        """
        Get role-specific risk recommendations based on analysis.
        
        Args:
            analysis: Risk analysis result
            user_role: User role (trader, analyst, portfolio_manager)
            
        Returns:
            List of role-specific recommendations
        """
        recommendations = []
        
        # Base recommendations from analysis
        recommendations.extend(analysis.recommendations)
        
        # Role-specific recommendations
        if user_role == "portfolio_manager":
            if analysis.is_high_risk:
                recommendations.append("Consider reducing position size or implementing hedging strategy")
                recommendations.append("Review portfolio-wide risk limits and concentration guidelines")
            
            if analysis.requires_approval:
                recommendations.append("This trade requires Portfolio Manager approval before execution")
        
        elif user_role == "trader":
            if analysis.is_high_risk:
                recommendations.append("Consult with Portfolio Manager before proceeding")
                recommendations.append("Consider using limit orders to control execution risk")
            
            # Add execution-specific recommendations
            high_vol_factors = analysis.get_risk_factors_by_category(RiskCategory.VOLATILITY)
            if high_vol_factors:
                recommendations.append("Consider splitting large orders to reduce market impact")
        
        elif user_role == "analyst":
            # Add research-focused recommendations
            recommendations.append("Review latest research reports and analyst coverage")
            if analysis.overall_risk_score > 0.7:
                recommendations.append("Conduct additional fundamental analysis before proceeding")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    async def _perform_comprehensive_analysis(
        self, 
        trade: Trade, 
        portfolio: Portfolio, 
        market_quote: MarketQuote
    ) -> RiskAnalysis:
        """
        Perform comprehensive AI-powered risk analysis using Amazon Bedrock.
        
        Args:
            trade: Trade to analyze
            portfolio: Current portfolio
            market_quote: Market data
            
        Returns:
            RiskAnalysis: Complete analysis result
        """
        if not self.bedrock_client:
            raise Exception("Bedrock client not initialized")
        
        # Prepare analysis context
        context = await self._prepare_analysis_context(trade, portfolio, market_quote)
        
        # Generate analysis prompt
        prompt = self._build_analysis_prompt(trade, context)
        
        # Call Amazon Bedrock Claude
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self._invoke_bedrock_model,
                prompt
            )
            
            # Parse AI response
            analysis_data = self._parse_ai_response(response)
            
            # Build RiskAnalysis object
            analysis = self._build_risk_analysis(trade, analysis_data, context)
            
            # Perform additional validation and enrichment
            analysis = await self._enrich_analysis(analysis, portfolio, market_quote)
            
            return analysis
            
        except Exception as e:
            self.logger.error("Bedrock analysis failed", error=str(e))
            raise e
    
    def _invoke_bedrock_model(self, prompt: str) -> Dict[str, Any]:
        """
        Invoke Amazon Bedrock Claude model synchronously.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            Model response
        """
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=self.config.aws.bedrock_model_id,
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        return response_body
    
    async def _prepare_analysis_context(
        self, 
        trade: Trade, 
        portfolio: Portfolio, 
        market_quote: MarketQuote
    ) -> Dict[str, Any]:
        """
        Prepare comprehensive context for risk analysis.
        
        Args:
            trade: Trade to analyze
            portfolio: Current portfolio
            market_quote: Market data
            
        Returns:
            Analysis context dictionary
        """
        # Portfolio summary
        portfolio_summary = {
            'total_value': float(portfolio.total_value),
            'position_count': len(portfolio.positions),
            'cash_balance': float(portfolio.cash_balance),
            'top_positions': [
                {
                    'symbol': pos.symbol,
                    'value': float(pos.current_value),
                    'percentage': float(pos.current_value / portfolio.total_value * 100)
                }
                for pos in sorted(portfolio.positions, key=lambda p: p.current_value, reverse=True)[:5]
            ]
        }
        
        # Current position in trade symbol
        current_position = portfolio.get_position(trade.symbol)
        position_info = {
            'has_position': current_position is not None,
            'current_quantity': current_position.quantity if current_position else 0,
            'current_value': float(current_position.current_value) if current_position else 0.0,
            'average_cost': float(current_position.average_cost) if current_position else 0.0
        }
        
        # Market context
        market_context = {
            'current_price': float(market_quote.current_price),
            'price_change': float(market_quote.price_change) if market_quote.price_change else 0.0,
            'price_change_percent': float(market_quote.price_change_percent) if market_quote.price_change_percent else 0.0,
            'volume': market_quote.volume,
            'market_status': market_quote.market_status.value,
            'data_quality': market_quote.data_quality.value
        }
        
        # Trade details
        trade_context = {
            'symbol': trade.symbol,
            'trade_type': trade.trade_type,
            'quantity': trade.quantity,
            'price': float(trade.price),
            'total_value': float(abs(trade.quantity * trade.price)),
            'trade_percentage': float(abs(trade.quantity * trade.price) / portfolio.total_value * 100)
        }
        
        return {
            'portfolio': portfolio_summary,
            'position': position_info,
            'market': market_context,
            'trade': trade_context,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _build_analysis_prompt(self, trade: Trade, context: Dict[str, Any]) -> str:
        """
        Build comprehensive analysis prompt for AI model.
        
        Args:
            trade: Trade to analyze
            context: Analysis context
            
        Returns:
            Formatted prompt string
        """
        # Format portfolio summary
        portfolio_summary = f"""
Total Portfolio Value: ${context['portfolio']['total_value']:,.2f}
Position Count: {context['portfolio']['position_count']}
Cash Balance: ${context['portfolio']['cash_balance']:,.2f}

Top Positions:
{chr(10).join([f"- {pos['symbol']}: ${pos['value']:,.2f} ({pos['percentage']:.1f}%)" for pos in context['portfolio']['top_positions']])}
"""
        
        # Format market data
        market_data = f"""
Current Price: ${context['market']['current_price']:.2f}
Price Change: ${context['market']['price_change']:.2f} ({context['market']['price_change_percent']:.2f}%)
Volume: {context['market']['volume']:,} (if available)
Market Status: {context['market']['market_status']}
Data Quality: {context['market']['data_quality']}
"""
        
        # Calculate total trade value
        total_value = abs(trade.quantity * trade.price)
        
        return PromptTemplate.BASE_ANALYSIS_PROMPT.format(
            symbol=trade.symbol,
            trade_type=trade.trade_type.upper(),
            quantity=trade.quantity,
            price=trade.price,
            total_value=total_value,
            portfolio_summary=portfolio_summary.strip(),
            market_data=market_data.strip()
        )
    
    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate AI model response.
        
        Args:
            response: Raw response from Bedrock
            
        Returns:
            Parsed analysis data
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            # Extract content from Claude response
            content = response.get('content', [])
            if not content:
                raise ValueError("Empty response from AI model")
            
            # Get the text content
            text_content = content[0].get('text', '')
            if not text_content:
                raise ValueError("No text content in AI response")
            
            # Parse JSON from the response
            # Look for JSON block in the response
            json_start = text_content.find('{')
            json_end = text_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in AI response")
            
            json_text = text_content[json_start:json_end]
            analysis_data = json.loads(json_text)
            
            # Validate required fields
            required_fields = [
                'overall_risk_level', 'overall_risk_score', 'analysis_summary',
                'portfolio_impact', 'risk_factors', 'recommendations'
            ]
            
            for field in required_fields:
                if field not in analysis_data:
                    raise ValueError(f"Missing required field in AI response: {field}")
            
            # Validate risk level
            valid_risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
            if analysis_data['overall_risk_level'] not in valid_risk_levels:
                raise ValueError(f"Invalid risk level: {analysis_data['overall_risk_level']}")
            
            # Validate risk score
            risk_score = analysis_data['overall_risk_score']
            if not isinstance(risk_score, (int, float)) or not (0.0 <= risk_score <= 1.0):
                raise ValueError(f"Invalid risk score: {risk_score}")
            
            return analysis_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in AI response: {e}")
        except Exception as e:
            self.logger.error("Failed to parse AI response", error=str(e))
            raise ValueError(f"Failed to parse AI response: {e}")
    
    def _build_risk_analysis(
        self, 
        trade: Trade, 
        analysis_data: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> RiskAnalysis:
        """
        Build RiskAnalysis object from AI response and context.
        
        Args:
            trade: Original trade
            analysis_data: Parsed AI response
            context: Analysis context
            
        Returns:
            RiskAnalysis object
        """
        # Parse risk factors
        risk_factors = []
        for factor_data in analysis_data.get('risk_factors', []):
            try:
                risk_factor = RiskFactor(
                    category=RiskCategory(factor_data['category']),
                    level=RiskLevel(factor_data['level']),
                    score=float(factor_data['score']),
                    description=factor_data['description'],
                    impact=factor_data['impact'],
                    recommendation=factor_data['recommendation'],
                    confidence=float(factor_data.get('confidence', 1.0))
                )
                risk_factors.append(risk_factor)
            except (ValueError, KeyError) as e:
                self.logger.warning("Invalid risk factor in AI response", error=str(e))
                continue
        
        # Build analysis object
        analysis = RiskAnalysis(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            trade_type=trade.trade_type,
            quantity=trade.quantity,
            price=trade.price,
            overall_risk_level=RiskLevel(analysis_data['overall_risk_level']),
            overall_risk_score=float(analysis_data['overall_risk_score']),
            risk_factors=risk_factors,
            analysis_summary=analysis_data.get('analysis_summary', ''),
            portfolio_impact=analysis_data.get('portfolio_impact', ''),
            market_context=analysis_data.get('market_context', ''),
            recommendations=analysis_data.get('recommendations', []),
            regulatory_flags=analysis_data.get('regulatory_flags', []),
            requires_approval=analysis_data.get('requires_approval', False),
            approval_reason=analysis_data.get('approval_reason'),
            confidence_score=float(analysis_data.get('confidence_score', 1.0))
        )
        
        return analysis
    
    async def _enrich_analysis(
        self, 
        analysis: RiskAnalysis, 
        portfolio: Portfolio, 
        market_quote: MarketQuote
    ) -> RiskAnalysis:
        """
        Enrich analysis with additional quantitative checks and validations.
        
        Args:
            analysis: Base analysis from AI
            portfolio: Portfolio data
            market_quote: Market data
            
        Returns:
            Enriched analysis
        """
        # Add quantitative risk checks
        trade_value = abs(analysis.quantity * analysis.price)
        portfolio_percentage = trade_value / portfolio.total_value
        
        # Check concentration limits
        if portfolio_percentage > self.risk_thresholds['position_size_limit']:
            concentration_factor = RiskFactor(
                category=RiskCategory.CONCENTRATION,
                level=RiskLevel.HIGH if portfolio_percentage > 0.10 else RiskLevel.MEDIUM,
                score=min(1.0, portfolio_percentage / 0.10),
                description=f"Trade represents {portfolio_percentage:.1%} of portfolio",
                impact="High concentration increases portfolio volatility and single-name risk",
                recommendation="Consider reducing position size or implementing hedging",
                confidence=1.0
            )
            analysis.risk_factors.append(concentration_factor)
        
        # Check if analysis needs approval override
        if analysis.overall_risk_score > 0.8 and not analysis.requires_approval:
            analysis.requires_approval = True
            analysis.approval_reason = "High risk score requires Portfolio Manager approval"
        
        # Update overall risk level if quantitative checks suggest higher risk
        if portfolio_percentage > 0.15 and analysis.overall_risk_level == RiskLevel.LOW:
            analysis.overall_risk_level = RiskLevel.MEDIUM
            analysis.overall_risk_score = max(analysis.overall_risk_score, 0.6)
        
        return analysis
    
    async def _analyze_sector_impact(self, trade: Trade, portfolio: Portfolio) -> Dict[str, Any]:
        """Analyze sector concentration impact of the trade."""
        # This would typically integrate with a sector classification service
        # For now, return basic analysis
        return {
            'sector_exposure_change': 0.0,
            'sector_concentration_risk': 'low',
            'sector_correlation_risk': 'medium'
        }
    
    async def _calculate_portfolio_risk_metrics(
        self, 
        trade: Trade, 
        portfolio: Portfolio
    ) -> Dict[str, Any]:
        """Calculate portfolio-level risk metrics."""
        # Basic risk metrics calculation
        trade_value = abs(trade.quantity * trade.price)
        portfolio_value = portfolio.total_value
        
        return {
            'portfolio_beta': 1.0,  # Would calculate from historical data
            'portfolio_volatility': 0.15,  # Would calculate from positions
            'var_impact': trade_value * 0.02,  # Simplified VaR calculation
            'concentration_ratio': trade_value / portfolio_value
        }
    
    def _check_concentration_limits(self, position_concentration: float) -> List[str]:
        """Check position concentration against limits."""
        flags = []
        
        if position_concentration > self.risk_thresholds['concentration_limit']:
            flags.append(f"Position exceeds concentration limit of {self.risk_thresholds['concentration_limit']:.1%}")
        
        if position_concentration > 0.20:
            flags.append("Position represents significant portfolio concentration")
        
        return flags
    
    def _create_fallback_analysis(self, trade: Trade, error_message: str) -> RiskAnalysis:
        """
        Create fallback risk analysis when AI service fails.
        
        Args:
            trade: Trade to analyze
            error_message: Error that occurred
            
        Returns:
            Basic fallback analysis
        """
        # Create conservative fallback analysis
        fallback_analysis = RiskAnalysis(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            trade_type=trade.trade_type,
            quantity=trade.quantity,
            price=trade.price,
            overall_risk_level=RiskLevel.MEDIUM,  # Conservative default
            overall_risk_score=0.6,  # Conservative default
            analysis_summary=f"Risk analysis service unavailable. Using fallback assessment. Error: {error_message}",
            portfolio_impact="Unable to assess portfolio impact due to service unavailability",
            market_context="Market context analysis unavailable",
            recommendations=[
                "Risk analysis service is currently unavailable",
                "Consider postponing trade until full analysis is available",
                "Consult with Portfolio Manager before proceeding"
            ],
            model_used="fallback",
            confidence_score=0.3  # Low confidence for fallback
        )
        
        # Add basic risk factor
        basic_risk_factor = RiskFactor(
            category=RiskCategory.OPERATIONAL,
            level=RiskLevel.MEDIUM,
            score=0.6,
            description="Risk analysis service unavailable",
            impact="Unable to assess comprehensive risk factors",
            recommendation="Wait for service recovery or seek manual analysis",
            confidence=0.3
        )
        fallback_analysis.risk_factors.append(basic_risk_factor)
        
        return fallback_analysis
    
    def _generate_cache_key(self, trade: Trade, portfolio: Portfolio) -> str:
        """Generate cache key for analysis."""
        # Create hash from trade details and portfolio state
        key_data = f"{trade.symbol}:{trade.trade_type}:{trade.quantity}:{trade.price}:{portfolio.total_value}:{len(portfolio.positions)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_analysis(self, cache_key: str) -> Optional[RiskAnalysis]:
        """Get cached analysis if available and not stale."""
        if cache_key in self.analysis_cache:
            analysis, cached_time = self.analysis_cache[cache_key]
            
            # Check if cache is still valid (5 minutes)
            if datetime.utcnow() - cached_time < timedelta(minutes=5):
                return analysis
            else:
                # Remove stale entry
                del self.analysis_cache[cache_key]
        
        return None
    
    def _cache_analysis(self, cache_key: str, analysis: RiskAnalysis) -> None:
        """Cache analysis result."""
        self.analysis_cache[cache_key] = (analysis, datetime.utcnow())
        
        # Limit cache size
        if len(self.analysis_cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self.analysis_cache.keys(),
                key=lambda k: self.analysis_cache[k][1]
            )[:20]
            
            for old_key in oldest_keys:
                del self.analysis_cache[old_key]
    
    async def _test_bedrock_connectivity(self) -> None:
        """Test Bedrock service connectivity."""
        try:
            # Simple test call to verify connectivity
            test_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": "Test"}]
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.bedrock_client.invoke_model(
                    modelId=self.config.aws.bedrock_model_id,
                    body=json.dumps(test_body),
                    contentType='application/json',
                    accept='application/json'
                )
            )
            
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                self.logger.info("Bedrock connectivity test successful")
            else:
                raise Exception(f"Bedrock test failed with status {response['ResponseMetadata']['HTTPStatusCode']}")
                
        except Exception as e:
            self.logger.error("Bedrock connectivity test failed", error=str(e))
            raise e
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status for monitoring.
        
        Returns:
            Dict containing health status information
        """
        status = {
            'service': 'RiskAnalysisService',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'cache_size': len(self.analysis_cache),
            'bedrock_available': self.bedrock_client is not None
        }
        
        # Test Bedrock connectivity
        try:
            await self._test_bedrock_connectivity()
            status['bedrock_connectivity'] = True
        except Exception as e:
            status['bedrock_connectivity'] = False
            status['bedrock_error'] = str(e)
            status['status'] = 'degraded'
        
        return status


# Global service instance
_risk_analysis_service: Optional[RiskAnalysisService] = None


async def get_risk_analysis_service() -> RiskAnalysisService:
    """
    Get or create the global RiskAnalysisService instance.
    
    Returns:
        RiskAnalysisService: Initialized service instance
    """
    global _risk_analysis_service
    
    if _risk_analysis_service is None:
        _risk_analysis_service = RiskAnalysisService()
        await _risk_analysis_service.initialize()
    
    return _risk_analysis_service


async def cleanup_risk_analysis_service() -> None:
    """Clean up the global RiskAnalysisService instance."""
    global _risk_analysis_service
    
    if _risk_analysis_service:
        await _risk_analysis_service.cleanup()
        _risk_analysis_service = None