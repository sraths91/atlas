"""
Widget Log Collector - Collects and sends widget logs to fleet server
"""
import json
import time
import threading
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

# Import encryption module
try:
    from .encryption import DataEncryption
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    DataEncryption = None

logger = logging.getLogger(__name__)


class WidgetLogCollector:
    """Collects widget logs and sends them to fleet server periodically"""
    
    def __init__(self, machine_id: str, server_url: str, api_key: str = None, interval: int = 300,
                 encryption_key: Optional[str] = None):
        """
        Initialize log collector
        
        Args:
            machine_id: Machine identifier
            server_url: Fleet server URL
            api_key: Optional API key for authentication
            interval: Send interval in seconds (default: 300 = 5 minutes)
            encryption_key: Optional encryption key for end-to-end encryption (base64)
        """
        self.machine_id = machine_id
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.interval = interval
        self.logs = []
        self.max_logs = 1000  # Keep max 1000 logs in memory
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        
        # Initialize end-to-end encryption
        if encryption_key and ENCRYPTION_AVAILABLE and DataEncryption:
            self.encryption = DataEncryption(encryption_key)
            logger.info("Widget log encryption enabled (AES-256-GCM)")
        else:
            self.encryption = None
            if encryption_key:
                logger.warning("Encryption key provided but encryption module not available")
    
    def log(self, level: str, widget_type: str, message: str, data: Dict[str, Any] = None):
        """
        Add a log entry
        
        Args:
            level: Log level (INFO, WARNING, ERROR)
            widget_type: Widget that generated the log
            message: Log message
            data: Additional data (optional)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'widget_type': widget_type,
            'message': message,
            'data': data or {}
        }
        
        with self.lock:
            self.logs.append(log_entry)
            
            # Keep only recent logs in memory
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
        
        # Also log to console
        logger.info(f"[{widget_type}] {level}: {message}")
    
    def send_logs(self) -> bool:
        """
        Send collected logs to fleet server
        
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            if not self.logs:
                logger.debug("No logs to send")
                return True
            
            logs_to_send = self.logs.copy()
            self.logs = []  # Clear logs after copying
        
        try:
            url = f"{self.server_url}/api/fleet/widget-logs"
            headers = {'Content-Type': 'application/json'}
            
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            payload = {
                'machine_id': self.machine_id,
                'logs': logs_to_send
            }
            
            # Encrypt payload if encryption is enabled
            if self.encryption:
                payload = self.encryption.encrypt_payload(payload)
                logger.debug("Widget logs encrypted before transmission")
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Sent {result.get('logs_stored', len(logs_to_send))} widget logs to fleet server")
                return True
            else:
                logger.error(f"Failed to send widget logs: {response.status_code} - {response.text}")
                # Put logs back if send failed
                with self.lock:
                    self.logs = logs_to_send + self.logs
                return False
                
        except Exception as e:
            logger.error(f"Error sending widget logs: {e}")
            # Put logs back if send failed
            with self.lock:
                self.logs = logs_to_send + self.logs
            return False
    
    def _send_loop(self):
        """Background thread that sends logs periodically"""
        logger.info(f"Widget log collector started (interval: {self.interval}s)")
        
        while self.running:
            try:
                time.sleep(self.interval)
                if self.running:  # Check again after sleep
                    self.send_logs()
            except Exception as e:
                logger.error(f"Error in log send loop: {e}")
    
    def start(self):
        """Start the log collector background thread"""
        if self.running:
            logger.warning("Log collector already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._send_loop, daemon=True)
        self.thread.start()
        logger.info(f"Widget log collector started for machine: {self.machine_id}")
    
    def stop(self):
        """Stop the log collector and send remaining logs"""
        if not self.running:
            return
        
        logger.info("Stopping widget log collector...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        # Send any remaining logs
        self.send_logs()
        logger.info("Widget log collector stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics"""
        with self.lock:
            return {
                'logs_in_memory': len(self.logs),
                'max_logs': self.max_logs,
                'interval': self.interval,
                'running': self.running
            }


# Global log collector instance
_log_collector = None


def init_log_collector(machine_id: str, server_url: str, api_key: str = None, interval: int = 300,
                      encryption_key: Optional[str] = None):
    """Initialize the global log collector"""
    global _log_collector
    _log_collector = WidgetLogCollector(machine_id, server_url, api_key, interval, encryption_key)
    _log_collector.start()
    return _log_collector


def get_log_collector() -> WidgetLogCollector:
    """Get the global log collector instance"""
    return _log_collector


def log_widget_event(level: str, widget_type: str, message: str, data: Dict[str, Any] = None):
    """Convenience function to log widget events"""
    if _log_collector:
        _log_collector.log(level, widget_type, message, data)
    else:
        logger.warning(f"Log collector not initialized: [{widget_type}] {level}: {message}")
