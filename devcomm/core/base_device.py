"""
Base device implementation for the DevCommV3 framework.

This module provides the abstract base class for all devices in the simulation.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import threading
from .registers import RegisterManager, RegisterType
from ..utils.trace_manager import TraceManager
from ..utils.event_constants import DeviceOperation


class DMAInterface:
    """Interface for devices that support DMA operations."""

    def __init__(self):
        self.dma_enabled = False
        self.dma_channel = None

    def enable_dma(self, channel_id: int) -> None:
        """Enable DMA for this device."""
        self.dma_enabled = True
        self.dma_channel = channel_id

    def disable_dma(self) -> None:
        """Disable DMA for this device."""
        self.dma_enabled = False
        self.dma_channel = None

    def is_dma_ready(self) -> bool:
        """Check if device is ready for DMA transfer."""
        return self.dma_enabled and self.dma_channel is not None


class BaseDevice(ABC):
    """Abstract base class for all devices."""

    def __init__(self, name: str, base_address: int, size: int, master_id: int):
        self.name = name
        self.base_address = base_address
        self.size = size
        self.master_id = master_id
        self.bus = None
        self.register_manager = RegisterManager()
        self.lock = threading.RLock()
        self._enabled = True
        # Use the global shared trace manager
        self.trace_manager = TraceManager.get_global_instance()

        # Initialize device-specific registers and state
        self.init()

    @abstractmethod
    def init(self) -> None:
        """Initialize device registers and state. Must be implemented by subclasses."""
        pass

    def set_bus(self, bus) -> None:
        """Register this device with a bus."""
        self.bus = bus

    def get_address_range(self) -> tuple[int, int]:
        """Get the address range for this device."""
        return (self.base_address, self.base_address + self.size - 1)

    def is_address_in_range(self, address: int) -> bool:
        """Check if an address falls within this device's range."""
        return self.base_address <= address < (self.base_address + self.size)

    def read(self, address: int, width: int = 4) -> int:
        """Read from device at the specified address."""
        with self.lock:
            if not self._enabled:
                self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.READ_FAILED, 
                                                  {"address": f"0x{address:08X}", 
                                                   "reason": "device_disabled"})
                raise RuntimeError(f"Device {self.name} is disabled")

            if not self.is_address_in_range(address):
                self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.READ_FAILED, 
                                                  {"address": f"0x{address:08X}", 
                                                   "reason": "address_out_of_range"})
                raise ValueError(f"Address 0x{address:08X} out of range for device {self.name}")

            offset = address - self.base_address
            value = self._read_implementation(offset, width)
            
            # Log successful read
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.READ, 
                                              {"address": f"0x{address:08X}", 
                                               "offset": f"0x{offset:08X}",
                                               "value": f"0x{value:08X}", 
                                               "width": width})
            return value

    def write(self, address: int, value: int, width: int = 4) -> None:
        """Write to device at the specified address."""
        with self.lock:
            if not self._enabled:
                self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.WRITE_FAILED, 
                                                  {"address": f"0x{address:08X}", 
                                                   "value": f"0x{value:08X}",
                                                   "reason": "device_disabled"})
                raise RuntimeError(f"Device {self.name} is disabled")

            if not self.is_address_in_range(address):
                self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.WRITE_FAILED, 
                                                  {"address": f"0x{address:08X}", 
                                                   "value": f"0x{value:08X}",
                                                   "reason": "address_out_of_range"})
                raise ValueError(f"Address 0x{address:08X} out of range for device {self.name}")

            offset = address - self.base_address
            self._write_implementation(offset, value, width)
            
            # Log successful write
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.WRITE, 
                                              {"address": f"0x{address:08X}", 
                                               "offset": f"0x{offset:08X}",
                                               "value": f"0x{value:08X}", 
                                               "width": width})

    @abstractmethod
    def _read_implementation(self, offset: int, width: int) -> int:
        """Device-specific read implementation. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """Device-specific write implementation. Must be implemented by subclasses."""
        pass

    def reset(self) -> None:
        """Reset device to initial state."""
        with self.lock:
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.RESET, {})
            self.register_manager.reset_all()
            self._reset_implementation()

    def _reset_implementation(self) -> None:
        """Device-specific reset implementation. Can be overridden by subclasses."""
        pass

    def enable(self) -> None:
        """Enable device operations."""
        with self.lock:
            self._enabled = True
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.ENABLE, {})

    def disable(self) -> None:
        """Disable device operations."""
        with self.lock:
            self._enabled = False
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.DISABLE, {})

    def is_enabled(self) -> bool:
        """Check if device is enabled."""
        return self._enabled

    def trigger_interrupt(self, irq_index: int = 0) -> None:
        """Trigger an interrupt through the bus."""
        if self.bus:
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.IRQ_TRIGGER, 
                                              {"irq_index": irq_index})
            print(f"Triggering interrupt {irq_index} on device {self.name}")
            self.bus.send_irq(self.master_id, irq_index)
        else:
            self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.IRQ_TRIGGER_FAILED, 
                                              {"irq_index": irq_index, "reason": "no_bus"})
            raise RuntimeError(f"Device {self.name} not connected to bus")

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        return {
            'name': self.name,
            'base_address': f"0x{self.base_address:08X}",
            'size': self.size,
            'end_address': f"0x{self.base_address + self.size - 1:08X}",
            'master_id': self.master_id,
            'enabled': self._enabled,
            'has_bus': self.bus is not None
        }

    def enable_trace(self) -> None:
        """Enable tracing for this device."""
        self.trace_manager.enable_module_trace(self.name)

    def disable_trace(self) -> None:
        """Disable tracing for this device."""
        self.trace_manager.disable_module_trace(self.name)

    def clear_trace(self) -> None:
        """Clear trace data for this device."""
        self.trace_manager.clear_trace(self.name)

    def get_trace_summary(self) -> Dict[str, Any]:
        """Get trace summary for this device."""
        return self.trace_manager.get_trace_summary(self.name)

    def save_trace_to_file(self, filename: str, format: str = 'json') -> None:
        """Save device trace data to file."""
        self.trace_manager.save_trace_to_file(filename, self.name, format)

    def get_trace_manager(self) -> TraceManager:
        """Get the device trace manager."""
        return self.trace_manager

    def dump_registers(self) -> Dict[int, Dict[str, Any]]:
        """Dump all register information."""
        return self.register_manager.list_registers()

    def __str__(self) -> str:
        return f"{self.name}(0x{self.base_address:08X}-0x{self.base_address + self.size - 1:08X})"

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"base_address=0x{self.base_address:08X}, size={self.size}, "
                f"master_id={self.master_id})")