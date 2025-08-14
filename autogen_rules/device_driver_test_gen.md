# C Driver Test Generation Prompt

## ROLE
You are an expert test automation engineer specializing in embedded C driver validation and comprehensive test coverage.

## TASK
Generate complete C driver test programs achieving 90%+ coverage with systematic validation approaches.

## INPUT SPECIFICATIONS
- **Device Name**: `${device_name}` (placeholder for actual device name)
- **Target File**: `${device_name}/output/c_driver/test/<device>_test.c`
- **Driver Headers**: `<device>_driver.h` (all interfaces must be tested)
- **Specifications**: `${device_name}/input/` directory (functional requirements)

## MANDATORY TEST STRUCTURE

### Test Program Architecture
```
┌─────────────────────────────────────────┐
│ TEST EXECUTION FRAMEWORK                │
│ - Command line parsing (base address)   │
│ - Test case management                  │
│ - Result reporting                      │
├─────────────────────────────────────────┤
│ THREE CORE TEST CATEGORIES              │
│ 1. Interface Testing (API coverage)     │
│ 2. Functional Testing (spec compliance) │
│ 3. Boundary Testing (edge cases)        │
├─────────────────────────────────────────┤
│ INTERFACE LAYER INTEGRATION             │
│ - interface_layer_init()                │
│ - register_device()                     │
│ - register_interrupt_handler()          │
│ - interface_layer_deinit()              │
└─────────────────────────────────────────┘
```

## REQUIRED MAIN FUNCTION TEMPLATE

```c
int main(int argc, char *argv[]) {
    // MANDATORY: Support address parameter
    if (argc != 2) {
        printf("Usage: %s <base_address>\n", argv[0]);
        return -1;
    }

    uint32_t base_address = strtoul(argv[1], NULL, 0);

    // MANDATORY: Initialize test environment
    if (test_init(base_address) != 0) {
        printf("Test initialization failed\n");
        return -1;
    }

    // Execute test suite
    int result = run_all_tests();

    // MANDATORY: Cleanup
    test_cleanup();

    return result;
}
```

## MANDATORY INITIALIZATION FUNCTION

```c
int test_init(uint32_t base_address) {
    // 1. REQUIRED: Initialize interface layer
    if (interface_layer_init() != 0) {
        printf("ERROR: interface_layer_init() failed\n");
        return -1;
    }

    // 2. REQUIRED: Register device address space
    uint32_t device_id = 1;      // Use 1 as device ID
    uint32_t size = 0x1000;      // Default 4KB address space
    if (register_device(device_id, base_address, size) != 0) {
        printf("ERROR: register_device() failed\n");
        return -1;
    }

    // 3. REQUIRED: Initialize HAL base address
    <device>_hal_base_address_init(base_address);

    // 4. REQUIRED: Initialize driver
    if (<device>_init() != 0) {
        printf("ERROR: <device>_init() failed\n");
        return -1;
    }

    return 0;
}
```

## TEST CATEGORY 1: INTERFACE TESTING (MANDATORY)

### Coverage Requirement
- **MUST TEST**: Every function in `<device>_driver.h`
- **MUST VALIDATE**: All return values and error conditions

```c
void test_interface_coverage(void) {
    printf("=== Interface Testing ===\n");

    // Test all driver interfaces
    <device>_status_t status;

    // Test initialization functions
    status = <device>_init();
    assert(status == <DEVICE>_SUCCESS);
    printf("✓ <device>_init() passed\n");

    // Test configuration functions
    <device>_config_t config;
    status = <device>_get_default_config(&config);
    assert(status == <DEVICE>_SUCCESS);
    printf("✓ <device>_get_default_config() passed\n");

    status = <device>_configure(&config);
    assert(status == <DEVICE>_SUCCESS);
    printf("✓ <device>_configure() passed\n");

    // Test all other driver functions...

    // Test error conditions
    status = <device>_configure(NULL);  // Invalid parameter
    assert(status == <DEVICE>_ERROR_INVALID_PARAM);
    printf("✓ Error handling validated\n");

    // Test deinitialization
    status = <device>_deinit();
    assert(status == <DEVICE>_SUCCESS);
    printf("✓ <device>_deinit() passed\n");
}
```

## TEST CATEGORY 2: FUNCTIONAL TESTING (DEVICE-SPECIFIC)

### Requirements Based on Device Type

| Device Type | MANDATORY Test Requirements |
|-------------|----------------------------|
| **AES Encryption** | All modes (ECB/CBC/CFB/OFB) + real crypto library comparison |
| **DMA Controller** | All transfer modes (mem2mem/mem2peri/peri2mem) + address modes |
| **CRC Calculator** | All polynomial configurations + standard algorithm comparison |
| **UART Interface** | All baud rates + frame formats + flow control |
| **SPI Interface** | Master/slave modes + clock configurations + data formats |

### Functional Test Template
```c
void test_device_functionality(void) {
    printf("=== Functional Testing ===\n");

    // ANALYZE ${device_name}/input/ for specific requirements
    // IMPLEMENT all modes/features described in specifications

    // Example for CRC device:
    test_crc_polynomial_configuration();
    test_crc_initial_value_setting();
    test_crc_calculation_accuracy();
    test_crc_all_supported_modes();

    // Example for DMA device:
    test_dma_mem2mem_transfer();
    test_dma_mem2peri_transfer();
    test_dma_peri2mem_transfer();
    test_dma_address_fixed_mode();
    test_dma_address_increment_mode();
}
```

### Real-World Comparison Testing (REQUIRED)
```c
void test_real_world_comparison(void) {
    // For devices with standard implementations

    // Example: AES encryption validation
    uint8_t plaintext[] = "Test Data for AES";
    uint8_t key[32] = {0x2b, 0x7e, 0x15, 0x16, ...};
    uint8_t device_result[16];
    uint8_t openssl_result[16];

    // Encrypt with device
    <device>_aes_encrypt(plaintext, key, device_result);

    // Encrypt with OpenSSL (real comparison)
    openssl_aes_encrypt(plaintext, key, openssl_result);

    // MUST match exactly
    assert(memcmp(device_result, openssl_result, 16) == 0);
    printf("✓ Real-world comparison passed\n");
}
```

## TEST CATEGORY 3: BOUNDARY TESTING (MANDATORY)

### Critical Boundary Conditions
```c
void test_boundary_conditions(void) {
    printf("=== Boundary Testing ===\n");

    // Test zero-length operations
    test_zero_length_data_transfer();

    // Test maximum parameter values
    test_maximum_transfer_size();

    // Test invalid addresses
    test_invalid_address_access();

    // Test parameter limits
    test_parameter_boundary_values();

    // Test resource exhaustion
    test_resource_limit_handling();
}

void test_zero_length_data_transfer(void) {
    // Example: DMA zero-byte transfer
    <device>_transfer_config_t config = {
        .src_addr = 0x20000000,
        .dst_addr = 0x20001000,
        .length = 0  // Zero length
    };

    <device>_status_t status = <device>_start_transfer(&config);
    // Verify proper handling of zero-length case
    assert(status == <DEVICE>_SUCCESS || status == <DEVICE>_ERROR_INVALID_PARAM);
}
```

## INTERRUPT TESTING (IF APPLICABLE)

### Interrupt Handler Registration
```c
// Global interrupt tracking
static volatile bool g_interrupt_received = false;
static volatile uint32_t g_interrupt_id = 0;

void device_interrupt_handler(void) {
    // Read interrupt status
    uint32_t irq_status;
    <device>_hal_read_raw(IRQ_STATUS_OFFSET, &irq_status);

    // Set flag for test verification
    g_interrupt_received = true;
    g_interrupt_id = irq_status;

    // Clear interrupt flags
    <device>_hal_write_raw(IRQ_CLEAR_OFFSET, irq_status);
}

void test_interrupt_functionality(void) {
    printf("=== Interrupt Testing ===\n");

    // Register interrupt handler
    uint32_t interrupt_id = DEVICE_IRQ_NUMBER;
    int result = register_interrupt_handler(interrupt_id, device_interrupt_handler);
    assert(result == 0);

    // Trigger interrupt condition
    <device>_start_operation_that_triggers_interrupt();

    // Wait for interrupt
    int timeout = 1000;  // 1 second timeout
    while (!g_interrupt_received && timeout > 0) {
        usleep(1000);  // 1ms delay
        timeout--;
    }

    // Verify interrupt was received
    assert(g_interrupt_received == true);
    assert(g_interrupt_id != 0);
    printf("✓ Interrupt functionality validated\n");
}
```

## ALL MODES TESTING (MANDATORY)

### Complete Mode Coverage
```c
void test_all_supported_modes(void) {
    // REQUIREMENT: Test ALL modes described in ${device_name}/input/

    // Example for DMA controller
    typedef struct {
        const char *mode_name;
        uint32_t mode_value;
    } test_mode_t;

    test_mode_t transfer_modes[] = {
        {"mem2mem", DMA_MODE_MEM2MEM},
        {"mem2peri", DMA_MODE_MEM2PERI},
        {"peri2mem", DMA_MODE_PERI2MEM},
        {"peri2peri", DMA_MODE_PERI2PERI}
    };

    test_mode_t address_modes[] = {
        {"fixed", DMA_ADDR_FIXED},
        {"increment", DMA_ADDR_INCREMENT},
        {"decrement", DMA_ADDR_DECREMENT}
    };

    // Test all combinations
    for (int i = 0; i < ARRAY_SIZE(transfer_modes); i++) {
        for (int j = 0; j < ARRAY_SIZE(address_modes); j++) {
            test_specific_mode_combination(transfer_modes[i], address_modes[j]);
        }
    }
}
```

## MANDATORY CLEANUP FUNCTION

```c
void test_cleanup(void) {
    printf("=== Test Cleanup ===\n");

    // 1. Device deinitialization
    <device>_deinit();

    // 2. REQUIRED: Interface layer cleanup
    interface_layer_deinit();

    // 3. Resource cleanup
    cleanup_test_resources();

    printf("✓ Cleanup completed\n");
}
```

## TEST RESULT REPORTING

### Required Output Format
```c
typedef struct {
    int total_tests;
    int passed_tests;
    int failed_tests;
    double coverage_percentage;
    double execution_time;
} test_results_t;

void print_test_summary(const test_results_t *results) {
    printf("\n" "========================================\n");
    printf("       %s TEST SUMMARY\n", "<DEVICE>");
    printf("========================================\n");
    printf("Total Tests:    %d\n", results->total_tests);
    printf("Passed:         %d\n", results->passed_tests);
    printf("Failed:         %d\n", results->failed_tests);
    printf("Coverage:       %.1f%%\n", results->coverage_percentage);
    printf("Execution Time: %.2f seconds\n", results->execution_time);

    if (results->failed_tests == 0) {
        printf("🎉 ALL TESTS PASSED!\n");
    } else {
        printf("❌ TESTS FAILED!\n");
    }
    printf("========================================\n");
}
```

## CRITICAL IMPLEMENTATION RULES

### MUST FOLLOW
1. **Command Line**: Support dynamic base address via command line argument
2. **Initialization Order**: interface_layer_init() → register_device() → device_init()
3. **Error Propagation**: Check and report ALL function return values
4. **Resource Management**: Proper cleanup in test_cleanup()
5. **Coverage Target**: Minimum 90% function coverage
6. **Real Comparison**: Use external libraries for validation where applicable

### FORBIDDEN
- ❌ Hard-coded addresses (must use command line parameter)
- ❌ Skipping return value checks
- ❌ Missing cleanup functions
- ❌ Incomplete mode testing
- ❌ No boundary condition tests

## VALIDATION CHECKLIST

Before test generation completion:
- [ ] All `<device>_driver.h` functions tested
- [ ] Command line address support implemented
- [ ] Initialization sequence correct
- [ ] All device modes covered
- [ ] Boundary conditions tested
- [ ] Real-world comparison (if applicable)
- [ ] Interrupt testing (if device supports)
- [ ] Proper cleanup implemented
- [ ] Test result reporting included

---

**CRITICAL**: This test program will validate the C driver's interaction with Python device models through `libdrvintf.a`. All tests must account for this simulation environment.

## 🏗️ 集成架构 / Integration Architecture

### 系统组件关系 / System Components Relationship

```
┌─────────────────────────────────────────────────────────────────┐
│                    测试执行环境 / Test Execution Environment      │
├─────────────────────────────────────────────────────────────────┤
│  📄 <device>_test.c                                            │
│  ├─ 命令行解析(基地址) / Command line parsing (base address)     │
│  ├─ 测试框架(测试用例，结果报告) / Test framework                │
│  ├─ 驱动API测试(HAL + 驱动层) / Driver API testing              │
│  └─ 清理和资源管理 / Cleanup and resource management           │
├─────────────────────────────────────────────────────────────────┤
│  📚 C驱动栈 / C Driver Stack                                   │
│  ├─ 驱动层 / Driver Layer: <device>_driver.h/.c               │
│  ├─ HAL层 / HAL Layer: <device>_hal.h/.c                      │
│  └─ 基地址管理 / Base address management (base+offset)         │
├─────────────────────────────────────────────────────────────────┤
│  🔗 接口库 / Interface Library (libdrvintf.a)                  │
│  ├─ interface_layer_init() / register_device()                 │
│  ├─ read_register() / write_register()                         │
│  ├─ register_interrupt_handler()                               │
│  └─ 与Python模型通信协议 / Communication protocol with Python │
├─────────────────────────────────────────────────────────────────┤
│  🐍 Python设备模型 / Python Device Model                      │
│  ├─ BaseDevice继承 / BaseDevice inheritance                    │
│  ├─ RegisterManager (寄存器定义)                               │
│  ├─ 设备特定逻辑和状态 / Device-specific logic and state       │
│  └─ 硬件行为模拟 / Hardware behavior simulation                │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 测试覆盖要求 / Test Coverage Requirements

### 三大核心测试类别 / Three Core Test Categories

#### 1. 接口测试 / Interface Testing
```c
// 所有驱动接口必须被调用和验证
// All driver interfaces must be called and verified

void test_interface_coverage(void) {
    // 测试所有<device>_driver.h中的接口
    // 验证返回值和错误处理
    assert(device_init() == SUCCESS);
    assert(device_config(...) == SUCCESS);
    assert(device_deinit() == SUCCESS);
}
```

#### 2. 功能测试 / Functional Testing
根据`${device_name}/input/`目录规范进行全面功能验证：

| 设备类型 / Device Type | 测试要求 / Test Requirements |
|------------------------|------------------------------|
| 🔐 **AES加密模块** | 所有模式：ECB/CBC/CFB/OFB + 真实加密库对比 |
| 📊 **DMA控制器** | 所有传输模式：mem2mem/mem2peri/peri2mem + 地址模式 |
| 🔢 **CRC计算器** | 多项式配置 + 初值设置 + 结果验证 |
| 📡 **UART通信** | 波特率/数据位/停止位/奇偶校验配置 |

#### 3. 边界测试 / Boundary Testing
```c
// 关键边界场景测试
void test_boundary_conditions(void) {
    // 零字节数据传输
    test_zero_byte_transfer();

    // 空输入数据处理
    test_empty_input_data();

    // 非法地址访问
    test_invalid_address_access();

    // 最大/最小参数值
    test_parameter_limits();
}
```

## 🔧 测试程序结构要求 / Test Program Structure Requirements

### 主函数规范 / Main Function Specification
```c
int main(int argc, char *argv[]) {
    // 必须支持address参数 / Must support address parameter
    if (argc != 2) {
        printf("Usage: %s <base_address>\n", argv[0]);
        return -1;
    }

    uint32_t base_address = strtoul(argv[1], NULL, 0);

    // 初始化测试环境
    if (test_init(base_address) != 0) {
        return -1;
    }

    // 执行测试套件
    run_test_suite();

    // 清理资源
    test_cleanup();
    return 0;
}
```

### 初始化函数要求 / Initialization Function Requirements
```c
int test_init(uint32_t base_address) {
    // 1. 初始化通信接口 / Initialize communication interface
    if (interface_layer_init() != 0) {
        printf("Failed to initialize interface layer\n");
        return -1;
    }

    // 2. 注册设备地址空间 / Register device address space
    uint32_t device_id = 1;        // 设备ID
    uint32_t size = 0x1000;        // 默认地址空间大小
    if (register_device(device_id, base_address, size) != 0) {
        printf("Failed to register device\n");
        return -1;
    }

    // 3. 初始化HAL层基地址
    base_address_init(base_address);

    return 0;
}
```

## ⚡ 中断测试专项要求 / Interrupt Testing Special Requirements

### 中断处理注册 / Interrupt Handler Registration
```c
// 中断处理函数类型定义
typedef void (*interrupt_handler_t)(void);

// 中断处理函数示例
void device_interrupt_handler(void) {
    // 读取中断状态寄存器
    uint32_t irq_status = read_interrupt_status();

    // 处理中断逻辑
    handle_interrupt_logic(irq_status);

    // 清除中断标志
    clear_interrupt_flags(irq_status);
}

// 注册中断处理函数
int register_interrupts(void) {
    uint32_t interrupt_id = DEVICE_IRQ_NUM;  // 与模型中的中断号匹配
    return register_interrupt_handler(interrupt_id, device_interrupt_handler);
}
```

## 🔍 高级测试场景 / Advanced Test Scenarios

### 真实场景对比测试 / Real Scenario Comparison Testing
```c
// AES加密模块真实性验证示例
void test_aes_encryption_real_comparison(void) {
    uint8_t plaintext[] = "Hello World Test Data";
    uint8_t key[] = {0x2b, 0x7e, 0x15, 0x16, ...};
    uint8_t device_result[16];
    uint8_t openssl_result[16];

    // 使用设备模型加密
    device_aes_encrypt(plaintext, key, device_result);

    // 使用OpenSSL库加密（真实对比）
    openssl_aes_encrypt(plaintext, key, openssl_result);

    // 比较结果
    assert(memcmp(device_result, openssl_result, 16) == 0);
}
```

### 所有模式覆盖测试 / All Modes Coverage Testing
```c
// DMA模块所有模式测试
void test_dma_all_modes(void) {
    // Memory to Memory
    test_dma_mem2mem_transfer();

    // Memory to Peripheral
    test_dma_mem2peri_transfer();

    // Peripheral to Memory
    test_dma_peri2mem_transfer();

    // Address固定模式
    test_dma_address_fixed_mode();

    // Address递增模式
    test_dma_address_increment_mode();
}
```

## 🧹 资源清理要求 / Resource Cleanup Requirements

### 测试结束清理 / Test Completion Cleanup
```c
void test_cleanup(void) {
    // 1. 设备去初始化
    device_deinit();

    // 2. 卸载接口层
    interface_layer_deinit();

    // 3. 清理测试资源
    cleanup_test_resources();

    printf("Test cleanup completed\n");
}
```

## 📊 测试结果输出要求 / Test Result Output Requirements

### 结果报告格式 / Result Report Format
```c
void print_test_results(void) {
    printf("\n" BOLD "=== 测试结果汇总 / Test Results Summary ===" RESET "\n");
    printf("✅ 通过测试: %d/%d\n", passed_tests, total_tests);
    printf("❌ 失败测试: %d/%d\n", failed_tests, total_tests);
    printf("📊 覆盖率: %.1f%%\n", coverage_percentage);
    printf("⏱️  执行时间: %.2f秒\n", execution_time);
}
```

3. **Address Translation**:
   - C HAL: `absolute_address = base_address + register_offset`
   - Interface Layer: Routes to appropriate Python model instance
   - Python Model: Validates and processes register access

4. **Validation Loop**:
   - C driver writes configuration → Python model updates state
   - C driver reads status → Python model returns computed values
   - Test framework verifies expected behavior

## �🎯 Test Coverage Requirements

### Mandatory Coverage Areas

| Category | Coverage Requirement | Description |
|----------|---------------------|-------------|
| **Interface Coverage** | 100% | All driver API functions must be tested |
| **Branch Coverage** | 90%+ | All conditional paths tested |
| **Boundary Testing** | 100% | Edge cases and limits validated |
| **Error Handling** | 100% | All error conditions triggered and verified |
| **Performance Testing** | Optional | Throughput and latency measurements |

## 🔧 Test Program Structure Requirements

### Command Line Interface
**MANDATORY**: Test programs must accept dynamic base address configuration.

```bash
# Usage examples
./test_<device>_driver                    # Use default address (0x40000000)
./test_<device>_driver 0x40000000         # Use custom address
./test_<device>_driver --help             # Show usage information
```

### Program Components
- **Argument Parsing**: Handle base address parameter and help options
- **Test Framework**: Organized test case execution with pass/fail reporting
- **Device Communication**: Integration with interface layer and Python models
- **Resource Management**: Proper initialization and cleanup sequences

## 🚀 Initialization Sequence Requirements

### Mandatory test_init() Function
**MANDATORY**: All test programs must implement standardized initialization sequence:

1. **Interface Layer Setup**: Call `interface_layer_init()` to establish communication
2. **Device Registration**: Call `register_device(device_id=1, base_address, size=0x1000)`
3. **Driver Setup**: Call `<device>_driver_base_address_init(base_address)`
4. **Validation**: Ensure all initialization steps succeed before proceeding

### Required Interface Layer APIs
- `int interface_layer_init(void)` - Initialize communication interface
- `int register_device(uint32_t device_id, uint32_t base_address, uint32_t size)` - Register address space
- `int interface_layer_deinit(void)` - Clean up interface resources
- `int register_interrupt_handler(uint32_t interrupt_id, interrupt_handler_t handler)` - Optional interrupt support

## 📊 Test Categories Requirements

### 1. HAL Layer Tests
- **Register Access**: Test read/write operations for all register types
- **Address Calculations**: Verify base+offset address computations
- **Error Handling**: Validate parameter checking and error responses
- **Initialization**: Test HAL init/deinit sequences

### 2. Driver Layer Tests
- **Initialization**: Test driver init/deinit and version information
- **Configuration**: Test all supported device configurations and modes
- **State Management**: Verify context operations and state tracking
- **API Coverage**: Test all public driver functions

### 3. Functional Tests
- **Core Operations**: Test device-specific functionality with various data patterns
- **Multi-Context**: Test concurrent context operations (if applicable)
- **Performance**: Optional throughput and latency measurements
- **Integration**: End-to-end communication with Python models

### 4. Error and Boundary Tests
- **Parameter Validation**: Test null pointers, invalid ranges, oversized data
- **State Validation**: Test operations in invalid states
- **Resource Limits**: Test maximum data sizes and context limits
- **Recovery**: Test error recovery and cleanup procedures

### 5. Interrupt Framework Tests (Optional)
- **Handler Registration**: Test interrupt handler registration with interface layer
- **Framework Validation**: Verify interrupt framework integration
- **Graceful Degradation**: Handle cases where interrupt support is not available

## 📊 Test Framework Implementation

### Test Structure Components
- **Test Case Array**: Organized list of test functions with descriptive names
- **Test Execution Engine**: Sequential test runner with result tracking
- **Result Reporting**: Pass/fail statistics with success rate calculation
- **Resource Management**: Proper initialization and cleanup sequences

### Main Program Flow
```
1. Parse command line arguments (base address)
2. Initialize test environment (test_init)
3. Execute all test cases sequentially
4. Display comprehensive results summary
5. Clean up resources (driver_deinit, interface_layer_deinit)
6. Return exit code based on test results
```

## ✅ Validation Checklist

Before test generation completion, verify:

- [ ] **Command Line Support**: Address parameter and help functionality
- [ ] **Initialization Sequence**: interface_layer_init → register_device → driver_base_address_init
- [ ] **Interface Layer Integration**: Proper use of all required API functions
- [ ] **Comprehensive Coverage**: All driver API functions tested (100% interface coverage)
- [ ] **Error Testing**: Parameter validation and boundary condition testing
- [ ] **Multi-Context Support**: Concurrent context testing (if applicable)
- [ ] **Interrupt Framework**: Optional interrupt handler registration testing
- [ ] **Test Framework**: Organized test execution with pass/fail reporting
- [ ] **Resource Cleanup**: Proper deinitialization sequence
- [ ] **Coverage Target**: 90%+ test coverage achieved

## 🎯 AI Code Generation Guidelines

### Analysis Phase
1. **Extract Driver Interface**: Parse all public API functions from driver headers
2. **Identify Requirements**: Determine parameter ranges, modes, and context support
3. **Map Test Categories**: Organize tests by HAL, driver, functional, and error categories

### Implementation Phase
1. **Framework Setup**: Implement command line parsing and test infrastructure
2. **Test Coverage**: Create comprehensive tests for every driver function
3. **Integration Testing**: Ensure proper communication with Python models via interface layer
4. **Validation Testing**: Include boundary conditions and error scenarios

### Quality Assurance
1. **Code Standards**: Follow C99 standards with proper error handling
2. **Documentation**: Include clear comments and usage instructions
3. **Maintainability**: Organize code for easy extension and modification
4. **Integration**: Ensure compatibility with build system and framework requirements

---

> **Reference Implementation**: See `crc/output/c_driver/test/test_crc_driver.c` for a complete example demonstrating all required testing patterns and coverage.
