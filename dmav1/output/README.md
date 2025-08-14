# DMA Device Model v1.1

## Overview

This DMA (Direct Memory Access) device model implementation provides a comprehensive simulation of a 16-channel DMA controller based on the AC7840 series specifications.

## Features

### Core Functionality
- **16 Independent Channels**: Each channel can be configured independently for different transfer operations
- **Multiple Transfer Modes**: 
  - Memory-to-Memory
  - Peripheral-to-Memory 
  - Memory-to-Peripheral
  - Peripheral-to-Peripheral
- **Priority-based Arbitration**: 4 priority levels (Very High, High, Medium, Low)
- **Data Transfer Sizes**: Support for 8-bit, 16-bit, and 32-bit transfers
- **Circular Buffer Mode**: Continuous transfer operation for streaming applications

### Advanced Features  
- **Address Offset Support**: Configurable source and destination address offsets
- **Status and Error Reporting**: Comprehensive error detection and status flags
- **Interrupt Generation**: Half-complete, complete, and error interrupts
- **Error Injection**: Testing capability for fault simulation
- **Thread-safe Operations**: Multi-threaded transfer execution with proper synchronization

### Register Interface
The device implements all registers from the DMA register map specification:
- `DMA_TOP_RST` (0x000): Global reset control
- `CHANNELx_STATUS_xx`: Channel status registers 
- `CHANNELx_CONFIG_xx`: Channel configuration registers
- `CHANNELx_*_ADDR_xx`: Source/destination address registers
- `CHANNELx_LENGTH_xx`: Transfer length registers
- And many more channel-specific registers

## Usage

### Basic Usage

```python
from dmav1.output.dma_device import DMADevice

# Create DMA device instance
dma = DMADevice(
    name="MainDMA",
    base_address=0x40000000,
    size=0x1000,
    master_id=1,
    num_channels=16
)

# Register interrupt callback
def interrupt_handler(channel_id, interrupt_type):
    print(f"DMA Channel {channel_id}: {interrupt_type}")

dma.register_irq_callback(interrupt_handler)
```

### Channel Configuration

```python
# Configure channel 0 for memory-to-memory transfer
channel_id = 0
base_addr = 0x40000000
channel_offset = channel_id * 0x40

# Configuration register (direction=0, circular=0, word transfers, high priority)
config_addr = base_addr + 0x50 + channel_offset
config_value = (0 << 7) | (0 << 6) | (2 << 4) | (2 << 2) | 2
dma.write(config_addr, config_value, 4)

# Set transfer parameters
length_addr = base_addr + 0x54 + channel_offset
source_addr = base_addr + 0x58 + channel_offset
dest_addr = base_addr + 0x60 + channel_offset

dma.write(length_addr, 1024, 4)          # Transfer 1024 bytes
dma.write(source_addr, 0x20000000, 4)    # Source address
dma.write(dest_addr, 0x20001000, 4)      # Destination address

# Enable channel to start transfer
enable_addr = base_addr + 0x64 + channel_offset
dma.write(enable_addr, 0x00000001, 4)
```

### Circular Buffer Mode

```python
# Configure for circular mode
config_value = (0 << 7) | (1 << 6) | (2 << 4) | (2 << 2) | 1  # circular=1
dma.write(config_addr, config_value, 4)

# Set circular buffer boundaries
sstart_addr = base_addr + 0x58 + channel_offset
send_addr = base_addr + 0x5C + channel_offset  
dstart_addr = base_addr + 0x60 + channel_offset

dma.write(sstart_addr, 0x20000000, 4)    # Source start
dma.write(send_addr, 0x20000400, 4)      # Source end  
dma.write(dstart_addr, 0x20001000, 4)    # Destination start

# Enable channel - will run continuously until disabled
dma.write(enable_addr, 0x00000001, 4)
```

### Error Injection (Testing)

```python
# Enable error injection for testing
dma.enable_error_injection(channel_id, "bus_error")

# Configure and start transfer (will trigger injected error)
# ... configuration code ...

# Check for error
channel_info = dma.get_channel_info(channel_id)
if channel_info['state'] == 'ERROR':
    print("Error injection successful")

# Disable error injection
dma.disable_error_injection(channel_id)
```

## Register Map

### Channel Register Layout
Each channel occupies 64 bytes (0x40) in the register space:

| Offset | Register Name | Description |
|--------|---------------|-------------|
| 0x40+n*0x40 | CHANNELx_STATUS | Channel status flags |
| 0x50+n*0x40 | CHANNELx_CONFIG | Channel configuration |
| 0x54+n*0x40 | CHANNELx_LENGTH | Transfer length |
| 0x58+n*0x40 | CHANNELx_SSTART_ADDR | Source start address |
| 0x5C+n*0x40 | CHANNELx_SEND_ADDR | Source end address |
| 0x60+n*0x40 | CHANNELx_DSTART_ADDR | Destination start address |
| 0x64+n*0x40 | CHANNELx_ENABLE | Channel enable control |
| 0x68+n*0x40 | CHANNELx_DATA_TRANS_NUM | Data transferred count |
| 0x74+n*0x40 | CHANNELx_ADDR_OFFSET | Address offset configuration |
| 0x78+n*0x40 | CHANNELx_DMAMUX_CFG | DMAMUX configuration |

### Configuration Register Fields

**CHANNELx_CONFIG Register (Offset: 0x50+n*0x40)**
- Bit 7: CHAN_DIR (0=Peripheral→Memory, 1=Memory→Peripheral)
- Bit 6: CHAN_CIRCULAR (0=Disable, 1=Enable circular mode)
- Bits 5-4: DSIZE (00=8bit, 01=16bit, 10=32bit)
- Bits 3-2: SSIZE (00=8bit, 01=16bit, 10=32bit)
- Bits 1-0: CHAN_PRIORITY (00=Low, 01=Medium, 10=High, 11=Very High)

**CHANNELx_STATUS Register (Offset: 0x40+n*0x40)**
- Bit 0: FINISH (Transfer complete flag)
- Bit 1: HALF_FINISH (Half transfer complete flag)
- Bit 2: DBE (Destination bus error)
- Bit 3: SBE (Source bus error)
- Bit 4: DOE (Destination offset error)
- Bit 5: SOE (Source offset error)
- Bit 6: DAE (Destination address error)
- Bit 7: SAE (Source address error)
- Bit 8: CLE (Channel length error)

## Testing

Run the comprehensive test suite:

```bash
cd /path/to/DeviceModel_V1.1
python3 dmav1/output/test_dma_device.py
```

The test suite validates:
- Basic register operations
- Channel configuration and management
- Transfer operations (all modes)
- Priority-based arbitration
- Circular buffer functionality
- Error conditions and injection
- Concurrent channel operations
- Interrupt generation

## Implementation Details

### Thread Safety
- All channel operations are protected by per-channel locks
- Register manager uses thread-safe operations
- Arbiter queue handles concurrent transfer requests

### Performance Considerations
- Background transfer execution using worker threads
- Priority-based arbitration for optimal throughput
- Minimal blocking operations in register interface

### Error Handling
- Comprehensive error detection and reporting
- Graceful handling of invalid configurations
- Error injection capability for robust testing

## Compliance

This implementation follows the device model generation rules specified in `autogen_rules/device_model_gen.txt`:
- Inherits from BaseDevice base class
- Uses RegisterManager for register management
- Supports IRQ callbacks
- Integrates DMA interface capabilities
- Provides error injection functionality
- Supports multiple instantiation
- Integrates trace functionality

## Future Enhancements

Potential areas for enhancement:
- Integration with memory device interfaces
- DMAMUX trigger functionality
- Advanced debug and monitoring features
- Performance optimization for large transfers
- Additional error recovery mechanisms