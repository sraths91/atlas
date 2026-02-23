"""
Configuration management for Atlas
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration"""

    DEFAULT_CONFIG = {
        "display": {
            "width": 320,
            "height": 480,
            "refresh_rate": 1.0,  # seconds
            "theme": "dark",
            "brightness": 80,  # percentage
        },
        "monitoring": {
            "cpu": True,
            "memory": True,
            "disk": True,
            "network": True,
            "gpu": True,
            "temperatures": True,
        },
        "advanced": {
            "debug": False,
            "log_level": "INFO",
            "update_check": True,
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager"""
        self.config_path = Path(config_path) if config_path else self.get_default_config_path()
        self.config = self.load_config()

    @staticmethod
    def get_default_config_path() -> Path:
        """Get the default configuration file path"""
        config_dir = Path.home() / ".config" / "atlas"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with default config to ensure all keys exist
                return self._merge_configs(self.DEFAULT_CONFIG, config)
            return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot notation"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any, save: bool = True):
        """Set a configuration value by dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        if save:
            self.save_config()
    
    @staticmethod
    def _merge_configs(default: Dict, custom: Dict) -> Dict:
        """Recursively merge two dictionaries"""
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
