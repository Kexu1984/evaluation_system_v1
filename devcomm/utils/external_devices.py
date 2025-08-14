"""
Example external devices for testing IO interface functionality.

This module provides simple external device implementations that can be
connected to devices with IO interfaces for testing purposes.
"""

import time
import random
from typing import List, Optional
from ..core.io_interface import ExternalDevice


class SimulatedUARTDevice(ExternalDevice):
    """Simulated external UART device for testing."""
    
    def __init__(self, device_id: str, response_data: str = "Hello from external UART!"):
        super().__init__(device_id)
        self.response_data = response_data
        self.data_index = 0
        self.received_data = []
        
    def on_data_received(self, data: int, width: int, connection_id: str):
        """Handle data received from connected UART device."""
        self.received_data.append(data)
        print(f"External UART {self.device_id} received: 0x{data:02X} ('{chr(data)}') from {connection_id}")
    
    def generate_data(self) -> tuple:
        """Generate data to send to connected UART device."""
        if self.data_index < len(self.response_data):
            char = self.response_data[self.data_index]
            self.data_index += 1
            return (ord(char), 1)
        return (None, 0)
    
    def get_received_string(self) -> str:
        """Get received data as string."""
        return ''.join(chr(b) for b in self.received_data if 32 <= b <= 126)
    
    def reset(self):
        """Reset the external device."""
        self.data_index = 0
        self.received_data.clear()


class SimulatedSPIDevice(ExternalDevice):
    """Simulated external SPI device for testing."""
    
    def __init__(self, device_id: str, response_pattern: List[int] = None):
        super().__init__(device_id)
        self.response_pattern = response_pattern or [0xAA, 0x55, 0xFF, 0x00]
        self.response_index = 0
        self.received_data = []
        
    def on_data_received(self, data: int, width: int, connection_id: str):
        """Handle data received from connected SPI device."""
        self.received_data.append(data)
        print(f"External SPI {self.device_id} received: 0x{data:02X} from {connection_id}")
    
    def generate_data(self) -> tuple:
        """Generate data to send to connected SPI device."""
        if self.response_pattern:
            response = self.response_pattern[self.response_index % len(self.response_pattern)]
            self.response_index += 1
            return (response, 1)
        return (0, 1)
    
    def get_received_data(self) -> List[int]:
        """Get all received data."""
        return self.received_data.copy()
    
    def reset(self):
        """Reset the external device."""
        self.response_index = 0
        self.received_data.clear()


class SimulatedCANDevice(ExternalDevice):
    """Simulated external CAN device for testing."""
    
    def __init__(self, device_id: str, can_id: int = 0x123):
        super().__init__(device_id)
        self.can_id = can_id
        self.received_messages = []
        self.send_counter = 0
        
    def on_data_received(self, data: int, width: int, connection_id: str):
        """Handle data received from connected CAN device."""
        self.received_messages.append(data)
        print(f"External CAN {self.device_id} received: 0x{data:02X} from {connection_id}")
    
    def generate_data(self) -> tuple:
        """Generate CAN data to send to connected device."""
        # Generate a simple CAN message every few calls
        if self.send_counter % 100 == 0:
            # Simple message format: send message ID byte by byte
            message_bytes = [
                (self.can_id >> 0) & 0xFF,
                (self.can_id >> 8) & 0xFF,
                0x00, 0x00,  # Remaining ID bytes
                0x04,        # DLC = 4
                0xDE, 0xAD, 0xBE, 0xEF,  # Data
                0x00, 0x00, 0x00,        # Padding
                0x00         # Flags
            ]
            
            byte_index = (self.send_counter // 100) % len(message_bytes)
            self.send_counter += 1
            return (message_bytes[byte_index], 1)
        
        self.send_counter += 1
        return (None, 0)
    
    def get_received_messages(self) -> List[int]:
        """Get all received message bytes."""
        return self.received_messages.copy()
    
    def reset(self):
        """Reset the external device."""
        self.send_counter = 0
        self.received_messages.clear()


class RandomDataGenerator(ExternalDevice):
    """External device that generates random data for testing."""
    
    def __init__(self, device_id: str, data_rate: float = 0.1):
        super().__init__(device_id)
        self.data_rate = data_rate  # Probability of generating data per call
        self.received_data = []
        
    def on_data_received(self, data: int, width: int, connection_id: str):
        """Handle data received from connected device."""
        self.received_data.append(data)
        print(f"Random generator {self.device_id} received: 0x{data:02X} from {connection_id}")
    
    def generate_data(self) -> tuple:
        """Generate random data occasionally."""
        if random.random() < self.data_rate:
            return (random.randint(0, 255), 1)
        return (None, 0)
    
    def get_received_data(self) -> List[int]:
        """Get all received data."""
        return self.received_data.copy()
    
    def reset(self):
        """Reset the external device."""
        self.received_data.clear()


class EchoDevice(ExternalDevice):
    """External device that echoes back received data."""
    
    def __init__(self, device_id: str):
        super().__init__(device_id)
        self.echo_buffer = []
        
    def on_data_received(self, data: int, width: int, connection_id: str):
        """Handle data received from connected device."""
        print(f"Echo device {self.device_id} received: 0x{data:02X} from {connection_id}")
        # Add to echo buffer to send back
        self.echo_buffer.append(data)
    
    def generate_data(self) -> tuple:
        """Echo back received data."""
        if self.echo_buffer:
            return (self.echo_buffer.pop(0), 1)
        return (None, 0)
    
    def reset(self):
        """Reset the external device."""
        self.echo_buffer.clear()