"""
Bus model implementation for the DevCommV3 framework.

This module provides the bus simulation with device management, address validation,
read/write operations, and IRQ handling.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
import threading
import time
from dataclasses import dataclass
from .base_device import BaseDevice
from ..utils.trace_manager import TraceManager
from ..utils.event_constants import EventType, BusOperation


class BusModel:
    """Simulates a system bus with device management and transaction handling."""

    def __init__(self, name: str = "SystemBus"):
        self.name = name
        self.devices: Dict[int, BaseDevice] = {}  # master_id -> device
        self.address_map: List[Tuple[int, int, BaseDevice]] = []  # (start, end, device)
        self.lock = threading.RLock()
        # Use the global shared trace manager
        self.trace_manager = TraceManager.get_global_instance()
        self.irq_handlers: Dict[int, Dict[int, Callable]] = {}  # master_id -> {irq_index -> handler}
        self.external_irq_sender: Optional[Callable[[int], None]] = None  # Global external IRQ sender
        self.max_log_size = 10000

    def add_device(self, device: BaseDevice) -> None:
        """Add a device to the bus."""
        with self.lock:
            # Check if master_id is already taken
            if device.master_id in self.devices:
                raise ValueError(f"Master ID {device.master_id} already assigned to device "
                               f"{self.devices[device.master_id].name}")

            # Check for address space overlap
            device_start, device_end = device.get_address_range()
            for start, end, existing_device in self.address_map:
                if not (device_end < start or device_start > end):
                    raise ValueError(f"Address space overlap: device {device.name} "
                                   f"(0x{device_start:08X}-0x{device_end:08X}) overlaps with "
                                   f"device {existing_device.name} (0x{start:08X}-0x{end:08X})")

            # Add device to bus
            self.devices[device.master_id] = device
            self.address_map.append((device_start, device_end, device))
            self.address_map.sort(key=lambda x: x[0])  # Sort by start address

            # Register bus with device
            device.set_bus(self)

    def remove_device(self, master_id: int) -> None:
        """Remove a device from the bus."""
        with self.lock:
            if master_id not in self.devices:
                raise KeyError(f"No device with master ID {master_id}")

            device = self.devices[master_id]

            # Remove from devices dict
            del self.devices[master_id]

            # Remove from address map
            self.address_map = [(start, end, dev) for start, end, dev in self.address_map
                              if dev.master_id != master_id]

            # Unregister bus from device
            device.set_bus(None)

    def _find_device_by_address(self, address: int) -> Optional[BaseDevice]:
        """Find device that handles the given address."""
        for start, end, device in self.address_map:
            if start <= address <= end:
                return device
        return None

    def read(self, master_id: int, address: int, width: int = 4) -> int:
        """Read from the bus at the specified address."""
        start_time = time.time()

        with self.lock:
            # Verify master ID
            if master_id not in self.devices:
                error_msg = f"Invalid master ID {master_id}"
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.READ, 0, width,
                                    "UNKNOWN", False, error_msg)
                raise ValueError(error_msg)

            # Find target device
            target_device = self._find_device_by_address(address)
            if target_device is None:
                error_msg = f"No device found for address 0x{address:08X}"
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.READ, 0, width,
                                    "NONE", False, error_msg)
                raise KeyError(error_msg)

            try:
                # Perform read operation
                value = target_device.read(address, width)
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.READ, value, width,
                                    target_device.name, True)
                return value

            except Exception as e:
                error_msg = str(e)
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.READ, 0, width,
                                    target_device.name, False, error_msg)
                raise

    def write(self, master_id: int, address: int, value: int, width: int = 4) -> None:
        """Write to the bus at the specified address."""
        start_time = time.time()

        with self.lock:
            # Verify master ID
            if master_id not in self.devices:
                error_msg = f"Invalid master ID {master_id}"
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.WRITE, value, width,
                                    "UNKNOWN", False, error_msg)
                raise ValueError(error_msg)

            # Find target device
            target_device = self._find_device_by_address(address)
            if target_device is None:
                error_msg = f"No device found for address 0x{address:08X}"
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.WRITE, value, width,
                                    "NONE", False, error_msg)
                raise KeyError(error_msg)

            try:
                # Perform write operation
                target_device.write(address, value, width)
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.WRITE, value, width,
                                    target_device.name, True)

            except Exception as e:
                error_msg = str(e)
                self.trace_manager.log_bus_transaction(self.name, master_id, address, BusOperation.WRITE, value, width,
                                    target_device.name, False, error_msg)
                raise

    def send_irq(self, master_id: int, irq_index: int) -> None:
        """Send an interrupt request."""
        with self.lock:
            if master_id not in self.devices:
                raise ValueError(f"Invalid master ID {master_id}")

            device = self.devices[master_id]

            # Log IRQ event
            self.trace_manager.log_irq_event(self.name, master_id, irq_index, device.name)

            # Call internal IRQ handler if registered
            if master_id in self.irq_handlers and irq_index in self.irq_handlers[master_id]:
                handler = self.irq_handlers[master_id][irq_index]
                try:
                    handler(master_id, irq_index, device)
                except Exception as e:
                    print(f"IRQ handler error: {e}")

            # Call external IRQ sender if registered
            if self.external_irq_sender is not None:
                try:
                    self.external_irq_sender(irq_index)
                except Exception as e:
                    print(f"External IRQ sender error: {e}")

    def register_irq_handler(self, master_id: int, irq_index: int, handler: Callable) -> None:
        """Register an IRQ handler for a specific device and IRQ index."""
        with self.lock:
            if master_id not in self.irq_handlers:
                self.irq_handlers[master_id] = {}
            self.irq_handlers[master_id][irq_index] = handler

    def unregister_irq_handler(self, master_id: int, irq_index: int) -> None:
        """Unregister an IRQ handler."""
        with self.lock:
            if master_id in self.irq_handlers and irq_index in self.irq_handlers[master_id]:
                del self.irq_handlers[master_id][irq_index]

    def register_send_irq(self, sender_func: Callable[[int, int, BaseDevice], None]) -> None:
        """Register a global external IRQ sender function.

        Args:
            sender_func: Function with signature sender_func(master_id, irq_index, device) -> None
                        This function will be called whenever send_irq is called for any device
        """
        with self.lock:
            self.external_irq_sender = sender_func
            print(f"Global external IRQ sender registered")

    def unregister_send_irq(self) -> None:
        """Unregister the global external IRQ sender."""
        with self.lock:
            if self.external_irq_sender is not None:
                self.external_irq_sender = None
                print(f"Global external IRQ sender unregistered")
            else:
                print(f"No global external IRQ sender registered")

    def has_external_irq_sender(self) -> bool:
        """Check if a global external IRQ sender is registered.

        Returns:
            True if an external IRQ sender is registered, False otherwise
        """
        with self.lock:
            return self.external_irq_sender is not None

    def _log_transaction(self, timestamp: float, master_id: int, address: int,
                        operation: str, value: int, width: int, device_name: str,
                        success: bool, error_message: Optional[str] = None) -> None:
        """Log a bus transaction - compatibility method."""
        # This method is kept for compatibility but delegates to TraceManager
        self.trace_manager.log_bus_transaction(self.name, master_id, address, 
                                             operation, value, width, device_name, 
                                             success, error_message)

    def enable_trace(self) -> None:
        """Enable transaction tracing."""
        self.trace_manager.enable_module_trace(self.name)

    def disable_trace(self) -> None:
        """Disable transaction tracing."""
        self.trace_manager.disable_module_trace(self.name)

    def clear_trace(self) -> None:
        """Clear transaction and IRQ logs."""
        with self.lock:
            self.trace_manager.clear_trace(self.name)

    def get_trace_summary(self) -> Dict[str, Any]:
        """Get a summary of bus activity."""
        with self.lock:
            summary = self.trace_manager.get_trace_summary(self.name)
            
            # Extract bus-specific events for compatibility
            bus_events = self.trace_manager.get_events(self.name)
            bus_transactions = [e for e in bus_events if e.event_type == EventType.BUS_TRANSACTION]
            irq_events = [e for e in bus_events if e.event_type == EventType.IRQ_EVENT]
            
            successful_transactions = sum(1 for e in bus_transactions 
                                        if e.event_data.get('success', False))

            return {
                'total_transactions': len(bus_transactions),
                'successful_transactions': successful_transactions,
                'failed_transactions': len(bus_transactions) - successful_transactions,
                'total_irqs': len(irq_events),
                'devices_count': len(self.devices),
                'trace_enabled': summary.get('enabled', True)
            }

    def save_trace_to_file(self, filename: str, format: str = 'json') -> None:
        """Save trace data to file."""
        self.trace_manager.save_trace_to_file(filename, self.name, format)

    def get_trace_manager(self) -> TraceManager:
        """Get the trace manager instance."""
        return self.trace_manager

    def get_device_list(self) -> List[Dict[str, Any]]:
        """Get list of all connected devices."""
        with self.lock:
            return [device.get_device_info() for device in self.devices.values()]

    def get_address_map(self) -> List[Dict[str, Any]]:
        """Get the current address map."""
        with self.lock:
            return [
                {
                    'start_address': f"0x{start:08X}",
                    'end_address': f"0x{end:08X}",
                    'device_name': device.name,
                    'master_id': device.master_id
                }
                for start, end, device in self.address_map
            ]

    def __str__(self) -> str:
        return f"BusModel({self.name}, {len(self.devices)} devices)"

    def __repr__(self) -> str:
        return f"BusModel(name='{self.name}', devices={len(self.devices)})"