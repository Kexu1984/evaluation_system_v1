# Python Device Model Generation Prompt

## ROLE
You are an expert Python device model architect specializing in hardware simulation and embedded system modeling.

## TASK
Generate complete Python device models that accurately simulate hardware behavior and integrate seamlessly with the devcomm framework.

## INPUT SPECIFICATIONS
- **Device Name**: `${device_name}` (placeholder for actual device name)
- **Input Source**: `${device_name}/input/` directory containing:
  - Device specification documents
  - Register map definitions (YAML/markdown)
  - Functional behavior descriptions
- **Output Location**: `${device_name}/output/`

## MANDATORY CLASS ARCHITECTURE

### Required Inheritance Hierarchy
```python
from devcomm.core.base_device import BaseDevice
from devcomm.core.registers import RegisterManager, RegisterType
from devcomm.utils.trace_manager import TraceManager

class <DeviceName>Device(BaseDevice):
    """
    Hardware simulation model for <DeviceName>
    MUST inherit from BaseDevice
    """

    def __init__(self, instance_id: int = 0, base_address: int = 0x40000000):
        super().__init__()
        self.instance_id = instance_id
        self.base_address = base_address
        self.register_manager = RegisterManager()
        self.trace = TraceManager(f"<DeviceName>_{instance_id}")

    def init(self) -> None:
        """MANDATORY: Device initialization"""
        self._define_registers()
        self._initialize_state()

    def _define_registers(self) -> None:
        """MANDATORY: Define all device registers"""
        # Implementation required

    def _initialize_state(self) -> None:
        """MANDATORY: Set initial device state"""
        # Implementation required
```

## MANDATORY BASE DEVICE METHODS

### 1. Register Access Methods (REQUIRED)
```python
def read(self, address: int, width: int = 4) -> int:
    """
    Register read operation
    MUST call RegisterManager and handle callbacks

    Args:
        address: Register address (absolute or offset-based)
        width: Access width in bytes (default: 4 for 32-bit)

    Returns:
        Register value
    """
    relative_address = address - self.base_address
    return self.register_manager.read(relative_address, width)

def write(self, address: int, value: int, width: int = 4) -> None:
    """
    Register write operation
    MUST call RegisterManager and trigger callbacks

    Args:
        address: Register address
        value: Value to write
        width: Access width in bytes
    """
    relative_address = address - self.base_address
    self.register_manager.write(relative_address, value, width)
```

### 2. Interrupt Callback Registration (REQUIRED)
```python
def register_irq_callback(self, callback: Callable[[int], None]) -> None:
    """
    Register interrupt callback function
    MUST store callback for interrupt generation

    Args:
        callback: Function to call when sending interrupts
                 Signature: callback(interrupt_id: int) -> None
    """
    self.irq_callback = callback

def _send_interrupt(self, interrupt_id: int) -> None:
    """Send interrupt to external system"""
    if hasattr(self, 'irq_callback') and self.irq_callback:
        self.irq_callback(interrupt_id)
```

## REGISTER MANAGER INTEGRATION

### Mandatory Register Definition Pattern
```python
def _define_registers(self) -> None:
    """Define all device registers with proper callbacks"""

    # Control register with write callback
    self.register_manager.define_register(
        offset=0x00,
        name="<DEVICE>_CTRL",
        register_type=RegisterType.READ_WRITE,
        reset_value=0x00000000,
        mask=0xFFFFFFFF,
        write_callback=self._ctrl_write_callback
    )

    # Status register with read callback
    self.register_manager.define_register(
        offset=0x04,
        name="<DEVICE>_STATUS",
        register_type=RegisterType.READ_ONLY,
        reset_value=0x00000000,
        read_callback=self._status_read_callback
    )

    # Data register (write-only for input)
    self.register_manager.define_register(
        offset=0x08,
        name="<DEVICE>_DATA",
        register_type=RegisterType.WRITE_ONLY,
        write_callback=self._data_write_callback
    )

    # Result register (read-only for output)
    self.register_manager.define_register(
        offset=0x0C,
        name="<DEVICE>_RESULT",
        register_type=RegisterType.READ_ONLY,
        read_callback=self._result_read_callback
    )
```

### Required Register Types Support
```python
from enum import Enum

class RegisterType(Enum):
    READ_WRITE = "RW"    # Normal read/write register
    READ_ONLY = "RO"     # Status/result registers
    WRITE_ONLY = "WO"    # Command/data input registers
    WRITE_CLEAR = "WC"   # Write 1 to clear bits
    READ_CLEAR = "RC"    # Read to clear register
```

## DEVICE-SPECIFIC CALLBACK IMPLEMENTATION

### Control Register Callback Pattern
```python
def _ctrl_write_callback(self, offset: int, value: int) -> None:
    """
    Handle control register writes
    MUST implement device-specific behavior
    """
    # Extract control bits
    enable_bit = (value >> 0) & 0x1
    mode_bits = (value >> 1) & 0x7
    start_bit = (value >> 31) & 0x1

    if enable_bit:
        self._enable_device()

    if start_bit:
        self._start_operation(mode_bits)

    # Update internal state
    self._update_device_state(value)
```

### Status Register Callback Pattern
```python
def _status_read_callback(self, offset: int, width: int) -> int:
    """
    Handle status register reads
    MUST return current device status
    """
    status = 0

    # Compose status bits
    if self._is_device_busy():
        status |= (1 << 0)  # BUSY bit

    if self._has_error():
        status |= (1 << 1)  # ERROR bit

    if self._operation_complete():
        status |= (1 << 2)  # DONE bit

    return status
```

## FUNCTIONAL IMPLEMENTATION REQUIREMENTS

### Device Operation Logic (MANDATORY)
```python
def _start_operation(self, mode: int) -> None:
    """
    Start device-specific operation
    MUST implement based on ${device_name}/input/ specifications
    """
    # Example for CRC device:
    if mode == 0:  # CRC32 mode
        self._start_crc32_calculation()
    elif mode == 1:  # CRC16 mode
        self._start_crc16_calculation()
    else:
        self._set_error_state("Invalid mode")

def _process_data(self, data: int) -> None:
    """
    Process input data according to device function
    MUST implement actual device algorithm
    """
    # Example: CRC calculation
    self.current_crc = self._calculate_crc_step(self.current_crc, data)

    # Check if operation complete
    if self._is_calculation_done():
        self._operation_complete = True
        self._send_interrupt(CRC_DONE_IRQ)
```

## IO INTERFACE SUPPORT (FOR EXTERNAL DEVICES)

### For devices like UART, SPI, CAN (REQUIRED)
```python
from devcomm.core.io_interface import IOInterface

class UARTDevice(BaseDevice):
    def __init__(self, instance_id: int = 0, base_address: int = 0x40001000):
        super().__init__()
        self.io_interface = IOInterface(device_name=f"UART_{instance_id}")

    def input(self, data: bytes, width: int = 1) -> None:
        """
        Handle external data input
        MUST process data and update registers
        """
        for byte in data:
            self._receive_byte(byte)

    def output(self, data: bytes, width: int = 1) -> None:
        """
        Send data to external interface
        MUST be called when TX register written
        """
        self.io_interface.send_data(data)

    def connect(self, external_device) -> None:
        """
        Connect external device for data exchange
        MUST create appropriate threads for data flow
        """
        if self._is_output_mode():
            # External device should create thread to receive data
            external_device.start_receive_thread(self.output)
        else:
            # This device creates thread to receive external data
            self._start_input_thread(external_device)
```

## MULTI-INSTANCE SUPPORT (MANDATORY)

### Instance Management
```python
# Support multiple instances of same device
class DeviceManager:
    _instances = {}

    @classmethod
    def create_device(cls, device_type: str, instance_id: int, base_address: int):
        """Create device instance with unique ID"""
        key = f"{device_type}_{instance_id}"
        if key not in cls._instances:
            if device_type == "UART":
                cls._instances[key] = UARTDevice(instance_id, base_address)
            elif device_type == "CRC":
                cls._instances[key] = CRCDevice(instance_id, base_address)
            # Add other device types...
        return cls._instances[key]
```

## ERROR INJECTION SUPPORT (REQUIRED)

### Fault Simulation Interface
```python
def inject_error(self, error_type: str, error_params: dict) -> None:
    """
    Inject errors for fault simulation
    MUST support error scenarios described in specifications

    Args:
        error_type: Type of error ("data_corruption", "clock_failure", etc.)
        error_params: Error-specific parameters
    """
    if error_type == "data_corruption":
        bit_position = error_params.get("bit_position", 0)
        self._inject_data_corruption(bit_position)
    elif error_type == "clock_failure":
        duration = error_params.get("duration", 0.1)
        self._inject_clock_failure(duration)
    elif error_type == "timeout":
        self._inject_timeout_error()
    else:
        raise ValueError(f"Unsupported error type: {error_type}")

def _inject_data_corruption(self, bit_position: int) -> None:
    """Simulate data corruption at specific bit position"""
    self.error_injection_active = True
    self.corrupted_bit_position = bit_position
    # Set error status register
    self._set_error_flag("DATA_CORRUPTION")
```

## COMPLETE DEVICE MODEL TEMPLATE

```python
"""
<DeviceName> Device Model
Generated from ${device_name}/input/ specifications
"""

from typing import Optional, Callable
from devcomm.core.base_device import BaseDevice
from devcomm.core.registers import RegisterManager, RegisterType
from devcomm.utils.trace_manager import TraceManager

class <DeviceName>Device(BaseDevice):
    """Hardware simulation model for <DeviceName>"""

    # Register offsets (from specification)
    CTRL_OFFSET = 0x00
    STATUS_OFFSET = 0x04
    DATA_OFFSET = 0x08
    RESULT_OFFSET = 0x0C

    # Interrupt IDs
    OPERATION_DONE_IRQ = 1
    ERROR_IRQ = 2

    def __init__(self, instance_id: int = 0, base_address: int = 0x40000000):
        super().__init__()
        self.instance_id = instance_id
        self.base_address = base_address
        self.register_manager = RegisterManager()
        self.trace = TraceManager(f"<DeviceName>_{instance_id}")

        # Device state
        self._device_enabled = False
        self._operation_active = False
        self._error_state = False
        self._result_ready = False

        # Error injection support
        self.error_injection_active = False

    def init(self) -> None:
        """Initialize device model"""
        self._define_registers()
        self._initialize_state()
        self.trace.info(f"<DeviceName> device {self.instance_id} initialized")

    def _define_registers(self) -> None:
        """Define all device registers"""
        # IMPLEMENT based on ${device_name}/input/ register map

    def _initialize_state(self) -> None:
        """Set initial device state"""
        # IMPLEMENT device-specific initialization

    # IMPLEMENT all callback methods
    # IMPLEMENT all device-specific functionality
    # IMPLEMENT error injection methods
```

## OUTPUT FILE REQUIREMENTS

### Mandatory Files to Generate
```
${device_name}/output/
├── <device>_device.py          # Main device model
├── python_<device>.py          # Python interface wrapper
└── test_<device>_device.py     # Comprehensive test suite
```

## VALIDATION REQUIREMENTS

### Generated Model Must Support:
- [ ] BaseDevice inheritance with all required methods
- [ ] RegisterManager integration with proper callbacks
- [ ] Multi-instance support with unique IDs
- [ ] Interrupt callback registration and generation
- [ ] Error injection for fault simulation
- [ ] IO interface (if external connectivity required)
- [ ] Complete functional behavior per specifications
- [ ] Trace logging for debugging

### Integration Requirements:
- [ ] Import devcomm framework components correctly
- [ ] Follow framework naming conventions
- [ ] Support dynamic base address configuration
- [ ] Thread-safe implementation (if multi-threading used)

---

**CRITICAL**: The generated device model will be used by C drivers through `libdrvintf.a`. All register operations must be compatible with the interface layer expectations.

## 🏗️ 架构要求 / Architecture Requirements

### 核心类结构 / Core Class Structure

```python
# 必需的继承层次 / Required inheritance hierarchy
class BaseDevice:
    """所有设备模型必须继承的基类 / Base class that all device models must inherit from"""

class RegisterManager:
    """所有设备的集中寄存器管理 / Centralized register management for all devices"""

class <DeviceName>Device(BaseDevice):
    """具体设备实现 / Specific device implementation"""
```

## 🔧 基础设备类规范 / Base Device Class Specification

### 必需方法 / Required Methods

#### 1. 初始化 / Initialization
```python
def init(self) -> None:
    """
    设备初始化包括：/ Device initialization including:
    - 寄存器定义和设置 / Register definitions and setup
    - 初始状态配置 / Initial state configuration
    - 内部数据结构初始化 / Internal data structure initialization
    - 默认配置应用 / Default configuration application
    """
```

#### 2. 寄存器访问 / Register Access
```python
def read(self, address: int, width: int = 4) -> int:
    """
    寄存器读操作 / Register read operation

    Args:
        address: 寄存器地址(绝对地址或基于偏移) / Register address (absolute or offset-based)
        width: 访问宽度(字节，默认4字节用于32位访问) / Access width in bytes (default: 4 for 32-bit access)

    Returns:
        寄存器值 / Register value
    """

def write(self, address: int, value: int, width: int = 4) -> None:
    """
    寄存器写操作 / Register write operation

    Args:
        address: 寄存器地址 / Register address
        value: 要写入的值 / Value to write
        width: 访问宽度(字节) / Access width in bytes
    """
```

#### 3. 中断回调注册 / Interrupt Callback Registration
```python
def register_irq_callback(self, callback: Callable[[int], None]) -> None:
    """
    注册中断回调函数 / Register interrupt callback function

    Args:
        callback: 中断发送函数 / Interrupt sending function
    """
```

## 📋 寄存器管理器规范 / Register Manager Specification

### 核心功能 / Core Functionality

#### 寄存器定义接口 / Register Definition Interface
```python
def define_register(self,
                   offset: int,
                   name: str,
                   register_type: RegisterType = RegisterType.READ_WRITE,
                   reset_value: int = 0,
                   mask: int = 0xFFFFFFFF,
                   read_callback: Optional[Callable[[self, int, int], int]] = None,
                   write_callback: Optional[Callable[[self, int, int], None]] = None) -> None:
    """
    添加寄存器定义 / Add register definition

    Args:
        offset: 寄存器偏移地址 / Register offset address
        name: 寄存器名称 / Register name
        register_type: 寄存器类型(读写/只读/只写) / Register type (RW/RO/WO)
        reset_value: 复位值 / Reset value
        mask: 有效位掩码 / Valid bit mask
        read_callback: 读回调(用于读清零等特殊行为) / Read callback for special behaviors
        write_callback: 写回调(用于触发设备操作) / Write callback for triggering operations
    """
```

### 寄存器类型定义 / Register Type Definitions
```python
from enum import Enum

class RegisterType(Enum):
    READ_WRITE = "RW"      # 读写寄存器 / Read-Write register
    READ_ONLY = "RO"       # 只读寄存器 / Read-Only register
    WRITE_ONLY = "WO"      # 只写寄存器 / Write-Only register
    WRITE_CLEAR = "WC"     # 写清零寄存器 / Write-Clear register
    READ_CLEAR = "RC"      # 读清零寄存器 / Read-Clear register
```

## 🔌 IO接口规范 / IO Interface Specification

### 外设连接设备要求 / External Device Connection Requirements

对于UART、SPI、CAN等可连接外设的设备：

```python
class IOInterface:
    """IO接口类用于设备数据输入输出 / IO interface class for device data input/output"""

    def input(self, data: bytes, width: int = 1) -> None:
        """
        数据输入接口 / Data input interface

        Args:
            data: 输入数据 / Input data
            width: 数据宽度 / Data width
        """

    def output(self, data: bytes, width: int = 1) -> None:
        """
        数据输出接口 / Data output interface

        Args:
            data: 输出数据 / Output data
            width: 数据宽度 / Data width
        """

    def connect(self, external_device) -> None:
        """
        连接外部设备 / Connect external device
        - 输出模式：外部设备创建线程等待数据 / Output mode: external device creates thread waiting for data
        - 输入模式：当前设备创建线程获取外部数据 / Input mode: current device creates thread to get external data
        """
```

## 🎯 特殊功能要求 / Special Feature Requirements

### 1. 多实例支持 / Multi-Instance Support
```python
# 支持同一设备的多个实例 / Support multiple instances of same device
uart1 = UARTDevice(instance_id=1, base_address=0x40001000)
uart2 = UARTDevice(instance_id=2, base_address=0x40002000)
```

### 2. DMA接口支持 / DMA Interface Support
```python
class DMAInterface:
    """DMA接口类用于主动操作DMA设备 / DMA interface class for actively operating DMA device"""

    def dma_request(self, src_addr: int, dst_addr: int, length: int) -> None:
        """发起DMA传输请求 / Initiate DMA transfer request"""
```

### 3. 错误注入功能 / Error Injection Feature
```python
def inject_error(self, error_type: str, error_params: dict) -> None:
    """
    故障注入接口 / Error injection interface

    Args:
        error_type: 错误类型 / Error type
        error_params: 错误参数 / Error parameters
    """
```

## 📊 完整设备模型示例 / Complete Device Model Example

```python
class CRCDevice(BaseDevice):
    """CRC计算设备模型 / CRC calculation device model"""

    def __init__(self, instance_id: int = 0, base_address: int = 0x40003000):
        super().__init__()
        self.instance_id = instance_id
        self.base_address = base_address
        self.register_manager = RegisterManager()
        self.trace = TraceManager(f"CRC_{instance_id}")

    def init(self) -> None:
        """初始化CRC设备 / Initialize CRC device"""
        # 定义寄存器 / Define registers
        self.register_manager.define_register(
            offset=0x00,
            name="CRC_CTRL",
            register_type=RegisterType.READ_WRITE,
            reset_value=0x00000000,
            write_callback=self._ctrl_write_callback
        )

        self.register_manager.define_register(
            offset=0x04,
            name="CRC_DATA",
            register_type=RegisterType.WRITE_ONLY,
            write_callback=self._data_write_callback
        )

        self.register_manager.define_register(
            offset=0x08,
            name="CRC_RESULT",
            register_type=RegisterType.READ_ONLY,
            read_callback=self._result_read_callback
        )

    def _ctrl_write_callback(self, offset: int, value: int) -> None:
        """控制寄存器写回调 / Control register write callback"""
        if value & 0x1:  # START bit
            self._start_crc_calculation()

    def _data_write_callback(self, offset: int, value: int) -> None:
        """数据寄存器写回调 / Data register write callback"""
        self._process_crc_data(value)

    def _result_read_callback(self, offset: int, width: int) -> int:
        """结果寄存器读回调 / Result register read callback"""
        return self._get_crc_result()
```

## 🧪 测试集成要求 / Test Integration Requirements

### 必需的测试文件 / Required Test Files
```
${device_name}/output/
├── 📄 ${device_name}_device.py     # 设备模型实现
├── 📄 python_${device_name}.py     # Python接口封装
└── 📄 test_${device_name}_device.py # 测试程序
```

### 框架集成 / Framework Integration
```python
# 必须集成的框架组件 / Required framework components to integrate
from devcomm.core.base_device import BaseDevice
from devcomm.core.registers import RegisterManager
from devcomm.utils.trace_manager import TraceManager
from devcomm.core.io_interface import IOInterface  # 如果需要
```

    Note: For register-based devices, this calls register_manager callbacks
          For memory devices, this performs direct memory access
    """

def write(self, address: int, value: int, width: int = 4) -> None:
    """
    Register write operation

    Args:
        address: Register address (absolute or offset-based)
        value: Value to write
        width: Access width in bytes (default: 4 for 32-bit access)

    Note: For register-based devices, this calls register_manager callbacks
          For memory devices, this performs direct memory access
    """
```

#### 3. Interrupt Management
```python
def register_irq_callback(self, irq_send_func: Callable[[int], None]) -> None:
    """
    Register external interrupt sending function

    Args:
        irq_send_func: Function to call when device needs to send interrupt
                      Signature: func(interrupt_id: int) -> None
    """
```

## 📋 Register Manager Class Specification

### Core Functionality

The RegisterManager class provides centralized register definition and access control for all device registers.

#### Register Definition Method
```python
def define_register(self,
                   offset: int,
                   name: str,
                   register_type: RegisterType = RegisterType.READ_WRITE,
                   reset_value: int = 0,
                   mask: int = 0xFFFFFFFF,
                   read_callback: Optional[Callable[[self, int, int], int]] = None,
                   write_callback: Optional[Callable[[self, int, int], None]] = None) -> None:
    """
    Define a device register with its properties and behaviors

    Args:
        offset: Register offset address within device address space
        name: Human-readable register name for debugging/logging
        register_type: Access permissions (READ_ONLY, WRITE_ONLY, READ_WRITE)
        reset_value: Initial value after device reset
        mask: Valid bits mask (0xFFFFFFFF for all bits valid)
        read_callback: Optional function called on register read
        write_callback: Optional function called on register write
    """
```

### Callback Function Specifications

#### Read Callback
```python
def read_callback(self, device_instance, offset: int, current_value: int) -> int:
    """
    Called when register is read

    Args:
        device_instance: Reference to device instance for register access
        offset: Register offset being read
        current_value: Current register value before callback

    Returns:
        Modified register value (if needed)

    Use Cases:
        - Read-clear registers (status bits cleared on read)
        - Computed values (counters, timestamps)
        - Hardware state updates
    """
```

#### Write Callback
```python
def write_callback(self, device_instance, offset: int, new_value: int) -> None:
    """
    Called when register is written

    Args:
        device_instance: Reference to device instance for register access
        offset: Register offset being written
        new_value: Value being written to register

    Use Cases:
        - Control register actions (start/stop operations)
        - Configuration changes (mode switches)
        - Trigger operations (commands, calculations)
        - Update dependent registers
    """
```

## 🔄 Multi-Instance Support

### Requirements
- Device models **MUST** support multiple instantiation
- Each instance **MUST** maintain independent state
- Register spaces **MUST** be isolated between instances
- Configuration **MUST** be per-instance

### Implementation Guidelines
```python
class CRCDevice(BaseDevice):
    def __init__(self, instance_id: int = 0):
        super().__init__()
        self.instance_id = instance_id
        self.register_manager = RegisterManager()
        # Instance-specific state
```

## 🔌 Interrupt Capability

### Implementation Requirements
When a device supports interrupt generation:

```python
class InterruptCapableDevice(BaseDevice):
    def __init__(self):
        super().__init__()
        self.irq_callback = None

    def send_interrupt(self, interrupt_id: int) -> None:
        """Send interrupt to external system"""
        if self.irq_callback:
            self.irq_callback(interrupt_id)

    def complete_operation(self):
        """Example: Send interrupt when operation completes"""
        # ... operation logic ...
        self.send_interrupt(interrupt_id=1)  # Signal completion
```

## 🚀 DMA Interface Support

### Requirements for DMA-Capable Devices
```python
class DMACapableDevice(BaseDevice):
    def __init__(self):
        super().__init__()
        self.dma_interface = None

    def register_dma_interface(self, dma_interface):
        """Register DMA interface for memory operations"""
        self.dma_interface = dma_interface

    def perform_dma_transfer(self, src_addr: int, dst_addr: int, size: int):
        """Initiate DMA transfer through registered interface"""
        if self.dma_interface:
            self.dma_interface.transfer(src_addr, dst_addr, size)
```

## 🔗 I/O Interface for Peripheral Devices

### For External Communication Devices (UART, SPI, CAN, etc.)

```python
class IOInterface:
    """Interface for devices that connect to external peripherals"""

    def output(self, data: bytes, width: int = 1) -> None:
        """
        Send data to external device

        Args:
            data: Data to transmit
            width: Data width in bytes
        """

    def input(self, width: int = 1) -> bytes:
        """
        Receive data from external device

        Args:
            width: Expected data width in bytes

        Returns:
            Received data
        """

    def connect_output(self, external_device_input_handler) -> None:
        """
        Connect this device's output to external device input
        External device should create thread to wait for output data
        """

    def connect_input(self, external_device_output_source) -> None:
        """
        Connect external device output to this device's input
        This device creates thread to receive data from external source
        """
```

## 📊 Memory Device Specifications

### Enhanced Read/Write for Memory Devices
```python
def read(self, address: int, width: int = 4) -> int:
    """
    Memory read with variable width support

    Args:
        address: Memory address
        width: Access width (1, 2, 4, 8 bytes supported)
    """

def write(self, address: int, value: int, width: int = 4) -> None:
    """
    Memory write with variable width support

    Args:
        address: Memory address
        value: Value to write
        width: Access width (1, 2, 4, 8 bytes supported)
    """
```

## 📝 Integration Requirements

### Framework Integration
All device models must integrate with:

1. **Trace Class**: For debugging and monitoring
   ```python
   def init(self):
       self.trace = TraceClass(device_name=self.__class__.__name__)
       self.trace.log("Device initialized")
   ```

2. **Framework Interfaces**: Standard communication protocols
3. **Test Infrastructure**: Automated test compatibility

### Output Location
- **MANDATORY**: All generated code must be placed in `<device_name>/output/` directory
- **FORBIDDEN**: Modification of any other directories
- **STRUCTURE**: Follow established directory conventions

## ✅ Validation Checklist

Before code generation completion, verify:

- [ ] BaseDevice inheritance implemented
- [ ] All required methods (init, read, write, register_irq_callback) present
- [ ] RegisterManager with define_register method implemented
- [ ] Multi-instance support working
- [ ] Appropriate callback functions for register behaviors
- [ ] I/O Interface implemented (if applicable)
- [ ] DMA Interface implemented (if applicable)
- [ ] Trace integration added
- [ ] Output placed in correct directory
- [ ] Test compatibility ensured

## 🎯 AI Code Generation Guidelines

When generating device model code:

1. **Analyze Input Specifications Thoroughly**
   - Parse device description for functional requirements
   - Extract register definitions from YAML specification
   - Identify interrupt and DMA requirements

2. **Apply Architecture Patterns Consistently**
   - Always inherit from BaseDevice
   - Implement RegisterManager for all register-based devices
   - Add appropriate callback functions for register behaviors

3. **Generate Comprehensive Implementations**
   - Include all required methods with proper signatures
   - Add appropriate error handling and validation
   - Implement device-specific functionality accurately

4. **Ensure Integration Compliance**
   - Follow directory structure requirements
   - Add trace integration
   - Maintain compatibility with test framework