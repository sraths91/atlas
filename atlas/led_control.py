"""
RGB LED Backplate Control for Turing Atlas
Supports displays with RGB LED backlighting
"""
import logging
import time
from typing import Tuple, List, Optional
from enum import IntEnum
import serial

logger = logging.getLogger(__name__)


class LEDMode(IntEnum):
    """LED display modes"""
    OFF = 0
    STATIC = 1
    BREATHING = 2
    RAINBOW = 3
    WAVE = 4
    CUSTOM = 5


class LEDController:
    """Controller for RGB LED backplate"""
    
    def __init__(self, serial_conn: Optional[serial.Serial] = None):
        """
        Initialize LED controller
        
        Args:
            serial_conn: Serial connection to display
        """
        self.serial_conn = serial_conn
        self.supported = self._check_support()
        self.current_mode = LEDMode.OFF
        self.current_color = (0, 0, 0)
        
    def _check_support(self) -> bool:
        """Check if connected display supports RGB LEDs"""
        if not self.serial_conn:
            return False
        
        try:
            # Try to query LED status
            # This is a simplified check - actual implementation would
            # query the display for LED capabilities
            return True
        except Exception as e:
            logger.debug(f"LED support check failed: {e}")
            return False
    
    def set_color(self, r: int, g: int, b: int, mode: LEDMode = LEDMode.STATIC):
        """
        Set LED color
        
        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            mode: LED mode
        """
        if not self.supported:
            logger.warning("RGB LEDs not supported on this display")
            return
        
        if not self.serial_conn:
            logger.error("No serial connection")
            return
        
        # Clamp values
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        try:
            # Command format for RGB LED control
            # Based on Turing Atlas protocol
            cmd = bytearray([
                0xC8,  # Command prefix
                0xEF,  # LED command
                0x80,  # Set color command
                r,     # Red
                g,     # Green
                b,     # Blue
                mode,  # Mode
                0x00   # Padding
            ])
            
            self.serial_conn.write(cmd)
            time.sleep(0.01)
            
            self.current_color = (r, g, b)
            self.current_mode = mode
            
            logger.info(f"LED color set to RGB({r}, {g}, {b}), mode: {mode.name}")
            
        except Exception as e:
            logger.error(f"Failed to set LED color: {e}")
    
    def set_brightness(self, brightness: int):
        """
        Set LED brightness
        
        Args:
            brightness: Brightness level (0-100)
        """
        if not self.supported or not self.serial_conn:
            return
        
        brightness = max(0, min(100, brightness))
        brightness_byte = int((brightness / 100) * 255)
        
        try:
            cmd = bytearray([
                0xC8,
                0xEF,
                0x81,  # Brightness command
                brightness_byte,
                0x00,
                0x00,
                0x00,
                0x00
            ])
            
            self.serial_conn.write(cmd)
            time.sleep(0.01)
            
            logger.info(f"LED brightness set to {brightness}%")
            
        except Exception as e:
            logger.error(f"Failed to set LED brightness: {e}")
    
    def set_mode(self, mode: LEDMode, speed: int = 50):
        """
        Set LED animation mode
        
        Args:
            mode: LED mode
            speed: Animation speed (0-100)
        """
        if not self.supported or not self.serial_conn:
            return
        
        speed = max(0, min(100, speed))
        speed_byte = int((speed / 100) * 255)
        
        try:
            cmd = bytearray([
                0xC8,
                0xEF,
                0x82,  # Mode command
                mode,
                speed_byte,
                0x00,
                0x00,
                0x00
            ])
            
            self.serial_conn.write(cmd)
            time.sleep(0.01)
            
            self.current_mode = mode
            logger.info(f"LED mode set to {mode.name}, speed: {speed}%")
            
        except Exception as e:
            logger.error(f"Failed to set LED mode: {e}")
    
    def turn_off(self):
        """Turn off RGB LEDs"""
        self.set_color(0, 0, 0, LEDMode.OFF)
    
    def set_rainbow(self, speed: int = 50):
        """Set rainbow animation"""
        self.set_mode(LEDMode.RAINBOW, speed)
    
    def set_breathing(self, r: int, g: int, b: int, speed: int = 50):
        """
        Set breathing animation with color
        
        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            speed: Breathing speed (0-100)
        """
        self.set_color(r, g, b, LEDMode.BREATHING)
        self.set_mode(LEDMode.BREATHING, speed)
    
    def set_wave(self, speed: int = 50):
        """Set wave animation"""
        self.set_mode(LEDMode.WAVE, speed)
    
    def set_preset(self, preset_name: str):
        """
        Set a preset LED configuration
        
        Args:
            preset_name: Name of preset (e.g., 'red', 'blue', 'purple', 'rainbow')
        """
        presets = {
            'red': (255, 0, 0, LEDMode.STATIC),
            'green': (0, 255, 0, LEDMode.STATIC),
            'blue': (0, 0, 255, LEDMode.STATIC),
            'cyan': (0, 255, 255, LEDMode.STATIC),
            'magenta': (255, 0, 255, LEDMode.STATIC),
            'yellow': (255, 255, 0, LEDMode.STATIC),
            'white': (255, 255, 255, LEDMode.STATIC),
            'purple': (128, 0, 128, LEDMode.STATIC),
            'orange': (255, 165, 0, LEDMode.STATIC),
            'pink': (255, 192, 203, LEDMode.STATIC),
            'rainbow': (0, 0, 0, LEDMode.RAINBOW),
            'off': (0, 0, 0, LEDMode.OFF),
        }
        
        preset = presets.get(preset_name.lower())
        if preset:
            r, g, b, mode = preset
            if mode == LEDMode.RAINBOW:
                self.set_rainbow()
            else:
                self.set_color(r, g, b, mode)
        else:
            logger.warning(f"Unknown preset: {preset_name}")
    
    def sync_with_theme(self, theme_colors: dict):
        """
        Sync LED color with current theme
        
        Args:
            theme_colors: Dictionary of theme colors
        """
        if not self.supported:
            return
        
        # Extract primary color from theme
        primary = theme_colors.get('primary', (0, 120, 255))
        
        # Convert hex to RGB if needed
        if isinstance(primary, str):
            primary = self._hex_to_rgb(primary)
        
        self.set_color(*primary, LEDMode.STATIC)
    
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_status(self) -> dict:
        """Get current LED status"""
        return {
            'supported': self.supported,
            'mode': self.current_mode.name if self.supported else 'N/A',
            'color': self.current_color if self.supported else (0, 0, 0)
        }


class LEDPresetManager:
    """Manager for LED presets and animations"""
    
    def __init__(self, led_controller: LEDController):
        self.controller = led_controller
        self.presets = self._load_default_presets()
    
    def _load_default_presets(self) -> dict:
        """Load default LED presets"""
        return {
            'gaming': {
                'colors': [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
                'mode': LEDMode.WAVE,
                'speed': 70
            },
            'work': {
                'colors': [(255, 255, 255)],
                'mode': LEDMode.STATIC,
                'speed': 0
            },
            'night': {
                'colors': [(50, 50, 100)],
                'mode': LEDMode.BREATHING,
                'speed': 30
            },
            'party': {
                'colors': [],
                'mode': LEDMode.RAINBOW,
                'speed': 80
            },
            'focus': {
                'colors': [(0, 120, 255)],
                'mode': LEDMode.STATIC,
                'speed': 0
            }
        }
    
    def apply_preset(self, preset_name: str):
        """Apply a preset configuration"""
        preset = self.presets.get(preset_name)
        if not preset:
            logger.warning(f"Unknown preset: {preset_name}")
            return
        
        mode = preset['mode']
        speed = preset['speed']
        
        if mode == LEDMode.RAINBOW:
            self.controller.set_rainbow(speed)
        elif preset['colors']:
            color = preset['colors'][0]
            self.controller.set_color(*color, mode)
            if mode != LEDMode.STATIC:
                self.controller.set_mode(mode, speed)
    
    def create_custom_preset(self, name: str, colors: List[Tuple[int, int, int]], 
                           mode: LEDMode, speed: int = 50):
        """Create a custom preset"""
        self.presets[name] = {
            'colors': colors,
            'mode': mode,
            'speed': speed
        }
        logger.info(f"Created custom preset: {name}")
    
    def list_presets(self) -> List[str]:
        """List all available presets"""
        return list(self.presets.keys())


# Example usage
if __name__ == "__main__":
    # This would normally be connected to actual hardware
    print("LED Control Module")
    print("Available presets:", LEDPresetManager(LEDController()).list_presets())
