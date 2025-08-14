# DevCommV3 Device Models

This directory contains device implementations for the DevCommV3 framework.

## Available Devices

### MemoryDevice (`memory_device.py`)
Simulates memory devices (RAM/ROM) with the following features:
- Byte, halfword, and word access methods
- DMA interface support for high-speed transfers
- Hex dump functionality for debugging
- File I/O operations (load/save memory contents)
- Configurable as read-only (ROM) or read-write (RAM)
- Memory initialization with configurable values

**Usage:**
```python
memory = MemoryDevice("MainRAM", 0x20000000, 0x10000, 1)
memory.write_word(0x100, 0xDEADBEEF)
value = memory.read_word(0x100)
print(memory.hex_dump(0x100, 16))
```

### DMADevice (`dma_device.py`)
Multi-channel DMA controller with:
- Configurable number of channels (default 4)
- Transfer modes: mem2mem, mem2peri, peri2mem, peri2peri
- Register-based configuration interface
- Interrupt generation on transfer completion/error
- Thread-safe operations with per-channel locking
- Real-time transfer progress monitoring

**Transfer Modes:**
- **mem2mem**: Memory-to-memory transfers
- **mem2peri**: Memory-to-peripheral transfers (for feeding data to devices)
- **peri2mem**: Peripheral-to-memory transfers (for reading device data)

**Usage:**
```python
dma = DMADevice("DMA", 0x40000000, 0x1000, 3, num_channels=4)
# Configure through registers or direct API
# Supports automatic transfer execution in background threads
```

### CRCDevice (`crc_device.py`)
Hardware CRC calculation unit supporting:
- Multiple CRC algorithms: CRC-8, CRC-16, CRC-16-CCITT, CRC-32, CRC-32C
- Configurable polynomials and initial values
- Register-based data input interface
- DMA interface for high-speed data processing
- Interrupt generation on calculation completion
- Direct calculation methods for testing

**Supported Algorithms:**
- CRC-8 (polynomial: 0x07)
- CRC-16 (polynomial: 0x8005)
- CRC-16-CCITT (polynomial: 0x1021)
- CRC-32 (polynomial: 0x04C11DB7)
- CRC-32C (polynomial: 0x1EDC6F41)

**Usage:**
```python
crc = CRCDevice("CRC", 0x40001000, 0x100, 4)
crc.load_data_for_calculation(b"Hello World")
result = crc.calculate_crc_direct(b"Hello World", 'crc16-ccitt')
```

## Adding New Devices

To add a new device type:

1. Create a new file in this directory (e.g., `uart_device.py`)
2. Import and inherit from `BaseDevice`
3. Implement required abstract methods:
   - `init()`: Initialize device registers and state
   - `_read_implementation()`: Handle read operations
   - `_write_implementation()`: Handle write operations
4. Add device-specific functionality
5. Update the device type mapping in `TopModel._get_device_class()`

Example skeleton:
```python
from ..core.base_device import BaseDevice
from ..core.registers import RegisterType

class UARTDevice(BaseDevice):
    def __init__(self, name: str, base_address: int, size: int, master_id: int):
        super().__init__(name, base_address, size, master_id)
        
    def init(self) -> None:
        # Define registers
        self.register_manager.define_register(0x00, "DATA", RegisterType.READ_WRITE)
        self.register_manager.define_register(0x04, "STATUS", RegisterType.READ_ONLY)
        
    def _read_implementation(self, offset: int, width: int) -> int:
        return self.register_manager.read_register(self, offset, width)
        
    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        self.register_manager.write_register(self, offset, value, width)
```

## Device Configuration

Devices are configured through YAML/JSON files in the system configuration:

```yaml
devices:
  my_memory:
    device_type: "memory"
    name: "MainMemory"
    base_address: 0x20000000
    size: 0x10000
    master_id: 1
    bus: "main_bus"
    initial_value: 0x00
    read_only: false
```

## Testing

Each device should include comprehensive tests covering:
- Register operations
- Device-specific functionality
- DMA interface (if applicable)
- Interrupt generation
- Error conditions
- Thread safety