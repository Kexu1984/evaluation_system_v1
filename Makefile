# Top-level Makefile for DeviceModel_V1.0
# This makefile allows building and testing individual modules
# Usage: make <module_name> - to build and test a specific module
# Example: make crc - builds and tests the CRC module

# Available modules (add new modules here)
MODULES = crc hsm

# Common directories
LIB_DRVINTF_DIR = lib_drvintf

# Select interface library by DEBUG flag
ifeq ($(DEBUG),1)
  LIB_DRVINTF_NAME = libdrvintf_dbg.a
else
  LIB_DRVINTF_NAME = libdrvintf.a
endif
LIB_DRVINTF_LIB = $(LIB_DRVINTF_DIR)/$(LIB_DRVINTF_NAME)

# Default target
all: help

# Generic module test target
# This target can be called for any module by name
# It ensures libdrvintf dependency and builds only the test
$(MODULES): $(LIB_DRVINTF_LIB)
	@echo "Building and testing $@ module... (DEBUG=$(DEBUG))"
	@if [ -d "$@/output/c_driver" ]; then \
		echo "Copying $(LIB_DRVINTF_NAME) to $@ module..."; \
		cp $(LIB_DRVINTF_LIB) $@/output/c_driver/; \
		cd $@/output/c_driver && $(MAKE) test LIBDRVINTF_LIB=$(LIB_DRVINTF_NAME) DEBUG=$(DEBUG); \
	else \
		echo "Error: $@ module C driver directory not found!"; \
		exit 1; \
	fi

# Ensure selected lib exists
$(LIB_DRVINTF_LIB):
	@if [ ! -f "$(LIB_DRVINTF_LIB)" ]; then \
		echo "Error: $(LIB_DRVINTF_LIB) not found!"; \
		echo "Please ensure the library is built in the $(LIB_DRVINTF_DIR) directory."; \
		exit 1; \
	fi

# Clean all modules
clean:
	@echo "Cleaning all modules..."
	@for module in $(MODULES); do \
		if [ -d "$$module/output/c_driver" ]; then \
			echo "Cleaning $$module module..."; \
			cd $$module/output/c_driver && $(MAKE) clean; \
			cd - > /dev/null; \
		fi; \
	done
	@echo "All modules cleaned."

# Test all available modules
test: $(MODULES)
	@echo "All available modules tested."

# List available modules
list-modules:
	@echo "Available modules:"
	@for module in $(MODULES); do \
		echo "  - $$module"; \
	done
	@echo ""
	@echo "Usage: make <module_name> [DEBUG=1]"
	@echo "Example: make crc DEBUG=1"

# Show module status
status:
	@echo "Module Status Report"
	@echo "==================="
	@echo ""
	@echo "libdrvintf dependency (DEBUG=$(DEBUG)):"
	@if [ -f "$(LIB_DRVINTF_LIB)" ]; then \
		echo "  ✓ $(LIB_DRVINTF_LIB) exists"; \
	else \
		echo "  ✗ $(LIB_DRVINTF_LIB) missing"; \
	fi
	@echo ""
	@for module in $(MODULES); do \
		echo "$$module Module:"; \
		if [ -d "$$module/output/c_driver" ]; then \
			echo "  ✓ C driver directory exists"; \
			if [ -f "$$module/output/c_driver/Makefile" ]; then \
				echo "  ✓ Makefile exists"; \
			else \
				echo "  ✗ Makefile missing"; \
			fi; \
		else \
			echo "  ✗ C driver directory missing"; \
		fi; \
		echo ""; \
	done

# Help target
help:
	@echo "DeviceModel_V1.0 Top-Level Makefile"
	@echo "===================================="
	@echo ""
	@echo "Usage: make <target> [DEBUG=1]"
	@echo ""
	@echo "Module Targets:"
	@for module in $(MODULES); do \
		echo "  $$module        - Build and test $$module module"; \
	done
	@echo ""
	@echo "General Targets:"
	@echo "  all          - Show this help (default)"
	@echo "  test         - Test all available modules"
	@echo "  clean        - Clean all modules"
	@echo "  status       - Show status of all modules"
	@echo "  list-modules - List available modules"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "Examples:"
	@for module in $(MODULES); do \
		echo "  make $$module              # Build and test $$module module (release lib)"; \
		echo "  make $$module DEBUG=1      # Build and test $$module module (debug lib)"; \
	done
	@echo "  make clean             # Clean all modules"
	@echo "  make status            # Check module status"
	@echo ""
	@echo "Dependencies:"
	@echo "  - Uses $(LIB_DRVINTF_NAME) from $(LIB_DRVINTF_DIR)"
	@echo "  - Only test targets are built (no separate driver/hal targets)"
	@echo ""
	@echo "Adding New Modules:"
	@echo "  1. Add module name to MODULES variable"
	@echo "  2. Ensure module has output/c_driver/Makefile"
	@echo "  3. Ensure module Makefile has 'test' and 'clean' targets"

# Phony targets
.PHONY: all $(MODULES) clean test list-modules status help
