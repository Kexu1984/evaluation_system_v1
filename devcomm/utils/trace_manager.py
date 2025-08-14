"""
Trace manager implementation for the DevCommV3 framework.

This module provides a common trace manager that can be shared across
top/bus/device components with module-based control and file persistence.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json

from .event_constants import EventType, BusOperation, DeviceOperation


@dataclass
class TraceEvent:
    """Base trace event with common fields."""
    timestamp: float
    formatted_time: str
    module_name: str
    event_type: str
    event_data: Dict[str, Any]


@dataclass
class BusTransaction(TraceEvent):
    """Bus transaction trace event."""
    def __init__(self, timestamp: float, module_name: str, master_id: int, 
                 address: int, operation: str, value: int, width: int, 
                 device_name: str, success: bool, error_message: Optional[str] = None):
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        event_data = {
            'master_id': master_id,
            'address': f"0x{address:08X}",
            'operation': operation,
            'value': f"0x{value:08X}",
            'width': width,
            'device_name': device_name,
            'success': success,
            'error_message': error_message
        }
        super().__init__(timestamp, formatted_time, module_name, EventType.BUS_TRANSACTION, event_data)


@dataclass
class IRQEvent(TraceEvent):
    """IRQ event trace."""
    def __init__(self, timestamp: float, module_name: str, master_id: int, 
                 irq_index: int, device_name: str):
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        event_data = {
            'master_id': master_id,
            'irq_index': irq_index,
            'device_name': device_name
        }
        super().__init__(timestamp, formatted_time, module_name, EventType.IRQ_EVENT, event_data)


@dataclass
class DeviceEvent(TraceEvent):
    """Device operation trace event."""
    def __init__(self, timestamp: float, module_name: str, device_name: str,
                 operation: str, details: Dict[str, Any]):
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        event_data = {
            'device_name': device_name,
            'operation': operation,
            **details
        }
        super().__init__(timestamp, formatted_time, module_name, EventType.DEVICE_EVENT, event_data)


class TraceManager:
    """Common trace manager for all DevCommV3 components."""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, name: str = "GlobalTraceManager", max_events: int = 10000):
        """Implement singleton pattern for shared trace buffer."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TraceManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, name: str = "GlobalTraceManager", max_events: int = 10000):
        # Only initialize once
        if self._initialized:
            return
            
        self.name = name
        self.max_events = max_events
        self.lock = threading.RLock()
        
        # Global trace control
        self.global_enabled = True
        
        # Module-based trace control
        self.module_enabled: Dict[str, bool] = {}
        
        # Event storage (shared by all components)
        self.events: List[TraceEvent] = []
        
        # Statistics
        self.stats: Dict[str, Dict[str, int]] = {}
        
        self._initialized = True
        
    def enable_global_trace(self) -> None:
        """Enable tracing globally."""
        with self.lock:
            self.global_enabled = True
            
    def disable_global_trace(self) -> None:
        """Disable tracing globally."""
        with self.lock:
            self.global_enabled = False
            
    def enable_module_trace(self, module_name: str) -> None:
        """Enable tracing for a specific module."""
        with self.lock:
            self.module_enabled[module_name] = True
            
    def disable_module_trace(self, module_name: str) -> None:
        """Disable tracing for a specific module."""
        with self.lock:
            self.module_enabled[module_name] = False
            
    def is_module_trace_enabled(self, module_name: str) -> bool:
        """Check if tracing is enabled for a module."""
        with self.lock:
            if not self.global_enabled:
                return False
            return self.module_enabled.get(module_name, True)  # Default enabled
            
    def log_bus_transaction(self, module_name: str, master_id: int, address: int,
                           operation: str, value: int, width: int, device_name: str,
                           success: bool, error_message: Optional[str] = None) -> None:
        """Log a bus transaction event."""
        if not self.is_module_trace_enabled(module_name):
            return
            
        timestamp = time.time()
        event = BusTransaction(timestamp, module_name, master_id, address, 
                             operation, value, width, device_name, success, error_message)
        self._add_event(event)
        
    def log_irq_event(self, module_name: str, master_id: int, irq_index: int, 
                     device_name: str) -> None:
        """Log an IRQ event."""
        if not self.is_module_trace_enabled(module_name):
            return
            
        timestamp = time.time()
        event = IRQEvent(timestamp, module_name, master_id, irq_index, device_name)
        self._add_event(event)
        
    def log_device_event(self, module_name: str, device_name: str, operation: str,
                        details: Dict[str, Any]) -> None:
        """Log a device operation event."""
        if not self.is_module_trace_enabled(module_name):
            return
            
        timestamp = time.time()
        event = DeviceEvent(timestamp, module_name, device_name, operation, details)
        self._add_event(event)
        
    def _add_event(self, event: TraceEvent) -> None:
        """Add an event to the trace log."""
        with self.lock:
            self.events.append(event)
            
            # Update statistics
            module_name = event.module_name
            event_type = event.event_type
            
            if module_name not in self.stats:
                self.stats[module_name] = {}
            if event_type not in self.stats[module_name]:
                self.stats[module_name][event_type] = 0
            self.stats[module_name][event_type] += 1
            
            # Trim events if too many
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events//2:]
                
    def clear_trace(self, module_name: Optional[str] = None) -> None:
        """Clear trace events. If module_name is specified, clear only that module's events."""
        with self.lock:
            if module_name is None:
                self.events.clear()
                self.stats.clear()
            else:
                # Remove events for specific module
                self.events = [e for e in self.events if e.module_name != module_name]
                if module_name in self.stats:
                    del self.stats[module_name]
                    
    def get_trace_summary(self, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Get trace summary. If module_name is specified, get summary for that module only."""
        with self.lock:
            if module_name is None:
                total_events = len(self.events)
                modules = list(set(e.module_name for e in self.events))
                return {
                    'total_events': total_events,
                    'modules': modules,
                    'module_stats': self.stats,
                    'global_enabled': self.global_enabled,
                    'module_enabled': self.module_enabled.copy()
                }
            else:
                module_events = [e for e in self.events if e.module_name == module_name]
                return {
                    'module_name': module_name,
                    'total_events': len(module_events),
                    'module_stats': self.stats.get(module_name, {}),
                    'enabled': self.is_module_trace_enabled(module_name)
                }
                
    def get_events(self, module_name: Optional[str] = None, event_type: Optional[str] = None,
                  limit: Optional[int] = None) -> List[TraceEvent]:
        """Get trace events with optional filtering."""
        with self.lock:
            events = self.events.copy()
            
            if module_name:
                events = [e for e in events if e.module_name == module_name]
                
            if event_type:
                events = [e for e in events if e.event_type == event_type]
                
            if limit:
                events = events[-limit:]
                
            return events
            
    @classmethod
    def get_global_instance(cls) -> 'TraceManager':
        """Get the global singleton instance of TraceManager."""
        if cls._instance is None:
            cls._instance = TraceManager()
        return cls._instance
    
    @classmethod
    def reset_global_instance(cls) -> None:
        """Reset the global instance (mainly for testing purposes)."""
        with cls._lock:
            cls._instance = None
        
    def save_trace_to_file(self, filename: str, module_name: Optional[str] = None,
                          format: str = 'json') -> None:
        """Save trace events to file. Now saves all events to a single unified file."""
        events = self.get_events(module_name)
        
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'json':
            self._save_as_json(filepath, events, module_name)
        elif format.lower() == 'txt':
            self._save_as_text(filepath, events, module_name)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _save_as_json(self, filepath: Path, events: List[TraceEvent], module_filter: Optional[str] = None) -> None:
        """Save events as JSON."""
        data = {
            'trace_info': {
                'total_events': len(events),
                'total_events_in_buffer': len(self.events),
                'saved_at': datetime.now().isoformat(),
                'trace_manager': self.name,
                'module_filter': module_filter,
                'unified_buffer': True  # Indicate this is from unified buffer
            },
            'events': [asdict(event) for event in events]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def _save_as_text(self, filepath: Path, events: List[TraceEvent], module_filter: Optional[str] = None) -> None:
        """Save events as human-readable text."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"DevCommV3 Unified Trace Log - {self.name}\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if module_filter:
                f.write(f"Module filter: {module_filter}\n")
            f.write(f"Filtered events: {len(events)}\n")
            f.write(f"Total events in buffer: {len(self.events)}\n")
            f.write("=" * 80 + "\n\n")
            
            for event in events:
                f.write(f"[{event.formatted_time}] {event.module_name}.{event.event_type}\n")
                for key, value in event.event_data.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
                
    def get_module_list(self) -> List[str]:
        """Get list of all modules that have generated events."""
        with self.lock:
            return list(set(e.module_name for e in self.events))
            
    def __str__(self) -> str:
        return f"TraceManager({self.name}, {len(self.events)} events)"
        
    def __repr__(self) -> str:
        return (f"TraceManager(name='{self.name}', events={len(self.events)}, "
                f"global_enabled={self.global_enabled})")