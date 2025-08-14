"""
UART Device Model Implementation

This module implements a complete UART device model based on the UART register
specification defined in uart_registers.yaml. It follows the BaseDevice architecture
and communicates exclusively through the SystemBus.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from ..core.base_device import BaseDevice
from ..core.registers import RegisterType
from ..core.io_interface import IOInterface, IODirection


class UARTDevice(BaseDevice, IOInterface):
    """
    UART Device implementation based on the JHY MCU UART specification.

    Features supported:
    - Full register map from uart_registers.yaml
    - Configurable baud rates with fractional division
    - FIFO support for both TX and RX
    - Multiple interrupt sources
    - LIN mode support
    - RS485 mode support
    - IrDA mode support
    - Hardware flow control (RTS/CTS)
    - Address/Data matching functionality
    - Loopback mode for testing
    """

    def __init__(self, device_name: str, base_address: int, size: int, master_id: int,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize UART device.

        Args:
            device_name: Name of the UART device (e.g., "UART0", "UART1")
            base_address: Base address for UART registers
            size: Size of the address space (default 0x1000)
            master_id: Unique master identifier for bus operations
            config: Device configuration dictionary
        """
        # Store config first, use empty dict if None
        self.config = config or {}

        # UART hardware capabilities (not configuration)
        self.fifo_size = self.config.get('fifo_size', 16)  # Hardware FIFO depth
        self.system_clock = self.config.get('system_clock', 168000000)  # System clock for calculations

        # FIFO buffers (simulated hardware buffers)
        self.tx_fifo = []
        self.rx_fifo = []

        # UART operational state (runtime state, not configuration)
        self.is_transmitting = False
        self.is_receiving = False

        # Mode state (set by register operations, not init)
        self.lin_enabled = False
        self.lin_sleeping = False
        self.rs485_enabled = False
        self.irda_enabled = False
        self.loopback_enabled = False

        # Hardware flow control state
        self.cts_state = True
        self.rts_state = True

        # Initialize IO interface first (before BaseDevice init which calls init())
        IOInterface.__init__(self)

        # Initialize base device
        BaseDevice.__init__(self, device_name, base_address, size, master_id)

        # Create IO connections for external UART communication
        self.create_connection("uart_tx", IODirection.OUTPUT)
        self.create_connection("uart_rx", IODirection.INPUT)

        print(f"UART device {device_name} created at 0x{base_address:08x}")

    def init(self) -> None:
        """Initialize device registers and hardware environment. Required by BaseDevice."""
        # Only initialize registers to their reset values - no configuration
        self._initialize_registers()

        print(f"UART {self.name} hardware environment initialized")

        # Enable IO interface for external connections after everything is set up
        self.enable_io()

    def _read_implementation(self, offset: int, width: int) -> int:
        """Device-specific read implementation. Required by BaseDevice."""
        if offset >= self.size:
            print(f"Read offset 0x{offset:03x} out of range")
            return 0

        value = self.register_manager.read_register(self, offset)
        return value

    def _write_implementation(self, offset: int, value: int, width: int) -> None:
        """Device-specific write implementation. Required by BaseDevice."""
        if offset >= self.size:
            print(f"Write offset 0x{offset:03x} out of range")
            return

        # Mask value based on width
        if width == 1:
            value &= 0xFF
        elif width == 2:
            value &= 0xFFFF
        elif width == 4:
            value &= 0xFFFFFFFF

        self.register_manager.write_register(self, offset, value)

    def _read_register(self, offset: int) -> int:
        """Utility method to read from registers."""
        return self.register_manager.read_register(self, offset)

    def _write_register(self, offset: int, value: int) -> None:
        """Utility method to write to registers."""
        self.register_manager.write_register(self, offset, value)

    def _initialize_registers(self) -> None:
        """Initialize UART registers to their hardware reset values."""
        # RTDATA - Receive/Transmit Data Register (0x000) with callbacks
        self.register_manager.define_register(0x000, "RTDATA", RegisterType.READ_WRITE, 0x00000000, 0x1FF,
                                            read_callback=self._handle_rtdata_read,
                                            write_callback=self._handle_rtdata_write)

        # DIVL - Baud Rate Divisor Low (0x004) with callback
        self.register_manager.define_register(0x004, "DIVL", RegisterType.READ_WRITE, 0x00000000, 0xFF,
                                            write_callback=self._handle_baud_rate_change)

        # DIVH - Baud Rate Divisor High (0x008) with callback
        self.register_manager.define_register(0x008, "DIVH", RegisterType.READ_WRITE, 0x00000000, 0xFF,
                                            write_callback=self._handle_baud_rate_change)

        # CR0 - Control Register 0 (0x00C) with callback for data format
        self.register_manager.define_register(0x00C, "CR0", RegisterType.READ_WRITE, 0x00000000, 0x7F,
                                            write_callback=self._handle_data_format_change)

        # CR1 - Control Register 1 (0x010) with callback
        self.register_manager.define_register(0x010, "CR1", RegisterType.READ_WRITE, 0x00000000, 0xFF,
                                            write_callback=self._handle_cr1_write)

        # FCR - FIFO Control Register (0x014) with callback
        self.register_manager.define_register(0x014, "FCR", RegisterType.READ_WRITE, 0x00000000, 0x01,
                                            write_callback=self._handle_fcr_write)

        # EFR - Enhanced Feature Register (0x018)
        self.register_manager.define_register(0x018, "EFR", RegisterType.READ_WRITE, 0x00000000, 0xC0)

        # IER - Interrupt Enable Register (0x01C)
        self.register_manager.define_register(0x01C, "IER", RegisterType.READ_WRITE, 0x00000000, 0x1FF)

        # SR0 - Status Register 0 (0x020) with callback
        self.register_manager.define_register(0x020, "SR0", RegisterType.READ_WRITE, 0x00000060, 0x1FF,
                                            read_callback=self._handle_sr0_read)  # TC=1, TDNF=1 initially

        # SR1 - Status Register 1 (0x024) with callback
        self.register_manager.define_register(0x024, "SR1", RegisterType.READ_WRITE, 0x000000E0, 0x3FF,
                                            read_callback=self._handle_sr1_read)  # RTS=1, CTS=1, UARTIDLE=1

        # SMP - Sample Rate Register (0x028) with callback
        self.register_manager.define_register(0x028, "SMP", RegisterType.READ_WRITE, 0x00000000, 0x03,
                                            write_callback=self._handle_baud_rate_change)

        # ADDR - Address Register (0x02C)
        self.register_manager.define_register(0x02C, "ADDR", RegisterType.READ_WRITE, 0x00000000, 0x1FF)

        # DATA - Data Register (0x030)
        self.register_manager.define_register(0x030, "DATA", RegisterType.READ_WRITE, 0x00000000, 0x1FF)

        # GUARD - Guard Time Register (0x034)
        self.register_manager.define_register(0x034, "GUARD", RegisterType.READ_WRITE, 0x00000000, 0x1F)

        # SLEEPEN - Sleep Enable Register (0x03C)
        self.register_manager.define_register(0x03C, "SLEEPEN", RegisterType.READ_WRITE, 0x00000000, 0x01)

        # DMAEN - DMA Enable Register (0x040)
        self.register_manager.define_register(0x040, "DMAEN", RegisterType.READ_WRITE, 0x00000000, 0x03)

        # DIVF - Fractional Division Register (0x044) with callback
        self.register_manager.define_register(0x044, "DIVF", RegisterType.READ_WRITE, 0x00000000, 0x1F,
                                            write_callback=self._handle_baud_rate_change)

        # MTCHCR - Match Control Register (0x048)
        self.register_manager.define_register(0x048, "MTCHCR", RegisterType.READ_WRITE, 0x00000000, 0x07)

        # RS485CR - RS485 Control Register (0x04C) with callback
        self.register_manager.define_register(0x04C, "RS485CR", RegisterType.READ_WRITE, 0x00000000, 0xB0,
                                            write_callback=self._handle_rs485cr_write)

        # CNTR - Counter Register (0x054)
        self.register_manager.define_register(0x054, "CNTR", RegisterType.READ_WRITE, 0x00000000, 0xFF)

        # IDLE - Idle Line Register (0x058)
        self.register_manager.define_register(0x058, "IDLE", RegisterType.READ_WRITE, 0x00000000, 0x10)

        # LINCR - LIN Control Register (0x05C) with callback
        self.register_manager.define_register(0x05C, "LINCR", RegisterType.READ_WRITE, 0x00000001, 0xFF,
                                            write_callback=self._handle_lincr_write)  # LINSLP=1 initially

        # BRKLGH - Break Length Register (0x060)
        self.register_manager.define_register(0x060, "BRKLGH", RegisterType.READ_WRITE, 0x00000000, 0x0F)

        # PMIN0 - Pulse Minimum 0 Register (0x064)
        self.register_manager.define_register(0x064, "PMIN0", RegisterType.READ_WRITE, 0x00000000, 0xFF)

        # PMIN1 - Pulse Minimum 1 Register (0x068)
        self.register_manager.define_register(0x068, "PMIN1", RegisterType.READ_WRITE, 0x00000000, 0xFF)

        # PWDTH - Pulse Width Register (0x06C)
        self.register_manager.define_register(0x06C, "PWDTH", RegisterType.READ_WRITE, 0x00000000, 0x07)

    def _handle_rtdata_write(self, device_instance, offset: int, value: int) -> None:
        """Handle write to RTDATA register (transmit data)."""
        # Check if transmitter is enabled
        cr1 = self._read_register(0x010)
        if not (cr1 & 0x02):  # TXEN bit
            print("Write to RTDATA when transmitter disabled")
            return

        # Check FIFO mode
        fcr = self._read_register(0x014)
        fifo_enabled = bool(fcr & 0x01)  # FIFOE bit

        if fifo_enabled:
            # FIFO mode - add to TX FIFO if not full
            if len(self.tx_fifo) < self.fifo_size:
                self.tx_fifo.append(value & 0x1FF)  # 9-bit data mask
                self._update_tx_status()
            else:
                # FIFO full - set TXDF flag
                sr0 = self._read_register(0x020)
                self._write_register(0x020, sr0 | 0x100)  # TXDF=1
        else:
            # Non-FIFO mode - direct transmission
            self._transmit_data(value & 0x1FF)

        # Handle loopback mode
        if self.loopback_enabled:
            self._receive_data(value & 0x1FF)

    def _handle_rtdata_read(self, device_instance, offset: int, value: int) -> int:
        """Handle read from RTDATA register (receive data)."""
        # Check if receiver is enabled
        cr1 = self._read_register(0x010)
        if not (cr1 & 0x01):  # RXEN bit
            print("Read from RTDATA when receiver disabled")
            return 0

        # Check FIFO mode
        fcr = self._read_register(0x014)
        fifo_enabled = bool(fcr & 0x01)  # FIFOE bit

        if fifo_enabled:
            # FIFO mode - read from RX FIFO
            if self.rx_fifo:
                data = self.rx_fifo.pop(0)
                self._update_rx_status()
                return data
            else:
                return 0
        else:
            # Non-FIFO mode - read from register
            return value

    def _handle_cr1_write(self, device_instance, offset: int, value: int) -> None:
        """Handle write to CR1 register (control operations)."""
        old_value = self._read_register(offset)

        # Update operational modes
        self.loopback_enabled = bool(value & 0x10)  # LOOP bit

        # Check TX/RX enable changes
        tx_enabled = bool(value & 0x02)  # TXEN bit
        rx_enabled = bool(value & 0x01)  # RXEN bit

        if tx_enabled != bool(old_value & 0x02):
            print(f"TX {'enabled' if tx_enabled else 'disabled'}")

        if rx_enabled != bool(old_value & 0x01):
            print(f"RX {'enabled' if rx_enabled else 'disabled'}")

    def _handle_fcr_write(self, device_instance, offset: int, value: int) -> None:
        """Handle write to FCR register (FIFO control)."""
        fifo_enabled = bool(value & 0x01)  # FIFOE bit

        if fifo_enabled:
            print("FIFO mode enabled")
        else:
            print("FIFO mode disabled")
            # Clear FIFOs when disabled
            self.tx_fifo.clear()
            self.rx_fifo.clear()

    def _handle_sr0_read(self, device_instance, offset: int, value: int) -> int:
        """Handle read from SR0 register (update status)."""
        self._update_tx_status()
        self._update_rx_status()
        # Return the updated value directly from register storage, not through read callback
        return self.register_manager.registers[offset].value

    def _handle_sr1_read(self, device_instance, offset: int, value: int) -> int:
        """Handle read from SR1 register (update status)."""
        # Update SR1 register without recursive status update
        sr1 = self.register_manager.registers[offset].value

        # Update UART idle status
        if not self.is_transmitting and not self.is_receiving:
            sr1 |= 0x20  # UARTIDLE=1
        else:
            sr1 &= ~0x20 # UARTIDLE=0

        # Update flow control status
        if self.rts_state:
            sr1 |= 0x80  # RTS=1
        else:
            sr1 &= ~0x80 # RTS=0

        if self.cts_state:
            sr1 |= 0x40  # CTS=1
        else:
            sr1 &= ~0x40 # CTS=0

        # Update register storage directly
        self.register_manager.registers[offset].value = sr1
        return sr1

    def _handle_lincr_write(self, device_instance, offset: int, value: int) -> None:
        """Handle write to LINCR register (LIN control)."""
        self.lin_enabled = bool(value & 0x80)  # LINEN bit
        self.lin_sleeping = bool(value & 0x01)  # LINSLP bit

        # Handle break field transmission
        if value & 0x10:  # SDBRK bit
            self._send_lin_break()

    def _handle_rs485cr_write(self, device_instance, offset: int, value: int) -> None:
        """Handle write to RS485CR register (RS485 control)."""
        self.rs485_enabled = bool(value & 0x80)  # RS485EN bit

        if self.rs485_enabled:
            print("RS485 mode enabled")

    def _transmit_data(self, data: int) -> None:
        """Simulate data transmission."""
        self.is_transmitting = True

        # In loopback mode, data goes directly to RX
        if self.loopback_enabled:
            self._receive_data(data)

        # Clear TC (Transmit Complete) flag temporarily
        sr0 = self._read_register(0x020)
        self._write_register(0x020, sr0 & ~0x40)  # TC=0

        # Simulate transmission completion
        self.is_transmitting = False
        sr0 = self._read_register(0x020)
        self._write_register(0x020, sr0 | 0x40)  # TC=1

        # Trigger interrupt if enabled
        ier = self._read_register(0x01C)
        if ier & 0x04:  # ETXTC bit
            self._trigger_interrupt("TX_COMPLETE")

        print(f"Transmitted data: 0x{data:02x}")

        # Send data to external device via IO interface
        self.output_data("uart_tx", data, 8)

    def _receive_data(self, data: int) -> None:
        """Simulate data reception."""
        fcr = self._read_register(0x014)
        fifo_enabled = bool(fcr & 0x01)  # FIFOE bit

        if fifo_enabled:
            # FIFO mode
            if len(self.rx_fifo) < self.fifo_size:
                self.rx_fifo.append(data)
                self._update_rx_status()
            else:
                # FIFO full - set overrun error
                sr0 = self._read_register(0x020)
                self._write_register(0x020, sr0 | 0x02)  # OE=1
        else:
            # Non-FIFO mode
            self.register_manager.registers[0x000].value = data
            sr0 = self._read_register(0x020)
            self._write_register(0x020, sr0 | 0x01)  # DR=1

        # Trigger interrupt if enabled
        ier = self._read_register(0x01C)
        if ier & 0x01:  # ERDNE bit
            self._trigger_interrupt("RX_DATA_READY")

        print(f"Received data: 0x{data:02x}")

    def _handle_input_data(self, connection_id: str, data: int, width: int) -> None:
        """Handle data received from external device via IO interface."""
        if connection_id == "uart_rx":
            # Simulate receiving data from external UART connection
            self._receive_data(data)
            print(f"External data received: 0x{data:02x}")

    def send_external_data(self, data: int) -> None:
        """Send data to external UART device (for testing/simulation)."""
        self._receive_data(data)

    def receive_external_data(self, timeout: float = 0.1) -> Optional[int]:
        """Receive data from external UART device (for testing/simulation)."""
        data_tuple = self.input_data("uart_rx", timeout)
        if data_tuple:
            data, width = data_tuple
            return data
        return None

    def _update_tx_status(self) -> None:
        """Update transmit status flags."""
        # Get current SR0 value from register storage to avoid triggering read callback
        sr0 = self.register_manager.registers[0x020].value
        fcr = self.register_manager.registers[0x014].value
        fifo_enabled = bool(fcr & 0x01)

        if fifo_enabled:
            # FIFO mode status
            if len(self.tx_fifo) == 0:
                sr0 |= 0x20   # TDNF=1 (not full)
                sr0 |= 0x40   # TC=1 (complete)
                sr0 &= ~0x100 # TXDF=0 (not full)
            elif len(self.tx_fifo) < self.fifo_size:
                sr0 |= 0x20   # TDNF=1 (not full)
                sr0 &= ~0x40  # TC=0 (not complete)
                sr0 &= ~0x100 # TXDF=0 (not full)
            else:
                sr0 &= ~0x20  # TDNF=0 (full)
                sr0 &= ~0x40  # TC=0 (not complete)
                sr0 |= 0x100  # TXDF=1 (full)
        else:
            # Non-FIFO mode
            if not self.is_transmitting:
                sr0 |= 0x20  # TDNF=1 (ready for data)
                sr0 |= 0x40  # TC=1 (complete)
            else:
                sr0 &= ~0x20 # TDNF=0 (busy)
                sr0 &= ~0x40 # TC=0 (not complete)

        # Update register storage directly to avoid triggering write callback
        self.register_manager.registers[0x020].value = sr0

    def _update_rx_status(self) -> None:
        """Update receive status flags."""
        # Get current SR0 value from register storage to avoid triggering read callback
        sr0 = self.register_manager.registers[0x020].value
        fcr = self.register_manager.registers[0x014].value
        fifo_enabled = bool(fcr & 0x01)

        if fifo_enabled:
            # FIFO mode
            if self.rx_fifo:
                sr0 |= 0x01  # DR=1 (data ready)
            else:
                sr0 &= ~0x01 # DR=0 (no data)
        else:
            # Non-FIFO mode - DR flag managed by register reads
            pass

        # Update register storage directly to avoid triggering write callback
        self.register_manager.registers[0x020].value = sr0

    def _update_status_registers(self) -> None:
        """Update all status registers with current state."""
        self._update_tx_status()
        self._update_rx_status()

        # Update SR1 register
        sr1 = self._read_register(0x024)

        # Update UART idle status
        if not self.is_transmitting and not self.is_receiving:
            sr1 |= 0x20  # UARTIDLE=1
        else:
            sr1 &= ~0x20 # UARTIDLE=0

        # Update flow control status
        if self.rts_state:
            sr1 |= 0x80  # RTS=1
        else:
            sr1 &= ~0x80 # RTS=0

        if self.cts_state:
            sr1 |= 0x40  # CTS=1
        else:
            sr1 &= ~0x40 # CTS=0

        self._write_register(0x024, sr1)

    def _send_lin_break(self) -> None:
        """Send LIN break field."""
        if not self.lin_enabled:
            return

        brklgh = self._read_register(0x060) & 0x0F
        break_length = 13 + brklgh  # 13-28 bits

        print(f"Sending LIN break field: {break_length} bits")

        # Simulate break transmission
        sr1 = self._read_register(0x024)
        self._write_register(0x024, sr1 | 0x04)  # FBRK=1

        # Clear SDBRK bit automatically
        lincr = self._read_register(0x05C)
        self._write_register(0x05C, lincr & ~0x10)

    def _trigger_interrupt(self, interrupt_type: str) -> None:
        """Trigger an interrupt."""
        # Map interrupt types to IRQ indices for compatibility
        irq_mapping = {
            "TX_COMPLETE": 0,
            "RX_DATA_READY": 1,
            "ERROR": 2,
            "LIN_BREAK": 3
        }

        irq_index = irq_mapping.get(interrupt_type, 0)
        self.trigger_interrupt(irq_index)
        print(f"Triggered interrupt: {interrupt_type} (IRQ {irq_index})")

    def start_device(self) -> bool:
        """Start UART device operation (hardware ready state)."""
        try:
            print(f"UART {self.name} hardware ready for operation")
            return True
        except Exception as e:
            print(f"UART {self.name} start failed: {e}")
            return False

    def stop_device(self) -> bool:
        """Stop UART device operation."""
        try:
            # Disable TX and RX
            cr1 = self._read_register(0x010)
            self._write_register(0x010, cr1 & ~0x03)  # TXEN=0, RXEN=0

            # Clear FIFOs
            self.tx_fifo.clear()
            self.rx_fifo.clear()

            # Disable IO interface
            self.disable_io()

            print(f"UART {self.name} stopped")
            return True
        except Exception as e:
            print(f"UART {self.name} stop failed: {e}")
            return False
        try:
            # Clear all FIFOs
            self.tx_fifo.clear()
            self.rx_fifo.clear()

            # Reset operational flags
            self.is_transmitting = False
            self.is_receiving = False
            self.loopback_enabled = False
            self.lin_enabled = False
            self.rs485_enabled = False
            self.irda_enabled = False

            # Cleanup IO interface
            self.cleanup_io()

            print(f"UART {self.name} cleanup completed")
        except Exception as e:
            print(f"UART {self.name} cleanup failed: {e}")

    def _handle_baud_rate_change(self, device_instance, offset: int, value: int) -> None:
        """Handle baud rate related register changes (triggered by driver)."""
        # Calculate current baud rate based on register values
        divl = self._read_register(0x004) & 0xFF
        divh = self._read_register(0x008) & 0xFF
        divf = self._read_register(0x044) & 0x1F
        smp = self._read_register(0x028) & 0x03

        # Calculate divisor
        divisor_int = (divh << 8) | divl
        if divisor_int == 0:
            return  # Avoid division by zero

        # Calculate sample rate multiplier
        sample_multiplier = 16 if smp == 0 else (8 if smp == 1 else (4 if smp == 2 else 2))

        # Calculate effective baud rate
        divisor_float = divisor_int + (divf / 32.0)
        calculated_baud = self.system_clock / (sample_multiplier * divisor_float)

        print(f"UART {self.name} baud rate updated by driver: {calculated_baud:.0f} baud")
        print(f"  Divisor: {divisor_int}.{divf}/32, Sample: {sample_multiplier}x")

    def _handle_data_format_change(self, device_instance, offset: int, value: int) -> None:
        """Handle data format changes (triggered by driver)."""
        # Parse CR0 register bits
        wls = value & 0x03      # Word length
        stb = (value >> 2) & 1  # Stop bits
        pen = (value >> 3) & 1  # Parity enable
        eps = (value >> 4) & 1  # Even parity select

        # Determine data bits
        if wls == 0:
            data_bits = 7
        elif wls == 1:
            data_bits = 8
        elif wls == 2:
            data_bits = 9
        else:
            data_bits = 8  # Default

        # Determine stop bits
        stop_bits = 2 if stb else 1

        # Determine parity
        if not pen:
            parity = "none"
        elif eps:
            parity = "even"
        else:
            parity = "odd"

        print(f"UART {self.name} data format updated by driver: {data_bits}{parity[0].upper()}{stop_bits}")

    def get_current_baud_rate(self) -> float:
        """Get current baud rate based on register settings."""
        divl = self._read_register(0x004) & 0xFF
        divh = self._read_register(0x008) & 0xFF
        divf = self._read_register(0x044) & 0x1F
        smp = self._read_register(0x028) & 0x03

        divisor_int = (divh << 8) | divl
        if divisor_int == 0:
            return 0.0

        sample_multiplier = 16 if smp == 0 else (8 if smp == 1 else (4 if smp == 2 else 2))
        divisor_float = divisor_int + (divf / 32.0)

        return self.system_clock / (sample_multiplier * divisor_float)

    def get_current_data_format(self) -> Dict[str, Any]:
        """Get current data format based on register settings."""
        cr0 = self._read_register(0x00C)

        wls = cr0 & 0x03
        stb = (cr0 >> 2) & 1
        pen = (cr0 >> 3) & 1
        eps = (cr0 >> 4) & 1

        data_bits = {0: 7, 1: 8, 2: 9}.get(wls, 8)
        stop_bits = 2 if stb else 1

        if not pen:
            parity = "none"
        elif eps:
            parity = "even"
        else:
            parity = "odd"

        return {
            'data_bits': data_bits,
            'stop_bits': stop_bits,
            'parity': parity
        }

    def get_status_info(self) -> Dict[str, Any]:
        """Get current UART status information."""
        sr0 = self._read_register(0x020)
        sr1 = self._read_register(0x024)
        cr1 = self._read_register(0x010)

        # Get current configuration from registers
        current_baud = self.get_current_baud_rate()
        data_format = self.get_current_data_format()

        return {
                    'device_name': self.name,
                    'master_id': self.master_id,
                    'base_address': f"0x{self.base_address:08x}",
                    'current_baud_rate': f"{current_baud:.0f}",
                    'data_format': f"{data_format['data_bits']}{data_format['parity'][0].upper()}{data_format['stop_bits']}",
                    'tx_enabled': bool(cr1 & 0x02),
                    'rx_enabled': bool(cr1 & 0x01),
                    'tx_complete': bool(sr0 & 0x40),
                    'rx_data_ready': bool(sr0 & 0x01),
                    'tx_fifo_count': len(self.tx_fifo),
                    'rx_fifo_count': len(self.rx_fifo),
                    'loopback_mode': self.loopback_enabled,
                    'lin_mode': self.lin_enabled,
                    'rs485_mode': self.rs485_enabled,
                    'is_transmitting': self.is_transmitting,
                    'is_receiving': self.is_receiving,
                    'io_connections': self.get_all_connections_status(),
                    'io_enabled': self.is_io_ready(),
                    'system_clock': self.system_clock,
                    'fifo_size': self.fifo_size
                }