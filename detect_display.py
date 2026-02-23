#!/usr/bin/env python3
"""
Display Detection Tool for Atlas
Automatically detects your display model and protocol
"""
import sys
import time
import serial
import serial.tools.list_ports
from typing import Optional, Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class DisplayDetector:
    """Detects display hardware and protocol"""
    
    # Known device identifiers
    KNOWN_DEVICES = {
        'USB35INCHIPSV2': ('Turing Atlas 3.5"', 'Revision A', 320, 480),
        'USB35INCHIPS': ('Turing Atlas 3.5"', 'Revision A', 320, 480),
        '2017-2-25': ('XuanFang 3.5"', 'Revision B', 320, 480),
    }
    
    # Common VID/PID combinations
    COMMON_VID_PID = [
        (0x1a86, 0x5722, 'CH340 Serial'),  # Common for Turing/XuanFang
        (0x1a86, 0x7523, 'CH340 Serial'),
    ]
    
    def __init__(self):
        self.detected_port = None
        self.detected_model = None
        self.detected_revision = None
        self.detected_resolution = None
    
    def list_ports(self):
        """List all available serial ports"""
        ports = serial.tools.list_ports.comports()
        
        print("\n📱 Available Serial Ports:")
        print("=" * 70)
        
        if not ports:
            print("   No serial ports found!")
            return []
        
        for i, port in enumerate(ports, 1):
            print(f"\n{i}. {port.device}")
            print(f"   Description: {port.description}")
            if port.manufacturer:
                print(f"   Manufacturer: {port.manufacturer}")
            if port.serial_number:
                print(f"   Serial Number: {port.serial_number}")
            if port.vid and port.pid:
                print(f"   VID:PID: {port.vid:04X}:{port.pid:04X}")
        
        print()
        return ports
    
    def detect_by_serial_number(self, ports) -> Optional[Tuple[str, str, str, int, int]]:
        """Detect display by serial number"""
        for port in ports:
            if port.serial_number in self.KNOWN_DEVICES:
                model, revision, width, height = self.KNOWN_DEVICES[port.serial_number]
                return port.device, model, revision, width, height
        return None
    
    def detect_by_vid_pid(self, ports) -> Optional[str]:
        """Detect potential display ports by VID/PID"""
        candidates = []
        for port in ports:
            for vid, pid, desc in self.COMMON_VID_PID:
                if port.vid == vid and port.pid == pid:
                    candidates.append(port.device)
        return candidates
    
    def test_revision_a(self, port_name: str) -> bool:
        """Test if display uses Revision A protocol"""
        try:
            ser = serial.Serial(port_name, 115200, timeout=1, rtscts=True)
            time.sleep(0.1)
            
            # Send HELLO command (Revision A)
            hello = bytearray([111] * 6)
            ser.write(hello)
            time.sleep(0.2)
            
            response = ser.read(6)
            ser.close()
            
            if len(response) == 6:
                logger.info(f"   Revision A protocol detected!")
                logger.info(f"      Response: {response.hex()}")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"   Revision A test failed: {e}")
            return False
    
    def test_revision_b(self, port_name: str) -> bool:
        """Test if display uses Revision B protocol"""
        try:
            ser = serial.Serial(port_name, 115200, timeout=1, rtscts=True)
            time.sleep(0.1)
            
            # Send HELLO command (Revision B)
            hello = [ord('H'), ord('E'), ord('L'), ord('L'), ord('O')]
            buffer = bytearray(10)
            buffer[0] = 0xC1  # Command.HELLO_B
            for i in range(5):
                buffer[i + 1] = hello[i]
            for i in range(3):
                buffer[6 + i] = 0
            buffer[9] = 0xC1
            
            ser.write(buffer)
            time.sleep(0.2)
            
            response = ser.read(10)
            ser.close()
            
            if len(response) == 10 and response[0] == 0xC1 and response[-1] == 0xC1:
                logger.info(f"   Revision B protocol detected!")
                if len(response) > 7:
                    sub_rev = f"A{response[7]:02X}"
                    logger.info(f"      Sub-revision: {sub_rev}")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"   Revision B test failed: {e}")
            return False
    
    def test_revision_c(self, port_name: str) -> bool:
        """Test if display uses Revision C protocol"""
        try:
            ser = serial.Serial(port_name, 115200, timeout=1, rtscts=True)
            time.sleep(0.1)
            
            # Send init sequence (Revision C)
            init_seq = bytearray([0xC8, 0xEF, 0x69, 0x00, 0x17, 0x70])
            ser.write(init_seq)
            time.sleep(0.2)
            
            response = ser.read(10)
            ser.close()
            
            if len(response) > 0:
                logger.info(f"   Revision C protocol detected!")
                logger.info(f"      Response: {response.hex()}")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"   Revision C test failed: {e}")
            return False
    
    def detect_protocol(self, port_name: str) -> Optional[str]:
        """Detect which protocol the display uses"""
        print(f"\nTesting protocols on {port_name}...")
        
        # Test Revision A
        if self.test_revision_a(port_name):
            return "Revision A"
        
        # Test Revision B
        if self.test_revision_b(port_name):
            return "Revision B"
        
        # Test Revision C
        if self.test_revision_c(port_name):
            return "Revision C"
        
        logger.warning("   No known protocol detected")
        return None
    
    def auto_detect(self) -> bool:
        """Automatically detect display"""
        print("\n🖥️  Atlas - Display Detection Tool")
        print("=" * 70)
        
        # List all ports
        ports = self.list_ports()
        
        if not ports:
            print("No serial ports found. Please check your display connection.")
            return False
        
        # Try to detect by serial number first
        result = self.detect_by_serial_number(ports)
        if result:
            port, model, revision, width, height = result
            print(f"\nDisplay Detected!")
            print(f"   Port: {port}")
            print(f"   Model: {model}")
            print(f"   Revision: {revision}")
            print(f"   Resolution: {width}x{height}")
            
            self.detected_port = port
            self.detected_model = model
            self.detected_revision = revision
            self.detected_resolution = (width, height)
            return True
        
        # Try to detect by VID/PID
        candidates = self.detect_by_vid_pid(ports)
        
        if candidates:
            print(f"\nFound {len(candidates)} potential display port(s)")
            
            for port_name in candidates:
                revision = self.detect_protocol(port_name)
                if revision:
                    print(f"\nDisplay Detected!")
                    print(f"   Port: {port_name}")
                    print(f"   Protocol: {revision}")
                    
                    # Guess resolution based on revision
                    if revision == "Revision A":
                        width, height = 320, 480
                        model = "Turing Atlas 3.5\" or UsbMonitor"
                    elif revision == "Revision B":
                        width, height = 320, 480
                        model = "XuanFang 3.5\""
                    else:  # Revision C
                        width, height = 480, 800
                        model = "Turing Atlas 5\" or larger"
                    
                    print(f"   Likely Model: {model}")
                    print(f"   Resolution: {width}x{height}")
                    
                    self.detected_port = port_name
                    self.detected_model = model
                    self.detected_revision = revision
                    self.detected_resolution = (width, height)
                    return True
        
        # Manual selection
        print("\n Could not auto-detect display.")
        print("\nWould you like to manually test a port? (y/n): ", end='')
        
        try:
            choice = input().strip().lower()
            if choice == 'y':
                print("\nEnter port number to test: ", end='')
                port_num = int(input().strip())
                if 1 <= port_num <= len(ports):
                    port_name = ports[port_num - 1].device
                    revision = self.detect_protocol(port_name)
                    if revision:
                        self.detected_port = port_name
                        self.detected_revision = revision
                        return True
        except (ValueError, KeyboardInterrupt):
            pass
        
        return False
    
    def save_config(self):
        """Save detected configuration"""
        if not self.detected_port:
            return
        
        config = {
            "port": self.detected_port,
            "model": self.detected_model or "Unknown",
            "revision": self.detected_revision or "Unknown",
            "resolution": self.detected_resolution or (320, 480)
        }
        
        print("\nDetected Configuration:")
        print(f"   Port: {config['port']}")
        print(f"   Model: {config['model']}")
        print(f"   Revision: {config['revision']}")
        print(f"   Resolution: {config['resolution'][0]}x{config['resolution'][1]}")
        
        return config


def main():
    """Main entry point"""
    detector = DisplayDetector()
    
    if detector.auto_detect():
        config = detector.save_config()
        
        print("\n" + "=" * 70)
        print("Detection Complete!")
        print("\nTo use this display with Atlas:")
        print(f"\n   python3 launch.py {config['port']}")
        print("\nOr update your config file with:")
        print(f"   Port: {config['port']}")
        print(f"   Revision: {config['revision']}")
        print("=" * 70)
        
        return 0
    else:
        print("\n" + "=" * 70)
        print("Could not detect display")
        print("\nTroubleshooting:")
        print("1. Check USB connection")
        print("2. Try a different USB port")
        print("3. Check if display is powered on")
        print("4. Try running with sudo (may need permissions)")
        print("\nYou can still use simulated mode:")
        print("   python3 -m atlas.app --simulated")
        print("=" * 70)
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
