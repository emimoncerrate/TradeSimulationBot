"""
Async compatibility utilities for Python 3.8+

This module provides compatibility functions for async operations
that may not be available in older Python versions.
"""

import asyncio
import sys
import functools
from typing import TypeVar, Callable, Any

T = TypeVar('T')


async def to_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a function in a separate thread and await the result.
    
    This is a compatibility wrapper for asyncio.to_thread() which was
    added in Python 3.9. For Python 3.8, it uses loop.run_in_executor().
    
    Args:
        func: The function to run in a thread
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function call
        
    Example:
        result = await to_thread(some_blocking_function, arg1, arg2, kwarg=value)
    """
    if sys.version_info >= (3, 9):
        # Use native asyncio.to_thread for Python 3.9+
        return await asyncio.to_thread(func, *args, **kwargs)
    else:
        # Fallback for Python 3.8
        loop = asyncio.get_event_loop()
        if kwargs:
            # If there are kwargs, use functools.partial
            func_with_kwargs = functools.partial(func, **kwargs)
            return await loop.run_in_executor(None, func_with_kwargs, *args)
        else:
            # No kwargs, can use directly
            return await loop.run_in_executor(None, func, *args)


# Alias for convenience
run_in_thread = to_thread

