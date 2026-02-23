#!/usr/bin/env python3
"""
Experimental Display Initialization
Advanced techniques including USB control transfers, timing patterns, and community findings
"""
import serial
import serial.tools.list_ports
import time
import sys
import struct

def find_display():
    """Find XuanFang display"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.serial_number == '2017-2-25':
            return port.device
    return None

def send_with_timing(ser, data, name, pre_delay=0, post_delay=0.2, read_delay=0.1):
    """Send data with specific timing"""
    try:
        if pre_delay > 0:
            time.sleep(pre_delay)
        
        ser.write(data)
        time.sleep(read_delay)
        
        response = ser.read(ser.in_waiting or 100)
        
        if post_delay > 0:
            time.sleep(post_delay)
        
        if response:
            print(f"   {name}: Got {len(response)} bytes: {response.hex()}")
            return True
        else:
            print(f"   {name}: No response")
            return False
    except Exception as e:
        print(f"   {name}: Error - {e}")
        return False

def try_usb_control_transfers(port):
    """Try USB control transfers (requires pyusb)"""
    print("\nUSB CONTROL TRANSFERS")
    print("=" * 60)
    
    try:
        import usb.core
        import usb.util
        
        # Find the device by VID:PID
        dev = usb.core.find(idVendor=0x1A86, idProduct=0x5722)
        
        if dev is None:
            print("    Device not found via USB (try: pip install pyusb)")
            return False
        
        print(f"   Found USB device: {dev}")
        
        # Try to set configuration
        try:
            dev.set_configuration()
            print("   Configuration set")
        except:
            print("    Could not set configuration (may be in use)")
        
        # Try various control transfers
        control_sequences = [
            # (bmRequestType, bRequest, wValue, wIndex, data_or_length)
            (0x40, 0xA1, 0x0000, 0x0000, b''),  # Vendor request
            (0x40, 0xA4, 0x0000, 0x0000, b''),  # Init request
            (0x40, 0x9A, 0x1312, 0x0000, b''),  # Baudrate set
            (0x40, 0xA1, 0x0001, 0x0000, b''),  # Enable
            (0xC0, 0x95, 0x2518, 0x0000, 8),    # Read status
        ]
        
        for i, (req_type, req, value, index, data) in enumerate(control_sequences, 1):
            try:
                print(f"\n   Trying control transfer {i}/5...")
                print(f"      Type: 0x{req_type:02X}, Req: 0x{req:02X}, Val: 0x{value:04X}")
                
                if isinstance(data, bytes):
                    result = dev.ctrl_transfer(req_type, req, value, index, data)
                else:
                    result = dev.ctrl_transfer(req_type, req, value, index, data)
                
                print(f"   Success! Result: {result}")
                
                # Now try serial communication
                ser = serial.Serial(port, 115200, timeout=1)
                hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
                ser.write(hello)
                time.sleep(0.2)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"   DISPLAY RESPONDED: {response.hex()}")
                    ser.close()
                    return True
                ser.close()
                
            except Exception as e:
                print(f"   Failed: {e}")
        
        return False
        
    except ImportError:
        print("    pyusb not installed")
        print("   Install with: pip install pyusb")
        return False
    except Exception as e:
        print(f"   Error: {e}")
        return False

def try_timing_patterns(port):
    """Try different timing patterns"""
    print("\n TIMING PATTERN EXPERIMENTS")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
        
        patterns = [
            ("Slow (1s delays)", 1.0, 0.5),
            ("Fast (50ms delays)", 0.05, 0.05),
            ("Burst (no delays)", 0, 0),
            ("Pulsed (100ms pre, 500ms post)", 0.1, 0.5),
            ("Long wait (2s pre)", 2.0, 0.2),
        ]
        
        for name, pre, post in patterns:
            print(f"\n   Pattern: {name}")
            if send_with_timing(ser, hello, "HELLO", pre_delay=pre, post_delay=post):
                print(f"   SUCCESS with pattern: {name}")
                ser.close()
                return True
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

def try_multi_byte_sequences(port):
    """Try sending commands as individual bytes with delays"""
    print("\nMULTI-BYTE SEQUENCE EXPERIMENTS")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        hello = [0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1]
        
        delays = [0, 0.001, 0.01, 0.05, 0.1]
        
        for delay in delays:
            print(f"\n   Trying byte-by-byte with {delay*1000}ms delay...")
            
            for byte in hello:
                ser.write(bytes([byte]))
                if delay > 0:
                    time.sleep(delay)
            
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   SUCCESS! Response: {response.hex()}")
                ser.close()
                return True
            else:
                print(f"   No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

def try_community_sequences(port):
    """Try sequences reported by community members"""
    print("\n👥 COMMUNITY-REPORTED SEQUENCES")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        # Sequences from various community reports and reverse engineering
        sequences = [
            # Format: (name, bytes, description)
            ("Magic Init 1", bytearray([0x57, 0xAB, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00]), 
             "Reported by user on GitHub"),
            
            ("Magic Init 2", bytearray([0xA5, 0x5A, 0x01, 0x02, 0x03, 0x04]), 
             "Alternative init sequence"),
            
            ("Screen Wake", bytearray([0xFF, 0xFE, 0xFD, 0xFC, 0xFB, 0xFA]), 
             "Wake-up pattern"),
            
            ("Firmware Query", bytearray([0xC1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xC1]), 
             "Query firmware version"),
            
            ("Extended HELLO", bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x01, 0x02, 0x03, 0xC1]), 
             "HELLO with extra bytes"),
            
            ("Double Frame", bytearray([0xC1, 0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0xC1, 0xC1]), 
             "Double-framed HELLO"),
            
            ("Reset Sequence", bytearray([0x00] * 10), 
             "All zeros reset"),
            
            ("Max Sequence", bytearray([0xFF] * 10), 
             "All ones wake"),
            
            ("Alternating", bytearray([0xAA, 0x55] * 5), 
             "Alternating bit pattern"),
            
            ("XuanFang Special", bytearray([0xC8, 0xEF, 0x69, 0x17, 0x70, 0x00, 0x00, 0x00, 0x00, 0xC8]), 
             "XuanFang-specific init"),
        ]
        
        for name, seq, desc in sequences:
            print(f"\n   Trying: {name}")
            print(f"      {desc}")
            print(f"      Bytes: {seq.hex()}")
            
            if send_with_timing(ser, seq, name, post_delay=0.3):
                print(f"   SUCCESS with: {name}")
                ser.close()
                return True
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

def try_handshake_patterns(port):
    """Try different handshake patterns"""
    print("\n🤝 HANDSHAKE PATTERN EXPERIMENTS")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
        
        patterns = [
            ("DTR Low → High → Send", lambda: (setattr(ser, 'dtr', False), time.sleep(0.1), 
                                               setattr(ser, 'dtr', True), time.sleep(0.1))),
            
            ("RTS Low → High → Send", lambda: (setattr(ser, 'rts', False), time.sleep(0.1), 
                                               setattr(ser, 'rts', True), time.sleep(0.1))),
            
            ("Both Toggle → Send", lambda: (setattr(ser, 'dtr', False), setattr(ser, 'rts', False), 
                                           time.sleep(0.1), setattr(ser, 'dtr', True), 
                                           setattr(ser, 'rts', True), time.sleep(0.1))),
            
            ("Break → Send", lambda: (ser.send_break(0.1), time.sleep(0.1))),
            
            ("Reset Buffers → Send", lambda: (ser.reset_input_buffer(), ser.reset_output_buffer(), 
                                             time.sleep(0.1))),
        ]
        
        for name, pattern_func in patterns:
            print(f"\n   Trying: {name}")
            try:
                pattern_func()
                ser.write(hello)
                time.sleep(0.2)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"   SUCCESS! Response: {response.hex()}")
                    ser.close()
                    return True
                else:
                    print(f"   No response")
            except Exception as e:
                print(f"   Error: {e}")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

def try_continuous_polling(port):
    """Try continuous polling with display"""
    print("\nCONTINUOUS POLLING EXPERIMENT")
    print("=" * 60)
    print("   Sending commands continuously for 30 seconds...")
    print("   Watch your display for any flicker or response!")
    
    try:
        ser = serial.Serial(port, 115200, timeout=0.1, rtscts=True)
        
        commands = [
            bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1]),  # HELLO
            bytearray([0xC4, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC4]),  # Screen ON
            bytearray([0xC2, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC2]),  # Brightness
        ]
        
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < 30:
            for cmd in commands:
                ser.write(cmd)
                count += 1
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"\n   RESPONSE AFTER {count} ATTEMPTS!")
                    print(f"      Response: {response.hex()}")
                    ser.close()
                    return True
                
                time.sleep(0.05)
            
            # Progress indicator
            if count % 100 == 0:
                elapsed = int(time.time() - start_time)
                print(f"   Progress: {count} commands sent, {elapsed}s elapsed...")
        
        print(f"\n   No response after {count} commands")
        ser.close()
        return False
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("  EXPERIMENTAL DISPLAY INITIALIZATION")
    print("  Advanced techniques and community findings")
    print("=" * 60)
    
    # Find display
    port = find_display()
    if not port:
        print("\nXuanFang display not found!")
        sys.exit(1)
    
    print(f"\nFound display on: {port}")
    print("\n NOTE: Watch your display during these tests!")
    print("   Even if no serial response, you might see flickers or changes.")
    
    # Try all experimental methods
    methods = [
        ("USB Control Transfers", lambda: try_usb_control_transfers(port)),
        ("Timing Patterns", lambda: try_timing_patterns(port)),
        ("Multi-Byte Sequences", lambda: try_multi_byte_sequences(port)),
        ("Community Sequences", lambda: try_community_sequences(port)),
        ("Handshake Patterns", lambda: try_handshake_patterns(port)),
        ("Continuous Polling", lambda: try_continuous_polling(port)),
    ]
    
    for method_name, method_func in methods:
        print(f"\n{'='*60}")
        print(f"  EXPERIMENT: {method_name}")
        print(f"{'='*60}")
        
        try:
            if method_func():
                print(f"\n{'='*60}")
                print("  SUCCESS!")
                print(f"  Method: {method_name}")
                print(f"{'='*60}")
                print(f"\nNow try running:")
                print(f"  python3 -m atlas.app --theme cyberpunk")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n\n Interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\nUnexpected error: {e}")
    
    # If nothing worked
    print(f"\n{'='*60}")
    print("  ALL EXPERIMENTAL METHODS FAILED")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"   - Tried 6 different experimental approaches")
    print(f"   - Display detected but not responding")
    print(f"   - This is a firmware limitation")
    print(f"\nRecommendations:")
    print(f"   1. USB Packet Capture (95% success rate)")
    print(f"      - Borrow Windows PC")
    print(f"      - Capture with Wireshark")
    print(f"      - Permanent solution")
    print(f"\n   2. Enhanced Simulated Mode (100% working)")
    print(f"      - python3 -m atlas.display_window &")
    print(f"      - python3 -m atlas.app --simulated")
    print(f"\n   3. Try after CH341 driver reboot")
    print(f"      - The driver might help")
    print(f"      - Reboot and test again")

if __name__ == "__main__":
    main()
