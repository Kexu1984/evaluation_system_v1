# Python Device Model Test Generation Prompt

## ROLE
You are an expert Python test automation engineer specializing in hardware device model validation and comprehensive test coverage.

## TASK
Generate complete Python test programs for device models ensuring 95%+ coverage, functional correctness, and real-world validation.

## INPUT SPECIFICATIONS
- **Device Name**: `${device_name}` (placeholder for actual device name)
- **Target File**: `${device_name}/output/test_<device>_device.py`
- **Device Model**: `<device>_device.py` (must test all functionality)
- **Specifications**: `${device_name}/input/` directory (ALL features must be tested)

## MANDATORY TEST FILE STRUCTURE

### Test Program Template
```python
"""
Comprehensive test suite for <DeviceName>Device
Tests ALL functionality described in ${device_name}/input/
"""

import unittest
import time
import threading
from typing import List, Dict, Any

# External libraries for real-world comparison
import numpy as np  # For numerical validation
# Import device-specific comparison libraries as needed

from <device>_device import <DeviceName>Device

class Test<DeviceName>Device(unittest.TestCase):
    """Comprehensive test suite for <DeviceName> device model"""

    def setUp(self) -> None:
        """Set up test environment before each test"""
        self.device = <DeviceName>Device(instance_id=1, base_address=0x40000000)
        self.device.init()
        self.test_results = []

    def tearDown(self) -> None:
        """Clean up after each test"""
        if hasattr(self.device, 'deinit'):
            self.device.deinit()

    # IMPLEMENT ALL TEST CATEGORIES
```

## TEST CATEGORY 1: DEVICE CREATION & INITIALIZATION (MANDATORY)

### Basic Device Validation
```python
def test_device_creation(self):
    """Test device creation and basic properties"""
    # Test single instance creation
    device = <DeviceName>Device(instance_id=1, base_address=0x40003000)
    self.assertIsNotNone(device)
    self.assertEqual(device.instance_id, 1)
    self.assertEqual(device.base_address, 0x40003000)

    # Test multiple instance creation
    device2 = <DeviceName>Device(instance_id=2, base_address=0x40004000)
    self.assertNotEqual(device.instance_id, device2.instance_id)
    self.assertNotEqual(device.base_address, device2.base_address)

    print("✓ Device creation test passed")

def test_device_initialization(self):
    """Test device initialization process"""
    device = <DeviceName>Device()

    # Test before initialization
    with self.assertRaises(Exception):
        device.read(0x00)  # Should fail before init

    # Initialize device
    device.init()

    # Test after initialization
    self.assertTrue(hasattr(device, 'register_manager'))
    self.assertTrue(hasattr(device, 'trace'))

    # Verify register definitions exist
    self.assertTrue(device.register_manager.has_register("<DEVICE>_CTRL"))
    self.assertTrue(device.register_manager.has_register("<DEVICE>_STATUS"))

    # Verify reset values
    ctrl_value = device.read(0x00)  # Control register
    self.assertEqual(ctrl_value, 0x00000000)  # Expected reset value

    print("✓ Device initialization test passed")
```

## TEST CATEGORY 2: REGISTER ACCESS VALIDATION (MANDATORY)

### Basic Register Operations
```python
def test_basic_register_access(self):
    """Test basic register read/write functionality"""
    # Test read/write registers
    self.device.write(0x00, 0x12345678)  # Control register
    value = self.device.read(0x00)
    self.assertEqual(value, 0x12345678)

    # Test different data patterns
    test_patterns = [0x00000000, 0xFFFFFFFF, 0xAAAAAAAA, 0x55555555]
    for pattern in test_patterns:
        self.device.write(0x00, pattern)
        self.assertEqual(self.device.read(0x00), pattern)

    print("✓ Basic register access test passed")

def test_register_type_enforcement(self):
    """Test register type constraints (RO, WO, RW)"""
    # Test read-only register behavior
    initial_status = self.device.read(0x04)  # Status register (RO)
    self.device.write(0x04, 0xFFFFFFFF)      # Should have no effect
    final_status = self.device.read(0x04)
    self.assertEqual(initial_status, final_status)

    # Test write-only register behavior
    self.device.write(0x08, 0x12345678)      # Data register (WO)
    # Reading WO register should return 0 or raise exception
    # Behavior depends on device specification

    print("✓ Register type enforcement test passed")

def test_special_register_behaviors(self):
    """Test special register behaviors (read-clear, write-clear)"""
    # Test read-clear register (if exists)
    if self.device.register_manager.has_register("<DEVICE>_IRQ_STATUS"):
        # Set up interrupt condition
        self._trigger_interrupt_condition()

        # First read should return interrupt status
        first_read = self.device.read(0x10)  # IRQ status register
        self.assertNotEqual(first_read, 0)

        # Second read should return 0 (read-clear behavior)
        second_read = self.device.read(0x10)
        self.assertEqual(second_read, 0)

    # Test write-clear register (if exists)
    if self.device.register_manager.has_register("<DEVICE>_ERROR_STATUS"):
        # Set error condition
        self._trigger_error_condition()

        # Read error status
        error_status = self.device.read(0x14)
        self.assertNotEqual(error_status, 0)

        # Clear specific error bits
        self.device.write(0x14, 0x00000001)  # Clear bit 0

        # Verify bit is cleared
        final_status = self.device.read(0x14)
        self.assertEqual(final_status & 0x1, 0)

    print("✓ Special register behaviors test passed")
```

## TEST CATEGORY 3: FUNCTIONAL TESTING (DEVICE-SPECIFIC)

### Complete Functionality Validation
```python
def test_all_device_functionality(self):
    """Test ALL functionality described in ${device_name}/input/"""
    # ANALYZE ${device_name}/input/ directory for requirements
    # IMPLEMENT tests for every feature mentioned

    # Example for CRC device:
    if "crc" in self.device.__class__.__name__.lower():
        self._test_crc_polynomial_configuration()
        self._test_crc_initial_value_settings()
        self._test_crc_calculation_accuracy()
        self._test_crc_all_modes()

    # Example for DMA device:
    elif "dma" in self.device.__class__.__name__.lower():
        self._test_dma_all_transfer_modes()
        self._test_dma_address_modes()
        self._test_dma_priority_handling()

    # Example for AES device:
    elif "aes" in self.device.__class__.__name__.lower():
        self._test_aes_all_encryption_modes()
        self._test_aes_key_sizes()
        self._test_aes_real_world_comparison()

def _test_crc_polynomial_configuration(self):
    """Test CRC polynomial configuration"""
    # Test standard polynomials
    standard_polynomials = [
        0x04C11DB7,  # CRC32
        0x1021,      # CRC16-CCITT
        0x8005       # CRC16-IBM
    ]

    for poly in standard_polynomials:
        self.device.write(0x10, poly)  # Polynomial register
        configured_poly = self.device.read(0x10)
        self.assertEqual(configured_poly, poly)

        # Test calculation with this polynomial
        self._perform_crc_calculation_test(poly)

def _test_crc_calculation_accuracy(self):
    """Test CRC calculation accuracy against known values"""
    # Test data with known CRC results
    test_vectors = [
        {
            "data": [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39],  # "123456789"
            "polynomial": 0x04C11DB7,  # CRC32
            "initial": 0xFFFFFFFF,
            "expected": 0xCBF43926
        }
    ]

    for vector in test_vectors:
        # Configure CRC
        self.device.write(0x10, vector["polynomial"])
        self.device.write(0x14, vector["initial"])

        # Start calculation
        self.device.write(0x00, 0x00000001)  # Start bit

        # Feed data
        for byte in vector["data"]:
            self.device.write(0x08, byte)

        # Get result
        result = self.device.read(0x0C)
        self.assertEqual(result, vector["expected"])
```

## TEST CATEGORY 4: REAL-WORLD COMPARISON (MANDATORY)

### External Library Validation
```python
def test_real_world_comparison(self):
    """Compare device results with standard library implementations"""
    # REQUIRED: For devices with standard implementations

    # Example: AES encryption validation
    if hasattr(self, '_test_aes_real_comparison'):
        self._test_aes_real_comparison()

    # Example: CRC calculation validation
    if hasattr(self, '_test_crc_real_comparison'):
        self._test_crc_real_comparison()

def _test_aes_real_comparison(self):
    """Compare AES encryption with cryptography library"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    import os

    # Test data
    plaintext = b"Hello World Test Data!123456"  # 16-byte aligned
    key = os.urandom(32)  # AES-256 key

    # Configure device for AES-256 ECB mode
    self.device.write(0x00, 0x00000001)  # AES-256 ECB mode

    # Load key into device
    for i in range(0, len(key), 4):
        key_word = int.from_bytes(key[i:i+4], byteorder='little')
        self.device.write(0x20 + i, key_word)  # Key registers

    # Encrypt with device
    device_result = bytearray()
    for i in range(0, len(plaintext), 16):  # Process 16-byte blocks
        block = plaintext[i:i+16]

        # Load block into device
        for j in range(0, len(block), 4):
            data_word = int.from_bytes(block[j:j+4], byteorder='little')
            self.device.write(0x30 + j, data_word)

        # Start encryption
        self.device.write(0x00, self.device.read(0x00) | 0x80000000)

        # Wait for completion
        while self.device.read(0x04) & 0x1 == 0:  # Wait for done flag
            time.sleep(0.001)

        # Read encrypted block
        for j in range(0, 16, 4):
            encrypted_word = self.device.read(0x40 + j)
            device_result.extend(encrypted_word.to_bytes(4, byteorder='little'))

    # Encrypt with standard library
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    encryptor = cipher.encryptor()
    standard_result = encryptor.update(plaintext) + encryptor.finalize()

    # Compare results
    self.assertEqual(bytes(device_result), standard_result)
    print("✓ AES real-world comparison test passed")

def _test_crc_real_comparison(self):
    """Compare CRC calculation with standard library"""
    import crc

    test_data = b"123456789"

    # Configure device for CRC32
    self.device.write(0x10, 0x04C11DB7)  # CRC32 polynomial
    self.device.write(0x14, 0xFFFFFFFF)  # Initial value
    self.device.write(0x00, 0x00000001)  # Start

    # Feed data to device
    for byte in test_data:
        self.device.write(0x08, byte)

    # Get device result
    device_crc = self.device.read(0x0C)

    # Calculate with standard library
    standard_crc = crc.crc32(test_data)

    # Compare results
    self.assertEqual(device_crc, standard_crc)
    print("✓ CRC real-world comparison test passed")
```

## TEST CATEGORY 5: INTERRUPT FUNCTIONALITY (IF APPLICABLE)

### Interrupt Testing
```python
def test_interrupt_functionality(self):
    """Test interrupt generation and handling"""
    if not hasattr(self.device, 'register_irq_callback'):
        self.skipTest("Device does not support interrupts")

    # Set up interrupt tracking
    self.interrupt_received = False
    self.interrupt_id = None

    def interrupt_handler(irq_id: int):
        self.interrupt_received = True
        self.interrupt_id = irq_id

    # Register interrupt callback
    self.device.register_irq_callback(interrupt_handler)

    # Trigger interrupt condition
    self._trigger_interrupt_condition()

    # Wait for interrupt (with timeout)
    timeout = 100  # 100ms timeout
    while not self.interrupt_received and timeout > 0:
        time.sleep(0.001)
        timeout -= 1

    # Verify interrupt was received
    self.assertTrue(self.interrupt_received)
    self.assertIsNotNone(self.interrupt_id)

    # Verify interrupt status register
    irq_status = self.device.read(0x1C)  # Interrupt status register
    self.assertNotEqual(irq_status, 0)

    print("✓ Interrupt functionality test passed")

def _trigger_interrupt_condition(self):
    """Trigger condition that should generate interrupt"""
    # Device-specific implementation
    # Example: Complete an operation that generates interrupt
    self.device.write(0x00, 0x00000001)  # Start operation
    self.device.write(0x08, 0x12345678)  # Provide data
    # Wait for operation completion and interrupt
```

## TEST CATEGORY 6: BOUNDARY CONDITIONS (MANDATORY)

### Edge Case Testing
```python
def test_boundary_conditions(self):
    """Test boundary conditions and edge cases"""

    # Test zero-length operations
    self._test_zero_length_operations()

    # Test maximum parameter values
    self._test_maximum_parameter_values()

    # Test invalid address access
    self._test_invalid_address_access()

    # Test resource limits
    self._test_resource_limits()

def _test_zero_length_operations(self):
    """Test operations with zero-length data"""
    # Example for DMA: zero-byte transfer
    if "dma" in self.device.__class__.__name__.lower():
        # Configure zero-length transfer
        self.device.write(0x08, 0x20000000)  # Source address
        self.device.write(0x0C, 0x20001000)  # Destination address
        self.device.write(0x10, 0)           # Length = 0

        # Start transfer
        self.device.write(0x00, 0x80000000)  # Start bit

        # Verify proper handling (should complete immediately or return error)
        status = self.device.read(0x04)
        # Check that device handles zero-length gracefully
        self.assertTrue((status & 0x2) == 0)  # No error flag

    print("✓ Zero-length operations test passed")

def _test_invalid_address_access(self):
    """Test invalid address access"""
    # Test reading from undefined register space
    try:
        value = self.device.read(0xFFFFFFFF)  # Invalid address
        # Some devices may return 0, others may raise exception
    except Exception as e:
        # Exception is acceptable for invalid address
        pass

    # Test writing to read-only addresses
    initial_value = self.device.read(0x04)  # Status register (read-only)
    self.device.write(0x04, 0xFFFFFFFF)
    final_value = self.device.read(0x04)
    self.assertEqual(initial_value, final_value)  # Should be unchanged

    print("✓ Invalid address access test passed")
```

## TEST CATEGORY 7: ERROR INJECTION (FOR SUPPORTED DEVICES)

### Fault Simulation Testing
```python
def test_error_injection(self):
    """Test error injection functionality"""
    if not hasattr(self.device, 'inject_error'):
        self.skipTest("Device does not support error injection")

    # Test data corruption error
    self.device.inject_error("data_corruption", {"bit_position": 5})

    # Perform operation and verify error detection
    self.device.write(0x00, 0x00000001)  # Start operation
    self.device.write(0x08, 0x12345678)  # Input data

    # Check error status
    error_status = self.device.read(0x1C)  # Error status register
    self.assertNotEqual(error_status & 0x1, 0)  # Data error flag

    # Test clock failure error
    self.device.inject_error("clock_failure", {"duration": 0.1})

    # Verify timeout detection
    start_time = time.time()
    self.device.write(0x00, 0x00000001)  # Start operation

    # Should timeout due to clock failure
    while time.time() - start_time < 0.2:
        status = self.device.read(0x04)
        if status & 0x4:  # Timeout flag
            break
        time.sleep(0.01)

    timeout_status = self.device.read(0x1C)
    self.assertNotEqual(timeout_status & 0x2, 0)  # Timeout error flag

    print("✓ Error injection test passed")
```

## TEST CATEGORY 8: ALL MODES COVERAGE (MANDATORY)

### Complete Mode Testing
```python
def test_all_supported_modes(self):
    """Test ALL modes described in device specifications"""
    # REQUIREMENT: Test every mode mentioned in ${device_name}/input/

    # Example for multi-mode device
    supported_modes = self._get_supported_modes_from_spec()

    for mode in supported_modes:
        with self.subTest(mode=mode):
            self._test_specific_mode(mode)

def _get_supported_modes_from_spec(self) -> List[Dict[str, Any]]:
    """Extract supported modes from device specifications"""
    # Parse ${device_name}/input/ to determine supported modes
    # This should be implemented based on actual specification format

    # Example return for DMA device:
    return [
        {"name": "mem2mem", "value": 0x0},
        {"name": "mem2peri", "value": 0x1},
        {"name": "peri2mem", "value": 0x2},
        {"name": "peri2peri", "value": 0x3}
    ]

def _test_specific_mode(self, mode: Dict[str, Any]):
    """Test a specific device mode"""
    # Configure device for this mode
    self.device.write(0x00, mode["value"])

    # Verify mode is set correctly
    current_mode = self.device.read(0x00) & 0x7  # Assume mode in bits 2:0
    self.assertEqual(current_mode, mode["value"])

    # Perform mode-specific operation
    self._perform_mode_specific_test(mode)

    print(f"✓ Mode {mode['name']} test passed")
```

## TEST RESULT REPORTING

### Comprehensive Test Summary
```python
def generate_test_report(self):
    """Generate comprehensive test report"""
    report = {
        "device_name": self.device.__class__.__name__,
        "test_summary": {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "coverage_percentage": 0.0
        },
        "test_categories": {
            "Device Creation": {"passed": 0, "failed": 0},
            "Register Access": {"passed": 0, "failed": 0},
            "Functional Testing": {"passed": 0, "failed": 0},
            "Real-world Comparison": {"passed": 0, "failed": 0},
            "Interrupt Testing": {"passed": 0, "failed": 0},
            "Boundary Testing": {"passed": 0, "failed": 0},
            "Error Injection": {"passed": 0, "failed": 0},
            "Mode Coverage": {"passed": 0, "failed": 0}
        }
    }

    # Calculate metrics from test results
    # Print formatted report
    self._print_test_report(report)

def _print_test_report(self, report: Dict[str, Any]):
    """Print formatted test report"""
    print("\n" + "="*60)
    print(f"🧪 {report['device_name']} DEVICE MODEL TEST REPORT")
    print("="*60)

    summary = report['test_summary']
    print(f"Total Tests:    {summary['total_tests']}")
    print(f"Passed:         {summary['passed_tests']}")
    print(f"Failed:         {summary['failed_tests']}")
    print(f"Coverage:       {summary['coverage_percentage']:.1f}%")

    print("\nTest Categories:")
    for category, results in report['test_categories'].items():
        status = "✅" if results['failed'] == 0 else "❌"
        print(f"  {status} {category}: {results['passed']}/{results['passed'] + results['failed']}")

    if summary['failed_tests'] == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n❌ {summary['failed_tests']} TESTS FAILED!")

    print("="*60)

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

## CRITICAL IMPLEMENTATION REQUIREMENTS

### MUST IMPLEMENT
1. **Complete Coverage**: Test ALL functionality in `${device_name}/input/`
2. **Real Comparison**: Use external libraries for validation where applicable
3. **Boundary Testing**: Cover all edge cases and error conditions
4. **Mode Testing**: Test every operational mode described in specifications
5. **Interrupt Testing**: Validate interrupt generation and status registers
6. **Error Injection**: Test fault simulation capabilities if supported

### FORBIDDEN
- ❌ Skipping any functionality mentioned in specifications
- ❌ Missing real-world comparison tests
- ❌ Inadequate boundary condition coverage
- ❌ Incomplete mode testing
- ❌ Missing error handling validation

---

**CRITICAL**: These tests validate the Python device model's accuracy in simulating real hardware behavior. All tests must reflect actual hardware specifications and expected behavior patterns.

## 🏗️ 测试架构 / Test Architecture

### 测试层次结构 / Test Hierarchy Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                     测试执行层 / Test Execution Layer           │
│  📄 test_<device>_device.py                                    │
│  ├─ 测试框架初始化 / Test framework initialization              │
│  ├─ 设备实例化和配置 / Device instantiation and configuration   │
│  ├─ 测试用例执行 / Test case execution                         │
│  └─ 结果验证和报告 / Result verification and reporting         │
├─────────────────────────────────────────────────────────────────┤
│                   设备模型层 / Device Model Layer               │
│  📄 <device>_device.py                                         │
│  ├─ BaseDevice继承 / BaseDevice inheritance                    │
│  ├─ RegisterManager集成 / RegisterManager integration          │
│  ├─ 设备特定逻辑 / Device-specific logic                       │
│  └─ 硬件行为模拟 / Hardware behavior simulation                │
├─────────────────────────────────────────────────────────────────┤
│                   框架支持层 / Framework Support Layer          │
│  📚 devcomm框架 / devcomm framework                            │
│  ├─ 核心基类 / Core base classes                               │
│  ├─ 寄存器管理 / Register management                           │
│  ├─ IO接口 / IO interfaces                                     │
│  └─ 跟踪和调试 / Tracing and debugging                         │
├─────────────────────────────────────────────────────────────────┤
│                   真实性验证层 / Reality Verification Layer     │
│  🔍 外部库对比 / External library comparison                   │
│  ├─ 加密库(OpenSSL, cryptography) / Crypto libraries          │
│  ├─ 计算库(NumPy, SciPy) / Calculation libraries              │
│  ├─ 通信库(pySerial, can) / Communication libraries           │
│  └─ 标准算法实现 / Standard algorithm implementations          │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 测试覆盖要求 / Test Coverage Requirements

### 1. 基础功能验证 / Basic Functionality Verification

#### 设备创建测试 / Device Creation Testing
```python
def test_device_creation():
    """测试设备创建是否成功 / Test device creation success"""
    device = CRCDevice(instance_id=1, base_address=0x40003000)
    assert device is not None
    assert device.instance_id == 1
    assert device.base_address == 0x40003000

    # 测试多实例创建 / Test multiple instance creation
    device2 = CRCDevice(instance_id=2, base_address=0x40004000)
    assert device2.instance_id != device.instance_id
```

#### 初始化验证 / Initialization Verification
```python
def test_device_initialization():
    """测试设备初始化过程 / Test device initialization process"""
    device = CRCDevice()
    device.init()

    # 验证寄存器已正确定义 / Verify registers are properly defined
    assert device.register_manager.has_register("CRC_CTRL")
    assert device.register_manager.has_register("CRC_DATA")
    assert device.register_manager.has_register("CRC_RESULT")

    # 验证复位值 / Verify reset values
    assert device.read(0x00) == 0x00000000  # CRC_CTRL reset value
```

### 2. 寄存器读写测试 / Register Read/Write Testing

#### 基础读写功能 / Basic Read/Write Functionality
```python
def test_basic_register_access():
    """测试基础寄存器读写功能 / Test basic register read/write functionality"""
    device = CRCDevice()
    device.init()

    # 测试读写寄存器 / Test read/write registers
    device.write(0x00, 0x12345678)  # CRC_CTRL
    assert device.read(0x00) == 0x12345678

    # 测试只读寄存器 / Test read-only registers
    initial_value = device.read(0x08)  # CRC_RESULT
    device.write(0x08, 0xFFFFFFFF)  # Should have no effect
    assert device.read(0x08) == initial_value
```

#### 特殊寄存器行为测试 / Special Register Behavior Testing
```python
def test_special_register_behaviors():
    """测试特殊寄存器行为 / Test special register behaviors"""
    device = CRCDevice()
    device.init()

    # 测试写清零寄存器 / Test write-clear registers
    device.write(0x10, 0xFFFFFFFF)  # 假设为写清零寄存器
    device.write(0x10, 0x0000000F)  # 写入清零位
    assert (device.read(0x10) & 0x0000000F) == 0

    # 测试读清零寄存器 / Test read-clear registers
    device.write(0x14, 0x12345678)  # 假设为读清零寄存器
    first_read = device.read(0x14)
    second_read = device.read(0x14)
    assert first_read == 0x12345678
    assert second_read == 0x00000000
```

### 3. 中断功能测试 / Interrupt Functionality Testing

#### 中断信号验证 / Interrupt Signal Verification
```python
def test_interrupt_functionality():
    """测试中断功能 / Test interrupt functionality"""
    device = CRCDevice()
    device.init()

    interrupt_received = False
    interrupt_id = None

    def interrupt_callback(irq_id):
        nonlocal interrupt_received, interrupt_id
        interrupt_received = True
        interrupt_id = irq_id

    # 注册中断回调 / Register interrupt callback
    device.register_irq_callback(interrupt_callback)

    # 触发中断条件 / Trigger interrupt condition
    device.write(0x00, 0x00000001)  # 启动操作
    device.write(0x04, 0x12345678)  # 写入数据

    # 等待操作完成 / Wait for operation completion
    time.sleep(0.1)

    # 验证中断状态 / Verify interrupt status
    assert interrupt_received == True
    assert interrupt_id is not None

    # 验证中断状态寄存器 / Verify interrupt status register
    irq_status = device.read(0x0C)  # 假设为中断状态寄存器
    assert irq_status & 0x1 == 0x1  # 中断标志应该被置位
```

### 4. 设备功能专项测试 / Device-Specific Functionality Testing

#### 功能完整性验证 / Functional Completeness Verification

根据 `${device_name}/input/` 目录中的规范，测试所有描述的功能：

| 设备类型 / Device Type | 必测功能 / Required Testing |
|------------------------|---------------------------|
| 🔐 **HSM加密模块** | 所有加密模式 + 密钥管理 + 证书处理 |
| 🔢 **CRC计算器** | 多项式配置 + 初值设置 + 反射配置 |
| 📊 **DMA控制器** | 所有传输模式 + 地址模式 + 优先级 |
| 📡 **UART通信** | 所有波特率 + 帧格式 + 流控制 |
| 🔄 **SPI接口** | 主从模式 + 时钟配置 + 数据格式 |
| 🚗 **CAN总线** | 标准/扩展帧 + 过滤器 + 错误处理 |

```python
def test_crc_all_modes():
    """测试CRC计算器所有模式 / Test CRC calculator all modes"""
    device = CRCDevice()
    device.init()

    test_data = [0x12, 0x34, 0x56, 0x78]

    # 测试不同多项式 / Test different polynomials
    polynomials = [0x04C11DB7, 0x1021, 0x8005]  # CRC32, CRC16-CCITT, CRC16-IBM

    for poly in polynomials:
        device.write(0x10, poly)  # 配置多项式

        # 测试不同初值 / Test different initial values
        for init_val in [0x00000000, 0xFFFFFFFF]:
            device.write(0x14, init_val)  # 配置初值

            # 执行计算 / Perform calculation
            device.write(0x00, 0x00000001)  # 启动
            for data in test_data:
                device.write(0x04, data)

            result = device.read(0x08)
            assert result != 0  # 验证有计算结果
```

### 5. 真实场景对比测试 / Real Scenario Comparison Testing

#### 外部库验证 / External Library Verification
```python
def test_aes_encryption_real_comparison():
    """AES加密真实性对比测试 / AES encryption reality comparison test"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    import os

    device = AESDevice()
    device.init()

    # 测试数据 / Test data
    plaintext = b"Hello World Test"
    key = os.urandom(32)  # AES-256 key

    # 使用设备模型加密 / Encrypt using device model
    device.write(0x00, 0x00000001)  # 设置AES-256模式
    device.load_key(key)
    device_result = device.encrypt(plaintext)

    # 使用标准库加密 / Encrypt using standard library
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    encryptor = cipher.encryptor()
    standard_result = encryptor.update(plaintext) + encryptor.finalize()

    # 比较结果 / Compare results
    assert device_result == standard_result

def test_crc_calculation_real_comparison():
    """CRC计算真实性对比测试 / CRC calculation reality comparison test"""
    import crc

    device = CRCDevice()
    device.init()

    test_data = b"123456789"

    # 使用设备模型计算CRC32 / Calculate CRC32 using device model
    device.write(0x10, 0x04C11DB7)  # CRC32多项式
    device.write(0x14, 0xFFFFFFFF)  # 初值
    device.write(0x00, 0x00000001)  # 启动

    for byte in test_data:
        device.write(0x04, byte)

    device_crc = device.read(0x08)

    # 使用标准库计算CRC32 / Calculate CRC32 using standard library
    standard_crc = crc.crc32(test_data)

    assert device_crc == standard_crc
```

### 6. 边界条件测试 / Boundary Condition Testing

#### 极限参数测试 / Extreme Parameter Testing
```python
def test_boundary_conditions():
    """边界条件测试 / Boundary condition testing"""
    device = CRCDevice()
    device.init()

    # 测试零长度数据 / Test zero-length data
    device.write(0x00, 0x00000001)  # 启动
    result = device.read(0x08)  # 读取结果
    assert result == 0xFFFFFFFF  # 应该等于初值

    # 测试最大长度数据 / Test maximum length data
    max_data = [0xFF] * 65536  # 64KB数据
    device.write(0x00, 0x00000001)  # 启动
    for data in max_data:
        device.write(0x04, data)
    result = device.read(0x08)
    assert result != 0  # 应该有有效结果

    # 测试非法地址访问 / Test illegal address access
    try:
        device.read(0xFFFFFFFF)  # 非法地址
        assert False, "应该抛出异常"
    except Exception:
        pass  # 期望的异常

    # 测试寄存器位域边界 / Test register bit field boundaries
    device.write(0x00, 0xFFFFFFFF)  # 写入全1
    value = device.read(0x00)
    # 根据寄存器定义验证有效位
```

### 7. 错误注入测试 / Error Injection Testing

#### 故障模拟验证 / Fault Simulation Verification
```python
def test_error_injection():
    """错误注入测试 / Error injection testing"""
    device = CRCDevice()
    device.init()

    # 测试数据错误注入 / Test data error injection
    device.inject_error("data_corruption", {"bit_position": 5})

    test_data = [0x12, 0x34, 0x56, 0x78]
    device.write(0x00, 0x00000001)  # 启动
    for data in test_data:
        device.write(0x04, data)

    # 验证错误状态寄存器 / Verify error status register
    error_status = device.read(0x1C)  # 假设为错误状态寄存器
    assert error_status & 0x1 == 0x1  # 数据错误标志

    # 测试时钟错误注入 / Test clock error injection
    device.inject_error("clock_failure", {"duration": 0.1})

    # 执行操作并验证超时 / Execute operation and verify timeout
    device.write(0x00, 0x00000001)  # 启动
    time.sleep(0.2)

    timeout_status = device.read(0x1C)
    assert timeout_status & 0x2 == 0x2  # 超时错误标志
```

### 8. 所有模式覆盖测试 / All Modes Coverage Testing

#### 模式完整性验证 / Mode Completeness Verification
```python
def test_all_supported_modes():
    """测试所有支持的模式 / Test all supported modes"""
    device = DMADevice()
    device.init()

    # DMA传输模式测试 / DMA transfer mode testing
    transfer_modes = [
        ("mem2mem", 0x00),      # 内存到内存
        ("mem2peri", 0x01),     # 内存到外设
        ("peri2mem", 0x02),     # 外设到内存
        ("peri2peri", 0x03)     # 外设到外设
    ]

    for mode_name, mode_value in transfer_modes:
        device.write(0x00, mode_value)  # 设置传输模式

        # 地址模式测试 / Address mode testing
        address_modes = [
            ("fixed", 0x00),        # 地址固定
            ("increment", 0x10),    # 地址递增
            ("decrement", 0x20)     # 地址递减
        ]

        for addr_mode_name, addr_mode_value in address_modes:
            device.write(0x04, addr_mode_value)  # 设置地址模式

            # 执行传输测试 / Execute transfer test
            test_transfer(device, mode_name, addr_mode_name)

def test_transfer(device, transfer_mode, address_mode):
    """执行具体的传输测试 / Execute specific transfer test"""
    # 配置源地址和目标地址 / Configure source and destination addresses
    device.write(0x08, 0x20000000)  # 源地址
    device.write(0x0C, 0x20001000)  # 目标地址
    device.write(0x10, 1024)        # 传输长度

    # 启动传输 / Start transfer
    device.write(0x00, device.read(0x00) | 0x80000000)

    # 等待完成 / Wait for completion
    while device.read(0x14) & 0x1 == 0:  # 等待完成标志
        time.sleep(0.001)

    # 验证结果 / Verify result
    assert device.read(0x14) & 0x2 == 0  # 验证无错误
```

## 📊 测试结果报告 / Test Result Reporting

### 测试结果格式 / Test Result Format
```python
def generate_test_report():
    """生成测试报告 / Generate test report"""
    report = {
        "device_name": "CRC",
        "test_summary": {
            "total_tests": 45,
            "passed_tests": 43,
            "failed_tests": 2,
            "skipped_tests": 0,
            "coverage_percentage": 95.6
        },
        "test_categories": {
            "基础功能测试": {"passed": 8, "failed": 0},
            "寄存器测试": {"passed": 12, "failed": 1},
            "中断测试": {"passed": 5, "failed": 0},
            "功能专项测试": {"passed": 10, "failed": 1},
            "真实性对比测试": {"passed": 4, "failed": 0},
            "边界测试": {"passed": 3, "failed": 0},
            "错误注入测试": {"passed": 1, "failed": 0}
        },
        "performance_metrics": {
            "execution_time": "12.5s",
            "average_test_time": "0.28s"
        }
    }

    print(f"\n{'='*60}")
    print(f"🧪 {report['device_name']} 设备模型测试报告")
    print(f"{'='*60}")
    print(f"✅ 通过: {report['test_summary']['passed_tests']}")
    print(f"❌ 失败: {report['test_summary']['failed_tests']}")
    print(f"📊 覆盖率: {report['test_summary']['coverage_percentage']}%")
    print(f"⏱️  执行时间: {report['performance_metrics']['execution_time']}")
```

## ⚠️ 重要提醒 / Important Reminders

1. **完整性要求**：必须测试 `input/` 目录中描述的所有功能
2. **真实性验证**：对于有标准实现的功能，必须与外部库对比
3. **边界覆盖**：必须包含边界条件和异常情况测试
4. **模式完整**：必须覆盖设备支持的所有工作模式
5. **错误处理**：对于支持错误注入的设备，必须测试故障场景
6. **性能验证**：对于有性能要求的设备，需要验证时序和吞吐量
