"""
Register management system for the DevCommV3 framework.

This module provides register types, register definitions, and register management
functionality for device simulation.
"""

from enum import Enum
from typing import Optional, Callable, Dict, Any
import threading


class RegisterType(Enum):
    """Define different types of registers."""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"
    READ_CLEAR = "read_clear"


class Register:
    """Individual register representation."""
    
    def __init__(self, offset: int, name: str, register_type: RegisterType = RegisterType.READ_WRITE,
                 reset_value: int = 0, mask: int = 0xFFFFFFFF,
                 read_callback: Optional[Callable] = None,
                 write_callback: Optional[Callable] = None):
        self.offset = offset
        self.name = name
        self.register_type = register_type
        self.reset_value = reset_value
        self.mask = mask
        self.value = reset_value
        self.read_callback = read_callback
        self.write_callback = write_callback
        
    def read(self, device_instance, width: int = 4) -> int:
        """Read register value with optional callback."""
        if self.register_type == RegisterType.WRITE_ONLY:
            raise PermissionError(f"Register {self.name} is write-only")
            
        # Apply mask for width
        if width == 1:
            mask = 0xFF
        elif width == 2:
            mask = 0xFFFF
        else:
            mask = 0xFFFFFFFF
            
        value = self.value & mask
        
        # Execute read callback if provided
        if self.read_callback:
            value = self.read_callback(device_instance, self.offset, value)
            
        # Handle read-clear registers
        if self.register_type == RegisterType.READ_CLEAR:
            self.value = 0
            
        return value
        
    def write(self, device_instance, value: int, width: int = 4) -> None:
        """Write register value with optional callback."""
        if self.register_type == RegisterType.READ_ONLY:
            raise PermissionError(f"Register {self.name} is read-only")
            
        # Apply mask for width
        if width == 1:
            mask = 0xFF
        elif width == 2:
            mask = 0xFFFF
        else:
            mask = 0xFFFFFFFF
            
        # Apply register mask
        masked_value = value & self.mask & mask
        
        if self.register_type != RegisterType.WRITE_ONLY:
            self.value = masked_value
            
        # Execute write callback if provided
        if self.write_callback:
            self.write_callback(device_instance, self.offset, masked_value)


class RegisterManager:
    """Manages all registers for a device."""
    
    def __init__(self):
        self.registers: Dict[int, Register] = {}
        self.lock = threading.RLock()
        
    def define_register(self, offset: int, name: str, register_type: RegisterType = RegisterType.READ_WRITE,
                       reset_value: int = 0, mask: int = 0xFFFFFFFF,
                       read_callback: Optional[Callable] = None,
                       write_callback: Optional[Callable] = None) -> None:
        """Define a new register."""
        with self.lock:
            if offset in self.registers:
                raise ValueError(f"Register at offset 0x{offset:08X} already exists")
                
            register = Register(offset, name, register_type, reset_value, mask,
                              read_callback, write_callback)
            self.registers[offset] = register
            
    def read_register(self, device_instance, offset: int, width: int = 4) -> int:
        """Read from a register at the specified offset."""
        with self.lock:
            if offset not in self.registers:
                raise KeyError(f"No register at offset 0x{offset:08X}")
            return self.registers[offset].read(device_instance, width)
            
    def write_register(self, device_instance, offset: int, value: int, width: int = 4) -> None:
        """Write to a register at the specified offset."""
        with self.lock:
            if offset not in self.registers:
                raise KeyError(f"No register at offset 0x{offset:08X}")
            self.registers[offset].write(device_instance, value, width)
            
    def reset_all(self) -> None:
        """Reset all registers to their default values."""
        with self.lock:
            for register in self.registers.values():
                register.value = register.reset_value
                
    def get_register_info(self, offset: int) -> Dict[str, Any]:
        """Get information about a register."""
        with self.lock:
            if offset not in self.registers:
                raise KeyError(f"No register at offset 0x{offset:08X}")
            reg = self.registers[offset]
            return {
                'name': reg.name,
                'offset': reg.offset,
                'type': reg.register_type.value,
                'value': reg.value,
                'reset_value': reg.reset_value,
                'mask': reg.mask
            }
            
    def list_registers(self) -> Dict[int, Dict[str, Any]]:
        """List all registers and their information."""
        with self.lock:
            return {offset: self.get_register_info(offset) for offset in self.registers.keys()}