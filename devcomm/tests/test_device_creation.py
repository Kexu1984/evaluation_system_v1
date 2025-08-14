"""
Simple test to verify all communication devices can be created successfully.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from devcomm.core.bus_model import BusModel
from devcomm.devices.uart_device import UARTDevice
from devcomm.devices.spi_device import SPIDevice
from devcomm.devices.can_device import CANDevice


def test_device_creation():
    """Test that all IO devices can be created successfully."""
    print("Testing IO device creation...")
    
    try:
        # Create bus
        bus = BusModel("TestBus")
        
        # Test UART device creation
        print("Creating UART device...")
        uart = UARTDevice("TestUART", 0x40001000, 0x100, 1, {"baud_rate": 115200})
        bus.add_device(uart)
        print("✅ UART device created successfully")
        
        # Test SPI device creation
        print("Creating SPI device...")
        spi = SPIDevice("TestSPI", 0x40002000, 0x100, 2, 2)
        bus.add_device(spi)
        print("✅ SPI device created successfully")
        
        # Test CAN device creation  
        print("Creating CAN device...")
        can = CANDevice("TestCAN", 0x40003000, 0x100, 3, 500000)
        bus.add_device(can)
        print("✅ CAN device created successfully")
        
        # Test basic device info
        print("\nDevice Information:")
        print(f"UART: {uart.get_device_info()}")
        print(f"SPI: {spi.get_device_info()}")  
        print(f"CAN: {can.get_device_info()}")
        
        # Test IO interface functionality
        print("\nTesting IO interface...")
        uart_status = uart.get_all_connections_status()
        spi_status = spi.get_all_connections_status()
        can_status = can.get_all_connections_status()
        
        print(f"UART connections: {len(uart_status)}")
        print(f"SPI connections: {len(spi_status)}")
        print(f"CAN connections: {len(can_status)}")
        
        print("\n✅ All devices created and tested successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Device creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_device_creation()
    sys.exit(0 if success else 1)