# C Driver Generation Prompt

## ROLE
You are an expert C driver code generator specializing in embedded systems and hardware abstraction layers.

## TASK
Generate complete C driver implementations following a standardized three-layer architecture.

## INPUT SPECIFICATIONS
- **Device Name**: `${device_name}` (placeholder for actual device name)
- **Input Source**: `${device_name}/input/` directory containing:
  - Device specification documents
  - Register map definitions
  - Functional requirements
- **Output Location**: `${device_name}/output/c_driver/`

## MANDATORY ARCHITECTURE

### Layer Structure
```
┌─────────────────────────────────┐
│ TEST LAYER                      │ ← Comprehensive validation
│ - <device>_test.c               │
├─────────────────────────────────┤
│ DRIVER LAYER                    │ ← Business logic & APIs
│ - <device>_driver.h/.c          │
├─────────────────────────────────┤
│ HAL LAYER                       │ ← Register abstraction
│ - <device>_hal.h/.c             │
├─────────────────────────────────┤
│ INTERFACE LAYER                 │ ← Model communication
│ - libdrvintf.a                  │
└─────────────────────────────────┘
```

### Directory Structure (MUST CREATE)
```
${device_name}/output/c_driver/
├── hal/
│   ├── <device>_hal.h
│   └── <device>_hal.c
├── driver/
│   ├── <device>_driver.h
│   └── <device>_driver.c
├── test/
│   └── <device>_test.c
├── Makefile
└── libdrvintf.a (copy from lib_drvintf/)
```

## HAL LAYER REQUIREMENTS

### 1. Register Structure Definition (MANDATORY)
```c
struct <Device>Register {
    uint32_t <DEVICE>_CTRL;
    uint32_t <DEVICE>_STATUS;
    uint32_t <DEVICE>_DATA;
    // ... all device registers
};
```

### 2. Register Access Macros (MUST IMPLEMENT)
```c
#ifdef REAL_CHIP
#define WRITE_REGISTER(addr, value)  *(volatile uint32_t *)(addr) = (value)
#define READ_REGISTER(addr)          *(volatile uint32_t *)(addr)
#else
#include <interface_layer.h>
int write_register(uint32_t address, uint32_t data, uint32_t size);
int read_register(uint32_t address, uint32_t size);
#define WRITE_REGISTER(addr, value)  (void)write_register(addr, value, 4)
#define READ_REGISTER(addr)          read_register(addr, 4)
#endif
```

### 3. Base Address Management (REQUIRED)
```c
// Global base address storage
static uint32_t g_<device>_base_address = 0;
static bool g_<device>_base_address_initialized = false;

// MUST IMPLEMENT
void <device>_hal_base_address_init(uint32_t base_addr);
int <device>_hal_init(void);
int <device>_hal_deinit(void);

// Register access pattern: WRITE_REGISTER(base + offset, value)
```

## DRIVER LAYER REQUIREMENTS

### Mandatory Functions (MUST IMPLEMENT)
```c
// Initialization functions
int <device>_init(void);
int <device>_deinit(void);

// Configuration functions
int <device>_configure(const <device>_config_t *config);
int <device>_get_status(<device>_status_t *status);

// Device-specific operations (based on input specifications)
// Example: For DMA device
int <device>_start_transfer(const <device>_transfer_config_t *config);
int <device>_stop_transfer(void);
```

### Error Handling (REQUIRED)
```c
typedef enum {
    <DEVICE>_SUCCESS = 0,
    <DEVICE>_ERROR_INVALID_PARAM,
    <DEVICE>_ERROR_NOT_INITIALIZED,
    <DEVICE>_ERROR_HARDWARE_FAULT,
    <DEVICE>_ERROR_TIMEOUT
} <device>_status_t;
```

## COMPILATION REQUIREMENTS

### Makefile Template (MUST CREATE)
```makefile
CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2
LIBS = -L../../../lib_drvintf -ldrvintf

# Support for real chip compilation
ifdef REAL_CHIP
    CFLAGS += -DREAL_CHIP
endif

# Build targets
HAL_LIB = lib<device>_hal.a
DRIVER_LIB = lib<device>_driver.a
TEST_EXEC = <device>_test

all: $(TEST_EXEC)

$(HAL_LIB): hal/<device>_hal.o
	ar rcs $@ $^

$(DRIVER_LIB): driver/<device>_driver.o
	ar rcs $@ $^

$(TEST_EXEC): test/<device>_test.o $(DRIVER_LIB) $(HAL_LIB)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)

clean:
	rm -f hal/*.o driver/*.o test/*.o
	rm -f $(HAL_LIB) $(DRIVER_LIB) $(TEST_EXEC)

.PHONY: all clean
```

## IMPLEMENTATION CONSTRAINTS

### CRITICAL RULES
1. **NO Interrupt Handling**: Driver layer does NOT handle interrupt registration (test layer responsibility)
2. **Address Pattern**: ALL register access MUST use `base + offset` calculation
3. **Library Dependency**: Link with `libdrvintf.a` when NOT `REAL_CHIP`
4. **Function Naming**: Use `<device>_` prefix for all public functions
5. **Return Values**: ALL functions MUST return status codes and check parameters

### Error Handling Pattern
```c
<device>_status_t <device>_function(const void *input, void *output) {
    // Parameter validation
    if (input == NULL || output == NULL) {
        return <DEVICE>_ERROR_INVALID_PARAM;
    }

    // Initialization check
    if (!g_<device>_initialized) {
        return <DEVICE>_ERROR_NOT_INITIALIZED;
    }

    // Implementation logic
    // ...

    return <DEVICE>_SUCCESS;
}
```

## FUNCTIONAL IMPLEMENTATION

### Device-Specific Logic
- **ANALYZE** `${device_name}/input/` directory for functional requirements
- **IMPLEMENT** all features described in specification documents
- **SUPPORT** all operating modes mentioned in documentation
- **VALIDATE** register operations match hardware behavior

### Example Implementation Patterns
```c
// For configuration registers
int <device>_set_mode(<device>_mode_t mode) {
    uint32_t ctrl_value;
    <device>_hal_read_raw(CTRL_OFFSET, &ctrl_value);
    ctrl_value = (ctrl_value & ~MODE_MASK) | (mode << MODE_SHIFT);
    <device>_hal_write_raw(CTRL_OFFSET, ctrl_value);
    return <DEVICE>_SUCCESS;
}

// For status monitoring
int <device>_is_busy(bool *busy) {
    uint32_t status;
    <device>_hal_read_raw(STATUS_OFFSET, &status);
    *busy = (status & BUSY_FLAG) != 0;
    return <DEVICE>_SUCCESS;
}
```

## OUTPUT VALIDATION

### Generated Code Must Include:
- [ ] Complete HAL layer with base address management
- [ ] Driver layer with device-specific functionality
- [ ] Proper error handling throughout
- [ ] Makefile with library dependencies
- [ ] All register access via interface layer
- [ ] Support for both simulation and real hardware modes

### Code Quality Requirements:
- ISO C99 compliance
- Consistent naming conventions
- Comprehensive parameter validation
- Memory leak prevention
- Thread-safe implementations (if applicable)

## GENERATION WORKFLOW

1. **Parse Input**: Extract device specifications from `${device_name}/input/`
2. **Generate HAL**: Create register definitions and access functions
3. **Generate Driver**: Implement business logic and device APIs
4. **Create Makefile**: Configure build system with dependencies
5. **Validate**: Ensure all requirements are met

---

**REMEMBER**: This driver will interface with Python device models via `libdrvintf.a`. All register access MUST go through the interface layer for proper simulation support.

## 🏗️ 架构概述 / Architecture Overview

```
┌─────────────────────────────────┐
│         测试层 / Test Layer      │ ← 综合测试程序 / Comprehensive test programs
│  - test_<device>_driver.c       │
│  - 单元测试和集成测试 / Unit tests & integration     │
├─────────────────────────────────┤
│         驱动层 / Driver Layer    │ ← 业务逻辑和配置 / Business logic & configuration
│  - <device>_driver.h/.c         │
│  - API函数和状态管理 / API functions & state mgmt   │
├─────────────────────────────────┤
│         HAL层 / HAL Layer        │ ← 寄存器抽象 / Register abstraction
│  - <device>_hal.h/.c            │
│  - 原始寄存器读写 / Raw register read/write      │
├─────────────────────────────────┤
│       接口层 / Interface Layer   │ ← 与模型通信 / Communication with models
│  - libdrvintf.a (静态库)        │
│  - interface_layer.h            │
└─────────────────────────────────┘
```

## 📁 目录结构要求 / Directory Structure Requirements

### 强制目录布局 / Mandatory Directory Layout
```
<device_name>/output/c_driver/
├── 📁 hal/                     # 硬件抽象层 / Hardware Abstraction Layer
│   ├── 📄 <device>_hal.h       # HAL接口定义 / HAL interface definitions
│   └── 📄 <device>_hal.c       # HAL实现 / HAL implementation
├── 📁 driver/                  # 驱动业务逻辑 / Driver Business Logic
│   ├── 📄 <device>_driver.h    # 驱动接口定义 / Driver interface definitions
│   └── 📄 <device>_driver.c    # 驱动实现 / Driver implementation
├── 📁 test/                    # 测试程序 / Test Programs
│   └── 📄 test_<device>_driver.c # 综合测试套件 / Comprehensive test suite
├── 📄 Makefile                 # 构建配置 / Build configuration
└── 📄 libdrvintf.a             # 接口库 / Interface library (复制自lib_drvintf/)
```

## 🔧 HAL层规范 / HAL Layer Specifications

### 关键特性 / Key Features

#### 1. 寄存器结构体定义 / Register Structure Definition
HAL层必须包含全局寄存器的结构体定义：
```c
struct DMARegister {
    uint32_t DMA_CTRL;          // DMA控制寄存器
    uint32_t DMA_CHAN_CTRL;     // DMA通道控制寄存器
    // ... 其他寄存器
};
```

#### 2. 寄存器访问宏定义 / Register Access Macros
```c
#ifdef REAL_CHIP
/* 直接读写内存 / Read/write memory directly */
#define WRITE_REGISTER(addr, value)  *(volatile uint32_t *)(addr) = (value)
#define READ_REGISTER(addr)          *(volatile uint32_t *)(addr)
#else
/* 通过libdrvintf.a与Python模型通信 / Communicate with Python model via libdrvintf.a */
#include <interface_layer.h>
int write_register(uint32_t address, uint32_t data, uint32_t size);
int read_register(uint32_t address, uint32_t size);
#define WRITE_REGISTER(addr, value)  (void)write_register(addr, value, 4)
#define READ_REGISTER(addr)   read_register(addr, 4)
#endif
```

#### 3. 基地址初始化 / Base Address Initialization
HAL层必须提供`base_address_init`接口：
```c
void base_address_init(uint32_t base_addr);
```
所有寄存器访问使用：`WRITE_REGISTER(base + offset, value)` / `READ_REGISTER(base + offset)`

## 🔥 编译配置 / Compilation Configuration

### 依赖库 / Dependencies
- **默认模式**：不定义`REAL_CHIP`，需要链接`libdrvintf.a`
- **真实芯片模式**：定义`REAL_CHIP`，直接内存访问

### Makefile要求 / Makefile Requirements
```makefile
# 默认链接模拟库
LIBS = -L../../../lib_drvintf -ldrvintf

# 支持真实芯片编译
ifdef REAL_CHIP
    CFLAGS += -DREAL_CHIP
endif
```

## 🎯 驱动层规范 / Driver Layer Specifications

### 必需功能 / Required Functions

#### 1. 初始化和去初始化 / Initialization & Deinitialization
```c
int <device>_init(void);        // 设备初始化
int <device>_deinit(void);      // 设备去初始化
```

#### 2. 功能API / Functional APIs
根据`${device_name}/input/`目录下的规范文档生成对应的功能接口

#### 3. 错误处理 / Error Handling
所有函数必须有适当的返回值检查和错误处理机制

## ⚠️ 重要约束 / Important Constraints

1. **中断处理**：驱动层不处理中断注册，由测试程序负责
2. **模块化设计**：HAL层和驱动层严格分离
3. **可移植性**：支持模拟器和真实硬件两种编译模式
4. **依赖管理**：正确配置库依赖和头文件路径

## 📊 质量保证 / Quality Assurance

### 代码标准 / Coding Standards
- 遵循C99标准
- 使用一致的命名约定
- 充分的错误检查和边界验证
- 完整的文档注释

### 测试要求 / Testing Requirements
- 所有公共接口必须有对应测试
- 覆盖正常和异常场景
- 包含边界条件测试

```c
/**
 * @brief Write data to a register
 * @param address Register address (absolute address)
 * @param data Data to write
 * @param size Access width in bytes (typically 4 for 32-bit)
 * @return 0 on success, non-zero on error
 */
int write_register(uint32_t address, uint32_t data, uint32_t size);

/**
 * @brief Read data from a register
 * @param address Register address (absolute address)
 * @param size Access width in bytes (typically 4 for 32-bit)
 * @return Register value, or error code on failure
 */
uint32_t read_register(uint32_t address, uint32_t size);
```

### Integration Requirements
- **Dependency**: Link with `lib_drvintf/libdrvintf.a` static library
- **Headers**: Include `interface_layer.h` for API definitions
- **Communication**: All model communication via interface layer functions

## 🔩 HAL Layer Specifications

### Base Address Management

#### Required API Functions
```c
/**
 * @brief Initialize HAL base address
 * @param base_address Register base address for device
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_base_address_init(uint32_t base_address);

/**
 * @brief Initialize HAL (requires base address already set)
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_init(void);

/**
 * @brief Deinitialize HAL
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_deinit(void);
```

### Register Access Implementation

#### Address Calculation Pattern
```c
// Global base address storage
static uint32_t g_<device>_base_address = 0;
static bool g_<device>_base_address_initialized = false;

/**
 * @brief Raw register read using base + offset
 * @param offset Register offset from base address
 * @param value Pointer to store read value
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_read_raw(uint32_t offset, uint32_t *value)
{
    if (!g_<device>_base_address_initialized) {
        return <DEVICE>_HAL_NOT_INITIALIZED;
    }

    uint32_t absolute_address = g_<device>_base_address + offset;
    uint32_t read_value = read_register(absolute_address, sizeof(uint32_t));

    if (value != NULL) {
        *value = read_value;
    }

    return <DEVICE>_HAL_OK;
}

/**
 * @brief Raw register write using base + offset
 * @param offset Register offset from base address
 * @param value Value to write
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_write_raw(uint32_t offset, uint32_t value)
{
    if (!g_<device>_base_address_initialized) {
        return <DEVICE>_HAL_NOT_INITIALIZED;
    }

    uint32_t absolute_address = g_<device>_base_address + offset;
    write_register(absolute_address, value, sizeof(uint32_t));

    return <DEVICE>_HAL_OK;
}
```

#### Direct Address Access
```c
/**
 * @brief Direct register read with absolute address
 * @param address Absolute register address
 * @param value Pointer to store read value
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_read_register_direct(uint32_t address, uint32_t *value);

/**
 * @brief Direct register write with absolute address
 * @param address Absolute register address
 * @param value Value to write
 * @return HAL status code
 */
<device>_hal_status_t <device>_hal_write_register_direct(uint32_t address, uint32_t value);
```

### Error Handling
```c
typedef enum {
    <DEVICE>_HAL_OK = 0,
    <DEVICE>_HAL_ERROR,
    <DEVICE>_HAL_INVALID_PARAM,
    <DEVICE>_HAL_NOT_INITIALIZED,
    <DEVICE>_HAL_HARDWARE_ERROR
} <device>_hal_status_t;
```

## 🚀 Driver Layer Specifications

### Initialization Pattern

#### Required API Functions
```c
/**
 * @brief Initialize driver base address
 * @param base_address Register base address for device
 * @return Driver status code
 */
<device>_drv_status_t <device>_driver_base_address_init(uint32_t base_address);

/**
 * @brief Initialize driver (requires base address already set)
 * @return Driver status code
 */
<device>_drv_status_t <device>_driver_init(void);

/**
 * @brief Deinitialize driver
 * @return Driver status code
 */
<device>_drv_status_t <device>_driver_deinit(void);
```

### Business Logic Implementation

#### Configuration Management
```c
/**
 * @brief Get default configuration for device
 * @param mode Operating mode
 * @param config Pointer to configuration structure
 * @return Driver status code
 */
<device>_drv_status_t <device>_driver_get_default_config(<device>_mode_t mode,
                                                         <device>_config_t *config);

/**
 * @brief Configure device context
 * @param context Device context identifier
 * @param config Configuration to apply
 * @return Driver status code
 */
<device>_drv_status_t <device>_driver_configure_context(<device>_context_t context,
                                                        const <device>_config_t *config);
```

#### Operational Functions
```c
/**
 * @brief Perform device-specific operation
 * @param context Device context
 * @param input_data Input parameters
 * @param output_data Output results
 * @return Driver status code
 */
<device>_drv_status_t <device>_driver_operation(<device>_context_t context,
                                                const void *input_data,
                                                void *output_data);
```

### Error Handling
```c
typedef enum {
    <DEVICE>_DRV_OK = 0,
    <DEVICE>_DRV_ERROR,
    <DEVICE>_DRV_INVALID_PARAM,
    <DEVICE>_DRV_NOT_INITIALIZED,
    <DEVICE>_DRV_HARDWARE_ERROR,
    <DEVICE>_DRV_TIMEOUT,
    <DEVICE>_DRV_BUSY
} <device>_drv_status_t;
```

## 🔧 Build System Requirements

### Makefile Structure
```makefile
# Compiler settings
CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2

# Directories
HAL_DIR = hal
DRIVER_DIR = driver
TEST_DIR = test

# Libraries
LIBDRVINTF_LIB ?= libdrvintf.a

# Build targets
HAL_LIB = lib<device>_hal.a
DRIVER_LIB = lib<device>_driver.a
TEST_EXEC = test_<device>_driver

# Default target
all: $(TEST_EXEC)

# HAL library
$(HAL_LIB): $(HAL_DIR)/<device>_hal.o
	ar rcs $@ $^

# Driver library
$(DRIVER_LIB): $(DRIVER_DIR)/<device>_driver.o
	ar rcs $@ $^

# Test executable
$(TEST_EXEC): $(TEST_DIR)/test_<device>_driver.o $(DRIVER_LIB) $(HAL_LIB)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBDRVINTF_LIB)

# Test target (called by top-level Makefile)
test: $(TEST_EXEC)
	@echo "Built $(TEST_EXEC) successfully"

# Clean target
clean:
	rm -f $(HAL_DIR)/*.o $(DRIVER_DIR)/*.o $(TEST_DIR)/*.o
	rm -f $(HAL_LIB) $(DRIVER_LIB) $(TEST_EXEC)

.PHONY: all test clean
```

### Library Dependencies
- **LIBDRVINTF_LIB**: Variable for interface library selection
- **Debug Support**: Use `libdrvintf_dbg.a` when `DEBUG=1`
- **Library Check**: Verify library presence before linking

## 📊 Code Quality Requirements

### Coding Standards
- **C Standard**: ISO C99 or later
- **Style**: Consistent naming conventions
- **Documentation**: Doxygen-compatible comments
- **Error Handling**: Comprehensive status code usage

### Memory Management
- **Static Allocation**: Prefer static over dynamic allocation
- **Resource Cleanup**: Proper deinitialization sequences
- **Leak Prevention**: No memory leaks in normal operation

### Thread Safety (if applicable)
- **Mutual Exclusion**: Critical section protection
- **Atomic Operations**: For shared state access
- **Reentrancy**: Functions safe for concurrent calls

## 🎯 Integration Points

### With Device Models
- **Register Access**: All through interface layer
- **Address Translation**: Base + offset calculations
- **Error Propagation**: Status codes to model layer

### With Test Framework
- **Initialization**: Compatible with test harness
- **Configuration**: Runtime address configuration
- **Validation**: Comprehensive coverage requirements

## ✅ Validation Checklist

Before driver generation completion, verify:

- [ ] Layered architecture (HAL → Driver → Test) implemented
- [ ] Base address initialization APIs present
- [ ] All register access via interface layer functions
- [ ] Base + offset address calculation implemented
- [ ] Direct address access functions available
- [ ] Proper error handling with status codes
- [ ] Makefile with library dependencies configured
- [ ] Test program with comprehensive coverage
- [ ] Documentation with function signatures
- [ ] Memory management without leaks

## 🎯 AI Code Generation Guidelines

When generating C driver code:

1. **Analyze Device Specification**
   - Extract register map and offsets
   - Identify functional requirements
   - Determine configuration parameters

2. **Apply Architectural Patterns**
   - Implement three-layer structure consistently
   - Separate base address initialization from operational initialization
   - Use standardized error handling

3. **Generate Complete Implementation**
   - Include all required API functions
   - Add comprehensive error checking
   - Implement device-specific functionality

4. **Ensure Integration Compliance**
   - Use interface layer for all register access
   - Follow build system requirements
   - Maintain test framework compatibility

---

> **Reference Implementation**: See `crc/output/c_driver/` for a complete example demonstrating all architectural patterns and requirements.
