"""
Simple test for IO Interface functionality.
"""

import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from devcomm.core.bus_model import BusModel
from devcomm.devices.uart_device import UARTDevice
from devcomm.utils.external_devices import SimulatedUARTDevice


def test_basic_uart():
    """Test basic UART functionality."""
    print("Testing basic UART functionality...")

    try:
        # Create bus
        bus = BusModel("TestBus")

        # Create UART device
        uart = UARTDevice("TestUART", 0x40001000, 0x100, 1, 115200)
        bus.add_device(uart)

        # Create external UART device
        external_uart = SimulatedUARTDevice("external_uart", "OK")

        # Connect external device
        if not uart.connect_external_uart(external_uart):
            print("❌ Failed to connect external UART")
            return False

        # Enable UART
        uart.write(uart.base_address + uart.CTRL_REG,
                  uart.CTRL_ENABLE | uart.CTRL_TX_ENABLE | uart.CTRL_RX_ENABLE)

        # Transmit test data
        test_char = ord('A')
        #uart.write(uart.base_address + uart.TX_DATA_REG, test_char)
        bus.write(1, uart.base_address + uart.TX_DATA_REG, test_char)
        bus.write(1, uart.base_address + uart.TX_DATA_REG, test_char)
        bus.write(1, uart.base_address + uart.TX_DATA_REG, test_char)
        bus.write(1, uart.base_address + uart.TX_DATA_REG, test_char)
        bus.write(1, uart.base_address + uart.TX_DATA_REG, test_char)

        # Wait for data exchange
        time.sleep(0.1)

        # Check if external device received data
        received_string = external_uart.get_received_string()

        # Disconnect
        uart.disconnect_external_uart()

        if 'A' in received_string:
            print("✅ UART test passed!")
            print(f"   Sent: 'A' (0x{test_char:02X})")
            print(f"   Received: '{received_string}'")
            return True
        else:
            print(f"❌ UART test failed: Expected 'A', got '{received_string}'")
            return False

    except Exception as e:
        print(f"❌ UART test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_basic_uart()
    sys.exit(0 if success else 1)