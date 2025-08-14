"""
Example UART Driver showing proper device configuration.
This demonstrates how external drivers should configure the UART device
through register operations, not through device model initialization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.devcomm.devices.uart_device import UARTDevice
from src.devcomm.core.top_model import TopModel
from src.devcomm.core.bus_model import BusModel

test_uart_base = 0x40000000
test_uart_size = 0x1000
def configure_uart_baud_rate(uart_device, target_baud: int, system_clock: int = 168000000):
    """
    Configure UART baud rate through register operations (driver responsibility).

    Args:
        uart_device: UART device instance
        target_baud: Target baud rate
        system_clock: System clock frequency
    """
    print(f"\n=== Configuring UART Baud Rate to {target_baud} ===")

    # Choose sample rate (16x is most common)
    sample_rate = 16
    uart_device.write(test_uart_base + 0x028, 0)  # SMP=0 for 16x sampling

    # Calculate divisor
    divisor_float = system_clock / (sample_rate * target_baud)
    divisor_int = int(divisor_float)
    divisor_frac = int((divisor_float - divisor_int) * 32) & 0x1F

    # Set divisor registers
    uart_device.write(test_uart_base + 0x004, divisor_int & 0xFF)        # DIVL
    uart_device.write(test_uart_base + 0x008, (divisor_int >> 8) & 0xFF) # DIVH
    uart_device.write(test_uart_base + 0x044, divisor_frac)              # DIVF

    # Verify configuration
    actual_baud = uart_device.get_current_baud_rate()
    print(f"Target baud rate: {target_baud}")
    print(f"Actual baud rate: {actual_baud:.2f}")
    print(f"Error: {abs(actual_baud - target_baud)/target_baud*100:.2f}%")

def configure_uart_data_format(uart_device, data_bits: int, stop_bits: int, parity: str):
    """
    Configure UART data format through register operations (driver responsibility).

    Args:
        uart_device: UART device instance
        data_bits: Number of data bits (7, 8, 9)
        stop_bits: Number of stop bits (1, 2)
        parity: Parity setting ('none', 'even', 'odd')
    """
    print(f"\n=== Configuring UART Data Format: {data_bits}{parity[0].upper()}{stop_bits} ===")

    cr0 = 0

    # Word length selection
    if data_bits == 7:
        cr0 |= 0x00  # WLS=0
    elif data_bits == 8:
        cr0 |= 0x01  # WLS=1
    elif data_bits == 9:
        cr0 |= 0x02  # WLS=2

    # Stop bits
    if stop_bits == 2:
        cr0 |= 0x04  # STB=1

    # Parity
    if parity == 'even':
        cr0 |= 0x08  # PEN=1
        cr0 |= 0x10  # EPS=1
    elif parity == 'odd':
        cr0 |= 0x08  # PEN=1
        # EPS=0 for odd parity

    # Write configuration
    uart_device.write(test_uart_base + 0x00C, cr0)

    # Verify configuration
    data_format = uart_device.get_current_data_format()
    print(f"Configured format: {data_format}")

def enable_uart_operation(uart_device):
    """
    Enable UART TX/RX operation through register operations (driver responsibility).
    """
    print(f"\n=== Enabling UART Operation ===")

    # Enable transmitter and receiver
    cr1 = uart_device.read(test_uart_base + 0x010)
    cr1 |= 0x03  # TXEN=1, RXEN=1
    uart_device.write(test_uart_base + 0x010, cr1)

    # Enable FIFO mode
    uart_device.write(test_uart_base + 0x014, 0x01)  # FIFOE=1

    # Enable interrupts
    ier = 0x03  # ERDNE=1 (RX), ETXTC=1 (TX complete)
    uart_device.write(test_uart_base + 0x01C, ier)

    print("UART TX/RX enabled, FIFO mode enabled, interrupts enabled")

def test_uart_communication(uart_device):
    """
    Test UART communication through register operations.
    """
    print(f"\n=== Testing UART Communication ===")

    # Enable loopback mode for testing
    cr1 = uart_device.read(test_uart_base + 0x010)
    cr1 |= 0x10  # LOOP=1
    uart_device.write(test_uart_base + 0x010, cr1)

    # Send test data
    test_data = [0x48, 0x65, 0x6C, 0x6C, 0x6F]  # "Hello"
    print(f"Sending data: {[hex(d) for d in test_data]}")

    for data in test_data:
        # Write to transmit register
        uart_device.write(test_uart_base + 0x000, data)

        # Check if data was received (loopback mode)
        sr0 = uart_device.read(test_uart_base + 0x020)
        if sr0 & 0x01:  # DR=1 (data ready)
            received = uart_device.read(test_uart_base + 0x000)
            print(f"Sent: 0x{data:02X}, Received: 0x{received:02X}")

def main():
    """Demonstrate proper UART driver configuration."""
    print("=== UART Driver Configuration Example ===")

    bus = BusModel('TestBus')

    # Create UART device (only hardware environment initialization)
    uart = UARTDevice("UART0", test_uart_base, test_uart_size, 1, {
        'system_clock': 168000000,
        'fifo_size': 16
    })

    bus.add_device(uart)

    # Start device (hardware ready)
    uart.start_device()

    # Driver configures the device through register operations
    configure_uart_baud_rate(uart, 115200)
    configure_uart_data_format(uart, 8, 1, 'none')
    enable_uart_operation(uart)

    # Test communication
    test_uart_communication(uart)

    # Show final status
    print(f"\n=== Final UART Status ===")
    status = uart.get_status_info()
    for key, value in status.items():
        if key not in ['io_connections']:  # Skip complex nested data
            print(f"{key}: {value}")

    # Clean up
    uart.stop_device()
    print("\n=== Driver Example Complete ===")

if __name__ == "__main__":
    main()