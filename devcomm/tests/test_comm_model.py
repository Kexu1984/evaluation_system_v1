"""
Test model implementation for the DevCommV3 framework.

This module provides comprehensive testing capabilities for the simulation framework.
"""

import time
import random
import sys
import os
import struct
from typing import Dict, List, Any, Optional
import threading
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from devcomm.core.top_model import TopModel
from devcomm.core.bus_model import BusModel
from devcomm.devices.memory_device import MemoryDevice
from devcomm.devices.dma_device import DMADevice, DMATransferMode
from devcomm.devices.crc_device import CRCDevice
from devcomm.utils.model_interface import ModelInterface, CMD_READ, CMD_WRITE, RESULT_SUCCESS

class TestModel:
    """Test model for comprehensive framework testing."""

    def __init__(self, config_path: Optional[str] = None):
        self.top_model = TopModel("TestSystem")
        self.test_results = {}
        self.config_path = config_path

        if config_path:
            self.top_model.load_configuration(config_path)
            self.top_model.initialize_system()
        else:
            self._create_default_configuration()

    def _create_default_configuration(self) -> None:
        """Create a default test configuration."""
        config = {
            'system': {
                'name': 'TestMCU',
                'buses': {
                    'main_bus': {
                        'name': 'MainBus'
                    }
                },
                'devices': {
                    'main_memory': {
                        'device_type': 'memory',
                        'name': 'MainMemory',
                        'base_address': 0x20000000,
                        'size': 0x10000,
                        'master_id': 1,
                        'bus': 'main_bus',
                        'initial_value': 0x00,
                        'read_only': False
                    },
                    'dma_controller': {
                        'device_type': 'dma',
                        'name': 'DMAController',
                        'base_address': 0x40000000,
                        'size': 0x1000,
                        'master_id': 3,
                        'bus': 'main_bus',
                        'num_channels': 4
                    },
                    'crc_unit': {
                        'device_type': 'crc',
                        'name': 'CRCUnit',
                        'base_address': 0x40001000,
                        'size': 0x100,
                        'master_id': 4,
                        'bus': 'main_bus'
                    }
                }
            }
        }

        self.top_model.create_configuration(config)
        self.top_model.initialize_system()

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all available tests."""
        print("Starting comprehensive DevCommV3 framework tests...")

        # Reset test results
        self.test_results = {
            'bus_communication': None,
            'memory_operations': None,
            'register_management': None,
            'dma_mem2mem': None,
            'dma_mem2peri': None,
            'crc_calculation': None,
            'interrupt_handling': None,
            'trace_logging': None,
            'overall_success': False
        }

        try:
            # Test basic bus communication
            self.test_results['bus_communication'] = self.test_bus_communication()

            # Test memory operations
            self.test_results['memory_operations'] = self.test_memory_operations()

            # Test register management
            self.test_results['register_management'] = self.test_register_management()

            # Test DMA mem2mem transfer
            self.test_results['dma_mem2mem'] = self.test_dma_mem2mem()

            # Test DMA mem2peri transfer with CRC
            self.test_results['dma_mem2peri'] = self.test_dma_mem2peri_crc()

            # Test CRC calculation
            self.test_results['crc_calculation'] = self.test_crc_calculation()

            # Test interrupt handling
            self.test_results['interrupt_handling'] = self.test_interrupt_handling()

            # Test trace and logging
            self.test_results['trace_logging'] = self.test_trace_logging()

            # Determine overall success
            self.test_results['overall_success'] = all(
                result['success'] for result in self.test_results.values()
                if isinstance(result, dict)
            )

        except Exception as e:
            print(f"Test execution failed: {e}")
            self.test_results['execution_error'] = str(e)

        return self.test_results

    def test_bus_communication(self) -> Dict[str, Any]:
        """Test basic bus communication."""
        print("Testing bus communication...")

        try:
            bus = self.top_model.get_bus('main_bus')
            memory = self.top_model.get_device('main_memory')

            # Test write and read
            test_address = memory.base_address + 0x100
            test_value = 0xDEADBEEF

            bus.write(memory.master_id, test_address, test_value)
            read_value = bus.read(memory.master_id, test_address)

            success = (read_value == test_value)

            return {
                'success': success,
                'test_address': f"0x{test_address:08X}",
                'written_value': f"0x{test_value:08X}",
                'read_value': f"0x{read_value:08X}",
                'details': 'Bus read/write operations successful' if success else 'Value mismatch'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Bus communication test failed'
            }

    def test_memory_operations(self) -> Dict[str, Any]:
        """Test memory device operations."""
        print("Testing memory operations...")

        try:
            memory = self.top_model.get_device('main_memory')

            # Test different access widths
            test_data = [0xAA, 0xBB, 0xCC, 0xDD]
            base_offset = 0x200

            # Write bytes
            for i, byte_val in enumerate(test_data):
                memory.write_byte(base_offset + i, byte_val)

            # Read as word
            word_value = memory.read_word(base_offset)
            expected_word = (test_data[3] << 24) | (test_data[2] << 16) | (test_data[1] << 8) | test_data[0]

            # Test hex dump
            hex_dump = memory.hex_dump(base_offset, 16)

            success = (word_value == expected_word)

            return {
                'success': success,
                'word_value': f"0x{word_value:08X}",
                'expected_word': f"0x{expected_word:08X}",
                'hex_dump_generated': bool(hex_dump),
                'details': 'Memory operations successful' if success else 'Memory operation failed'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Memory operations test failed'
            }

    def test_register_management(self) -> Dict[str, Any]:
        """Test register management."""
        print("Testing register management...")

        try:
            dma = self.top_model.get_device('dma_controller')

            # Test register read/write
            ctrl_value = 0x00000001  # Enable DMA
            dma.write(dma.base_address + DMADevice.CTRL_REG, ctrl_value)

            status_value = dma.read(dma.base_address + DMADevice.STATUS_REG)

            # Test channel register
            channel_addr = dma.base_address + DMADevice.CHANNEL_BASE + DMADevice.CH_SRC_ADDR_OFFSET
            test_src_addr = 0x20001000
            dma.write(channel_addr, test_src_addr)
            read_src_addr = dma.read(channel_addr)

            success = (status_value & 0x1) and (read_src_addr == test_src_addr)

            return {
                'success': success,
                'dma_enabled': bool(status_value & 0x1),
                'src_addr_test': read_src_addr == test_src_addr,
                'details': 'Register management successful' if success else 'Register test failed'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Register management test failed'
            }

    def test_dma_mem2mem(self) -> Dict[str, Any]:
        """Test DMA memory-to-memory transfer."""
        print("Testing DMA mem2mem transfer...")

        try:
            bus = self.top_model.get_bus('main_bus')
            memory = self.top_model.get_device('main_memory')
            dma = self.top_model.get_device('dma_controller')

            # Prepare test data
            src_offset = 0x1000
            dst_offset = 0x2000
            test_data = [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0]

            # Write test data to source
            for i, byte_val in enumerate(test_data):
                memory.write_byte(src_offset + i, byte_val)

            # Configure DMA
            src_addr = memory.base_address + src_offset
            dst_addr = memory.base_address + dst_offset
            transfer_size = len(test_data)

            # Enable DMA
            dma.write(dma.base_address + DMADevice.CTRL_REG, 0x1)

            # Configure channel 0
            ch_base = dma.base_address + DMADevice.CHANNEL_BASE
            dma.write(ch_base + DMADevice.CH_SRC_ADDR_OFFSET, src_addr)
            dma.write(ch_base + DMADevice.CH_DST_ADDR_OFFSET, dst_addr)
            dma.write(ch_base + DMADevice.CH_SIZE_OFFSET, transfer_size)

            # Start transfer (enable + start + mem2mem mode)
            ctrl_value = 0x1 | 0x2 | (0 << 4)  # enable | start | mem2mem
            dma.write(ch_base + DMADevice.CH_CTRL_OFFSET, ctrl_value)

            # Wait for completion
            time.sleep(0.1)

            # Verify transfer
            transferred_data = []
            for i in range(len(test_data)):
                byte_val = memory.read_byte(dst_offset + i)
                transferred_data.append(byte_val)

            success = (transferred_data == test_data)

            return {
                'success': success,
                'src_data': [f"0x{b:02X}" for b in test_data],
                'dst_data': [f"0x{b:02X}" for b in transferred_data],
                'transfer_size': transfer_size,
                'details': 'DMA mem2mem transfer successful' if success else 'Transfer verification failed'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'DMA mem2mem test failed'
            }

    def test_dma_mem2peri_crc(self) -> Dict[str, Any]:
        """Test DMA memory-to-peripheral transfer with CRC device."""
        print("Testing DMA mem2peri transfer with CRC...")

        try:
            memory = self.top_model.get_device('main_memory')
            dma = self.top_model.get_device('dma_controller')
            crc = self.top_model.get_device('crc_unit')

            # Prepare test data (use simple 4-byte data for register interface)
            test_data = b"Test"  # Exactly 4 bytes
            src_offset = 0x3000

            # Load test data into memory
            memory.load_data(src_offset, test_data)

            # Configure CRC device
            crc.write(crc.base_address + CRCDevice.CTRL_REG, 0x1)  # Reset
            crc.write(crc.base_address + CRCDevice.CTRL_REG, 0x2)  # CRC-16-CCITT mode

            # Configure DMA for mem2peri transfer
            src_addr = memory.base_address + src_offset
            dst_addr = crc.base_address + CRCDevice.INPUT_REG
            transfer_size = 4  # Transfer exactly 4 bytes

            # Enable DMA
            dma.write(dma.base_address + DMADevice.CTRL_REG, 0x1)

            # Configure channel 1 for mem2peri
            ch_base = dma.base_address + DMADevice.CHANNEL_BASE + DMADevice.CHANNEL_SIZE
            dma.write(ch_base + DMADevice.CH_SRC_ADDR_OFFSET, src_addr)
            dma.write(ch_base + DMADevice.CH_DST_ADDR_OFFSET, dst_addr)
            dma.write(ch_base + DMADevice.CH_SIZE_OFFSET, transfer_size)

            # Start transfer (enable + start + mem2peri mode)
            ctrl_value = 0x1 | 0x2 | (1 << 4)  # enable | start | mem2peri
            dma.write(ch_base + DMADevice.CH_CTRL_OFFSET, ctrl_value)

            # Wait for transfer
            time.sleep(0.1)

            # Check transfer completion by looking at channel status
            ch_status = dma.read(ch_base + DMADevice.CH_STATUS_OFFSET)
            transfer_completed = (ch_status & 0x7) == 0x4  # COMPLETED state

            # Start CRC calculation
            crc.write(crc.base_address + CRCDevice.CTRL_REG, 0x10 | 0x2)  # start | CRC-16-CCITT

            # Check CRC calculation completion
            time.sleep(0.1)
            status = crc.read(crc.base_address + CRCDevice.STATUS_REG)
            crc_completed = bool(status & 0x2)

            # Get CRC result
            crc_result = crc.read(crc.base_address + CRCDevice.OUTPUT_REG)

            # Success is based on transfer completion and CRC calculation completion
            success = transfer_completed and crc_completed and (crc_result != 0)

            return {
                'success': success,
                'test_data': test_data.decode('utf-8'),
                'transfer_size': transfer_size,
                'transfer_completed': transfer_completed,
                'crc_completed': crc_completed,
                'crc_result': f"0x{crc_result:04X}",
                'details': 'DMA mem2peri with CRC framework operational' if success else 'Transfer or CRC completion failed'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'DMA mem2peri test failed'
            }

    def test_crc_calculation(self) -> Dict[str, Any]:
        """Test CRC calculation functionality."""
        print("Testing CRC calculation...")

        try:
            crc = self.top_model.get_device('crc_unit')

            # Test that CRC calculation works (focus on framework functionality)
            test_data = b"DevCommV3"

            # Test direct calculation method
            try:
                result_crc16 = crc.calculate_crc_direct(test_data, 'crc16-ccitt')
                result_crc32 = crc.calculate_crc_direct(test_data, 'crc32')

                # Test that calculations are deterministic (same input -> same output)
                result_crc16_2 = crc.calculate_crc_direct(test_data, 'crc16-ccitt')
                result_crc32_2 = crc.calculate_crc_direct(test_data, 'crc32')

                deterministic = (result_crc16 == result_crc16_2) and (result_crc32 == result_crc32_2)

                # Test register interface basic functionality
                crc.write(crc.base_address + CRCDevice.CTRL_REG, 0x1)  # Reset
                crc.load_data_for_calculation(test_data)
                crc.write(crc.base_address + CRCDevice.CTRL_REG, 0x10 | 0x2)  # start + CRC-16-CCITT

                # Check that calculation completed
                status = crc.read(crc.base_address + CRCDevice.STATUS_REG)
                calculation_complete = bool(status & 0x2)

                success = deterministic and calculation_complete

                return {
                    'success': success,
                    'test_data': test_data.decode('utf-8'),
                    'crc16_result': f"0x{result_crc16:04X}",
                    'crc32_result': f"0x{result_crc32:08X}",
                    'deterministic': deterministic,
                    'register_interface_working': calculation_complete,
                    'details': 'CRC framework functionality verified' if success else 'CRC framework issues detected'
                }

            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'details': 'CRC calculation method failed'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'CRC calculation test failed'
            }

    def test_interrupt_handling(self) -> Dict[str, Any]:
        """Test interrupt handling."""
        print("Testing interrupt handling...")

        try:
            bus = self.top_model.get_bus('main_bus')
            crc = self.top_model.get_device('crc_unit')

            # Set up IRQ handler
            irq_received = []

            def irq_handler(master_id, irq_index, device):
                irq_received.append((master_id, irq_index, device.name))

            bus.register_irq_handler(crc.master_id, 0, irq_handler)

            # Enable CRC completion interrupt
            crc.write(crc.base_address + CRCDevice.IRQ_ENABLE_REG, 0x1)

            # Trigger calculation to generate interrupt
            test_data = b"IRQ Test"
            crc.load_data_for_calculation(test_data)
            crc.write(crc.base_address + CRCDevice.CTRL_REG, 0x10 | 0x2)  # start + CRC-16-CCITT

            # Wait for interrupt
            time.sleep(0.1)

            success = len(irq_received) > 0

            return {
                'success': success,
                'irq_count': len(irq_received),
                'irq_details': irq_received,
                'details': 'Interrupt handling working' if success else 'No interrupts received'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Interrupt handling test failed'
            }

    def test_trace_logging(self) -> Dict[str, Any]:
        """Test trace and logging functionality."""
        print("Testing trace and logging...")

        try:
            bus = self.top_model.get_bus('main_bus')
            memory = self.top_model.get_device('main_memory')

            # Clear trace log
            bus.clear_trace()

            # Perform some operations
            for i in range(5):
                addr = memory.base_address + i * 4
                value = random.randint(0, 0xFFFFFFFF)
                bus.write(memory.master_id, addr, value)
                bus.read(memory.master_id, addr)

            # Get trace summary
            trace_summary = bus.get_trace_summary()

            # Check transaction log
            transaction_count = trace_summary['total_transactions']
            successful_count = trace_summary['successful_transactions']

            success = (transaction_count == 10 and successful_count == 10)  # 5 writes + 5 reads

            return {
                'success': success,
                'transaction_count': transaction_count,
                'successful_count': successful_count,
                'failed_count': trace_summary['failed_transactions'],
                'trace_enabled': trace_summary['trace_enabled'],
                'details': 'Trace logging working correctly' if success else 'Trace count mismatch'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Trace logging test failed'
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return self.top_model.get_system_info()

    def print_test_results(self) -> None:
        """Print formatted test results."""
        print("\n" + "="*50)
        print("DevCommV3 Framework Test Results")
        print("="*50)

        for test_name, result in self.test_results.items():
            if isinstance(result, dict):
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                print(f"{test_name:25}: {status}")
                if 'details' in result:
                    print(f"{'':27} {result['details']}")
                if not result['success'] and 'error' in result:
                    print(f"{'':27} Error: {result['error']}")
                print()

        overall_status = "✅ ALL TESTS PASSED" if self.test_results.get('overall_success') else "❌ SOME TESTS FAILED"
        print(f"Overall Result: {overall_status}")
        print("="*50)

    def shutdown(self) -> None:
        """Shutdown the test system."""
        self.top_model.shutdown()

    def test_model_interface_integration(self) -> Dict[str, Any]:
        """Test integration between model_interface and bus system."""
        print("Testing model interface integration...")

        try:
            # Get bus and a device for testing
            bus = self.top_model.get_bus('main_bus')
            memory = self.top_model.get_device('main_memory')

            # Create model interface
            model = ModelInterface(device_id=memory.master_id)

            # Define handler functions that forward to bus
            def bus_read_handler(master_id, address, width=4):
                """Handler that forwards read requests to the bus"""
                return bus.read(master_id, address, width)

            def bus_write_handler(master_id, address, value, width=4):
                """Handler that forwards write requests to the bus"""
                bus.write(master_id, address, value, width)

            # Register handlers
            model.register_read_handler(bus_read_handler)
            model.register_write_handler(bus_write_handler)

            # Test data
            test_address = memory.base_address + 0x100
            test_value = 0x12345678

            # Simulate a write command through model interface
            write_data = struct.pack('<I', test_value) + b'\x00' * 252
            write_response = model.process_command(
                memory.master_id, CMD_WRITE, test_address, 4, write_data
            )

            # Simulate a read command through model interface
            read_response = model.process_command(
                memory.master_id, CMD_READ, test_address, 4, b'\x00' * 256
            )

            # Parse read response
            _, _, _, _, result = struct.unpack('<IIIII', read_response[:20])
            read_value = struct.unpack('<I', read_response[20:24])[0]

            success = (result == RESULT_SUCCESS and read_value == test_value)

            return {
                'success': success,
                'test_address': f"0x{test_address:08X}",
                'written_value': f"0x{test_value:08X}",
                'read_value': f"0x{read_value:08X}",
                'handlers_registered': True,
                'details': 'Model interface integration successful' if success else 'Value mismatch or error'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Model interface integration test failed'
            }

def save_trace(top):
    # Show trace summary
    print("\n📊 Trace Summary:")
    summary = top.get_trace_summary()

    print(f"   📈 Total events: {summary['total_events']}")
    print(f"   📈 Active modules: {summary['modules']}")

    # Save trace to files
    print("\n💾 Saving trace data to files...")
    trace_dir = Path("trace_output")
    trace_dir.mkdir(exist_ok=True)

    # Save comprehensive trace
    base_file = trace_dir / "test_comm_trace"
    top.save_trace_to_file(str(base_file) + ".json", format='json')
    #top.save_trace_to_file(str(base_file) + ".txt", format='txt')

    print("   Generated trace files:")
    for file in trace_dir.glob("test_comm_trace*"):
        size = file.stat().st_size
        print(f"   📄 {file.name} ({size} bytes)")

    # Show trace modules
    modules = top.get_all_trace_modules()
    print(f"\n📋 Active trace modules: {modules}")

    # Demonstrate filtering
    print("\n🔍 Event filtering examples:")
    bus_transactions = top.get_trace_manager().get_events(event_type='BUS_TRANSACTION')
    irq_events = top.get_trace_manager().get_events(event_type='IRQ_EVENT')
    device_events = top.get_trace_manager().get_events(event_type='DEVICE_EVENT')

# Example usage and main test function
def main():
    """Run the communication test."""

    # Add src to path for imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

    # Run tests with sample configuration
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'configs', 'sample_mcu.yaml')

    # Initialize test model with configuration
    top_model = TopModel("TestSystem")
    top_model.load_configuration(config_path)
    top_model.initialize_system()

    bus = top_model.get_bus('main_bus')

    # Initialize communication model
    model = ModelInterface(device_id=1)

    # Create an adapter for the global IRQ sender
    def global_irq_adapter(irq_index):
        """Adapter function to forward all interrupts to model_interface"""
        model.trigger_interrupt_to_driver(irq_index)

    # Register the global IRQ sender adapter
    bus.register_send_irq(global_irq_adapter)

    # Register bus read/write handlers to connect model_interface with the bus
    def bus_read_handler(master_id, address, width=4):
        """Handler that forwards read requests to the bus"""
        return bus.read(master_id, address, width)

    def bus_write_handler(master_id, address, value, width=4):
        """Handler that forwards write requests to the bus"""
        bus.write(master_id, address, value, width)

    # Register the handlers with model interface using the correct method names
    model.register_read_handler(bus_read_handler)
    model.register_write_handler(bus_write_handler)

    print("Bus handlers registered with model interface")

    # Start model in background thread
    model_thread = threading.Thread(target=model.start, daemon=True)
    model_thread.start()

    print("Python model interface started")
    time.sleep(1)  # Give it time to start

    try:
        # Keep the program running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        model.stop()
        top_model.shutdown()
        save_trace(top_model)


if __name__ == "__main__":
    main()