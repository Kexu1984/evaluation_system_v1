"""
IO Interface implementation for the DevCommV3 framework.

This module provides the IO interface for devices that support external peripheral
connections such as UART, SPI, CAN, etc. It enables simulation of device 
connections and real-time data exchange.
"""

import threading
import queue
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any, Dict, List
from enum import Enum


class IODirection(Enum):
    """IO direction enumeration."""
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"


class IOConnection:
    """Represents a connection to an external device."""
    
    def __init__(self, connection_id: str, direction: IODirection):
        self.connection_id = connection_id
        self.direction = direction
        self.connected = False
        self.data_queue = queue.Queue()
        self.thread = None
        self.stop_event = threading.Event()
        self.data_callback = None
        
    def start_thread(self, target_func: Callable, *args, **kwargs):
        """Start a thread for this connection."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=target_func, args=args, kwargs=kwargs)
            self.thread.daemon = True
            self.thread.start()
    
    def stop_thread(self):
        """Stop the connection thread."""
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=1.0)
    
    def put_data(self, data: int, width: int):
        """Put data into the connection queue."""
        try:
            self.data_queue.put((data, width), timeout=0.1)
        except queue.Full:
            pass  # Drop data if queue is full
    
    def get_data(self, timeout: float = 0.1) -> Optional[tuple]:
        """Get data from the connection queue."""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None


class ExternalDevice(ABC):
    """Abstract base class for external devices that can connect to IO interfaces."""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.connections = {}
    
    @abstractmethod
    def on_data_received(self, data: int, width: int, connection_id: str):
        """Handle data received from connected device."""
        pass
    
    @abstractmethod
    def generate_data(self) -> tuple:
        """Generate data to send to connected device. Returns (data, width)."""
        pass


class IOInterface:
    """Interface for devices that support external peripheral connections."""
    
    def __init__(self):
        self.io_enabled = False
        self.connections = {}  # connection_id -> IOConnection
        self.input_threads = {}
        self.output_threads = {}
        self.io_lock = threading.RLock()
        
    def enable_io(self) -> None:
        """Enable IO for this device."""
        with self.io_lock:
            self.io_enabled = True
    
    def disable_io(self) -> None:
        """Disable IO for this device."""
        with self.io_lock:
            self.io_enabled = False
            # Stop all connection threads
            for conn in self.connections.values():
                conn.stop_thread()
    
    def is_io_ready(self) -> bool:
        """Check if device is ready for IO operations."""
        return self.io_enabled
    
    def create_connection(self, connection_id: str, direction: IODirection) -> bool:
        """Create a new IO connection."""
        with self.io_lock:
            if connection_id in self.connections:
                return False
            
            self.connections[connection_id] = IOConnection(connection_id, direction)
            return True
    
    def connect_external_device(self, connection_id: str, external_device: Optional[ExternalDevice] = None) -> bool:
        """Connect an external device to this IO interface."""
        with self.io_lock:
            if connection_id not in self.connections:
                return False
            
            conn = self.connections[connection_id]
            if conn.connected:
                return False
            
            conn.connected = True
            
            # Start appropriate threads based on direction
            if conn.direction == IODirection.INPUT:
                # Device expects input from external device
                # Start thread to receive data from external device
                conn.start_thread(self._input_thread_worker, connection_id, external_device)
            elif conn.direction == IODirection.OUTPUT:
                # Device outputs data to external device
                # Start thread to send data to external device
                conn.start_thread(self._output_thread_worker, connection_id, external_device)
            elif conn.direction == IODirection.BIDIRECTIONAL:
                # Start both input and output threads
                conn.start_thread(self._input_thread_worker, connection_id, external_device)
                # Note: For bidirectional, we might need separate threads
            
            return True
    
    def disconnect_external_device(self, connection_id: str) -> bool:
        """Disconnect an external device from this IO interface."""
        with self.io_lock:
            if connection_id not in self.connections:
                return False
            
            conn = self.connections[connection_id]
            conn.connected = False
            conn.stop_thread()
            return True
    
    def output_data(self, connection_id: str, data: int, width: int) -> bool:
        """Output data to a connected external device."""
        with self.io_lock:
            if not self.io_enabled:
                return False
            
            if connection_id not in self.connections:
                return False
            
            conn = self.connections[connection_id]
            if not conn.connected:
                return False
            
            if conn.direction not in [IODirection.OUTPUT, IODirection.BIDIRECTIONAL]:
                return False
            
            # Put data in the connection queue for the output thread to process
            conn.put_data(data, width)
            return True
    
    def input_data(self, connection_id: str, timeout: float = 0.1) -> Optional[tuple]:
        """Get input data from a connected external device."""
        with self.io_lock:
            if not self.io_enabled:
                return None
            
            if connection_id not in self.connections:
                return None
            
            conn = self.connections[connection_id]
            if not conn.connected:
                return None
            
            if conn.direction not in [IODirection.INPUT, IODirection.BIDIRECTIONAL]:
                return None
            
            # Get data from the connection queue
            return conn.get_data(timeout)
    
    def _input_thread_worker(self, connection_id: str, external_device: Optional[ExternalDevice]):
        """Thread worker for handling input from external devices."""
        conn = self.connections[connection_id]
        
        while not conn.stop_event.is_set() and conn.connected:
            try:
                if external_device:
                    # Get data from external device
                    data, width = external_device.generate_data()
                    if data is not None:
                        conn.put_data(data, width)
                        # Call device-specific input handler if available
                        if hasattr(self, '_handle_input_data'):
                            self._handle_input_data(connection_id, data, width)
                
                time.sleep(0.001)  # Small delay to prevent busy waiting
            except Exception:
                break
    
    def _output_thread_worker(self, connection_id: str, external_device: Optional[ExternalDevice]):
        """Thread worker for handling output to external devices."""
        conn = self.connections[connection_id]
        
        while not conn.stop_event.is_set() and conn.connected:
            try:
                # Get data from our output queue
                data_tuple = conn.get_data(timeout=0.1)
                if data_tuple and external_device:
                    data, width = data_tuple
                    external_device.on_data_received(data, width, connection_id)
                
            except Exception:
                break
    
    def get_connection_status(self, connection_id: str) -> Dict[str, Any]:
        """Get status of a specific connection."""
        with self.io_lock:
            if connection_id not in self.connections:
                return {}
            
            conn = self.connections[connection_id]
            return {
                'connection_id': connection_id,
                'direction': conn.direction.value,
                'connected': conn.connected,
                'queue_size': conn.data_queue.qsize(),
                'thread_alive': conn.thread.is_alive() if conn.thread else False
            }
    
    def get_all_connections_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connections."""
        return {conn_id: self.get_connection_status(conn_id) 
                for conn_id in self.connections.keys()}
    
    def cleanup_io(self):
        """Clean up all IO connections and threads."""
        with self.io_lock:
            for conn in self.connections.values():
                conn.stop_thread()
            self.connections.clear()
            self.io_enabled = False