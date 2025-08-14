"""
Memory device implementation for the DevCommV3 framework.

This module provides a memory device that supports byte-level access,
DMA operations, and memory dumping capabilities.
"""

from typing import Optional, Dict, Any, Union
import array
from ..core.base_device import BaseDevice, DMAInterface


class MemoryDevice(BaseDevice, DMAInterface):
    """Memory device implementation with DMA support."""

    def __init__(self, name: str, base_address: int, size: int, master_id: int,
                 initial_value: int = 0, read_only: bool = False):
        # Initialize DMA interface first
        DMAInterface.__init__(self)

        # Store memory-specific parameters
        self.initial_value = initial_value
        self.read_only = read_only

        # Initialize memory storage (using array for efficiency)
        self.memory = array.array('B', [initial_value & 0xFF] * size)

        # Initialize base device
        BaseDevice.__init__(self, name, base_address, size, master_id)

    def init(self) -> None:
        """Initialize memory device - no registers needed for basic memory."""
        # Memory devices typically don't have registers, just memory space
        # But we could add control registers if needed
        pass

    def _read_implementation(self, offset: int, width: int) -> int:
        """Read from memory at the specified offset."""
        if offset + width > self.size:
            raise ValueError(f"Read beyond memory bounds: offset=0x{offset:08X}, width={width}")

        value = 0
        for i in range(width):
            if offset + i < len(self.memory):
                value |= (self.memory[offset + i] << (i * 8))

        #print(">>>>Read value:", f"0x{value:02X}", "from offset:", f"0x{offset:08X}", "with width:", width)
        return value

    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """Write to memory at the specified offset."""
        if self.read_only:
            raise PermissionError(f"Memory device {self.name} is read-only")

        if offset + width > self.size:
            raise ValueError(f"Write beyond memory bounds: offset=0x{offset:08X}, width={width}")

        for i in range(width):
            if offset + i < len(self.memory):
                byte_value = (value >> (i * 8)) & 0xFF
                self.memory[offset + i] = byte_value

        #print(">>>>Wrote value:", f"0x{value:02X}", "to offset:", f"0x{offset:08X}", "with width:", width)

    def read_byte(self, offset: int) -> int:
        """Read a single byte from memory."""
        return self._read_implementation(offset, 1)

    def write_byte(self, offset: int, value: int) -> None:
        """Write a single byte to memory."""
        self._write_implementation(offset, value & 0xFF, 1)

    def read_word(self, offset: int) -> int:
        """Read a 32-bit word from memory."""
        return self._read_implementation(offset, 4)

    def write_word(self, offset: int, value: int) -> None:
        """Write a 32-bit word to memory."""
        self._write_implementation(offset, value & 0xFFFFFFFF, 4)

    def read_halfword(self, offset: int) -> int:
        """Read a 16-bit halfword from memory."""
        return self._read_implementation(offset, 2)

    def write_halfword(self, offset: int, value: int) -> None:
        """Write a 16-bit halfword to memory."""
        self._write_implementation(offset, value & 0xFFFF, 2)

    def clear(self, value: int = 0) -> None:
        """Clear memory with specified value."""
        if self.read_only:
            raise PermissionError(f"Memory device {self.name} is read-only")

        with self.lock:
            for i in range(len(self.memory)):
                self.memory[i] = value & 0xFF

    def load_data(self, offset: int, data: Union[bytes, bytearray, list]) -> None:
        """Load data into memory at specified offset."""
        if self.read_only:
            raise PermissionError(f"Memory device {self.name} is read-only")

        if offset + len(data) > self.size:
            raise ValueError(f"Data too large for memory: offset=0x{offset:08X}, size={len(data)}")

        with self.lock:
            for i, byte_val in enumerate(data):
                if isinstance(byte_val, int):
                    self.memory[offset + i] = byte_val & 0xFF
                else:
                    self.memory[offset + i] = ord(byte_val) & 0xFF

    def get_data(self, offset: int, length: int) -> bytes:
        """Get data from memory as bytes."""
        if offset + length > self.size:
            raise ValueError(f"Read beyond memory bounds: offset=0x{offset:08X}, length={length}")

        with self.lock:
            return bytes(self.memory[offset:offset + length])

    def hex_dump(self, start_offset: int = 0, length: Optional[int] = None,
                 bytes_per_line: int = 16) -> str:
        """Generate a hex dump of memory contents."""
        if length is None:
            length = min(256, self.size - start_offset)

        if start_offset + length > self.size:
            length = self.size - start_offset

        lines = []
        for i in range(0, length, bytes_per_line):
            addr = self.base_address + start_offset + i
            line_data = self.memory[start_offset + i:start_offset + i + bytes_per_line]

            # Format address
            addr_str = f"{addr:08X}"

            # Format hex bytes
            hex_str = ' '.join(f"{b:02X}" for b in line_data)
            hex_str = hex_str.ljust(bytes_per_line * 3 - 1)

            # Format ASCII representation
            ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in line_data)

            lines.append(f"{addr_str}: {hex_str} |{ascii_str}|")

        return '\n'.join(lines)

    def save_to_file(self, filename: str, start_offset: int = 0,
                     length: Optional[int] = None) -> None:
        """Save memory contents to file."""
        if length is None:
            length = self.size - start_offset

        data = self.get_data(start_offset, length)
        with open(filename, 'wb') as f:
            f.write(data)

    def load_from_file(self, filename: str, offset: int = 0) -> None:
        """Load memory contents from file."""
        if self.read_only:
            raise PermissionError(f"Memory device {self.name} is read-only")

        with open(filename, 'rb') as f:
            data = f.read()

        self.load_data(offset, data)

    def _reset_implementation(self) -> None:
        """Reset memory to initial state."""
        with self.lock:
            for i in range(len(self.memory)):
                self.memory[i] = self.initial_value & 0xFF

    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory device information."""
        info = self.get_device_info()
        info.update({
            'memory_type': 'RAM' if not self.read_only else 'ROM',
            'initial_value': f"0x{self.initial_value:02X}",
            'dma_enabled': self.dma_enabled,
            'dma_channel': self.dma_channel
        })
        return info

    def __str__(self) -> str:
        mem_type = 'ROM' if self.read_only else 'RAM'
        return f"{mem_type}({self.name}, 0x{self.base_address:08X}-0x{self.base_address + self.size - 1:08X})"