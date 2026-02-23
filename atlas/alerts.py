"""Alert system for monitoring system metrics and triggering notifications."""
import os
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import psutil
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

class AlertType(Enum):
    CPU = "CPU"
    GPU = "GPU"
    MEMORY = "Memory"
    TEMPERATURE = "Temperature"
    BATTERY = "Battery"
    NETWORK = "Network"
    PROCESS_ZOMBIE = "Process_Zombie"
    PROCESS_STUCK = "Process_Stuck"
    PROCESS_HIGH_CPU = "Process_High_CPU"
    PROCESS_HIGH_MEMORY = "Process_High_Memory"
    PROCESS_UNRESPONSIVE = "Process_Unresponsive"

@dataclass
class AlertRule:
    alert_type: AlertType
    threshold: float
    condition: str  # '>', '<', '==', '>=', '<='
    duration: int = 60  # seconds
    cooldown: int = 300  # seconds
    message: str = ""
    last_triggered: float = 0
    active: bool = True
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if the alert should be triggered based on current value."""
        if not self.active:
            return False
            
        now = time.time()
        if now - self.last_triggered < self.cooldown:
            return False
            
        condition_met = {
            '>': current_value > self.threshold,
            '<': current_value < self.threshold,
            '>=': current_value >= self.threshold,
            '<=': current_value <= self.threshold,
            '==': current_value == self.threshold,
        }.get(self.condition, False)
        
        return condition_met

class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default alert rules."""
        default_rules = [
            AlertRule(AlertType.CPU, 90, '>', message="High CPU usage detected: {value}%"),
            AlertRule(AlertType.GPU, 90, '>', message="High GPU usage detected: {value}%"),
            AlertRule(AlertType.MEMORY, 90, '>', message="High memory usage: {value}%"),
            AlertRule(AlertType.TEMPERATURE, 80, '>', message="High temperature: {value}°C"),
            AlertRule(AlertType.BATTERY, 20, '<', message="Low battery: {value}% remaining"),
            AlertRule(AlertType.BATTERY, 10, '<', message="Critical battery: {value}% remaining"),
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule) -> str:
        """Add a new alert rule."""
        rule_id = f"{rule.alert_type.value.lower()}_{len(self.rules)}"
        self.rules[rule_id] = rule
        return rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
    
    def check_metrics(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Check metrics against all rules and return triggered alerts."""
        triggered = []
        now = time.time()
        
        for rule_id, rule in self.rules.items():
            metric_value = metrics.get(rule.alert_type.value.lower())
            if metric_value is None:
                continue
                
            if rule.should_trigger(metric_value):
                rule.last_triggered = now
                alert_data = {
                    'id': rule_id,
                    'type': rule.alert_type.value,
                    'value': metric_value,
                    'threshold': rule.threshold,
                    'timestamp': now,
                    'message': rule.message.format(value=f"{metric_value:.1f}")
                }
                triggered.append(alert_data)
                self.alert_history.append(alert_data)
                
                # Keep only last 100 alerts in history
                if len(self.alert_history) > 100:
                    self.alert_history = self.alert_history[-100:]
                
                # Send notification
                self._send_notification(alert_data)
        
        return triggered
    
    @staticmethod
    def _escape_applescript(text: str) -> str:
        """Escape a string for safe use in AppleScript double-quoted strings"""
        return text.replace('\\', '\\\\').replace('"', '\\"')

    def _send_notification(self, alert: Dict[str, Any]) -> None:
        """Send a system notification."""
        title = self._escape_applescript(f"{alert['type']} Alert")
        message = self._escape_applescript(str(alert['message']))

        try:
            if os.uname().sysname == 'Darwin':  # macOS
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
            else:  # Linux/other
                subprocess.run(['notify-send', title, message], timeout=5)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts from history."""
        return sorted(
            self.alert_history,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    def check_process_issues(self, issues: Dict[str, List]) -> List[Dict[str, Any]]:
        """Check for process-related issues and trigger alerts."""
        triggered = []
        now = time.time()
        
        # Check for zombie processes
        if issues.get('zombie'):
            for proc_info in issues['zombie']:
                alert_data = {
                    'id': f'zombie_{proc_info.pid}',
                    'type': 'Process_Zombie',
                    'value': proc_info.pid,
                    'threshold': 0,
                    'timestamp': now,
                    'message': f"Zombie process detected: {proc_info.name} (PID: {proc_info.pid})"
                }
                triggered.append(alert_data)
                self.alert_history.append(alert_data)
                self._send_notification(alert_data)
        
        # Check for stuck processes
        if issues.get('stuck'):
            for proc_info in issues['stuck']:
                alert_data = {
                    'id': f'stuck_{proc_info.pid}',
                    'type': 'Process_Stuck',
                    'value': proc_info.cpu_percent,
                    'threshold': 95,
                    'timestamp': now,
                    'message': f"Stuck process: {proc_info.name} (PID: {proc_info.pid}, CPU: {proc_info.cpu_percent:.1f}%)"
                }
                triggered.append(alert_data)
                self.alert_history.append(alert_data)
                self._send_notification(alert_data)
        
        # Check for unresponsive processes
        if issues.get('unresponsive'):
            for proc_info in issues['unresponsive']:
                alert_data = {
                    'id': f'unresponsive_{proc_info.pid}',
                    'type': 'Process_Unresponsive',
                    'value': proc_info.pid,
                    'threshold': 0,
                    'timestamp': now,
                    'message': f"Unresponsive process: {proc_info.name} (PID: {proc_info.pid})"
                }
                triggered.append(alert_data)
                self.alert_history.append(alert_data)
                self._send_notification(alert_data)
        
        # Keep only last 100 alerts in history
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        return triggered

# Singleton instance
alert_manager = AlertManager()

def check_system_alerts(metrics: Dict[str, float]) -> List[Dict[str, Any]]:
    """Convenience function to check alerts with default manager."""
    return alert_manager.check_metrics(metrics)
