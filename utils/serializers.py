"""
Database serialization utilities for DynamoDB compatibility.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Union
from dataclasses import asdict, is_dataclass
from enum import Enum


class DynamoDBSerializer:
    """Handles serialization/deserialization for DynamoDB compatibility."""
    
    @staticmethod
    def serialize_item(obj: Any) -> Dict[str, Any]:
        """
        Serialize a Python object to DynamoDB-compatible format.
        
        Args:
            obj: Object to serialize (dataclass, dict, etc.)
            
        Returns:
            DynamoDB-compatible dictionary
        """
        if is_dataclass(obj):
            # Convert dataclass to dict first
            data = asdict(obj)
        elif isinstance(obj, dict):
            data = obj.copy()
        else:
            # Try to convert to dict
            data = obj.__dict__ if hasattr(obj, '__dict__') else str(obj)
        
        return DynamoDBSerializer._serialize_value(data)
    
    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Recursively serialize a value to DynamoDB format."""
        if value is None:
            return None
        elif isinstance(value, datetime):
            # Convert datetime to ISO string
            return value.isoformat()
        elif isinstance(value, Decimal):
            # DynamoDB handles Decimal natively
            return value
        elif isinstance(value, Enum):
            # Convert enum to its value
            return value.value
        elif isinstance(value, (int, float, str, bool)):
            # Native types
            return value
        elif isinstance(value, dict):
            # Recursively serialize dictionary
            return {k: DynamoDBSerializer._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple, set)):
            # Recursively serialize sequences
            return [DynamoDBSerializer._serialize_value(item) for item in value]
        else:
            # Convert unknown types to string
            return str(value)
    
    @staticmethod
    def deserialize_item(data: Dict[str, Any], target_class=None) -> Dict[str, Any]:
        """
        Deserialize DynamoDB item back to Python objects.
        
        Args:
            data: DynamoDB item data
            target_class: Optional target class for type hints
            
        Returns:
            Deserialized dictionary
        """
        result = {}
        
        for key, value in data.items():
            # Skip DynamoDB metadata keys
            if key.startswith(('pk', 'sk', 'gsi', 'ttl')):
                continue
                
            result[key] = DynamoDBSerializer._deserialize_value(value)
        
        return result
    
    @staticmethod
    def _deserialize_value(value: Any) -> Any:
        """Recursively deserialize a value from DynamoDB format."""
        if value is None:
            return None
        elif isinstance(value, str):
            # Try to parse as datetime
            if DynamoDBSerializer._is_iso_datetime(value):
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    return value
            return value
        elif isinstance(value, Decimal):
            # Convert Decimal to appropriate type
            if value % 1 == 0:
                # It's a whole number, convert to int
                return int(value)
            else:
                # Keep as Decimal for precision
                return value
        elif isinstance(value, dict):
            # Recursively deserialize dictionary
            return {k: DynamoDBSerializer._deserialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            # Recursively deserialize list
            return [DynamoDBSerializer._deserialize_value(item) for item in value]
        else:
            # Return as-is for native types
            return value
    
    @staticmethod
    def _is_iso_datetime(value: str) -> bool:
        """Check if string looks like an ISO datetime."""
        if not isinstance(value, str) or len(value) < 19:
            return False
        
        # Simple check for ISO format patterns
        iso_patterns = [
            'T',  # ISO separator
            '-',  # Date separators
            ':'   # Time separators
        ]
        
        return all(pattern in value for pattern in iso_patterns[:2])


def serialize_for_dynamodb(obj: Any) -> Dict[str, Any]:
    """Convenience function to serialize objects for DynamoDB."""
    return DynamoDBSerializer.serialize_item(obj)


def deserialize_from_dynamodb(data: Dict[str, Any], target_class=None) -> Dict[str, Any]:
    """Convenience function to deserialize from DynamoDB."""
    return DynamoDBSerializer.deserialize_item(data, target_class)


# Utility functions for common operations
def datetime_to_dynamodb(dt: datetime) -> str:
    """Convert datetime to DynamoDB string format."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def datetime_from_dynamodb(dt_str: str) -> datetime:
    """Convert DynamoDB string back to datetime."""
    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))


def enum_to_dynamodb(enum_value: Enum) -> str:
    """Convert enum to DynamoDB string."""
    return enum_value.value


def decimal_to_dynamodb(decimal_value: Union[float, int, str]) -> Decimal:
    """Convert number to DynamoDB Decimal."""
    return Decimal(str(decimal_value))