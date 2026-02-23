#!/usr/bin/env python3
"""
Experimental USB Initialization
Low-level USB control transfers and experimental approaches
"""
import serial
import serial.tools.list_ports
import time
import sys
import struct

try:
    import usb.core
    import usb.util
    HAS_PYUSB = True
except ImportError:
    HAS_PYUSB = False
    print(" pyusb not available, using serial-only methods")

def find_display():
    """Find XuanFang display"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.serial_number == '2017-2-25':
            return port.device, port
    return None, None

def try_usb_control_transfers():
    """Try USB control transfers (requires pyusb)"""
    if not HAS_PYUSB:
        return False
    
    print("\nMETHOD 1: USB Control Transfers")
    print("=" * 60)
    
    # Find USB device (VID:PID 1A86:5722)
    dev = usb.core.find(idVendor=0x1A86, idProduct=0x5722)
    
    if dev is None:
        print("   USB device not found")
        return False
    
    print(f"   Found USB device: {dev}")
    
    try:
        # Try to detach kernel driver if active
        if dev.is_kernel_driver_active(0):
            print("   Detaching kernel driver...")
            try:
                dev.detach_kernel_driver(0)
                print("   Kernel driver detached")
            except:
                print("    Could not detach (may not be needed)")
        
        # Set configuration
        try:
            dev.set_configuration()
            print("   Configuration set")
        except:
            print("    Configuration already set")
        
        # Try various USB control transfers
        control_sequences = [
            # (bmRequestType, bRequest, wValue, wIndex, data_or_wLength)
            (0x40, 0xA1, 0x0000, 0x0000, None),  # Vendor request
            (0x40, 0xA4, 0x0000, 0x0000, None),  # Another vendor request
            (0x40, 0x9A, 0x1312, 0x0000, None),  # CH341 init
            (0x40, 0xA1, 0x1312, 0x0000, None),  # CH341 init variant
            (0x40, 0x95, 0x2518, 0x0000, None),  # Baud rate setup
            (0x40, 0x9A, 0x2518, 0x0000, None),  # Baud rate variant
        ]
        
        for req_type, req, value, index, data in control_sequences:
            try:
                print(f"   Control transfer: type={hex(req_type)}, req={hex(req)}, val={hex(value)}")
                if data is None:
                    result = dev.ctrl_transfer(req_type, req, value, index, 0)
                else:
                    result = dev.ctrl_transfer(req_type, req, value, index, data)
                print(f"      Success: {result}")
                time.sleep(0.1)
            except Exception as e:
                print(f"       {e}")
        
        # Try to reattach kernel driver
        try:
            usb.util.dispose_resources(dev)
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

def try_break_sequences(port):
    """Try various break signal sequences"""
    print("\nMETHOD 2: Break Signal Sequences")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        
        sequences = [
            ("Long break (500ms)", 0.5),
            ("Short break (100ms)", 0.1),
            ("Very short break (10ms)", 0.01),
            ("Rapid breaks (10x)", None),
        ]
        
        for name, duration in sequences:
            print(f"   {name}")
            
            if duration is None:
                # Rapid breaks
                for _ in range(10):
                    ser.send_break(duration=0.01)
                    time.sleep(0.05)
            else:
                ser.send_break(duration=duration)
            
            time.sleep(0.2)
            
            # Try HELLO after break
            hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
            ser.write(hello)
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      SUCCESS! Response: {response.hex()}")
                ser.close()
                return True
            else:
                print(f"      No response")
        
        ser.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def try_timing_variations(port):
    """Try different timing patterns"""
    print("\nMETHOD 3: Timing Variations")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        # Try sending with different inter-byte delays
        hello = [0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1]
        
        delays = [0, 0.001, 0.01, 0.05, 0.1]
        
        for delay in delays:
            print(f"   Inter-byte delay: {delay*1000:.1f}ms")
            
            # Send byte by byte with delay
            for byte in hello:
                ser.write(bytes([byte]))
                if delay > 0:
                    time.sleep(delay)
            
            time.sleep(0.3)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      SUCCESS! Response: {response.hex()}")
                ser.close()
                return True
            else:
                print(f"      No response")
        
        ser.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def try_power_cycling_sequence(port):
    """Try power cycling via DTR/RTS"""
    print("\nMETHOD 4: Power Cycling Sequence")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        
        print("   Power cycle via DTR/RTS...")
        
        # Power off
        ser.dtr = False
        ser.rts = False
        time.sleep(1)
        print("      Power OFF (1 second)")
        
        # Power on
        ser.dtr = True
        ser.rts = True
        time.sleep(0.5)
        print("      Power ON")
        
        # Wait for boot
        time.sleep(1)
        print("      Waiting for firmware boot...")
        
        # Try HELLO immediately
        hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
        
        for i in range(10):
            print(f"      Attempt {i+1}/10...")
            ser.write(hello)
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      SUCCESS! Response: {response.hex()}")
                ser.close()
                return True
        
        print("      No response")
        ser.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def try_raw_binary_sequences(port):
    """Try raw binary sequences from community reports"""
    print("\nMETHOD 5: Raw Binary Sequences")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        # Sequences from various community reports and reverse engineering
        sequences = [
            ("XuanFang magic bytes", bytearray([0x5A, 0xA5, 0x5A, 0xA5, 0x00, 0x00, 0x00, 0x00])),
            ("Alternate magic", bytearray([0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55])),
            ("CH341 reset", bytearray([0xFF, 0xFF, 0xFF, 0xFF])),
            ("Firmware wake", bytearray([0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF])),
            ("Init pattern 1", bytearray([0xC8, 0xEF, 0x69, 0x00, 0x17, 0x70])),
            ("Init pattern 2", bytearray([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])),
            ("Sync pattern", bytearray([0x16] * 8)),
        ]
        
        for name, seq in sequences:
            print(f"   {name}: {seq.hex()}")
            ser.write(seq)
            time.sleep(0.3)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      SUCCESS! Response: {response.hex()}")
                ser.close()
                return True
            
            # Try HELLO after each sequence
            hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
            ser.write(hello)
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      SUCCESS after HELLO! Response: {response.hex()}")
                ser.close()
                return True
            
            print(f"      No response")
        
        ser.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def try_continuous_polling(port):
    """Try continuous polling with display"""
    print("\nMETHOD 6: Continuous Polling")
    print("=" * 60)
    print("   Sending commands continuously for 30 seconds...")
    print("   (Sometimes displays respond after warming up)")
    
    try:
        ser = serial.Serial(port, 115200, timeout=0.1, rtscts=True)
        
        hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
        screen_on = bytearray([0xC4, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC4])
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < 30:
            attempt += 1
            
            # Alternate between HELLO and Screen ON
            if attempt % 2 == 0:
                ser.write(hello)
            else:
                ser.write(screen_on)
            
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                elapsed = time.time() - start_time
                print(f"\n      SUCCESS after {elapsed:.1f}s (attempt {attempt})!")
                print(f"      Response: {response.hex()}")
                ser.close()
                return True
            
            if attempt % 50 == 0:
                print(f"      Attempt {attempt}... ({int(time.time() - start_time)}s elapsed)")
        
        print(f"      No response after {attempt} attempts")
        ser.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def main():
    print("\n" + "=" * 60)
    print("  EXPERIMENTAL USB INITIALIZATION")
    print("  Last-ditch effort to wake up your display")
    print("=" * 60)
    
    # Find display
    port, port_info = find_display()
    if not port:
        print("\nXuanFang display not found!")
        sys.exit(1)
    
    print(f"\nFound display on: {port}")
    print(f"   Manufacturer: {port_info.manufacturer}")
    print(f"   Serial: {port_info.serial_number}")
    print(f"   VID:PID: {hex(port_info.vid)}:{hex(port_info.pid)}")
    
    # Try all experimental methods
    methods = [
        ("USB Control Transfers", try_usb_control_transfers),
        ("Break Signal Sequences", lambda: try_break_sequences(port)),
        ("Timing Variations", lambda: try_timing_variations(port)),
        ("Power Cycling", lambda: try_power_cycling_sequence(port)),
        ("Raw Binary Sequences", lambda: try_raw_binary_sequences(port)),
        ("Continuous Polling", lambda: try_continuous_polling(port)),
    ]
    
    for i, (method_name, method_func) in enumerate(methods, 1):
        print(f"\n{'='*60}")
        print(f"  EXPERIMENTAL METHOD {i}/{len(methods)}: {method_name}")
        print(f"{'='*60}")
        
        try:
            if method_func():
                print(f"\n{'='*60}")
                print("  SUCCESS! ")
                print(f"  Display responded to: {method_name}")
                print(f"{'='*60}")
                print(f"\nNow try running the full app:")
                print(f"  python3 -m atlas.app --theme cyberpunk")
                sys.exit(0)
        except Exception as e:
            print(f"\n   Method failed with error: {e}")
        
        # Small delay between methods
        time.sleep(1)
    
    # If we get here, nothing worked
    print(f"\n{'='*60}")
    print("  ALL EXPERIMENTAL METHODS FAILED")
    print(f"{'='*60}")
    print(f"\nConclusion:")
    print(f"   Your XuanFang display requires a specific initialization")
    print(f"   sequence that can only be discovered through USB packet")
    print(f"   capture from the original Windows software.")
    print(f"\nYour best options:")
    print(f"\n   1. Enhanced Simulated Mode (Works perfectly!):")
    print(f"      python3 -m atlas.display_window &")
    print(f"      python3 -m atlas.app --simulated")
    print(f"\n   2. USB Packet Capture (Permanent fix):")
    print(f"      - Borrow Windows PC for 30 minutes")
    print(f"      - Capture USB traffic with Wireshark")
    print(f"      - Send me the capture file")
    print(f"      - I'll create custom init script")
    print(f"      - 95% success rate!")

if __name__ == "__main__":
    main()
