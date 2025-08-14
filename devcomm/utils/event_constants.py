"""
Centralized event type and operation constants for the DevCommV3 framework.

This module provides unified definitions for all event types and operations
used throughout the trace system, improving maintainability and consistency.
"""

from typing import Final, List


class EventType:
    """Event type constants for trace events."""
    BUS_TRANSACTION: Final[str] = 'BUS_TRANSACTION'
    IRQ_EVENT: Final[str] = 'IRQ_EVENT'
    DEVICE_EVENT: Final[str] = 'DEVICE_EVENT'
    
    @classmethod
    def all_types(cls) -> List[str]:
        """Get all available event types."""
        return [cls.BUS_TRANSACTION, cls.IRQ_EVENT, cls.DEVICE_EVENT]


class BusOperation:
    """Bus operation constants for bus transactions."""
    READ: Final[str] = 'READ'
    WRITE: Final[str] = 'WRITE'
    
    @classmethod
    def all_operations(cls) -> List[str]:
        """Get all available bus operations."""
        return [cls.READ, cls.WRITE]


class DeviceOperation:
    """Device operation constants for device events."""
    # Basic read/write operations
    READ: Final[str] = 'READ'
    WRITE: Final[str] = 'WRITE'
    READ_FAILED: Final[str] = 'READ_FAILED'
    WRITE_FAILED: Final[str] = 'WRITE_FAILED'
    
    # Device control operations
    RESET: Final[str] = 'RESET'
    ENABLE: Final[str] = 'ENABLE'
    DISABLE: Final[str] = 'DISABLE'
    
    # Interrupt operations
    IRQ_TRIGGER: Final[str] = 'IRQ_TRIGGER'
    IRQ_TRIGGER_FAILED: Final[str] = 'IRQ_TRIGGER_FAILED'
    
    # Lifecycle operations
    INIT_START: Final[str] = 'INIT_START'
    INIT_COMPLETE: Final[str] = 'INIT_COMPLETE'
    RESET_START: Final[str] = 'RESET_START'
    RESET_COMPLETE: Final[str] = 'RESET_COMPLETE'
    SHUTDOWN_START: Final[str] = 'SHUTDOWN_START'
    SHUTDOWN_COMPLETE: Final[str] = 'SHUTDOWN_COMPLETE'
    
    @classmethod
    def all_operations(cls) -> List[str]:
        """Get all available device operations."""
        return [
            cls.READ, cls.WRITE, cls.READ_FAILED, cls.WRITE_FAILED,
            cls.RESET, cls.ENABLE, cls.DISABLE,
            cls.IRQ_TRIGGER, cls.IRQ_TRIGGER_FAILED,
            cls.INIT_START, cls.INIT_COMPLETE,
            cls.RESET_START, cls.RESET_COMPLETE,
            cls.SHUTDOWN_START, cls.SHUTDOWN_COMPLETE
        ]