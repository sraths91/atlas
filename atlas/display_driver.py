"""
Display driver for Turing Atlas and compatible devices
"""
import serial
import serial.tools.list_ports
import logging
import time
from typing import Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont
import io
from .protocols import (
    DisplayProtocol, RevisionAProtocol, RevisionBProtocol, RevisionCProtocol,
    HardwareRevision, Orientation
)

logger = logging.getLogger(__name__)

class DisplayDriver:
    """Driver for communicating with Turing Atlas devices"""
    
    # Display models and their specifications
    DISPLAY_MODELS = {
        "turing_3.5": {"width": 320, "height": 480, "orientation": 0},
        "turing_5.0": {"width": 480, "height": 800, "orientation": 0},
        "turing_7.0": {"width": 800, "height": 480, "orientation": 1},
        "xuanfang_3.5": {"width": 320, "height": 480, "orientation": 0},
    }
    
    def __init__(self, model: str = "turing_3.5", port: Optional[str] = None, baudrate: int = 115200, revision: Optional[str] = None):
        """
        Initialize the display driver
        
        Args:
            model: Display model name
            port: Serial port (auto-detected if None)
            baudrate: Serial communication baudrate
            revision: Hardware revision ("A", "B", or "C") - auto-detected if None
        """
        self.model = model
        self.specs = self.DISPLAY_MODELS.get(model, self.DISPLAY_MODELS["turing_3.5"])
        self.width = self.specs["width"]
        self.height = self.specs["height"]
        self.orientation = self.specs["orientation"]
        self.baudrate = baudrate
        self.port = port or self._auto_detect_port()
        self.serial_conn: Optional[serial.Serial] = None
        self.protocol: Optional[DisplayProtocol] = None
        self.revision = revision
        self.buffer = Image.new('RGB', (self.width, self.height), color=(0, 0, 0))
        
    def _auto_detect_port(self) -> Optional[str]:
        """Auto-detect the serial port for the display"""
        ports = serial.tools.list_ports.comports()
        
        # Check for known serial numbers first
        known_serials = {
            'USB35INCHIPSV2': 'Turing 3.5"',
            'USB35INCHIPS': 'Turing 3.5"',
            '2017-2-25': 'XuanFang 3.5"'
        }
        
        for port in ports:
            if port.serial_number in known_serials:
                logger.info(f"Auto-detected {known_serials[port.serial_number]} on port: {port.device}")
                return port.device
        
        # Check for common VID/PID
        for port in ports:
            if port.vid == 0x1a86 and port.pid == 0x5722:
                logger.info(f"Auto-detected display on port: {port.device}")
                return port.device
        
        # Fallback to common identifiers
        identifiers = ['usbmodem', 'usbserial', 'CH340']
        for port in ports:
            port_desc = port.description.upper() if port.description else ""
            port_device = port.device.upper()
            
            for identifier in identifiers:
                if identifier.upper() in port_desc or identifier.upper() in port_device:
                    logger.info(f"Auto-detected display on port: {port.device}")
                    return port.device
        
        logger.warning("Could not auto-detect display port")
        return None
    
    def connect(self) -> bool:
        """
        Connect to the display
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.port:
            logger.error("No port specified and auto-detection failed")
            return False
        
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2,
                write_timeout=2,
                rtscts=True  # Hardware flow control - required for these displays
            )
            time.sleep(0.5)  # Give display time to initialize
            logger.info(f"Connected to display on {self.port}")
            self._initialize_display()
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to display: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the display"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from display")
    
    def _detect_protocol(self) -> Optional[DisplayProtocol]:
        """Detect which protocol the display uses"""
        if not self.serial_conn:
            return None
        
        # If revision is specified, use it
        if self.revision:
            if self.revision.upper() == "A":
                return RevisionAProtocol(self.serial_conn, self.width, self.height)
            elif self.revision.upper() == "B":
                return RevisionBProtocol(self.serial_conn, self.width, self.height)
            elif self.revision.upper() == "C":
                return RevisionCProtocol(self.serial_conn, self.width, self.height)
        
        # Try to auto-detect protocol
        logger.info("Auto-detecting display protocol...")
        
        # Try Revision B first (most common)
        protocol = RevisionBProtocol(self.serial_conn, self.width, self.height)
        if protocol.initialize():
            return protocol
        
        # Try Revision A
        protocol = RevisionAProtocol(self.serial_conn, self.width, self.height)
        if protocol.initialize():
            return protocol
        
        # Try Revision C
        protocol = RevisionCProtocol(self.serial_conn, self.width, self.height)
        if protocol.initialize():
            return protocol
        
        logger.error("Could not detect display protocol")
        return None
    
    def _initialize_display(self):
        """Initialize the display with default settings"""
        if not self.serial_conn:
            return
        
        try:
            # Detect and initialize protocol
            self.protocol = self._detect_protocol()
            if not self.protocol:
                raise Exception("Failed to detect display protocol")
            
            # Clear screen
            self.protocol.clear()
            # Set brightness to 80%
            self.protocol.set_brightness(80)
            
            logger.info("Display initialized successfully")
        except Exception as e:
            logger.error(f"Display initialization failed: {e}")
    
    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)):
        """
        Clear the display with a specific color
        
        Args:
            color: RGB color tuple (default: black)
        """
        if self.protocol:
            self.protocol.clear()
        self.buffer = Image.new('RGB', (self.width, self.height), color=color)
    
    def set_brightness(self, brightness: int):
        """
        Set display brightness
        
        Args:
            brightness: Brightness level (0-100)
        """
        if self.protocol:
            self.protocol.set_brightness(brightness)
    
    def set_orientation(self, orientation: int):
        """
        Set display orientation
        
        Args:
            orientation: 0=portrait, 1=landscape, 2=portrait inverted, 3=landscape inverted
        """
        if self.protocol:
            self.protocol.set_orientation(Orientation(orientation))
            self.orientation = orientation
    
    def display_image(self, image: Image.Image, x: int = 0, y: int = 0):
        """
        Display an image on the screen
        
        Args:
            image: PIL Image object
            x: X coordinate
            y: Y coordinate
        """
        # Paste image onto buffer
        self.buffer.paste(image, (x, y))
        self._update_screen()
    
    def draw_text(self, text: str, x: int, y: int, font_size: int = 20, 
                  color: Tuple[int, int, int] = (255, 255, 255)):
        """
        Draw text on the display
        
        Args:
            text: Text to display
            x: X coordinate
            y: Y coordinate
            font_size: Font size
            color: RGB color tuple
        """
        draw = ImageDraw.Draw(self.buffer)
        
        try:
            # Try to use a system font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            # Fall back to default font
            font = ImageFont.load_default()
        
        draw.text((x, y), text, font=font, fill=color)
    
    def draw_rectangle(self, x: int, y: int, width: int, height: int, 
                      color: Tuple[int, int, int], fill: bool = False):
        """
        Draw a rectangle on the display
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Rectangle width
            height: Rectangle height
            color: RGB color tuple
            fill: Whether to fill the rectangle
        """
        draw = ImageDraw.Draw(self.buffer)
        
        if fill:
            draw.rectangle([x, y, x + width, y + height], fill=color)
        else:
            draw.rectangle([x, y, x + width, y + height], outline=color)
    
    def draw_progress_bar(self, x: int, y: int, width: int, height: int, 
                         progress: float, bg_color: Tuple[int, int, int] = (50, 50, 50),
                         fg_color: Tuple[int, int, int] = (0, 255, 0)):
        """
        Draw a progress bar
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Bar width
            height: Bar height
            progress: Progress value (0.0 to 1.0)
            bg_color: Background color
            fg_color: Foreground color
        """
        draw = ImageDraw.Draw(self.buffer)
        
        # Draw background
        draw.rectangle([x, y, x + width, y + height], fill=bg_color)
        
        # Draw progress
        progress = max(0.0, min(1.0, progress))
        progress_width = int(width * progress)
        if progress_width > 0:
            draw.rectangle([x, y, x + progress_width, y + height], fill=fg_color)
    
    def update(self):
        """Update the display with the current buffer"""
        self._update_screen()
    
    def _update_screen(self):
        """Send the current buffer to the display"""
        if not self.protocol:
            return
        
        try:
            self.protocol.display_image(self.buffer, 0, 0)
        except Exception as e:
            logger.error(f"Failed to update screen: {e}")
    
    def _convert_to_rgb565(self, image: Image.Image) -> bytes:
        """
        Convert PIL Image to RGB565 format
        
        Args:
            image: PIL Image object
            
        Returns:
            RGB565 formatted bytes
        """
        # Ensure image is in RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to RGB565
        rgb565_data = bytearray()
        pixels = image.load()
        
        for y in range(image.height):
            for x in range(image.width):
                r, g, b = pixels[x, y]
                
                # Convert 8-bit RGB to 5-6-5 format
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                
                # Combine into 16-bit value
                rgb565 = (r5 << 11) | (g6 << 5) | b5
                
                # Add as big-endian bytes
                rgb565_data.extend(rgb565.to_bytes(2, byteorder='big'))
        
        return bytes(rgb565_data)
    
    def list_available_ports(self) -> List[str]:
        """
        List all available serial ports
        
        Returns:
            List of port names
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class SimulatedDisplay(DisplayDriver):
    """Simulated display for testing without hardware"""
    
    def __init__(self, model: str = "turing_3.5"):
        """Initialize simulated display"""
        super().__init__(model=model, port="SIMULATED")
        self.connected = False
    
    def connect(self) -> bool:
        """Simulate connection"""
        self.connected = True
        logger.info("Connected to simulated display")
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        self.connected = False
        logger.info("Disconnected from simulated display")
    
    def _update_screen(self):
        """Save buffer to file instead of sending to hardware"""
        if self.connected:
            # Save to a preview file
            try:
                preview_path = "/tmp/atlas_preview.png"
                self.buffer.save(preview_path)
                logger.debug(f"Preview saved to {preview_path}")
            except Exception as e:
                logger.error(f"Failed to save preview: {e}")
    
    def save_preview(self, path: str):
        """Save current buffer to a file"""
        self.buffer.save(path)
        logger.info(f"Preview saved to {path}")
