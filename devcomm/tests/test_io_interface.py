"""
Test cases for IO Interface functionality.

This module provides comprehensive testing for the IO interface and
communication devices (UART, SPI, CAN).
"""

import time
import sys
import os
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from devcomm.core.top_model import TopModel
from devcomm.core.bus_model import BusModel
from devcomm.devices.uart_device import UARTDevice
from devcomm.devices.spi_device import SPIDevice
from devcomm.devices.can_device import CANDevice
from devcomm.utils.external_devices import (
    SimulatedUARTDevice, SimulatedSPIDevice, SimulatedCANDevice,
    RandomDataGenerator, EchoDevice
)


class IOInterfaceTestModel:
    """Test model for IO interface functionality."""

    def __init__(self):
        self.top_model = TopModel("IOTestSystem")
        self.test_results = {}
        self._create_test_configuration()

    def _create_test_configuration(self) -> None:
        """Create test configuration with communication devices."""
        config = {
            'system': {
                'name': 'IOTestSystem',
                'buses': {
                    'main_bus': {
                        'name': 'MainBus'
                    }
                },
                'devices': {
                    'uart_device': {
                        'device_type': 'uart',
                        'name': 'TestUART',
                        'base_address': 0x40001000,
                        'size': 0x100,
                        'master_id': 1,
                        'bus': 'main_bus',
                        'baud_rate': 115200
                    },
                    'spi_device': {
                        'device_type': 'spi',
                        'name': 'TestSPI',
                        'base_address': 0x40002000,
                        'size': 0x100,
                        'master_id': 2,
                        'bus': 'main_bus',
                        'num_chip_selects': 2
                    },
                    'can_device': {
                        'device_type': 'can',
                        'name': 'TestCAN',
                        'base_address': 0x40003000,
                        'size': 0x100,
                        'master_id': 3,
                        'bus': 'main_bus',
                        'baud_rate': 500000
                    }
                }
            }
        }

        # Use configuration-based initialization
        self.top_model.create_configuration(config)
        self.top_model.initialize_system()


    def test_uart_loopback(self) -> Dict[str, Any]:
        """Test UART loopback functionality."""
        try:
            print("Testing UART loopback...")

            # Get UART device
            uart = self.top_model.get_device("uart_device")
            bus = self.top_model.get_bus("main_bus")

            # Create external UART device
            external_uart = SimulatedUARTDevice("external_uart", "UART_OK")

            # Connect external device
            if not uart.connect_external_uart(external_uart):
                return {'status': 'FAIL', 'error': 'Failed to connect external UART'}

            # Enable UART
            uart.write(uart.base_address + uart.CTRL_REG,
                      uart.CTRL_ENABLE | uart.CTRL_TX_ENABLE | uart.CTRL_RX_ENABLE)

            # Transmit test string
            test_string = "Hello UART!"
            uart.transmit_string(test_string)

            # Wait for data exchange
            time.sleep(0.1)

            # Check if external device received data
            received_string = external_uart.get_received_string()

            # Disconnect
            uart.disconnect_external_uart()

            if test_string in received_string:
                return {'status': 'PASS', 'transmitted': test_string, 'received': received_string}
            else:
                return {'status': 'FAIL', 'error': f'Expected: {test_string}, Got: {received_string}'}

        except Exception as e:
            return {'status': 'FAIL', 'error': str(e)}

    def test_spi_communication(self) -> Dict[str, Any]:
        """Test SPI communication functionality."""
        try:
            print("Testing SPI communication...")

            # Get SPI device
            spi = self.top_model.get_device("spi_device")

            # Create external SPI device
            external_spi = SimulatedSPIDevice("external_spi", [0xAA, 0x55, 0xFF, 0x00])

            # Connect external device to chip select 0
            if not spi.connect_spi_device(0, external_spi):
                return {'status': 'FAIL', 'error': 'Failed to connect external SPI device'}

            # Enable SPI
            spi.write(spi.base_address + spi.CTRL_REG, spi.CTRL_ENABLE)

            # Perform SPI transfer
            tx_data = [0x12, 0x34, 0x56, 0x78]
            rx_data = spi.transfer_data(0, tx_data)

            # Wait for data exchange
            time.sleep(0.1)

            # Check if external device received data
            received_data = external_spi.get_received_data()

            # Disconnect
            spi.disconnect_spi_device(0)

            if len(received_data) >= len(tx_data):
                return {
                    'status': 'PASS',
                    'transmitted': tx_data,
                    'received_by_external': received_data[:len(tx_data)],
                    'rx_data': rx_data
                }
            else:
                return {'status': 'FAIL', 'error': f'Expected at least {len(tx_data)} bytes, got {len(received_data)}'}

        except Exception as e:
            return {'status': 'FAIL', 'error': str(e)}

    def test_can_messaging(self) -> Dict[str, Any]:
        """Test CAN messaging functionality."""
        try:
            print("Testing CAN messaging...")

            # Get CAN device
            can = self.top_model.get_device("can_device")

            # Create external CAN device
            external_can = SimulatedCANDevice("external_can", 0x456)

            # Connect external device
            if not can.connect_can_bus(external_can):
                return {'status': 'FAIL', 'error': 'Failed to connect external CAN device'}

            # Enable CAN
            can.write(can.base_address + can.CTRL_REG, can.CTRL_ENABLE)

            # Send CAN message
            test_message_id = 0x123
            test_data = [0xDE, 0xAD, 0xBE, 0xEF]

            if not can.send_can_message(test_message_id, test_data):
                return {'status': 'FAIL', 'error': 'Failed to send CAN message'}

            # Wait for data exchange
            time.sleep(0.1)

            # Check if external device received data
            received_messages = external_can.get_received_messages()

            # Disconnect
            can.disconnect_can_bus()

            if len(received_messages) > 0:
                return {
                    'status': 'PASS',
                    'sent_id': test_message_id,
                    'sent_data': test_data,
                    'received_bytes': len(received_messages)
                }
            else:
                return {'status': 'FAIL', 'error': 'No data received by external CAN device'}

        except Exception as e:
            return {'status': 'FAIL', 'error': str(e)}

    def test_io_interface_status(self) -> Dict[str, Any]:
        """Test IO interface status reporting."""
        try:
            print("Testing IO interface status...")

            # Get all devices
            uart = self.top_model.get_device("uart_device")
            spi = self.top_model.get_device("spi_device")
            can = self.top_model.get_device("can_device")

            # Get status from all devices
            uart_status = uart.get_uart_status()
            spi_status = spi.get_spi_status()
            can_status = can.get_can_status()

            return {
                'status': 'PASS',
                'uart_status': uart_status,
                'spi_status': spi_status,
                'can_status': can_status
            }

        except Exception as e:
            return {'status': 'FAIL', 'error': str(e)}

    def test_concurrent_connections(self) -> Dict[str, Any]:
        """Test multiple concurrent IO connections."""
        try:
            print("Testing concurrent connections...")

            # Get devices
            uart = self.top_model.get_device("uart_device")
            spi = self.top_model.get_device("spi_device")
            can = self.top_model.get_device("can_device")

            # Create external devices
            external_uart = EchoDevice("echo_uart")
            external_spi = EchoDevice("echo_spi")
            external_can = EchoDevice("echo_can")

            # Connect all devices
            uart_connected = uart.connect_external_uart(external_uart)
            spi_connected = spi.connect_spi_device(0, external_spi)
            can_connected = can.connect_can_bus(external_can)

            print(f"UART connected: {uart_connected}, SPI connected: {spi_connected}, CAN connected: {can_connected}")
            if not (uart_connected and spi_connected and can_connected):
                return {'status': 'FAIL', 'error': 'Failed to connect all devices'}

            # Enable all devices
            uart.write(uart.base_address + uart.CTRL_REG,
                      uart.CTRL_ENABLE | uart.CTRL_TX_ENABLE | uart.CTRL_RX_ENABLE)
            spi.write(spi.base_address + spi.CTRL_REG, spi.CTRL_ENABLE)
            can.write(can.base_address + can.CTRL_REG, can.CTRL_ENABLE)

            # Send data simultaneously
            uart.write(uart.base_address + uart.TX_DATA_REG, ord('A'))
            spi.write(spi.base_address + spi.DATA_REG, 0x55)
            can.send_can_message(0x100, [0x42])

            # Wait for processing
            time.sleep(0.2)

            # Disconnect all
            uart.disconnect_external_uart()
            spi.disconnect_spi_device(0)
            can.disconnect_can_bus()

            return {'status': 'PASS', 'connections': 'All devices connected and disconnected successfully'}

        except Exception as e:
            return {'status': 'FAIL', 'error': str(e)}

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all IO interface tests."""
        print("Starting IO Interface Tests...")
        print("=" * 50)

        tests = [
            ('uart_loopback', self.test_uart_loopback),
            ('spi_communication', self.test_spi_communication),
            ('can_messaging', self.test_can_messaging),
            ('io_interface_status', self.test_io_interface_status),
            ('concurrent_connections', self.test_concurrent_connections)
        ]

        results = {}
        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\nRunning {test_name}...")
            try:
                result = test_func()
                results[test_name] = result
                if result['status'] == 'PASS':
                    passed += 1
                    print(f"✅ {test_name}: PASS")
                else:
                    print(f"❌ {test_name}: FAIL - {result.get('error', 'Unknown error')}")
            except Exception as e:
                results[test_name] = {'status': 'FAIL', 'error': str(e)}
                print(f"❌ {test_name}: FAIL - {str(e)}")

        print("\n" + "=" * 50)
        print("IO Interface Test Summary")
        print("=" * 50)

        for test_name, result in results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {test_name:25}: {result['status']}")
            if result['status'] == 'FAIL' and 'error' in result:
                print(f"    Error: {result['error']}")

        print(f"\nOverall Result: {passed}/{total} tests passed")
        print("=" * 50)

        return {
            'passed': passed,
            'total': total,
            'success_rate': passed / total if total > 0 else 0,
            'results': results
        }


def main():
    """Main test function."""
    test_model = IOInterfaceTestModel()
    return test_model.run_all_tests()


if __name__ == "__main__":
    main()