"""
SPI device implementation for the DevCommV3 framework.

This module provides an SPI device that supports external peripheral connections
using the IO interface for simulating real SPI communication.
"""

from typing import Optional, Dict, Any, List
from ..core.base_device import BaseDevice
from ..core.io_interface import IOInterface, IODirection
from ..core.registers import RegisterType


class SPIDevice(BaseDevice, IOInterface):
    """SPI device implementation with IO interface support."""
    
    # Register offsets
    CTRL_REG = 0x00       # Control register
    STATUS_REG = 0x04     # Status register
    DATA_REG = 0x08       # Data register (TX/RX)
    CLOCK_REG = 0x0C      # Clock configuration register
    CS_REG = 0x10         # Chip select register
    IRQ_ENABLE_REG = 0x14 # IRQ enable register
    IRQ_STATUS_REG = 0x18 # IRQ status register
    
    # Control register bits
    CTRL_ENABLE = 0x01
    CTRL_MASTER = 0x02
    CTRL_SLAVE = 0x04
    CTRL_CPOL = 0x08      # Clock polarity
    CTRL_CPHA = 0x10      # Clock phase
    CTRL_LSB_FIRST = 0x20
    CTRL_RESET = 0x80
    
    # Status register bits
    STATUS_READY = 0x01
    STATUS_BUSY = 0x02
    STATUS_TX_EMPTY = 0x04
    STATUS_RX_FULL = 0x08
    
    # IRQ enable/status bits
    IRQ_TRANSFER_COMPLETE = 0x01
    IRQ_RX_READY = 0x02
    IRQ_ERROR = 0x04
    
    def __init__(self, name: str, base_address: int, size: int, master_id: int,
                 num_chip_selects: int = 4):
        # Initialize IO interface first
        IOInterface.__init__(self)
        
        # Store SPI-specific parameters
        self.num_chip_selects = num_chip_selects
        self.active_cs = None
        self.tx_buffer = []
        self.rx_buffer = []
        self.clock_freq = 1000000  # 1MHz default
        
        # Initialize base device
        BaseDevice.__init__(self, name, base_address, size, master_id)
        
        # Create connections for each chip select
        for i in range(num_chip_selects):
            self.create_connection(f"spi_cs{i}", IODirection.BIDIRECTIONAL)
    
    def init(self) -> None:
        """Initialize SPI device registers."""
        # Control register - default disabled, master mode
        self.register_manager.define_register(
            self.CTRL_REG, "SPI_CTRL", RegisterType.READ_WRITE, self.CTRL_MASTER
        )
        
        # Status register - ready, TX empty
        self.register_manager.define_register(
            self.STATUS_REG, "SPI_STATUS", RegisterType.READ_ONLY,
            self.STATUS_READY | self.STATUS_TX_EMPTY
        )
        
        # Data register
        self.register_manager.define_register(
            self.DATA_REG, "SPI_DATA", RegisterType.READ_WRITE, 0x00000000,
            write_callback=self._on_data_write,
            read_callback=self._on_data_read
        )
        
        # Clock configuration register
        self.register_manager.define_register(
            self.CLOCK_REG, "SPI_CLOCK", RegisterType.READ_WRITE, self.clock_freq
        )
        
        # Chip select register
        self.register_manager.define_register(
            self.CS_REG, "SPI_CS", RegisterType.READ_WRITE, 0x00000000,
            write_callback=self._on_cs_write
        )
        
        # IRQ enable register
        self.register_manager.define_register(
            self.IRQ_ENABLE_REG, "SPI_IRQ_ENABLE", RegisterType.READ_WRITE, 0x00000000
        )
        
        # IRQ status register
        self.register_manager.define_register(
            self.IRQ_STATUS_REG, "SPI_IRQ_STATUS", RegisterType.READ_WRITE, 0x00000000
        )
        
        # Enable IO by default
        self.enable_io()
    
    def _read_implementation(self, offset: int, width: int) -> int:
        """SPI-specific read implementation."""
        if offset in self.register_manager.registers:
            return self.register_manager.read_register(self, offset, width)
        return 0
    
    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """SPI-specific write implementation."""
        if offset in self.register_manager.registers:
            self.register_manager.write_register(self, offset, value, width)
    
    def _on_data_write(self, device_instance, offset: int, value: int) -> None:
        """Handle data register write (TX operation)."""
        ctrl_reg = self.register_manager.read_register(self, self.CTRL_REG)
        
        # Check if SPI is enabled
        if ctrl_reg & self.CTRL_ENABLE:
            # Set busy status
            status = self.register_manager.read_register(self, self.STATUS_REG)
            status |= self.STATUS_BUSY
            status &= ~self.STATUS_TX_EMPTY
            self.register_manager.registers[self.STATUS_REG].value = status
            
            # Send data to the active chip select
            if self.active_cs is not None:
                connection_id = f"spi_cs{self.active_cs}"
                self.output_data(connection_id, value, 1)
            
            # Simulate transfer completion
            self._complete_transfer()
    
    def _on_data_read(self, device_instance, offset: int, current_value: int) -> int:
        """Handle data register read (RX operation)."""
        if self.rx_buffer:
            return self.rx_buffer.pop(0)
        return 0
    
    def _on_cs_write(self, device_instance, offset: int, value: int) -> None:
        """Handle chip select register write."""
        # Find which CS is active (assuming one-hot encoding)
        old_cs = self.active_cs
        self.active_cs = None
        
        for i in range(self.num_chip_selects):
            if value & (1 << i):
                self.active_cs = i
                break
        
        # If CS changed, handle connection changes
        if old_cs != self.active_cs:
            if old_cs is not None:
                # Deactivate old connection
                self.disconnect_external_device(f"spi_cs{old_cs}")
            
            if self.active_cs is not None:
                # Activate new connection - this would typically be done externally
                pass
    
    def _complete_transfer(self) -> None:
        """Complete SPI transfer and update status."""
        # Clear busy status
        status = self.register_manager.read_register(self, self.STATUS_REG)
        status &= ~self.STATUS_BUSY
        status |= self.STATUS_TX_EMPTY
        self.register_manager.registers[self.STATUS_REG].value = status
        
        # Trigger transfer complete interrupt if enabled
        irq_enable = self.register_manager.read_register(self, self.IRQ_ENABLE_REG)
        if irq_enable & self.IRQ_TRANSFER_COMPLETE:
            irq_status = self.register_manager.read_register(self, self.IRQ_STATUS_REG)
            irq_status |= self.IRQ_TRANSFER_COMPLETE
            self.register_manager.registers[self.IRQ_STATUS_REG].value = irq_status
            self.trigger_interrupt(0)
    
    def _handle_input_data(self, connection_id: str, data: int, width: int):
        """Handle input data from external SPI device."""
        ctrl_reg = self.register_manager.read_register(self, self.CTRL_REG)
        
        # Check if SPI is enabled
        if ctrl_reg & self.CTRL_ENABLE:
            # Add received data to RX buffer
            self.rx_buffer.append(data)
            
            # Update status register
            status = self.register_manager.read_register(self, self.STATUS_REG)
            status |= self.STATUS_RX_FULL
            self.register_manager.registers[self.STATUS_REG].value = status
            
            # Trigger RX ready interrupt if enabled
            irq_enable = self.register_manager.read_register(self, self.IRQ_ENABLE_REG)
            if irq_enable & self.IRQ_RX_READY:
                irq_status = self.register_manager.read_register(self, self.IRQ_STATUS_REG)
                irq_status |= self.IRQ_RX_READY
                self.register_manager.registers[self.IRQ_STATUS_REG].value = irq_status
                self.trigger_interrupt(1)
    
    def connect_spi_device(self, chip_select: int, external_device=None) -> bool:
        """Connect an external SPI device to a specific chip select."""
        if chip_select >= self.num_chip_selects:
            return False
        
        connection_id = f"spi_cs{chip_select}"
        return self.connect_external_device(connection_id, external_device)
    
    def disconnect_spi_device(self, chip_select: int) -> bool:
        """Disconnect external SPI device from a specific chip select."""
        if chip_select >= self.num_chip_selects:
            return False
        
        connection_id = f"spi_cs{chip_select}"
        return self.disconnect_external_device(connection_id)
    
    def transfer_data(self, chip_select: int, tx_data: List[int]) -> List[int]:
        """Perform SPI transfer with specified chip select."""
        # Set chip select
        self.write(self.base_address + self.CS_REG, 1 << chip_select)
        
        rx_data = []
        for data in tx_data:
            # Write data to trigger transfer
            self.write(self.base_address + self.DATA_REG, data)
            
            # Read response (in real hardware this would be simultaneous)
            response = self.read(self.base_address + self.DATA_REG)
            rx_data.append(response)
        
        # Clear chip select
        self.write(self.base_address + self.CS_REG, 0)
        
        return rx_data
    
    def configure_clock(self, frequency: int, cpol: bool = False, cpha: bool = False) -> None:
        """Configure SPI clock settings."""
        # Set clock frequency
        self.write(self.base_address + self.CLOCK_REG, frequency)
        
        # Set clock polarity and phase
        ctrl = self.read(self.base_address + self.CTRL_REG)
        if cpol:
            ctrl |= self.CTRL_CPOL
        else:
            ctrl &= ~self.CTRL_CPOL
        
        if cpha:
            ctrl |= self.CTRL_CPHA
        else:
            ctrl &= ~self.CTRL_CPHA
        
        self.write(self.base_address + self.CTRL_REG, ctrl)
    
    def get_spi_status(self) -> Dict[str, Any]:
        """Get comprehensive SPI status."""
        status = self.register_manager.read_register(self, self.STATUS_REG)
        ctrl = self.register_manager.read_register(self, self.CTRL_REG)
        cs = self.register_manager.read_register(self, self.CS_REG)
        
        return {
            'enabled': bool(ctrl & self.CTRL_ENABLE),
            'master_mode': bool(ctrl & self.CTRL_MASTER),
            'slave_mode': bool(ctrl & self.CTRL_SLAVE),
            'ready': bool(status & self.STATUS_READY),
            'busy': bool(status & self.STATUS_BUSY),
            'tx_empty': bool(status & self.STATUS_TX_EMPTY),
            'rx_full': bool(status & self.STATUS_RX_FULL),
            'active_cs': self.active_cs,
            'cs_register': cs,
            'clock_freq': self.register_manager.read_register(self, self.CLOCK_REG),
            'cpol': bool(ctrl & self.CTRL_CPOL),
            'cpha': bool(ctrl & self.CTRL_CPHA),
            'lsb_first': bool(ctrl & self.CTRL_LSB_FIRST),
            'rx_buffer_size': len(self.rx_buffer),
            'connections': self.get_all_connections_status()
        }
    
    def reset(self) -> None:
        """Reset SPI device."""
        super().reset()
        self.active_cs = None
        self.tx_buffer.clear()
        self.rx_buffer.clear()
        
        # Reset status register
        status = self.STATUS_READY | self.STATUS_TX_EMPTY
        self.register_manager.registers[self.STATUS_REG].value = status
    
    def _reset_implementation(self) -> None:
        """SPI-specific reset implementation."""
        # Disconnect all external devices
        for i in range(self.num_chip_selects):
            self.disconnect_spi_device(i)
        
        # Clear IRQ status
        self.register_manager.registers[self.IRQ_STATUS_REG].value = 0
    
    def cleanup(self) -> None:
        """Clean up SPI device resources."""
        self.cleanup_io()
        for i in range(self.num_chip_selects):
            self.disconnect_spi_device(i)