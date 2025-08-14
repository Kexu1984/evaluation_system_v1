"""
CAN device implementation for the DevCommV3 framework.

This module provides a CAN device that supports external peripheral connections
using the IO interface for simulating real CAN bus communication.
"""

from typing import Optional, Dict, Any, List, NamedTuple
from ..core.base_device import BaseDevice
from ..core.io_interface import IOInterface, IODirection
from ..core.registers import RegisterType


class CANMessage(NamedTuple):
    """CAN message structure."""
    id: int
    data: List[int]
    dlc: int
    extended: bool = False
    rtr: bool = False


class CANDevice(BaseDevice, IOInterface):
    """CAN device implementation with IO interface support."""
    
    # Register offsets
    CTRL_REG = 0x00        # Control register
    STATUS_REG = 0x04      # Status register
    ERROR_REG = 0x08       # Error register
    BAUD_REG = 0x0C        # Baud rate register
    TX_ID_REG = 0x10       # TX message ID register
    TX_DLC_REG = 0x14      # TX data length code register
    TX_DATA_REG = 0x18     # TX data registers (0x18-0x1F for 8 bytes)
    RX_ID_REG = 0x20       # RX message ID register
    RX_DLC_REG = 0x24      # RX data length code register
    RX_DATA_REG = 0x28     # RX data registers (0x28-0x2F for 8 bytes)
    FILTER_REG = 0x30      # Message filter register
    MASK_REG = 0x34        # Message mask register
    IRQ_ENABLE_REG = 0x38  # IRQ enable register
    IRQ_STATUS_REG = 0x3C  # IRQ status register
    
    # Control register bits
    CTRL_ENABLE = 0x01
    CTRL_RESET = 0x02
    CTRL_LOOPBACK = 0x04
    CTRL_LISTEN_ONLY = 0x08
    CTRL_TX_REQUEST = 0x10
    CTRL_EXTENDED_ID = 0x20
    CTRL_RTR = 0x40
    
    # Status register bits
    STATUS_TX_READY = 0x01
    STATUS_RX_READY = 0x02
    STATUS_ERROR_WARNING = 0x04
    STATUS_ERROR_PASSIVE = 0x08
    STATUS_BUS_OFF = 0x10
    STATUS_TX_COMPLETE = 0x20
    
    # Error register bits
    ERROR_STUFF = 0x01
    ERROR_FORM = 0x02
    ERROR_ACK = 0x04
    ERROR_BIT1 = 0x08
    ERROR_BIT0 = 0x10
    ERROR_CRC = 0x20
    
    # IRQ enable/status bits
    IRQ_TX_COMPLETE = 0x01
    IRQ_RX_READY = 0x02
    IRQ_ERROR = 0x04
    IRQ_WAKEUP = 0x08
    
    def __init__(self, name: str, base_address: int, size: int, master_id: int,
                 baud_rate: int = 500000):
        # Initialize IO interface first
        IOInterface.__init__(self)
        
        # Store CAN-specific parameters
        self.baud_rate = baud_rate
        self.tx_buffer = []
        self.rx_buffer = []
        self.error_counters = {'tx': 0, 'rx': 0}
        self.message_filter = 0x000
        self.message_mask = 0x7FF
        
        # Initialize base device
        BaseDevice.__init__(self, name, base_address, size, master_id)
        
        # Create CAN bus connection
        self.create_connection("can_bus", IODirection.BIDIRECTIONAL)
    
    def init(self) -> None:
        """Initialize CAN device registers."""
        # Control register - default disabled
        self.register_manager.define_register(
            self.CTRL_REG, "CAN_CTRL", RegisterType.READ_WRITE, 0x00000000,
            write_callback=self._on_ctrl_write
        )
        
        # Status register - TX ready
        self.register_manager.define_register(
            self.STATUS_REG, "CAN_STATUS", RegisterType.READ_ONLY, self.STATUS_TX_READY
        )
        
        # Error register
        self.register_manager.define_register(
            self.ERROR_REG, "CAN_ERROR", RegisterType.READ_ONLY, 0x00000000
        )
        
        # Baud rate register
        self.register_manager.define_register(
            self.BAUD_REG, "CAN_BAUD", RegisterType.READ_WRITE, self.baud_rate
        )
        
        # TX registers
        self.register_manager.define_register(
            self.TX_ID_REG, "CAN_TX_ID", RegisterType.READ_WRITE, 0x00000000
        )
        
        self.register_manager.define_register(
            self.TX_DLC_REG, "CAN_TX_DLC", RegisterType.READ_WRITE, 0x00000000
        )
        
        # TX data registers (8 bytes)
        for i in range(8):
            self.register_manager.define_register(
                self.TX_DATA_REG + i, f"CAN_TX_DATA_{i}", RegisterType.READ_WRITE, 0x00000000
            )
        
        # RX registers
        self.register_manager.define_register(
            self.RX_ID_REG, "CAN_RX_ID", RegisterType.READ_ONLY, 0x00000000
        )
        
        self.register_manager.define_register(
            self.RX_DLC_REG, "CAN_RX_DLC", RegisterType.READ_ONLY, 0x00000000
        )
        
        # RX data registers (8 bytes)
        for i in range(8):
            self.register_manager.define_register(
                self.RX_DATA_REG + i, f"CAN_RX_DATA_{i}", RegisterType.READ_ONLY, 0x00000000
            )
        
        # Filter and mask registers
        self.register_manager.define_register(
            self.FILTER_REG, "CAN_FILTER", RegisterType.READ_WRITE, 0x00000000
        )
        
        self.register_manager.define_register(
            self.MASK_REG, "CAN_MASK", RegisterType.READ_WRITE, 0x000007FF
        )
        
        # IRQ registers
        self.register_manager.define_register(
            self.IRQ_ENABLE_REG, "CAN_IRQ_ENABLE", RegisterType.READ_WRITE, 0x00000000
        )
        
        self.register_manager.define_register(
            self.IRQ_STATUS_REG, "CAN_IRQ_STATUS", RegisterType.READ_WRITE, 0x00000000
        )
        
        # Enable IO by default
        self.enable_io()
    
    def _read_implementation(self, offset: int, width: int) -> int:
        """CAN-specific read implementation."""
        if offset in self.register_manager.registers:
            return self.register_manager.read_register(self, offset, width)
        return 0
    
    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """CAN-specific write implementation."""
        if offset in self.register_manager.registers:
            self.register_manager.write_register(self, offset, value, width)
    
    def _on_ctrl_write(self, device_instance, offset: int, value: int) -> None:
        """Handle control register write."""
        if value & self.CTRL_TX_REQUEST:
            self._transmit_message()
        
        if value & self.CTRL_RESET:
            self._perform_reset()
    
    def _transmit_message(self) -> None:
        """Transmit CAN message."""
        ctrl_reg = self.register_manager.read_register(self.CTRL_REG)
        
        # Check if CAN is enabled
        if not (ctrl_reg & self.CTRL_ENABLE):
            return
        
        # Read message data from registers
        msg_id = self.register_manager.read_register(self.TX_ID_REG)
        dlc = self.register_manager.read_register(self.TX_DLC_REG) & 0x0F
        
        data = []
        for i in range(min(dlc, 8)):
            data.append(self.register_manager.read_register(self.TX_DATA_REG + i) & 0xFF)
        
        # Create CAN message
        message = CANMessage(
            id=msg_id,
            data=data,
            dlc=dlc,
            extended=bool(ctrl_reg & self.CTRL_EXTENDED_ID),
            rtr=bool(ctrl_reg & self.CTRL_RTR)
        )
        
        # Send message to CAN bus
        self._send_to_bus(message)
        
        # Update status
        status = self.register_manager.read_register(self.STATUS_REG)
        status |= self.STATUS_TX_COMPLETE
        self.register_manager.write_register(self.STATUS_REG, status)
        
        # Clear TX request bit
        ctrl_reg &= ~self.CTRL_TX_REQUEST
        self.register_manager.write_register(self.CTRL_REG, ctrl_reg)
        
        # Trigger TX complete interrupt if enabled
        irq_enable = self.register_manager.read_register(self.IRQ_ENABLE_REG)
        if irq_enable & self.IRQ_TX_COMPLETE:
            irq_status = self.register_manager.read_register(self.IRQ_STATUS_REG)
            irq_status |= self.IRQ_TX_COMPLETE
            self.register_manager.write_register(self.IRQ_STATUS_REG, irq_status)
            self.trigger_interrupt(0)
    
    def _send_to_bus(self, message: CANMessage) -> None:
        """Send CAN message to the bus."""
        # Serialize message for transmission
        # Format: [ID (4 bytes), DLC (1 byte), Data (up to 8 bytes), Flags (1 byte)]
        msg_data = []
        msg_data.extend([(message.id >> (i * 8)) & 0xFF for i in range(4)])
        msg_data.append(message.dlc)
        msg_data.extend(message.data[:8])
        
        # Add padding if needed
        while len(msg_data) < 13:
            msg_data.append(0)
        
        # Add flags
        flags = 0
        if message.extended:
            flags |= 0x01
        if message.rtr:
            flags |= 0x02
        msg_data.append(flags)
        
        # Send to CAN bus connection
        for byte in msg_data:
            self.output_data("can_bus", byte, 1)
    
    def _handle_input_data(self, connection_id: str, data: int, width: int):
        """Handle input data from CAN bus."""
        if connection_id == "can_bus":
            ctrl_reg = self.register_manager.read_register(self.CTRL_REG)
            
            # Check if CAN is enabled and not in listen-only mode for RX
            if ctrl_reg & self.CTRL_ENABLE:
                # This is a simplified implementation - in reality, CAN frames
                # would be parsed as complete messages
                self.rx_buffer.append(data)
                
                # When we have enough data for a complete message, process it
                if len(self.rx_buffer) >= 14:  # Minimum CAN frame size
                    self._process_received_message()
    
    def _process_received_message(self) -> None:
        """Process a received CAN message."""
        if len(self.rx_buffer) < 14:
            return
        
        # Parse message from buffer
        msg_id = 0
        for i in range(4):
            msg_id |= (self.rx_buffer.pop(0) << (i * 8))
        
        dlc = self.rx_buffer.pop(0) & 0x0F
        
        data = []
        for i in range(8):
            if self.rx_buffer:
                data.append(self.rx_buffer.pop(0))
            else:
                data.append(0)
        
        if self.rx_buffer:
            flags = self.rx_buffer.pop(0)
            extended = bool(flags & 0x01)
            rtr = bool(flags & 0x02)
        else:
            extended = False
            rtr = False
        
        # Apply message filtering
        filter_reg = self.register_manager.read_register(self.FILTER_REG)
        mask_reg = self.register_manager.read_register(self.MASK_REG)
        
        if (msg_id & mask_reg) == (filter_reg & mask_reg):
            # Message passes filter, store in RX registers
            self.register_manager.write_register(self.RX_ID_REG, msg_id)
            self.register_manager.write_register(self.RX_DLC_REG, dlc)
            
            for i in range(8):
                self.register_manager.write_register(self.RX_DATA_REG + i, data[i])
            
            # Update status
            status = self.register_manager.read_register(self.STATUS_REG)
            status |= self.STATUS_RX_READY
            self.register_manager.write_register(self.STATUS_REG, status)
            
            # Trigger RX ready interrupt if enabled
            irq_enable = self.register_manager.read_register(self.IRQ_ENABLE_REG)
            if irq_enable & self.IRQ_RX_READY:
                irq_status = self.register_manager.read_register(self.IRQ_STATUS_REG)
                irq_status |= self.IRQ_RX_READY
                self.register_manager.write_register(self.IRQ_STATUS_REG, irq_status)
                self.trigger_interrupt(1)
    
    def connect_can_bus(self, external_device=None) -> bool:
        """Connect to CAN bus."""
        return self.connect_external_device("can_bus", external_device)
    
    def disconnect_can_bus(self) -> bool:
        """Disconnect from CAN bus."""
        return self.disconnect_external_device("can_bus")
    
    def send_can_message(self, msg_id: int, data: List[int], extended: bool = False, rtr: bool = False) -> bool:
        """Send a CAN message."""
        if len(data) > 8:
            return False
        
        # Set message ID
        self.write(self.base_address + self.TX_ID_REG, msg_id)
        
        # Set DLC
        self.write(self.base_address + self.TX_DLC_REG, len(data))
        
        # Set data
        for i, byte in enumerate(data):
            self.write(self.base_address + self.TX_DATA_REG + i, byte)
        
        # Clear remaining data registers
        for i in range(len(data), 8):
            self.write(self.base_address + self.TX_DATA_REG + i, 0)
        
        # Set control flags and request transmission
        ctrl = self.read(self.base_address + self.CTRL_REG)
        ctrl |= self.CTRL_ENABLE | self.CTRL_TX_REQUEST
        
        if extended:
            ctrl |= self.CTRL_EXTENDED_ID
        else:
            ctrl &= ~self.CTRL_EXTENDED_ID
        
        if rtr:
            ctrl |= self.CTRL_RTR
        else:
            ctrl &= ~self.CTRL_RTR
        
        self.write(self.base_address + self.CTRL_REG, ctrl)
        
        return True
    
    def receive_can_message(self) -> Optional[CANMessage]:
        """Receive a CAN message if available."""
        status = self.read(self.base_address + self.STATUS_REG)
        
        if status & self.STATUS_RX_READY:
            # Read message data
            msg_id = self.read(self.base_address + self.RX_ID_REG)
            dlc = self.read(self.base_address + self.RX_DLC_REG) & 0x0F
            
            data = []
            for i in range(dlc):
                data.append(self.read(self.base_address + self.RX_DATA_REG + i))
            
            # Clear RX ready status
            status &= ~self.STATUS_RX_READY
            self.register_manager.write_register(self.STATUS_REG, status)
            
            return CANMessage(id=msg_id, data=data, dlc=dlc)
        
        return None
    
    def set_message_filter(self, filter_id: int, mask: int) -> None:
        """Set message filter and mask."""
        self.write(self.base_address + self.FILTER_REG, filter_id)
        self.write(self.base_address + self.MASK_REG, mask)
    
    def _perform_reset(self) -> None:
        """Perform CAN controller reset."""
        self.reset()
    
    def get_can_status(self) -> Dict[str, Any]:
        """Get comprehensive CAN status."""
        status = self.register_manager.read_register(self.STATUS_REG)
        ctrl = self.register_manager.read_register(self.CTRL_REG)
        error = self.register_manager.read_register(self.ERROR_REG)
        
        return {
            'enabled': bool(ctrl & self.CTRL_ENABLE),
            'loopback': bool(ctrl & self.CTRL_LOOPBACK),
            'listen_only': bool(ctrl & self.CTRL_LISTEN_ONLY),
            'tx_ready': bool(status & self.STATUS_TX_READY),
            'rx_ready': bool(status & self.STATUS_RX_READY),
            'tx_complete': bool(status & self.STATUS_TX_COMPLETE),
            'error_warning': bool(status & self.STATUS_ERROR_WARNING),
            'error_passive': bool(status & self.STATUS_ERROR_PASSIVE),
            'bus_off': bool(status & self.STATUS_BUS_OFF),
            'error_register': error,
            'error_counters': self.error_counters.copy(),
            'baud_rate': self.register_manager.read_register(self.BAUD_REG),
            'message_filter': self.register_manager.read_register(self.FILTER_REG),
            'message_mask': self.register_manager.read_register(self.MASK_REG),
            'rx_buffer_size': len(self.rx_buffer),
            'connections': self.get_all_connections_status()
        }
    
    def reset(self) -> None:
        """Reset CAN device."""
        super().reset()
        self.tx_buffer.clear()
        self.rx_buffer.clear()
        self.error_counters = {'tx': 0, 'rx': 0}
        
        # Reset status register
        status = self.STATUS_TX_READY
        self.register_manager.write_register(self.STATUS_REG, status)
    
    def _reset_implementation(self) -> None:
        """CAN-specific reset implementation."""
        # Disconnect from CAN bus
        self.disconnect_can_bus()
        
        # Clear IRQ status
        self.register_manager.write_register(self.IRQ_STATUS_REG, 0)
    
    def cleanup(self) -> None:
        """Clean up CAN device resources."""
        self.cleanup_io()
        self.disconnect_can_bus()