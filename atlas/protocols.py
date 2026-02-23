"""
Display protocol implementations for different hardware revisions
Based on the original turing-smart-screen-python project
"""
import time
import logging
from enum import IntEnum
from typing import Optional, Tuple
from PIL import Image
import serial

logger = logging.getLogger(__name__)


class Command(IntEnum):
    """Command codes for display communication"""
    # Revision A commands
    RESET = 101
    CLEAR = 102
    SCREEN_OFF = 108
    SCREEN_ON = 109
    SET_BRIGHTNESS = 110
    SET_ORIENTATION = 121
    DISPLAY_BITMAP = 197
    HELLO = 111
    
    # Revision B/C commands (different protocol)
    HELLO_B = 0xC1


class Orientation(IntEnum):
    """Display orientation modes"""
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3


class HardwareRevision(IntEnum):
    """Hardware revision types"""
    REVISION_A = 1  # Turing 3.5", UsbMonitor
    REVISION_B = 2  # XuanFang rev B & flagship
    REVISION_C = 3  # Turing 5", 8.8", 2.1"


class DisplayProtocol:
    """Base class for display protocols"""
    
    def __init__(self, serial_conn: serial.Serial, width: int = 320, height: int = 480):
        self.serial_conn = serial_conn
        self.width = width
        self.height = height
        self.orientation = Orientation.PORTRAIT
        
    def initialize(self) -> bool:
        """Initialize communication with display"""
        raise NotImplementedError
    
    def clear(self):
        """Clear the display"""
        raise NotImplementedError
    
    def set_brightness(self, level: int):
        """Set display brightness (0-100)"""
        raise NotImplementedError
    
    def set_orientation(self, orientation: Orientation):
        """Set display orientation"""
        raise NotImplementedError
    
    def display_image(self, image: Image.Image, x: int = 0, y: int = 0):
        """Display an image"""
        raise NotImplementedError


class RevisionAProtocol(DisplayProtocol):
    """Protocol for Turing Atlas 3.5" (Revision A) and UsbMonitor"""
    
    def __init__(self, serial_conn: serial.Serial, width: int = 320, height: int = 480):
        super().__init__(serial_conn, width, height)
        logger.info("Using Revision A protocol")
    
    def initialize(self) -> bool:
        """Send HELLO command and detect sub-revision"""
        try:
            hello = bytearray([Command.HELLO] * 6)
            self.serial_conn.write(hello)
            time.sleep(0.1)
            
            response = self.serial_conn.read(6)
            self.serial_conn.reset_input_buffer()
            
            if len(response) == 6:
                logger.info(f"Revision A initialized, response: {response.hex()}")
                return True
            else:
                logger.warning(f"Unexpected response length: {len(response)}")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize Revision A: {e}")
            return False
    
    def _send_command(self, cmd: Command, x: int, y: int, ex: int, ey: int):
        """Send a command with coordinates"""
        buffer = bytearray(6)
        buffer[0] = (x >> 2)
        buffer[1] = (((x & 3) << 6) + (y >> 4))
        buffer[2] = (((y & 15) << 4) + (ex >> 6))
        buffer[3] = (((ex & 63) << 2) + (ey >> 8))
        buffer[4] = (ey & 255)
        buffer[5] = cmd
        
        self.serial_conn.write(buffer)
    
    def clear(self):
        """Clear the display"""
        # Bug workaround: orientation needs to be PORTRAIT before clearing
        backup_orientation = self.orientation
        self.set_orientation(Orientation.PORTRAIT)
        self._send_command(Command.CLEAR, 0, 0, 0, 0)
        time.sleep(0.1)
        self.set_orientation(backup_orientation)
    
    def set_brightness(self, level: int):
        """Set brightness (0-100)"""
        level = max(0, min(100, level))
        # Display scales from 0 (brightest) to 255 (darkest)
        level_absolute = int(255 - ((level / 100) * 255))
        self._send_command(Command.SET_BRIGHTNESS, level_absolute, 0, 0, 0)
    
    def set_orientation(self, orientation: Orientation):
        """Set display orientation"""
        self.orientation = orientation
        width = self.width if orientation in [Orientation.PORTRAIT, Orientation.REVERSE_PORTRAIT] else self.height
        height = self.height if orientation in [Orientation.PORTRAIT, Orientation.REVERSE_PORTRAIT] else self.width
        
        buffer = bytearray(16)
        buffer[0] = 0
        buffer[1] = 0
        buffer[2] = 0
        buffer[3] = 0
        buffer[4] = 0
        buffer[5] = Command.SET_ORIENTATION
        buffer[6] = (width >> 8)
        buffer[7] = (width & 0xFF)
        buffer[8] = (height >> 8)
        buffer[9] = (height & 0xFF)
        buffer[10] = orientation
        buffer[11] = 0
        buffer[12] = 0
        buffer[13] = 0
        buffer[14] = 0
        buffer[15] = 0
        
        self.serial_conn.write(buffer)
    
    def display_image(self, image: Image.Image, x: int = 0, y: int = 0):
        """Display an image at coordinates"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        
        # Send display bitmap command
        self._send_command(Command.DISPLAY_BITMAP, x, y, x + width - 1, y + height - 1)
        
        # Convert to RGB565 and send
        pixels = image.load()
        for py in range(height):
            for px in range(width):
                r, g, b = pixels[px, py]
                # Convert to RGB565
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                rgb565 = (r5 << 11) | (g6 << 5) | b5
                
                # Send as big-endian
                self.serial_conn.write(rgb565.to_bytes(2, byteorder='big'))


class RevisionBProtocol(DisplayProtocol):
    """Protocol for XuanFang 3.5" (Revision B & Flagship)"""
    
    def __init__(self, serial_conn: serial.Serial, width: int = 320, height: int = 480):
        super().__init__(serial_conn, width, height)
        self.sub_revision = None
        logger.info("Using Revision B protocol")
    
    def initialize(self) -> bool:
        """Send HELLO command and detect sub-revision"""
        try:
            hello = [ord('H'), ord('E'), ord('L'), ord('L'), ord('O')]
            self._send_command(Command.HELLO_B, hello, bypass_timeout=True)
            
            response = self.serial_conn.read(10)
            self.serial_conn.reset_input_buffer()
            
            if len(response) == 10:
                if response[0] == Command.HELLO_B and response[-1] == Command.HELLO_B:
                    # Check sub-revision
                    if response[6] == 0xA:
                        self.sub_revision = f"A{response[7]:02X}"
                        logger.info(f"Revision B initialized, sub-revision: {self.sub_revision}")
                        return True
                else:
                    logger.warning("Bad framing in HELLO response")
            else:
                logger.warning(f"Unexpected response length: {len(response)}")
            
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Revision B: {e}")
            return False
    
    def _send_command(self, cmd: int, payload=None, bypass_timeout: bool = False):
        """Send a 10-byte framed command"""
        if payload is None:
            payload = [0] * 8
        elif len(payload) < 8:
            payload = list(payload) + [0] * (8 - len(payload))
        
        buffer = bytearray(10)
        buffer[0] = cmd
        for i in range(8):
            buffer[i + 1] = payload[i]
        buffer[9] = cmd
        
        self.serial_conn.write(buffer)
        if not bypass_timeout:
            time.sleep(0.01)
    
    def clear(self):
        """Clear display by showing blank image"""
        blank = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        self.display_image(blank)
    
    def set_brightness(self, level: int):
        """Set brightness (0-100)"""
        level = max(0, min(100, level))
        # Revision B uses 0-255 range
        level_absolute = int((level / 100) * 255)
        self._send_command(0xC2, [level_absolute])
    
    def set_orientation(self, orientation: Orientation):
        """Set display orientation"""
        self.orientation = orientation
        self._send_command(0xC3, [orientation])
    
    def display_image(self, image: Image.Image, x: int = 0, y: int = 0):
        """Display an image"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        
        # Send bitmap start command
        payload = [
            (x >> 8) & 0xFF, x & 0xFF,
            (y >> 8) & 0xFF, y & 0xFF,
            (width >> 8) & 0xFF, width & 0xFF,
            (height >> 8) & 0xFF, height & 0xFF
        ]
        self._send_command(0xC5, payload)
        
        # Send pixel data
        pixels = image.load()
        for py in range(height):
            for px in range(width):
                r, g, b = pixels[px, py]
                # Convert to RGB565
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                rgb565 = (r5 << 11) | (g6 << 5) | b5
                
                self.serial_conn.write(rgb565.to_bytes(2, byteorder='big'))


class RevisionCProtocol(DisplayProtocol):
    """Protocol for Turing 5", 8.8", and 2.1" displays"""
    
    def __init__(self, serial_conn: serial.Serial, width: int = 480, height: int = 800):
        super().__init__(serial_conn, width, height)
        logger.info("Using Revision C protocol")
    
    def initialize(self) -> bool:
        """Initialize Revision C display"""
        try:
            # Revision C uses a different initialization sequence
            init_sequence = bytearray([0xC8, 0xEF, 0x69, 0x00, 0x17, 0x70])
            self.serial_conn.write(init_sequence)
            time.sleep(0.2)
            
            response = self.serial_conn.read(6)
            self.serial_conn.reset_input_buffer()
            
            if len(response) > 0:
                logger.info(f"Revision C initialized, response: {response.hex()}")
                return True
            else:
                logger.warning("No response from Revision C display")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize Revision C: {e}")
            return False
    
    def clear(self):
        """Clear the display"""
        blank = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        self.display_image(blank)
    
    def set_brightness(self, level: int):
        """Set brightness (0-100)"""
        level = max(0, min(100, level))
        level_absolute = int((level / 100) * 255)
        
        cmd = bytearray([0xC8, 0xEF, 0x6A, level_absolute, 0x00, 0x00])
        self.serial_conn.write(cmd)
    
    def set_orientation(self, orientation: Orientation):
        """Set display orientation"""
        self.orientation = orientation
        cmd = bytearray([0xC8, 0xEF, 0x6B, orientation, 0x00, 0x00])
        self.serial_conn.write(cmd)
    
    def display_image(self, image: Image.Image, x: int = 0, y: int = 0):
        """Display an image"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        
        # Send bitmap command
        cmd = bytearray([
            0xC8, 0xEF, 0x6C,
            (x >> 8) & 0xFF, x & 0xFF,
            (y >> 8) & 0xFF, y & 0xFF,
            (width >> 8) & 0xFF, width & 0xFF,
            (height >> 8) & 0xFF, height & 0xFF
        ])
        self.serial_conn.write(cmd)
        
        # Send pixel data
        pixels = image.load()
        for py in range(height):
            for px in range(width):
                r, g, b = pixels[px, py]
                # Convert to RGB565
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                rgb565 = (r5 << 11) | (g6 << 5) | b5
                
                self.serial_conn.write(rgb565.to_bytes(2, byteorder='big'))
