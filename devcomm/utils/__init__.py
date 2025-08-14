"""Utilities for the DevCommV3 framework."""

from .event_constants import DeviceOperation
from .model_interface import ModelInterface
from .trace_manager import TraceManager
from .external_devices import (
    SimulatedUARTDevice, SimulatedSPIDevice, SimulatedCANDevice,
    RandomDataGenerator, EchoDevice
)

__all__ = [
    'DeviceOperation',
    'ModelInterface', 
    'TraceManager',
    'SimulatedUARTDevice',
    'SimulatedSPIDevice', 
    'SimulatedCANDevice',
    'RandomDataGenerator',
    'EchoDevice'
]