"""
DMAv2 device implementation for the DevCommV3 framework.

This module provides a DMAv2 controller that supports:
- 16 independent configurable channels
- Multiple transfer modes (mem2mem, mem2peri, peri2mem, peri2peri)
- 4-level priority system
- Circular buffer management
- Interrupt generation on completion/errors
- Error injection for fault simulation
- Multi-instance support
"""

import time
import threading
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
import logging

# Import base classes from the framework
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from devcomm.core.base_device import BaseDevice, DMAInterface
from devcomm.core.registers import RegisterType


class DMAv2TransferMode(Enum):
    """DMAv2 transfer modes."""
    MEM2MEM = 0    # Memory to Memory
    MEM2PERI = 1   # Memory to Peripheral  
    PERI2MEM = 2   # Peripheral to Memory
    PERI2PERI = 3  # Peripheral to Peripheral


class DMAv2Priority(Enum):
    """DMAv2 channel priority levels."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    VERY_HIGH = 3


class DMAv2DataWidth(Enum):
    """DMAv2 data transfer widths."""
    BYTE = 1
    HALF_WORD = 2
    WORD = 4


class DMAv2ChannelState(Enum):
    """DMAv2 channel states."""
    IDLE = "idle"
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class DMAv2Channel:
    """Individual DMAv2 channel implementation."""
    
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.state = DMAv2ChannelState.IDLE
        self.enabled = False
        self.debug_enabled = False
        
        # Transfer configuration
        self.src_address = 0
        self.dst_address = 0
        self.src_start_addr = 0
        self.dst_start_addr = 0
        self.src_end_addr = 0
        self.dst_end_addr = 0
        self.src_offset = 0
        self.dst_offset = 0
        self.transfer_length = 0
        self.data_transferred = 0
        
        # Configuration
        self.transfer_mode = DMAv2TransferMode.MEM2MEM
        self.priority = DMAv2Priority.LOW
        self.src_data_width = DMAv2DataWidth.WORD
        self.dst_data_width = DMAv2DataWidth.WORD
        self.circular_mode = False
        self.req_id = 0
        self.trigger_enabled = False
        
        # Status flags
        self.transfer_complete = False
        self.half_complete = False
        self.transfer_error = False
        self.src_addr_error = False
        self.dst_addr_error = False
        self.src_offset_error = False
        self.dst_offset_error = False
        self.channel_length_error = False
        self.src_bus_error = False
        self.dst_bus_error = False
        
        # FIFO management
        self.fifo_data_left = 0
        
        # Threading
        self.lock = threading.RLock()
        self.transfer_thread = None
        
    def reset(self):
        """Reset channel to initial state."""
        with self.lock:
            self.state = DMAv2ChannelState.IDLE
            self.enabled = False
            self.src_address = 0
            self.dst_address = 0
            self.transfer_length = 0
            self.data_transferred = 0
            self._clear_status_flags()
            
    def _clear_status_flags(self):
        """Clear all status flags."""
        self.transfer_complete = False
        self.half_complete = False
        self.transfer_error = False
        self.src_addr_error = False
        self.dst_addr_error = False
        self.src_offset_error = False
        self.dst_offset_error = False
        self.channel_length_error = False
        self.src_bus_error = False
        self.dst_bus_error = False
        
    def configure(self, src_addr: int, dst_addr: int, length: int, 
                  mode: DMAv2TransferMode = DMAv2TransferMode.MEM2MEM):
        """Configure channel for transfer."""
        with self.lock:
            self.src_address = src_addr
            self.dst_address = dst_addr
            self.transfer_length = length
            self.transfer_mode = mode
            self.data_transferred = 0
            self._clear_status_flags()
            self.state = DMAv2ChannelState.CONFIGURED
            
    def enable(self):
        """Enable the channel."""
        with self.lock:
            self.enabled = True
            if self.state == DMAv2ChannelState.CONFIGURED:
                self.state = DMAv2ChannelState.RUNNING
                
    def disable(self):
        """Disable the channel."""
        with self.lock:
            self.enabled = False
            self.state = DMAv2ChannelState.IDLE
            
    def is_running(self) -> bool:
        """Check if channel is currently running."""
        return self.state == DMAv2ChannelState.RUNNING
        
    def get_status_word(self) -> int:
        """Get channel status as register value."""
        status = 0
        if self.channel_length_error:
            status |= (1 << 8)
        if self.src_addr_error:
            status |= (1 << 7)
        if self.dst_addr_error:
            status |= (1 << 6)
        if self.src_offset_error:
            status |= (1 << 5)
        if self.dst_offset_error:
            status |= (1 << 4)
        if self.src_bus_error:
            status |= (1 << 3)
        if self.dst_bus_error:
            status |= (1 << 2)
        if self.half_complete:
            status |= (1 << 1)
        if self.transfer_complete:
            status |= (1 << 0)
        return status


class DMAv2Interface(DMAInterface):
    """DMAv2 interface for active DMA operations."""
    
    def __init__(self, device):
        super().__init__()
        self.device = device
        
    def dma_request(self, src_addr: int, dst_addr: int, length: int, 
                   channel_id: int = None) -> int:
        """Initiate DMA transfer request."""
        if channel_id is None:
            # Find available channel
            channel_id = self.device._find_available_channel()
            if channel_id is None:
                raise RuntimeError("No available DMA channels")
                
        channel = self.device.channels[channel_id]
        channel.configure(src_addr, dst_addr, length)
        channel.enable()
        self.device._start_transfer(channel_id)
        return channel_id
        
    def get_transfer_status(self, channel_id: int) -> Dict[str, Any]:
        """Get transfer status for a channel."""
        if channel_id not in self.device.channels:
            raise ValueError(f"Invalid channel ID: {channel_id}")
            
        channel = self.device.channels[channel_id]
        return {
            'channel_id': channel_id,
            'state': channel.state.value,
            'progress': channel.data_transferred,
            'total': channel.transfer_length,
            'complete': channel.transfer_complete,
            'error': channel.transfer_error
        }


class DMAv2Device(BaseDevice):
    """DMAv2 controller device implementation."""
    
    # Global registers
    DMA_TOP_RST_REG = 0x000
    
    # Channel base addresses (each channel is 0x40 bytes apart)
    CHANNEL_BASE = 0x040
    CHANNEL_SIZE = 0x40
    
    # Channel register offsets within each channel
    CH_STATUS_OFFSET = 0x00      # CHANNELx_STATUS
    CH_ENABLE_OFFSET = 0x24      # CHANNELx_CHAN_ENABLE  
    CH_DATA_TRANS_NUM_OFFSET = 0x28  # CHANNELx_DATA_TRANS_NUM
    CH_FIFO_DATA_LEFT_OFFSET = 0x2C  # CHANNELx_INTER_FIFO_DATA_LEFT_NUM
    CH_DEND_ADDR_OFFSET = 0x30   # CHANNELx_DEND_ADDR
    CH_DSTART_ADDR_OFFSET = 0x34 # CHANNELx_DSTART_ADDR (calculated from YAML)
    CH_ADDR_OFFSET_OFFSET = 0x34 # CHANNELx_ADDR_OFFSET 
    CH_DMAMUX_CFG_OFFSET = 0x38  # CHANNELx_DMAMUX_CFG
    
    def __init__(self, instance_id: int = 0, base_address: int = 0x40000000):
        self.instance_id = instance_id
        self.device_size = 0x1000  # 4KB address space
        
        # Device state (must be set before parent init)
        self.num_channels = 16
        self.channels: Dict[int, DMAv2Channel] = {}
        self.global_idle = True
        self.hard_reset_active = False
        self.warm_reset_active = False
        
        # Interfaces
        self.dma_interface = None  # Will be set after init
        
        # Interrupt callback
        self.irq_callback: Optional[Callable] = None
        
        # Error injection support
        self.error_injection_enabled = False
        self.injected_errors = {}
        
        # Initialize parent class
        super().__init__(f"DMAv2_{instance_id}", base_address, self.device_size, instance_id + 10)
        
        # Set up DMA interface after parent init
        self.dma_interface = DMAv2Interface(self)
        
    def init(self) -> None:
        """Initialize DMAv2 device registers and channels."""
        self._initialize_channels()
        self._define_registers()
        self._initialize_state()
        
    def _initialize_channels(self):
        """Initialize all DMA channels."""
        for ch in range(self.num_channels):
            self.channels[ch] = DMAv2Channel(ch)
            
    def _define_registers(self):
        """Define all device registers."""
        # Global reset register
        self.register_manager.define_register(
            self.DMA_TOP_RST_REG, "DMA_TOP_RST",
            RegisterType.READ_WRITE, 0x00000004,  # DMA_IDLE = 1 initially
            write_callback=self._dma_top_rst_write_callback
        )
        
        # Channel-specific registers
        for ch in range(self.num_channels):
            base_offset = self.CHANNEL_BASE + ch * self.CHANNEL_SIZE
            
            # Channel status register (read-only)
            self.register_manager.define_register(
                base_offset + self.CH_STATUS_OFFSET, f"CH{ch}_STATUS",
                RegisterType.READ_ONLY, 0x00000000,
                read_callback=lambda dev, offset, value, ch=ch: self._channel_status_read_callback(dev, offset, value, ch)
            )
            
            # Channel enable register
            self.register_manager.define_register(
                base_offset + self.CH_ENABLE_OFFSET, f"CH{ch}_ENABLE",
                RegisterType.READ_WRITE, 0x00000000,
                write_callback=lambda dev, offset, value, ch=ch: self._channel_enable_write_callback(dev, offset, value, ch)
            )
            
            # Data transfer number (read-only)
            self.register_manager.define_register(
                base_offset + self.CH_DATA_TRANS_NUM_OFFSET, f"CH{ch}_DATA_TRANS_NUM",
                RegisterType.READ_ONLY, 0x00000000,
                read_callback=lambda dev, offset, value, ch=ch: self._channel_data_trans_read_callback(dev, offset, value, ch)
            )
            
            # FIFO data left (read-only)
            self.register_manager.define_register(
                base_offset + self.CH_FIFO_DATA_LEFT_OFFSET, f"CH{ch}_FIFO_DATA_LEFT",
                RegisterType.READ_ONLY, 0x00000000,
                read_callback=lambda dev, offset, value, ch=ch: self._channel_fifo_read_callback(dev, offset, value, ch)
            )
            
            # Destination end address
            self.register_manager.define_register(
                base_offset + self.CH_DEND_ADDR_OFFSET, f"CH{ch}_DEND_ADDR",
                RegisterType.READ_WRITE, 0x00000000
            )
            
            # Address offset configuration
            self.register_manager.define_register(
                base_offset + self.CH_ADDR_OFFSET_OFFSET, f"CH{ch}_ADDR_OFFSET",
                RegisterType.READ_WRITE, 0x00000000
            )
            
            # DMAMUX configuration
            self.register_manager.define_register(
                base_offset + self.CH_DMAMUX_CFG_OFFSET, f"CH{ch}_DMAMUX_CFG",
                RegisterType.READ_WRITE, 0x00000000,
                write_callback=lambda dev, offset, value, ch=ch: self._channel_dmamux_write_callback(dev, offset, value, ch)
            )
            
    def _initialize_state(self):
        """Set initial device state."""
        self.global_idle = True
        
    def _read_implementation(self, offset: int, width: int = 4) -> int:
        """Device-specific read implementation."""
        return self.register_manager.read_register(self, offset, width)
        
    def _write_implementation(self, offset: int, value: int, width: int = 4) -> None:
        """Device-specific write implementation."""
        self.register_manager.write_register(self, offset, value, width)
        
    # Register callback implementations
    def _dma_top_rst_write_callback(self, device, offset: int, value: int) -> None:
        """Handle writes to DMA_TOP_RST register."""
        warm_rst = (value >> 0) & 1
        hard_rst = (value >> 1) & 1
        
        if hard_rst:
            self._perform_hard_reset()
        elif warm_rst:
            self._perform_warm_reset()
            
    def _channel_status_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from channel status register."""
        if channel_id in self.channels:
            return self.channels[channel_id].get_status_word()
        return 0
        
    def _channel_enable_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel enable register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        chan_en = (value >> 0) & 1
        edbg = (value >> 1) & 1
        
        channel.debug_enabled = bool(edbg)
        
        if chan_en and not channel.enabled:
            channel.enable()
            self._start_transfer(channel_id)
        elif not chan_en and channel.enabled:
            channel.disable()
            
    def _channel_data_trans_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from data transfer number register."""
        if channel_id in self.channels:
            return self.channels[channel_id].data_transferred & 0xFFFF
        return 0
        
    def _channel_fifo_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from FIFO data left register."""
        if channel_id in self.channels:
            return self.channels[channel_id].fifo_data_left & 0x3F
        return 0
        
    def _channel_dmamux_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to DMAMUX configuration register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        req_id = value & 0x7F
        trig_en = (value >> 7) & 1
        
        channel.req_id = req_id
        channel.trigger_enabled = bool(trig_en)
        
    # Transfer management
    def _find_available_channel(self) -> Optional[int]:
        """Find an available channel for transfer."""
        for ch_id, channel in self.channels.items():
            if channel.state == DMAv2ChannelState.IDLE:
                return ch_id
        return None
        
    def _start_transfer(self, channel_id: int):
        """Start transfer on specified channel."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        if not channel.enabled or channel.is_running():
            return
            
        # Start transfer in a separate thread to simulate hardware behavior
        def transfer_worker():
            try:
                self._perform_transfer(channel_id)
            except Exception as e:
                channel.transfer_error = True
                channel.state = DMAv2ChannelState.ERROR
                logging.error(f"Transfer error on channel {channel_id}: {e}")
                
        channel.transfer_thread = threading.Thread(target=transfer_worker)
        channel.transfer_thread.start()
        
    def _perform_transfer(self, channel_id: int):
        """Perform actual transfer (simulation)."""
        channel = self.channels[channel_id]
        channel.state = DMAv2ChannelState.RUNNING
        
        # Simulate transfer progress
        total_length = channel.transfer_length
        half_point = total_length // 2
        
        try:
            for transferred in range(0, total_length + 1, 4):  # Transfer in 4-byte chunks
                if not channel.enabled:
                    break
                    
                # Update progress
                channel.data_transferred = min(transferred, total_length)
                
                # Check for half completion
                if not channel.half_complete and channel.data_transferred >= half_point:
                    channel.half_complete = True
                    self._trigger_interrupt(channel_id, "half_complete")
                    
                # Simulate transfer delay
                time.sleep(0.01)  # 10ms per chunk (reduced for testing)
                
            # Mark as complete
            if channel.enabled and channel.data_transferred >= total_length:
                channel.transfer_complete = True
                channel.state = DMAv2ChannelState.COMPLETED
                
                # In non-circular mode, disable channel
                if not channel.circular_mode:
                    channel.enabled = False
                    
                self._trigger_interrupt(channel_id, "complete")
        except Exception as e:
            channel.transfer_error = True
            channel.state = DMAv2ChannelState.ERROR
            self._trigger_interrupt(channel_id, "error")
            
    def _perform_hard_reset(self):
        """Perform hard reset of the DMA controller."""
        self.hard_reset_active = True
        
        # Stop all channels immediately
        for channel in self.channels.values():
            channel.reset()
            
        # Reset global state
        self.global_idle = True
        self.hard_reset_active = False
        
    def _perform_warm_reset(self):
        """Perform warm reset of the DMA controller."""
        self.warm_reset_active = True
        
        # Wait for current transfers to complete, then reset
        for channel in self.channels.values():
            if channel.is_running() and channel.transfer_thread:
                channel.transfer_thread.join(timeout=1.0)
            channel.reset()
            
        # Reset global state
        self.global_idle = True
        self.warm_reset_active = False
        
    def _trigger_interrupt(self, channel_id: int, event_type: str):
        """Trigger interrupt for channel event."""
        # Call custom interrupt handler first
        if self.irq_callback:
            try:
                self.irq_callback(channel_id, event_type)
            except Exception as e:
                print(f"Error in interrupt callback: {e}")
        
        # Use base device interrupt mechanism
        try:
            irq_vector = channel_id * 4  # Each channel gets 4 interrupt vectors
            if event_type == "half_complete":
                irq_vector += 1
            elif event_type == "complete":
                irq_vector += 2
            elif event_type == "error":
                irq_vector += 3
                
            self.trigger_interrupt(irq_vector)
        except Exception as e:
            # Bus might not be set up, that's OK for testing
            pass
            
    # Multi-instance support
    @classmethod
    def create_instance(cls, instance_id: int, base_address: int) -> 'DMAv2Device':
        """Create a new DMAv2 device instance."""
        return cls(instance_id, base_address)
        
    # Error injection support
    def inject_error(self, channel_id: int, error_type: str):
        """Inject error for testing purposes."""
        if not self.error_injection_enabled:
            return
            
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        
        if error_type == "src_addr_error":
            channel.src_addr_error = True
        elif error_type == "dst_addr_error":
            channel.dst_addr_error = True
        elif error_type == "src_bus_error":
            channel.src_bus_error = True
        elif error_type == "dst_bus_error":
            channel.dst_bus_error = True
        elif error_type == "channel_length_error":
            channel.channel_length_error = True
            
        channel.transfer_error = True
        self._trigger_interrupt(channel_id, "error")
        
    def enable_error_injection(self):
        """Enable error injection for testing."""
        self.error_injection_enabled = True
        
    def disable_error_injection(self):
        """Disable error injection."""
        self.error_injection_enabled = False
        
    # Public interface methods
    def register_irq_callback(self, callback: Callable):
        """Register interrupt callback function."""
        self.irq_callback = callback
        
    def get_channel_status(self, channel_id: int) -> Dict[str, Any]:
        """Get detailed status of a channel."""
        if channel_id not in self.channels:
            raise ValueError(f"Invalid channel ID: {channel_id}")
            
        channel = self.channels[channel_id]
        return {
            'channel_id': channel_id,
            'state': channel.state.value,
            'enabled': channel.enabled,
            'src_address': channel.src_address,
            'dst_address': channel.dst_address,
            'transfer_length': channel.transfer_length,
            'data_transferred': channel.data_transferred,
            'transfer_complete': channel.transfer_complete,
            'half_complete': channel.half_complete,
            'transfer_error': channel.transfer_error,
            'transfer_mode': channel.transfer_mode.value,
            'priority': channel.priority.value
        }
        
    def get_device_status(self) -> Dict[str, Any]:
        """Get overall device status."""
        active_channels = sum(1 for ch in self.channels.values() if ch.is_running())
        
        return {
            'instance_id': self.instance_id,
            'base_address': f"0x{self.base_address:08X}",
            'num_channels': self.num_channels,
            'active_channels': active_channels,
            'global_idle': self.global_idle,
            'error_injection_enabled': self.error_injection_enabled
        }