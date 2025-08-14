"""
Top model implementation for the DevCommV3 framework.

This module provides system orchestration and configuration management
for the entire simulation.
"""

import json
import yaml
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
import importlib
from .bus_model import BusModel
from .base_device import BaseDevice
from ..utils.trace_manager import TraceManager
from ..utils.event_constants import DeviceOperation


class TopModel:
    """Top-level system model for orchestrating the entire simulation."""

    def __init__(self, name: str = "SystemTop"):
        self.name = name
        self.buses: Dict[str, BusModel] = {}
        self.devices: Dict[str, BaseDevice] = {}
        self.configuration: Dict[str, Any] = {}
        self._initialized = False
        # Use the global shared trace manager
        self.trace_manager = TraceManager.get_global_instance()

    def load_configuration(self, config_path: str) -> None:
        """Load system configuration from file."""
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Support both JSON and YAML formats
        if config_file.suffix.lower() in ['.yaml', '.yml']:
            with open(config_file, 'r') as f:
                self.configuration = yaml.safe_load(f)
        elif config_file.suffix.lower() == '.json':
            with open(config_file, 'r') as f:
                self.configuration = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration format: {config_file.suffix}")

        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate the loaded configuration."""
        if 'system' not in self.configuration:
            raise ValueError("Configuration must contain 'system' section")

        system_config = self.configuration['system']

        if 'buses' not in system_config:
            raise ValueError("System configuration must contain 'buses' section")

        if 'devices' not in system_config:
            raise ValueError("System configuration must contain 'devices' section")

        # Validate bus configurations
        for bus_name, bus_config in system_config['buses'].items():
            if 'name' not in bus_config:
                bus_config['name'] = bus_name
                print(f">>>>>>bus_name = {bus_name}<<<<<<")

        # Validate device configurations
        for device_name, device_config in system_config['devices'].items():
            required_fields = ['device_type', 'base_address', 'size', 'master_id']
            for field in required_fields:
                if field not in device_config:
                    raise ValueError(f"Device {device_name} missing required field: {field}")

            if 'name' not in device_config:
                device_config['name'] = device_name
                print(f">>>>>>device_name = {device_name}<<<<<<")

            if 'bus' not in device_config:
                device_config['bus'] = 'main_bus'  # Default bus
                print(">>>>>>device_bus = 'main_bus'<<<<<<")

    def create_configuration(self, config_dict: Dict[str, Any]) -> None:
        """Create configuration from dictionary."""
        self.configuration = config_dict
        self._validate_configuration()

    def initialize_system(self) -> None:
        """Initialize the entire system based on configuration."""
        if self._initialized:
            raise RuntimeError("System already initialized")

        if not self.configuration:
            raise RuntimeError("No configuration loaded")

        system_config = self.configuration['system']

        # Log system initialization
        self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.INIT_START,
                                          {"buses_count": len(system_config['buses']),
                                           "devices_count": len(system_config['devices'])})

        # Create buses
        self._create_buses(system_config['buses'])

        # Create devices
        self._create_devices(system_config['devices'])

        # Connect devices to buses
        self._connect_devices_to_buses(system_config['devices'])

        self._initialized = True

        # Log successful initialization
        self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.INIT_COMPLETE,
                                          {"status": "success"})

    def _create_buses(self, bus_configs: Dict[str, Any]) -> None:
        """Create bus instances from configuration."""
        for bus_name, bus_config in bus_configs.items():
            bus = BusModel(bus_config['name'])
            self.buses[bus_name] = bus

    def _create_devices(self, device_configs: Dict[str, Any]) -> None:
        """Create device instances from configuration."""
        for device_name, device_config in device_configs.items():
            device = self._create_device_instance(device_config)
            self.devices[device_name] = device

    def _create_device_instance(self, device_config: Dict[str, Any]) -> BaseDevice:
        """Create a single device instance."""
        device_type = device_config['device_type']

        # Import device class dynamically
        device_class = self._get_device_class(device_type)

        # Extract common parameters
        name = device_config['name']
        base_address = device_config['base_address']
        size = device_config['size']
        master_id = device_config['master_id']

        # Handle address specification formats
        if isinstance(base_address, str):
            if base_address.startswith('0x'):
                base_address = int(base_address, 16)
            else:
                base_address = int(base_address)

        # Create device instance with additional parameters
        device_params = {
            'name': name,
            'base_address': base_address,
            'size': size,
            'master_id': master_id
        }

        # Add device-specific parameters
        for key, value in device_config.items():
            if key not in ['device_type', 'name', 'base_address', 'size', 'master_id', 'bus']:
                device_params[key] = value

        return device_class(**device_params)

    def _get_device_class(self, device_type: str) -> Type[BaseDevice]:
        """Get device class by type name."""
        # Map device types to their classes
        device_type_map = {
            'memory': 'devcomm.devices.memory_device.MemoryDevice',
            'dma': 'devcomm.devices.dma_device.DMADevice',
            'crc': 'devcomm.devices.crc_device.CRCDevice',
            'uart': 'devcomm.devices.uart_device.UARTDevice',
            'spi': 'devcomm.devices.spi_device.SPIDevice',
            'can': 'devcomm.devices.can_device.CANDevice',
            'gpio': 'devcomm.devices.gpio_device.GPIODevice',
            'timer': 'devcomm.devices.timer_device.TimerDevice'
        }

        if device_type not in device_type_map:
            raise ValueError(f"Unknown device type: {device_type}")

        module_path = device_type_map[device_type]
        module_name, class_name = module_path.rsplit('.', 1)

        try:
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Failed to import device class {module_path}: {e}")

    def _connect_devices_to_buses(self, device_configs: Dict[str, Any]) -> None:
        """Connect devices to their respective buses."""
        for device_name, device_config in device_configs.items():
            bus_name = device_config.get('bus', 'main_bus')

            if bus_name not in self.buses:
                raise ValueError(f"Bus {bus_name} not found for device {device_name}")

            if device_name not in self.devices:
                raise ValueError(f"Device {device_name} not created")

            bus = self.buses[bus_name]
            device = self.devices[device_name]

            bus.add_device(device)

    def get_bus(self, name: str) -> BusModel:
        """Get bus instance by name."""
        if name not in self.buses:
            raise KeyError(f"Bus {name} not found")
        return self.buses[name]

    def get_device(self, name: str) -> BaseDevice:
        """Get device instance by name."""
        if name not in self.devices:
            raise KeyError(f"Device {name} not found")
        return self.devices[name]

    def list_buses(self) -> List[str]:
        """Get list of all bus names."""
        return list(self.buses.keys())

    def list_devices(self) -> List[str]:
        """Get list of all device names."""
        return list(self.devices.keys())

    def reset_system(self) -> None:
        """Reset all devices in the system."""
        if not self._initialized:
            raise RuntimeError("System not initialized")

        # Log system reset
        self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.RESET_START, {})

        for device in self.devices.values():
            device.reset()

        # Clear trace from the shared manager (no need to clear per bus)
        # self.trace_manager.clear_trace()  # Uncomment if you want to clear on reset

        # Log reset completion
        self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.RESET_COMPLETE, {})

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        if not self._initialized:
            return {'initialized': False}

        return {
            'initialized': True,
            'name': self.name,
            'buses': {name: {'name': bus.name, 'devices': len(bus.devices)} for name, bus in self.buses.items()},
            'devices': {name: device.get_device_info() for name, device in self.devices.items()},
            'address_maps': {name: bus.get_address_map() for name, bus in self.buses.items()},
            'trace_summary': self.trace_manager.get_trace_summary()  # Unified trace summary
        }

    def save_configuration(self, config_path: str) -> None:
        """Save current configuration to file."""
        config_file = Path(config_path)

        if config_file.suffix.lower() in ['.yaml', '.yml']:
            with open(config_file, 'w') as f:
                yaml.dump(self.configuration, f, default_flow_style=False, indent=2)
        elif config_file.suffix.lower() == '.json':
            with open(config_file, 'w') as f:
                json.dump(self.configuration, f, indent=2)
        else:
            raise ValueError(f"Unsupported configuration format: {config_file.suffix}")

    def is_initialized(self) -> bool:
        """Check if system is initialized."""
        return self._initialized

    def shutdown(self) -> None:
        """Shutdown the system."""
        if not self._initialized:
            return

        # Log shutdown
        self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.SHUTDOWN_START, {})

        # Disable all devices
        for device in self.devices.values():
            device.disable()

        # Clear all buses
        for bus in self.buses.values():
            device_list = list(bus.devices.keys())
            for master_id in device_list:
                bus.remove_device(master_id)

        # Clear trace from the shared manager (optionally)
        # self.trace_manager.clear_trace()  # Uncomment if you want to clear on shutdown

        self._initialized = False

        # Log shutdown completion
        self.trace_manager.log_device_event(self.name, self.name, DeviceOperation.SHUTDOWN_COMPLETE, {})

    def enable_trace(self, module_name: Optional[str] = None) -> None:
        """Enable tracing for the system or specific module."""
        if module_name is None:
            # Enable global tracing (affects the shared trace manager)
            self.trace_manager.enable_global_trace()
        else:
            # Enable tracing for specific module (affects the shared trace manager)
            self.trace_manager.enable_module_trace(module_name)

    def disable_trace(self, module_name: Optional[str] = None) -> None:
        """Disable tracing for the system or specific module."""
        if module_name is None:
            # Disable global tracing (affects the shared trace manager)
            self.trace_manager.disable_global_trace()
        else:
            # Disable tracing for specific module (affects the shared trace manager)
            self.trace_manager.disable_module_trace(module_name)

    def clear_trace(self, module_name: Optional[str] = None) -> None:
        """Clear trace data for the system or specific module."""
        # Since all components use the same trace manager, clear once
        self.trace_manager.clear_trace(module_name)

    def get_trace_summary(self, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive trace summary from the unified buffer."""
        # Since all components use the same trace manager, get unified summary
        return self.trace_manager.get_trace_summary(module_name)

    def save_trace_to_file(self, filename: str, module_name: Optional[str] = None,
                          format: str = 'json') -> None:
        """Save unified trace data to a single file."""
        # Save all trace events to a single file
        self.trace_manager.save_trace_to_file(filename, module_name, format)

    def get_trace_manager(self) -> TraceManager:
        """Get the top-level trace manager."""
        return self.trace_manager

    def get_all_trace_modules(self) -> List[str]:
        """Get list of all modules that have generated trace events."""
        # Since all components use the same trace manager, get modules from shared buffer
        return self.trace_manager.get_module_list()

    def __str__(self) -> str:
        return f"TopModel({self.name}, {len(self.buses)} buses, {len(self.devices)} devices)"

    def __repr__(self) -> str:
        return (f"TopModel(name='{self.name}', buses={len(self.buses)}, "
                f"devices={len(self.devices)}, initialized={self._initialized})")