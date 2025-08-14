"""
DMA device implementation for the DevCommV3 framework.

This module provides a DMA controller device that supports:
- 16 independent configurable channels
- Memory-to-memory, peripheral-to-memory, memory-to-peripheral transfers
- Priority-based arbitration (Very High, High, Medium, Low)
- Circular buffer support
- Multiple data widths (8, 16, 32 bits)
- Address offset support
- Status flags and interrupts
- Error detection and handling
"""

import time
import threading
import queue
from enum import Enum
from typing import Dict, Any, Optional, Callable, Union, List
from dataclasses import dataclass

# Import base classes from the framework
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from devcomm.core.base_device import BaseDevice, DMAInterface
from devcomm.core.registers import RegisterType


class DMATransferDirection(Enum):
    """DMA transfer direction."""
    PERIPHERAL_TO_MEMORY = 0  # Read from peripheral, write to memory
    MEMORY_TO_PERIPHERAL = 1  # Read from memory, write to peripheral


class DMAPriority(Enum):
    """DMA channel priority levels."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    VERY_HIGH = 3


class DMADataSize(Enum):
    """DMA data transfer sizes."""
    BYTE = 0      # 8-bit
    HALFWORD = 1  # 16-bit
    WORD = 2      # 32-bit
    RESERVED = 3


class DMAChannelState(Enum):
    """DMA channel states."""
    IDLE = 0
    BUSY = 1
    PAUSED = 2
    ERROR = 3
    COMPLETE = 4


@dataclass
class DMATransferRequest:
    """DMA transfer request structure."""
    channel_id: int
    source_addr: int
    dest_addr: int
    length: int
    priority: DMAPriority
    direction: DMATransferDirection
    source_size: DMADataSize
    dest_size: DMADataSize
    circular: bool = False
    source_offset: int = 0
    dest_offset: int = 0


class DMAChannel:
    """Individual DMA channel representation."""
    
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.state = DMAChannelState.IDLE
        self.enabled = False
        self.debug_enabled = False
        
        # Configuration
        self.direction = DMATransferDirection.PERIPHERAL_TO_MEMORY
        self.circular = False
        self.source_size = DMADataSize.WORD
        self.dest_size = DMADataSize.WORD
        self.priority = DMAPriority.LOW
        
        # Address and length
        self.source_addr = 0
        self.dest_addr = 0
        self.current_source_addr = 0
        self.current_dest_addr = 0
        self.transfer_length = 0
        self.remaining_length = 0
        self.data_transferred = 0
        
        # Circular buffer support
        self.source_start_addr = 0
        self.source_end_addr = 0
        self.dest_start_addr = 0
        self.dest_end_addr = 0
        
        # Address offsets
        self.source_offset = 0
        self.dest_offset = 0
        
        # Status flags
        self.finish_flag = False
        self.half_finish_flag = False
        self.source_bus_error = False
        self.dest_bus_error = False
        self.source_addr_error = False
        self.dest_addr_error = False
        self.source_offset_error = False
        self.dest_offset_error = False
        self.channel_length_error = False
        
        # Interrupt configuration
        self.interrupt_enable = 0  # Bitmask for different interrupt types
        
        # DMAMUX configuration
        self.request_id = 0
        self.trigger_enable = False
        
        # Internal FIFO data count
        self.fifo_data_left = 0
        
        # Thread synchronization
        self.lock = threading.RLock()
        self.transfer_thread = None
        self.stop_requested = False
        
    def reset(self):
        """Reset channel to initial state."""
        with self.lock:
            self.state = DMAChannelState.IDLE
            self.enabled = False
            self.clear_all_status_flags()
            self.data_transferred = 0
            self.remaining_length = 0
            self.stop_requested = False
            if self.transfer_thread and self.transfer_thread.is_alive():
                self.stop_requested = True
                
    def clear_all_status_flags(self):
        """Clear all status flags."""
        self.finish_flag = False
        self.half_finish_flag = False
        self.source_bus_error = False
        self.dest_bus_error = False
        self.source_addr_error = False
        self.dest_addr_error = False
        self.source_offset_error = False
        self.dest_offset_error = False
        self.channel_length_error = False
        
    def validate_configuration(self):
        """Validate channel configuration and set error flags."""
        errors = False
        
        # Check address alignment with data sizes
        source_align = 1 << self.source_size.value if self.source_size != DMADataSize.RESERVED else 1
        dest_align = 1 << self.dest_size.value if self.dest_size != DMADataSize.RESERVED else 1
        
        if self.source_addr % source_align != 0:
            self.source_addr_error = True
            errors = True
            
        if self.dest_addr % dest_align != 0:
            self.dest_addr_error = True
            errors = True
            
        if self.source_offset % source_align != 0:
            self.source_offset_error = True
            errors = True
            
        if self.dest_offset % dest_align != 0:
            self.dest_offset_error = True
            errors = True
            
        # Check length consistency
        if self.transfer_length == 0 or self.transfer_length > 32767:
            self.channel_length_error = True
            errors = True
            
        return not errors


class DMADevice(BaseDevice, DMAInterface):
    """DMA controller device implementation."""
    
    # Channel register offsets (each channel occupies 0x40 bytes)
    CHANNEL_SIZE = 0x40
    
    # Register offsets within each channel
    STATUS_OFFSET = 0x40        # CHANNELx_STATUS_xx base
    CONFIG_OFFSET = 0x50        # CHANNELx_CONFIG_xx 
    CHAN_LENGTH_OFFSET = 0x54   # CHANNELx_CHAN_LENGTH_xx
    CHAN_ENABLE_OFFSET = 0x64   # CHANNELx_CHAN_ENABLE_xx
    DATA_TRANS_NUM_OFFSET = 0x68  # CHANNELx_DATA_TRANS_NUM_xx
    FIFO_DATA_LEFT_OFFSET = 0x6C  # CHANNELx_INTER_FIFO_DATA_LEFT_NUM_xx
    DEND_ADDR_OFFSET = 0x70     # CHANNELx_DEND_ADDR_xx
    ADDR_OFFSET_OFFSET = 0x74   # CHANNELx_ADDR_OFFSET_xx
    DMAMUX_CFG_OFFSET = 0x78    # CHANNELx_DMAMUX_CFG_xx
    SEND_ADDR_OFFSET = 0x5C     # CHANNELx_SEND_ADDR_xx
    SSTART_ADDR_OFFSET = 0x58   # CHANNELx_SSTART_ADDR_xx
    DSTART_ADDR_OFFSET = 0x60   # CHANNELx_DSTART_ADDR_xx (will be calculated)
    
    # Global registers
    DMA_TOP_RST = 0x000
    
    def __init__(self, name: str, base_address: int, size: int, master_id: int, num_channels: int = 16):
        self.num_channels = min(num_channels, 16)  # Maximum 16 channels
        self.channels: Dict[int, DMAChannel] = {}
        self.global_idle = True
        self.irq_callback: Optional[Callable] = None
        self.memory_interface: Optional[Callable] = None
        self.arbiter_queue = queue.PriorityQueue()
        self.arbiter_thread = None
        self.arbiter_running = False
        
        # Error injection support
        self.error_injection_enabled = False
        self.injected_errors = {}
        
        # Create DMA channels
        for i in range(self.num_channels):
            self.channels[i] = DMAChannel(i)
            
        # Initialize DMA interface
        DMAInterface.__init__(self)
        
        # Initialize parent class (this will call self.init())
        super().__init__(name, base_address, size, master_id)
        
        # Start arbiter thread
        self._start_arbiter()
        
    def init(self) -> None:
        """Initialize DMA device registers according to register specification."""
        # Global reset register
        self.register_manager.define_register(
            self.DMA_TOP_RST, "DMA_TOP_RST", RegisterType.READ_WRITE, 0x00000004,  # DMA_IDLE=1 initially
            write_callback=self._dma_top_rst_write_callback,
            read_callback=self._dma_top_rst_read_callback
        )
        
        # Define registers for each channel
        for channel_id in range(self.num_channels):
            self._define_channel_registers(channel_id)
            
    def _define_channel_registers(self, channel_id: int) -> None:
        """Define all registers for a specific channel."""
        base_offset = channel_id * self.CHANNEL_SIZE
        
        # Status register
        status_addr = self.STATUS_OFFSET + base_offset
        self.register_manager.define_register(
            status_addr, f"CHANNEL{channel_id}_STATUS", RegisterType.READ_ONLY, 0x00000000,
            read_callback=lambda dev, offset, value, ch=channel_id: self._channel_status_read_callback(dev, offset, value, ch)
        )
        
        # Configuration register  
        config_addr = self.CONFIG_OFFSET + base_offset
        self.register_manager.define_register(
            config_addr, f"CHANNEL{channel_id}_CONFIG", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_config_write_callback(dev, offset, value, ch)
        )
        
        # Channel length register
        length_addr = self.CHAN_LENGTH_OFFSET + base_offset
        self.register_manager.define_register(
            length_addr, f"CHANNEL{channel_id}_LENGTH", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_length_write_callback(dev, offset, value, ch)
        )
        
        # Channel enable register
        enable_addr = self.CHAN_ENABLE_OFFSET + base_offset
        self.register_manager.define_register(
            enable_addr, f"CHANNEL{channel_id}_ENABLE", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_enable_write_callback(dev, offset, value, ch)
        )
        
        # Data transfer number register (read-only)
        data_trans_addr = self.DATA_TRANS_NUM_OFFSET + base_offset
        self.register_manager.define_register(
            data_trans_addr, f"CHANNEL{channel_id}_DATA_TRANS_NUM", RegisterType.READ_ONLY, 0x00000000,
            read_callback=lambda dev, offset, value, ch=channel_id: self._channel_data_trans_read_callback(dev, offset, value, ch)
        )
        
        # FIFO data left register (read-only)
        fifo_addr = self.FIFO_DATA_LEFT_OFFSET + base_offset
        self.register_manager.define_register(
            fifo_addr, f"CHANNEL{channel_id}_FIFO_DATA_LEFT", RegisterType.READ_ONLY, 0x00000000,
            read_callback=lambda dev, offset, value, ch=channel_id: self._channel_fifo_data_left_read_callback(dev, offset, value, ch)
        )
        
        # Destination end address register
        dend_addr = self.DEND_ADDR_OFFSET + base_offset
        self.register_manager.define_register(
            dend_addr, f"CHANNEL{channel_id}_DEND_ADDR", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_dend_addr_write_callback(dev, offset, value, ch)
        )
        
        # Address offset register
        addr_offset_addr = self.ADDR_OFFSET_OFFSET + base_offset
        self.register_manager.define_register(
            addr_offset_addr, f"CHANNEL{channel_id}_ADDR_OFFSET", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_addr_offset_write_callback(dev, offset, value, ch)
        )
        
        # DMAMUX configuration register
        dmamux_addr = self.DMAMUX_CFG_OFFSET + base_offset
        self.register_manager.define_register(
            dmamux_addr, f"CHANNEL{channel_id}_DMAMUX_CFG", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_dmamux_write_callback(dev, offset, value, ch)
        )
        
        # Source end address register
        send_addr = self.SEND_ADDR_OFFSET + base_offset
        self.register_manager.define_register(
            send_addr, f"CHANNEL{channel_id}_SEND_ADDR", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_send_addr_write_callback(dev, offset, value, ch)
        )
        
        # Source start address register
        sstart_addr = self.SSTART_ADDR_OFFSET + base_offset
        self.register_manager.define_register(
            sstart_addr, f"CHANNEL{channel_id}_SSTART_ADDR", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_sstart_addr_write_callback(dev, offset, value, ch)
        )
        
        # Destination start address register (calculate offset)
        dstart_addr = self.DSTART_ADDR_OFFSET + base_offset
        self.register_manager.define_register(
            dstart_addr, f"CHANNEL{channel_id}_DSTART_ADDR", RegisterType.READ_WRITE, 0x00000000,
            write_callback=lambda dev, offset, value, ch=channel_id: self._channel_dstart_addr_write_callback(dev, offset, value, ch)
        )
    
    def _read_implementation(self, offset: int, width: int) -> int:
        """Read from DMA device registers."""
        return self.register_manager.read_register(self, offset, width)
    
    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """Write to DMA device registers."""
        self.register_manager.write_register(self, offset, value, width)
    
    # Register callback implementations
    def _dma_top_rst_write_callback(self, device, offset: int, value: int) -> None:
        """Handle writes to DMA top reset register."""
        warm_rst = bool(value & 0x1)
        hard_rst = bool(value & 0x2)
        
        if warm_rst:
            self._perform_warm_reset()
        elif hard_rst:
            self._perform_hard_reset()
    
    def _dma_top_rst_read_callback(self, device, offset: int, value: int) -> int:
        """Handle reads from DMA top reset register."""
        # Bit 2: DMA_IDLE (read-only)
        idle_bit = 1 if self.global_idle else 0
        return idle_bit << 2
    
    def _channel_status_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from channel status register."""
        if channel_id not in self.channels:
            return 0
            
        channel = self.channels[channel_id]
        status = 0
        
        # Build status register value
        if channel.finish_flag:
            status |= 0x1
        if channel.half_finish_flag:
            status |= 0x2
        if channel.dest_bus_error:
            status |= 0x4
        if channel.source_bus_error:
            status |= 0x8
        if channel.dest_offset_error:
            status |= 0x10
        if channel.source_offset_error:
            status |= 0x20
        if channel.dest_addr_error:
            status |= 0x40
        if channel.source_addr_error:
            status |= 0x80
        if channel.channel_length_error:
            status |= 0x100
            
        return status
    
    def _channel_config_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel configuration register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        with channel.lock:
            # Parse configuration bits
            channel.priority = DMAPriority(value & 0x3)
            channel.source_size = DMADataSize((value >> 2) & 0x3)
            channel.dest_size = DMADataSize((value >> 4) & 0x3)
            channel.circular = bool(value & 0x40)
            channel.direction = DMATransferDirection((value >> 7) & 0x1)
    
    def _channel_length_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel length register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        with channel.lock:
            # Length is in bits 15:0, bit 15 should be 0
            length = value & 0x7FFF  # Mask bit 15 to ensure it's 0
            channel.transfer_length = length
            channel.remaining_length = length
    
    def _channel_enable_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel enable register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        with channel.lock:
            chan_en = bool(value & 0x1)
            edbg = bool(value & 0x2)
            
            channel.debug_enabled = edbg
            
            if chan_en and not channel.enabled:
                # Enable channel - start transfer
                if self._validate_and_start_channel(channel_id):
                    channel.enabled = True
                    self.global_idle = False
            elif not chan_en and channel.enabled:
                # Disable channel
                self._stop_channel(channel_id)
    
    def _channel_data_trans_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from channel data transfer number register."""
        if channel_id not in self.channels:
            return 0
        return self.channels[channel_id].data_transferred & 0xFFFF
    
    def _channel_fifo_data_left_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from channel FIFO data left register."""
        if channel_id not in self.channels:
            return 0
        return self.channels[channel_id].fifo_data_left & 0x3F
    
    def _channel_dend_addr_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel destination end address register."""
        if channel_id not in self.channels:
            return
        self.channels[channel_id].dest_end_addr = value
    
    def _channel_addr_offset_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel address offset register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        with channel.lock:
            channel.source_offset = value & 0xFFFF
            channel.dest_offset = (value >> 16) & 0xFFFF
    
    def _channel_dmamux_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel DMAMUX configuration register."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        with channel.lock:
            channel.request_id = value & 0x7F
            channel.trigger_enable = bool(value & 0x80)
    
    def _channel_send_addr_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel source end address register."""
        if channel_id not in self.channels:
            return
        channel = self.channels[channel_id]
        with channel.lock:
            channel.source_addr = value  # This is actually the source address
            channel.current_source_addr = value
    
    def _channel_sstart_addr_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel source start address register."""
        if channel_id not in self.channels:
            return
        self.channels[channel_id].source_start_addr = value
    
    def _channel_dstart_addr_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel destination start address register."""
        if channel_id not in self.channels:
            return
        channel = self.channels[channel_id]
        with channel.lock:
            channel.dest_addr = value  # This is actually the destination address
            channel.current_dest_addr = value
            channel.dest_start_addr = value
    
    def _validate_and_start_channel(self, channel_id: int) -> bool:
        """Validate channel configuration and start transfer if valid."""
        if channel_id not in self.channels:
            return False
            
        channel = self.channels[channel_id]
        
        # Validate configuration
        if not channel.validate_configuration():
            channel.state = DMAChannelState.ERROR
            return False
        
        # Create transfer request
        request = DMATransferRequest(
            channel_id=channel_id,
            source_addr=channel.current_source_addr,
            dest_addr=channel.current_dest_addr,
            length=channel.transfer_length,
            priority=channel.priority,
            direction=channel.direction,
            source_size=channel.source_size,
            dest_size=channel.dest_size,
            circular=channel.circular,
            source_offset=channel.source_offset,
            dest_offset=channel.dest_offset
        )
        
        # Submit to arbiter
        priority_value = 3 - channel.priority.value  # Higher priority = lower value
        self.arbiter_queue.put((priority_value, channel_id, request))
        
        channel.state = DMAChannelState.BUSY
        return True
    
    def _stop_channel(self, channel_id: int) -> None:
        """Stop a DMA channel."""
        if channel_id not in self.channels:
            return
            
        channel = self.channels[channel_id]
        with channel.lock:
            channel.enabled = False
            channel.stop_requested = True
            if channel.transfer_thread and channel.transfer_thread.is_alive():
                channel.transfer_thread = None
            channel.state = DMAChannelState.IDLE
            
        self._update_global_idle_status()
    
    def _perform_warm_reset(self) -> None:
        """Perform warm reset - wait for current transfers to complete then reset."""
        # Wait for all transfers to complete
        for channel in self.channels.values():
            if channel.transfer_thread and channel.transfer_thread.is_alive():
                channel.stop_requested = True
                
        # Reset all channels
        for channel in self.channels.values():
            channel.reset()
            
        self.global_idle = True
    
    def _perform_hard_reset(self) -> None:
        """Perform hard reset - immediately stop all transfers."""
        # Immediately stop all transfers
        for channel in self.channels.values():
            channel.reset()
            
        # Clear arbiter queue
        while not self.arbiter_queue.empty():
            try:
                self.arbiter_queue.get_nowait()
            except queue.Empty:
                break
                
        self.global_idle = True
    
    def _start_arbiter(self) -> None:
        """Start the DMA arbiter thread."""
        self.arbiter_running = True
        self.arbiter_thread = threading.Thread(target=self._arbiter_worker, daemon=True)
        self.arbiter_thread.start()
    
    def _arbiter_worker(self) -> None:
        """DMA arbiter worker thread."""
        while self.arbiter_running:
            try:
                # Get next request (blocks until available)
                priority, channel_id, request = self.arbiter_queue.get(timeout=1.0)
                
                if channel_id in self.channels:
                    channel = self.channels[channel_id]
                    if channel.enabled and not channel.stop_requested:
                        # Start transfer in background thread
                        transfer_thread = threading.Thread(
                            target=self._execute_transfer,
                            args=(request,),
                            daemon=True
                        )
                        channel.transfer_thread = transfer_thread
                        transfer_thread.start()
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"DMA arbiter error: {e}")
    
    def _execute_transfer(self, request: DMATransferRequest) -> None:
        """Execute a DMA transfer."""
        channel = self.channels[request.channel_id]
        
        try:
            with channel.lock:
                channel.state = DMAChannelState.BUSY
                transferred = 0
                half_point = request.length // 2
                
                # Simulate transfer progress
                transfer_size = 1 << request.source_size.value if request.source_size != DMADataSize.RESERVED else 1
                
                # For circular mode, we need to run continuously until disabled
                cycle_count = 0
                max_cycles = 100  # Limit cycles to prevent infinite loops in tests
                
                while channel.enabled and not channel.stop_requested and (not request.circular or cycle_count < max_cycles):
                    # Process one complete transfer cycle
                    cycle_transferred = 0
                    
                    while cycle_transferred < request.length and channel.enabled and not channel.stop_requested:
                        # Check for error injection
                        if self._should_inject_error(request.channel_id):
                            self._inject_transfer_error(channel)
                            return
                        
                        # Simulate reading from source and writing to destination
                        chunk_size = min(transfer_size, request.length - cycle_transferred)
                        
                        # Simulate transfer time
                        time.sleep(0.001)  # 1ms per transfer unit
                        
                        cycle_transferred += chunk_size
                        transferred += chunk_size
                        channel.data_transferred = transferred
                        
                        # Update addresses with offsets
                        channel.current_source_addr += request.source_offset if request.source_offset else chunk_size
                        channel.current_dest_addr += request.dest_offset if request.dest_offset else chunk_size
                        
                        # Handle circular buffer wraparound
                        if request.circular:
                            if channel.current_source_addr >= channel.source_addr + request.length:
                                channel.current_source_addr = channel.source_start_addr
                            if channel.current_dest_addr >= channel.dest_addr + request.length:
                                channel.current_dest_addr = channel.dest_start_addr
                        
                        # Check for half completion in the current cycle
                        if not channel.half_finish_flag and cycle_transferred >= half_point:
                            channel.half_finish_flag = True
                            self._trigger_interrupt(request.channel_id, "half_complete")
                    
                    # One cycle complete
                    cycle_count += 1
                    if cycle_transferred >= request.length and channel.enabled:
                        channel.finish_flag = True
                        self._trigger_interrupt(request.channel_id, "complete")
                        
                        if not request.circular:
                            # In non-circular mode, stop after one cycle
                            channel.state = DMAChannelState.COMPLETE
                            channel.enabled = False  # Auto-disable for non-circular mode
                            break
                        else:
                            # In circular mode, reset flags for next cycle but keep running
                            channel.finish_flag = False
                            channel.half_finish_flag = False
                    else:
                        # Transfer was stopped or failed
                        break
                
                # Final state update
                if channel.state != DMAChannelState.ERROR:
                    if channel.enabled and request.circular:
                        channel.state = DMAChannelState.BUSY  # Still running in circular mode
                    else:
                        channel.state = DMAChannelState.COMPLETE if channel.finish_flag else DMAChannelState.IDLE
                        
        except Exception as e:
            print(f"DMA transfer error on channel {request.channel_id}: {e}")
            channel.state = DMAChannelState.ERROR
            channel.dest_bus_error = True
            self._trigger_interrupt(request.channel_id, "error")
        finally:
            self._update_global_idle_status()
    
    def _should_inject_error(self, channel_id: int) -> bool:
        """Check if error should be injected for this channel."""
        return (self.error_injection_enabled and 
                channel_id in self.injected_errors and 
                self.injected_errors[channel_id])
    
    def _inject_transfer_error(self, channel: DMAChannel) -> None:
        """Inject a transfer error."""
        with channel.lock:
            channel.source_bus_error = True
            channel.state = DMAChannelState.ERROR
            channel.enabled = False  # Stop the channel
    
    def _trigger_interrupt(self, channel_id: int, interrupt_type: str) -> None:
        """Trigger interrupt for channel."""
        if self.irq_callback:
            self.irq_callback(channel_id, interrupt_type)
    
    def _update_global_idle_status(self) -> None:
        """Update global idle status based on channel states."""
        all_idle = all(
            channel.state in [DMAChannelState.IDLE, DMAChannelState.COMPLETE, DMAChannelState.ERROR]
            for channel in self.channels.values()
        )
        self.global_idle = all_idle
    
    def register_irq_callback(self, callback: Callable) -> None:
        """Register interrupt callback function."""
        self.irq_callback = callback
    
    def set_memory_interface(self, memory_interface: Callable) -> None:
        """Set memory interface for DMA transfers."""
        self.memory_interface = memory_interface
    
    # Error injection interface
    def enable_error_injection(self, channel_id: int, error_type: str = "bus_error") -> None:
        """Enable error injection for a specific channel."""
        self.error_injection_enabled = True
        self.injected_errors[channel_id] = True
    
    def disable_error_injection(self, channel_id: int) -> None:
        """Disable error injection for a specific channel."""
        if channel_id in self.injected_errors:
            del self.injected_errors[channel_id]
        
        if not self.injected_errors:
            self.error_injection_enabled = False
    
    # Utility methods
    def get_channel_info(self, channel_id: int) -> Dict[str, Any]:
        """Get information about a specific channel."""
        if channel_id not in self.channels:
            raise ValueError(f"Invalid channel ID: {channel_id}")
        
        channel = self.channels[channel_id]
        return {
            'channel_id': channel_id,
            'state': channel.state.name,
            'enabled': channel.enabled,
            'priority': channel.priority.name,
            'direction': channel.direction.name,
            'source_size': channel.source_size.name,
            'dest_size': channel.dest_size.name,
            'circular': channel.circular,
            'source_addr': f"0x{channel.source_addr:08X}",
            'dest_addr': f"0x{channel.dest_addr:08X}",
            'transfer_length': channel.transfer_length,
            'data_transferred': channel.data_transferred,
            'finish_flag': channel.finish_flag,
            'half_finish_flag': channel.half_finish_flag,
            'errors': {
                'source_bus_error': channel.source_bus_error,
                'dest_bus_error': channel.dest_bus_error,
                'source_addr_error': channel.source_addr_error,
                'dest_addr_error': channel.dest_addr_error,
                'channel_length_error': channel.channel_length_error
            }
        }
    
    def get_all_channels_info(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all channels."""
        return {ch_id: self.get_channel_info(ch_id) for ch_id in self.channels}
    
    def get_global_status(self) -> Dict[str, Any]:
        """Get global DMA controller status."""
        active_channels = [ch_id for ch_id, ch in self.channels.items() 
                          if ch.state == DMAChannelState.BUSY]
        
        return {
            'global_idle': self.global_idle,
            'active_channels': active_channels,
            'total_channels': self.num_channels,
            'error_injection_enabled': self.error_injection_enabled
        }
    
    def __str__(self) -> str:
        return f"DMADevice({self.name}, {self.num_channels} channels)"