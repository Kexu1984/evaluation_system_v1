# DeviceModel_V1.1 Framework

## 📋 Overview

This repository provides an automated device model generation framework that creates both **Python device models** and **C driver implementations** from device specifications. The framework enables seamless integration testing between C drivers and Python device models through a standardized communication interface.

## 🏗️ System Architecture

### Integration Testing Framework

```
┌─────────────────────────────────┐                    ┌─────────────────────────────────┐
│        C Driver Test Side       │                    │      Python Model Side         │
│ ┌─────────────────────────────┐ │                    │ ┌─────────────────────────────┐ │
│ │         test_case.c         │ │                    │ │       DevComm_V3            │ │
│ │    (Generated Test Suite)   │ │                    │ │   Python Model Framework   │ │
│ └─────────────────────────────┘ │                    │ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │                    │ ┌─────────────────────────────┐ │
│ │      device_driver.c        │ │                    │ │      device_model.py       │ │
│ │    (Business Logic Layer)   │ │                    │ │   (Device Behavior Model)  │ │
│ └─────────────────────────────┘ │                    │ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │                    │                                 │
│ │       device_hal.c          │ │                    │                                 │
│ │  (Hardware Abstraction)     │ │                    │                                 │
│ └─────────────────────────────┘ │                    │                                 │
│ ┌─────────────────────────────┐ │   Socket Commands  │                                 │
│ │      libdrvintf.a           │ │ ◄─────────────────► │                                 │
│ │ ┌─────────────────────────┐ │ │                    │                                 │
│ │ │    communication        │ │ │                    │                                 │
│ │ │    read_register        │ │ │                    │                                 │
│ │ │    write_register       │ │ │                    │                                 │
│ │ │ register_int_handler    │ │ │                    │                                 │
│ │ └─────────────────────────┘ │ │                    │                                 │
│ └─────────────────────────────┘ │                    │                                 │
└─────────────────────────────────┘                    └─────────────────────────────────┘
```

### Communication Flow

1. **C Test Execution**: Test program calls driver functions
2. **Driver → HAL**: Driver layer calls HAL register operations
3. **HAL → Interface**: HAL calls `read_register()`/`write_register()` from `libdrvintf.a`
4. **Socket Communication**: Interface library sends commands via socket to DevComm_V3
5. **Python Model Processing**: DevComm_V3 routes commands to appropriate device model
6. **Response Path**: Results flow back through the same chain to C test program

### Key Benefits

- **Automated Testing**: Comprehensive C driver validation against Python models
- **Coverage Analysis**: Test coverage measurement for driver implementation
- **Behavioral Verification**: Python models simulate real hardware behavior
- **Integration Validation**: End-to-end communication testing

## 📁 Directory Structure

```
DeviceModel_V1.1/
├── 📁 <device_name>/           # Device-specific directory
│   ├── 📁 input/               # User-provided specifications
│   │   ├── 📄 description.docx # Device functional specification
│   │   └── 📄 register.yaml    # Register definition file
│   └── 📁 output/              # Auto-generated code
│       ├── 📄 <device>_device.py    # Python device model
│       ├── 📄 python_<device>.py    # Python test/integration
│       ├── 📄 test_<device>_device.py # Python unit tests
│       └── 📁 c_driver/        # C driver implementation
│           ├── 📁 hal/         # Hardware Abstraction Layer
│           ├── 📁 driver/      # Business Logic Layer
│           ├── 📁 test/        # C test programs
│           └── 📄 Makefile     # Build configuration
├── 📁 lib_drvintf/             # Interface library for C ◄─► Python
│   ├── 📄 libdrvintf.a         # Release library
│   ├── 📄 libdrvintf_dbg.a     # Debug library
│   └── 📄 interface_layer.h    # API definitions
├── 📁 autogen_rules/           # Code generation rules
└── 📄 Makefile                 # Top-level build system
```

## 🚀 Quick Start

### 1. Adding a New Device

Follow these standardized steps to add a new device:

1. **Define Device Name**: Choose a descriptive name (e.g., `crc`, `uart`, `spi`)
2. **Create Directory Structure**:
   ```bash
   mkdir -p <device_name>/input
   mkdir -p <device_name>/output
   ```
3. **Provide Input Specifications**:
   - `<device_name>/input/description.docx` - Device functional specification
   - `<device_name>/input/register.yaml` - Register map definition

4. **Generation**:
The device production contains two manners: python model / c driver
- **Python model**: <device>.py | <device>_test.py
- **C language driver**: <device>_hal.c | <device>_driver.c | <device>_test.c

### 2. Building and Testing



### 3. Running Integration Tests

```bash
# Navigate to device test directory
cd <device_name>/output/c_driver

# Run tests with custom base address (connects to Python model via DevComm_V3)
./test_<device_name>_driver 0x40000000
```

### 4. DevComm_V3 Integration

The C driver tests communicate with Python device models through the **DevComm_V3** framework:

- **Repository**: [DevComm_V3](https://github.com/ATC-WangChu/DevCommV3/)
- **Purpose**: Python model execution framework that receives socket commands from C tests
- **Communication**: Socket-based command protocol for register read/write operations
- **Benefits**: Real-time hardware simulation and behavioral validation

## 📐 Component Architecture

### Python Device Model Layer
- **Base Device Class**: Common interface for all device models
- **Register Manager**: Centralized register definition and access
- **I/O Interface**: External device connectivity support
- **Interrupt Handling**: Generate an interrupt to outside

### C Driver Layer
```
┌─────────────────┐
│   Test Layer    │ ← Comprehensive test programs
├─────────────────┤
│  Driver Layer   │ ← Business logic and configuration
├─────────────────┤
│    HAL Layer    │ ← Register read/write abstraction
├─────────────────┤
│ Interface Layer │ ← Communication with Python models
└─────────────────┘
```

### Build System
- **Top-level Makefile**: Orchestrates module builds with library dependencies
- **Module Makefiles**: Device-specific build configurations
- **Library Management**: Automatic selection of debug/release libraries

## 🔧 Configuration

### Runtime Configuration
- **Base Address**: Configurable via command-line parameter
- **Debug Mode**: Enhanced logging and debug library selection
- **Context Support**: Multiple concurrent operation contexts

### Build Configuration
- **DEBUG=1**: Enables debug symbols and verbose logging
- **Library Dependencies**: Automatic `libdrvintf.a` integration
- **Cross-compilation**: Configurable toolchain support

```bash
# Build and test a specific device module
make <device_name>              # Release build
make <device_name> DEBUG=1      # Debug build with enhanced logging

# Examples
make crc                        # Build CRC module tests
make crc DEBUG=1               # Build with debug interface library

# Other commands
make clean                     # Clean all modules
make status                    # Check build environment
make help                      # Display usage information
```

## 📚 Development Guidelines

### Code Generation Rules
All auto-generated code must follow the specifications in:
- `autogen_rules/device_model_gen.md` - Python model generation
- `autogen_rules/device_driver_gen.md` - C driver generation
- `autogen_rules/device_driver_test_gen.md` - Test program generation

### Interface Compliance
- **Register Access**: All register operations via interface layer
- **Address Management**: Base + offset addressing scheme
- **Error Handling**: Standardized error codes and status reporting
- **Testing**: Minimum 90% test coverage requirement

## 🔍 Testing & Validation Framework

### Test Categories
1. **HAL Layer Tests**: Register access, address calculations, error conditions
2. **Driver Layer Tests**: Configuration, calculations, context management
3. **Integration Tests**: C driver ↔ Python model communication via DevComm_V3
4. **Performance Tests**: Throughput and latency measurements
5. **Coverage Analysis**: Automated test coverage measurement and reporting

### Test Execution Flow
1. **Initialization**: Interface layer setup and device registration with Python model
2. **Base Address Setup**: Dynamic address configuration from command line
3. **Test Execution**: Comprehensive test suite with real-time Python model interaction
4. **Validation**: Results verification against expected Python model behavior
5. **Cleanup**: Resource deallocation and interface cleanup

### Integration Benefits
- **Real Hardware Simulation**: Python models provide accurate hardware behavior
- **Automated Validation**: Continuous testing against model specifications
- **Coverage Metrics**: Detailed analysis of driver code coverage
- **Regression Testing**: Automated detection of driver behavior changes

## 🏷️ Current Modules

| Module | Status | Description |
|--------|--------|-------------|
| **crc** | ✅ Complete | CRC16/CRC32 calculation engine with multiple contexts |

## 🛠️ Dependencies

### Required Libraries
- `lib_drvintf/libdrvintf.a` - Release interface library for C driver communication
- `lib_drvintf/libdrvintf_dbg.a` - Debug interface library with enhanced logging

### External Frameworks
- **DevComm_V3**: Python model execution framework
  - Repository: [DevComm_V3](https://github.com/ATC-WangChu/DevCommV3/)
  - Purpose: Socket-based communication server for Python device models
  - Integration: Receives register read/write commands from C test programs

### Build Tools
- **GCC**: C compiler toolchain
- **Make**: Build system
- **Python 3.x**: Model execution and DevComm_V3 framework

### Runtime Requirements
- **Socket Communication**: TCP/IP stack for C ↔ Python communication
- **Interface Layer**: libdrvintf.a for standardized register access
- **Model Framework**: DevComm_V3 for Python model hosting and command processing

## 📖 Additional Resources

- [Device Model Generation Rules](autogen_rules/device_model_gen.md)
- [C Driver Generation Rules](autogen_rules/device_driver_gen.md)
- [Test Generation Rules](autogen_rules/device_driver_test_gen.md)

## 🤝 Contributing

When adding new devices or modifying existing ones:
1. Follow the established directory structure
2. Adhere to code generation rules in `autogen_rules/`
3. Ensure comprehensive test coverage (90%+ target)
4. Verify integration with DevComm_V3 Python models
5. Update documentation as needed

## 🚀 Getting Started

### Basic Workflow
1. **Prepare Device Specification**: Create `description.docx` and `register.yaml`
2. **Generate Code**: Run code generation tools following autogen rules
3. **Build Tests**: Use `make <device_name>` to build C driver tests
4. **Setup Python Models**: Configure DevComm_V3 with generated device models
5. **Run Integration Tests**: Execute C tests that communicate with Python models
6. **Analyze Results**: Review test coverage and behavioral validation

### Example: CRC Module
```bash
# Build CRC driver tests
make crc

# Run tests (requires DevComm_V3 running with CRC model)
cd crc/output/c_driver
./test_crc_driver 0x40000000
```

---

> **Framework Goal**: Provide automated, comprehensive testing of C drivers against Python hardware models through standardized interfaces and communication protocols.
