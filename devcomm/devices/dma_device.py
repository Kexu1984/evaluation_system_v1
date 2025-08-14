"""
DMA device implementation for the DevCommV3 framework.

This module provides a DMA controller that supports multiple channels
and various transfer modes (mem2mem, mem2peri, peri2mem).
"""

from typing import Dict, Any, Optional, Callable
from enum import Enum
import threading
import time
from ..core.base_device import BaseDevice
from ..core.registers import RegisterType


class DMATransferMode(Enum):
    """DMA transfer modes."""
    MEM2MEM = "mem2mem"
    MEM2PERI = "mem2peri"
    PERI2MEM = "peri2mem"
    PERI2PERI = "peri2peri"


class DMAChannelState(Enum):
    """DMA channel states."""
    IDLE = "idle"
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class DMAChannel:
    """Individual DMA channel."""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.state = DMAChannelState.IDLE
        self.src_address = 0
        self.dst_address = 0
        self.transfer_size = 0
        self.remaining_size = 0
        self.transfer_mode = DMATransferMode.MEM2MEM
        self.src_device = None
        self.dst_device = None
        self.completion_callback = None
        self.error_callback = None
        self.lock = threading.RLock()
        self.src_increase = True
        self.dst_increase = True

    def configure(self, src_address: int, dst_address: int, size: int, src_fix: bool, dst_fix: bool,
                  mode: DMATransferMode, src_device=None, dst_device=None) -> None:
        """Configure DMA channel for transfer."""
        with self.lock:
            if self.state == DMAChannelState.RUNNING:
                raise RuntimeError(f"DMA channel {self.channel_id} is currently running")

            self.src_address = src_address
            self.dst_address = dst_address
            self.transfer_size = size
            self.remaining_size = size
            self.transfer_mode = mode
            self.src_device = src_device
            self.dst_device = dst_device
            self.state = DMAChannelState.CONFIGURED
            self.src_fix = src_fix
            self.dst_fix = dst_fix

    def start(self) -> None:
        """Start DMA transfer."""
        with self.lock:
            if self.state != DMAChannelState.CONFIGURED:
                raise RuntimeError(f"DMA channel {self.channel_id} not configured")
            self.state = DMAChannelState.RUNNING

    def pause(self) -> None:
        """Pause DMA transfer."""
        with self.lock:
            if self.state == DMAChannelState.RUNNING:
                self.state = DMAChannelState.PAUSED

    def resume(self) -> None:
        """Resume DMA transfer."""
        with self.lock:
            if self.state == DMAChannelState.PAUSED:
                self.state = DMAChannelState.RUNNING

    def stop(self) -> None:
        """Stop DMA transfer."""
        with self.lock:
            self.state = DMAChannelState.IDLE
            self.remaining_size = 0

    def is_running(self) -> bool:
        """Check if channel is running."""
        return self.state == DMAChannelState.RUNNING

    def is_completed(self) -> bool:
        """Check if transfer is completed."""
        return self.state == DMAChannelState.COMPLETED

    def get_progress(self) -> float:
        """Get transfer progress (0.0 to 1.0)."""
        if self.transfer_size == 0:
            return 0.0
        return (self.transfer_size - self.remaining_size) / self.transfer_size


class DMADevice(BaseDevice):
    """DMA controller device implementation."""

    # Register offsets
    CTRL_REG = 0x00
    STATUS_REG = 0x04
    IRQ_STATUS_REG = 0x08
    IRQ_ENABLE_REG = 0x0C

    # Channel registers (per channel, starting at 0x10)
    CHANNEL_BASE = 0x10
    CHANNEL_SIZE = 0x20
    CH_CTRL_OFFSET = 0x00
    CH_SRC_ADDR_OFFSET = 0x04
    CH_DST_ADDR_OFFSET = 0x08
    CH_SIZE_OFFSET = 0x0C
    CH_STATUS_OFFSET = 0x10

    def __init__(self, name: str, base_address: int, size: int, master_id: int,
                 num_channels: int = 4):
        self.num_channels = num_channels
        self.channels: Dict[int, DMAChannel] = {}
        self.transfer_threads: Dict[int, threading.Thread] = {}
        self.global_enable = False

        # Create DMA channels
        for i in range(num_channels):
            self.channels[i] = DMAChannel(i)

        super().__init__(name, base_address, size, master_id)

    def init(self) -> None:
        """Initialize DMA device registers."""
        # Global control registers
        self.register_manager.define_register(
            self.CTRL_REG, "CTRL", RegisterType.READ_WRITE, 0x00000000,
            write_callback=self._ctrl_write_callback
        )

        self.register_manager.define_register(
            self.STATUS_REG, "STATUS", RegisterType.READ_ONLY, 0x00000000,
            read_callback=self._status_read_callback
        )

        self.register_manager.define_register(
            self.IRQ_STATUS_REG, "IRQ_STATUS", RegisterType.READ_CLEAR, 0x00000000
        )

        self.register_manager.define_register(
            self.IRQ_ENABLE_REG, "IRQ_ENABLE", RegisterType.READ_WRITE, 0x00000000
        )

        # Channel-specific registers
        for ch in range(self.num_channels):
            base_offset = self.CHANNEL_BASE + ch * self.CHANNEL_SIZE

            self.register_manager.define_register(
                base_offset + self.CH_CTRL_OFFSET, f"CH{ch}_CTRL",
                RegisterType.READ_WRITE, 0x00000000,
                write_callback=lambda dev, offset, value, ch=ch: self._channel_ctrl_write_callback(dev, offset, value, ch)
            )

            self.register_manager.define_register(
                base_offset + self.CH_SRC_ADDR_OFFSET, f"CH{ch}_SRC_ADDR",
                RegisterType.READ_WRITE, 0x00000000
            )

            self.register_manager.define_register(
                base_offset + self.CH_DST_ADDR_OFFSET, f"CH{ch}_DST_ADDR",
                RegisterType.READ_WRITE, 0x00000000
            )

            self.register_manager.define_register(
                base_offset + self.CH_SIZE_OFFSET, f"CH{ch}_SIZE",
                RegisterType.READ_WRITE, 0x00000000
            )

            self.register_manager.define_register(
                base_offset + self.CH_STATUS_OFFSET, f"CH{ch}_STATUS",
                RegisterType.READ_ONLY, 0x00000000,
                read_callback=lambda dev, offset, value, ch=ch: self._channel_status_read_callback(dev, offset, value, ch)
            )

    def _read_implementation(self, offset: int, width: int) -> int:
        """Read from DMA device registers."""
        return self.register_manager.read_register(self, offset, width)

    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """Write to DMA device registers."""
        self.register_manager.write_register(self, offset, value, width)

    def _ctrl_write_callback(self, device, offset: int, value: int) -> None:
        """Handle writes to control register."""
        self.global_enable = bool(value & 0x1)

        # Global reset
        if value & 0x2:
            self._reset_all_channels()

    def _status_read_callback(self, device, offset: int, value: int) -> int:
        """Handle reads from status register."""
        status = 0
        if self.global_enable:
            status |= 0x1

        # Set bits for running channels
        for ch_id, channel in self.channels.items():
            if channel.is_running():
                status |= (1 << (ch_id + 8))

        return status

    def _channel_ctrl_write_callback(self, device, offset: int, value: int, channel_id: int) -> None:
        """Handle writes to channel control register."""
        if channel_id not in self.channels:
            return

        print(">>>>Channel control write:", f"Channel {channel_id}, Value: 0x{value:08X}")
        channel = self.channels[channel_id]

        # Extract control bits
        enable = bool(value & 0x1)
        start = bool(value & 0x2)
        pause = bool(value & 0x4)
        stop = bool(value & 0x8)
        mode = (value >> 4) & 0x3
        src_fix = bool(value & 0x100)
        dst_fix = bool(value & 0x200)

        # Configure transfer mode
        if mode == 0:
            transfer_mode = DMATransferMode.MEM2MEM
        elif mode == 1:
            transfer_mode = DMATransferMode.MEM2PERI
        elif mode == 2:
            transfer_mode = DMATransferMode.PERI2MEM
        else:
            transfer_mode = DMATransferMode.PERI2PERI

        if enable and not channel.is_running():
            # Configure channel from registers
            src_addr_offset = self.CHANNEL_BASE + channel_id * self.CHANNEL_SIZE + self.CH_SRC_ADDR_OFFSET
            dst_addr_offset = self.CHANNEL_BASE + channel_id * self.CHANNEL_SIZE + self.CH_DST_ADDR_OFFSET
            size_offset = self.CHANNEL_BASE + channel_id * self.CHANNEL_SIZE + self.CH_SIZE_OFFSET

            src_addr = self.register_manager.read_register(self, src_addr_offset)
            dst_addr = self.register_manager.read_register(self, dst_addr_offset)
            size = self.register_manager.read_register(self, size_offset)

            try:
                channel.configure(src_addr, dst_addr, size, src_fix, dst_fix, transfer_mode)
            except Exception as e:
                self._set_channel_error(channel_id, str(e))
                return

        if start and channel.state == DMAChannelState.CONFIGURED:
            self._start_transfer(channel_id)
        elif pause:
            channel.pause()
        elif stop:
            self._stop_transfer(channel_id)

    def _channel_status_read_callback(self, device, offset: int, value: int, channel_id: int) -> int:
        """Handle reads from channel status register."""
        if channel_id not in self.channels:
            return 0

        channel = self.channels[channel_id]
        status = 0

        # State bits
        if channel.state == DMAChannelState.IDLE:
            status |= 0x0
        elif channel.state == DMAChannelState.CONFIGURED:
            status |= 0x1
        elif channel.state == DMAChannelState.RUNNING:
            status |= 0x2
        elif channel.state == DMAChannelState.PAUSED:
            status |= 0x3
        elif channel.state == DMAChannelState.COMPLETED:
            status |= 0x4
        elif channel.state == DMAChannelState.ERROR:
            status |= 0x5

        # Progress (remaining size in upper 16 bits)
        status |= (channel.remaining_size & 0xFFFF) << 16

        return status

    def _start_transfer(self, channel_id: int) -> None:
        """Start DMA transfer in a separate thread."""
        if not self.global_enable:
            self._set_channel_error(channel_id, "DMA globally disabled")
            return

        channel = self.channels[channel_id]
        channel.start()

        # Create transfer thread
        transfer_thread = threading.Thread(
            target=self._execute_transfer,
            args=(channel_id,),
            daemon=True
        )

        self.transfer_threads[channel_id] = transfer_thread
        transfer_thread.start()

    def _execute_transfer(self, channel_id: int) -> None:
        """Execute DMA transfer."""
        channel = self.channels[channel_id]

        try:
            while channel.remaining_size > 0 and channel.is_running():
                # Transfer one word at a time
                transfer_size = min(4, channel.remaining_size)

                # Calculate current addresses
                transferred = channel.transfer_size - channel.remaining_size
                if channel.src_fix == False:
                    current_src = channel.src_address + transferred
                else:
                    current_src = channel.src_address
                if channel.dst_fix == False:
                    current_dst = channel.dst_address + transferred
                else:
                    current_dst = channel.dst_address

                # Perform transfer based on mode
                print(f"DMA start transfer: src:{current_src} dst:{current_dst} trans:{transfer_size}")
                if channel.transfer_mode == DMATransferMode.MEM2MEM:
                    self._transfer_mem2mem(current_src, current_dst, transfer_size)
                elif channel.transfer_mode == DMATransferMode.MEM2PERI:
                    self._transfer_mem2peri(current_src, current_dst, transfer_size, channel.dst_device)
                elif channel.transfer_mode == DMATransferMode.PERI2MEM:
                    self._transfer_peri2mem(current_src, current_dst, transfer_size, channel.src_device)
                else:
                    raise NotImplementedError(f"Transfer mode {channel.transfer_mode} not implemented")

                channel.remaining_size -= transfer_size

                # Small delay to prevent overwhelming the bus
                time.sleep(0.001)

            if channel.remaining_size == 0:
                channel.state = DMAChannelState.COMPLETED
                self._signal_completion(channel_id)

        except Exception as e:
            print(f"Channel error happend:{e}")
            self._set_channel_error(channel_id, str(e))

    def _transfer_mem2mem(self, src_addr: int, dst_addr: int, size: int) -> None:
        """Perform memory-to-memory transfer."""
        if not self.bus:
            raise RuntimeError("DMA device not connected to bus")

        # Read from source
        data = self.bus.read(self.master_id, src_addr, size)

        # Write to destination
        self.bus.write(self.master_id, dst_addr, data, size)

    def _transfer_mem2peri(self, src_addr: int, dst_addr: int, size: int, dst_device) -> None:
        """Perform memory-to-peripheral transfer."""
        if not self.bus:
            raise RuntimeError("DMA device not connected to bus")

        # Read from memory
        data = self.bus.read(self.master_id, src_addr, size)

        # Write to peripheral
        print(f">>>DMA mem2peri read from: {src_addr:08X}=={size:08X} write to: {dst_addr:08X}=={data:08X}")
        self.bus.write(self.master_id, dst_addr, data, size)

    def _transfer_peri2mem(self, src_addr: int, dst_addr: int, size: int, src_device) -> None:
        """Perform peripheral-to-memory transfer."""
        if not self.bus:
            raise RuntimeError("DMA device not connected to bus")

        # Read from peripheral
        data = self.bus.read(self.master_id, src_addr, size)

        # Write to memory
        self.bus.write(self.master_id, dst_addr, data, size)

    def _stop_transfer(self, channel_id: int) -> None:
        """Stop DMA transfer."""
        channel = self.channels[channel_id]
        channel.stop()

        # Wait for transfer thread to complete
        if channel_id in self.transfer_threads:
            thread = self.transfer_threads[channel_id]
            if thread.is_alive():
                thread.join(timeout=1.0)
            del self.transfer_threads[channel_id]

    def _set_channel_error(self, channel_id: int, error_msg: str) -> None:
        """Set channel to error state."""
        channel = self.channels[channel_id]
        channel.state = DMAChannelState.ERROR

        # Set IRQ status bit
        irq_status = self.register_manager.read_register(self, self.IRQ_STATUS_REG)
        irq_status |= (1 << channel_id)
        self.register_manager.write_register(self, self.IRQ_STATUS_REG, irq_status)

        # Trigger interrupt if enabled
        irq_enable = self.register_manager.read_register(self, self.IRQ_ENABLE_REG)
        if irq_enable & (1 << channel_id):
            self.trigger_interrupt(channel_id)

    def _signal_completion(self, channel_id: int) -> None:
        """Signal DMA transfer completion."""
        # Set IRQ status bit
        irq_status = self.register_manager.read_register(self, self.IRQ_STATUS_REG)
        irq_status |= (1 << (channel_id + 8))  # Completion bits start at bit 8
        self.register_manager.write_register(self, self.IRQ_STATUS_REG, irq_status)

        # Trigger interrupt if enabled
        irq_enable = self.register_manager.read_register(self, self.IRQ_ENABLE_REG)
        print(f"Triggering completion interrupt for channel {channel_id} with irqstatus {irq_enable:08X}")
        if irq_enable & (1 << (channel_id + 8)):
            self.trigger_interrupt(channel_id + 8)

    def _reset_all_channels(self) -> None:
        """Reset all DMA channels."""
        for channel_id in self.channels:
            self._stop_transfer(channel_id)

    def get_channel_info(self, channel_id: int) -> Dict[str, Any]:
        """Get information about a specific channel."""
        if channel_id not in self.channels:
            raise ValueError(f"Invalid channel ID: {channel_id}")

        channel = self.channels[channel_id]
        return {
            'channel_id': channel_id,
            'state': channel.state.value,
            'src_address': f"0x{channel.src_address:08X}",
            'dst_address': f"0x{channel.dst_address:08X}",
            'transfer_size': channel.transfer_size,
            'remaining_size': channel.remaining_size,
            'progress': channel.get_progress(),
            'transfer_mode': channel.transfer_mode.value
        }

    def get_all_channels_info(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all channels."""
        return {ch_id: self.get_channel_info(ch_id) for ch_id in self.channels}

    def __str__(self) -> str:
        return f"DMADevice({self.name}, {self.num_channels} channels)"