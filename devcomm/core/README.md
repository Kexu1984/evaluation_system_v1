# DevCommV3 Core Framework

This directory contains the core components of the DevCommV3 hardware simulation framework.

## Components

### RegisterManager (`registers.py`)
- Manages device registers with different access types (read-only, write-only, read-write, read-clear)
- Supports register callbacks for custom behavior on read/write operations
- Thread-safe operations with proper locking
- Register information and debugging capabilities

### BaseDevice (`base_device.py`)
- Abstract base class for all simulated devices
- Provides common functionality: address validation, bus communication, IRQ generation
- Includes DMA interface for devices that support DMA operations
- Thread-safe device operations with enable/disable functionality

### BusModel (`bus_model.py`)
- Simulates system bus with device management and address validation
- Transaction logging and tracing capabilities
- IRQ handling with configurable handlers
- Address space overlap detection
- Thread-safe operations with global locking

### TopModel (`top_model.py`)
- System orchestration and configuration management
- Dynamic device instantiation from configuration files
- YAML/JSON configuration support
- System initialization and shutdown procedures

## Usage Example

```python
from devcomm.core.top_model import TopModel

# Create and configure system
top_model = TopModel("MySystem")
top_model.load_configuration("config.yaml")
top_model.initialize_system()

# Access components
bus = top_model.get_bus('main_bus')
device = top_model.get_device('memory')

# Perform operations
bus.write(device.master_id, device.base_address, 0x12345678)
value = bus.read(device.master_id, device.base_address)
```