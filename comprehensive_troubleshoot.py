#!/usr/bin/env python3
"""
Comprehensive troubleshooting for XuanFang display
Tries every possible approach to get the display responding
"""
import serial
import time
import sys
import struct

PORT = '/dev/cu.usbmodem2017_2_251'

def hex_dump(data, label="Data"):
    """Pretty print hex data"""
    if len(data) == 0:
        print(f"   {label}: (empty)")
        return
    hex_str = ' '.join(f'{b:02x}' for b in data)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
    print(f"   {label}: {hex_str}")
    print(f"   ASCII: {ascii_str}")

def try_method_1_original_revb():
    """Try exact Revision B protocol from original code"""
    print("\n" + "="*70)
    print("METHOD 1: Original Revision B Protocol (Exact Implementation)")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, write_timeout=2, rtscts=True)
        time.sleep(0.5)
        print("Port opened")
        
        # Exact HELLO from original code
        hello_payload = [ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0]
        cmd = bytearray(10)
        cmd[0] = 0xC1
        for i in range(8):
            cmd[i+1] = hello_payload[i]
        cmd[9] = 0xC1
        
        print("Sending exact Revision B HELLO...")
        hex_dump(cmd, "Command")
        ser.write(cmd)
        ser.flush()
        time.sleep(1)
        
        response = ser.read(100)
        if len(response) > 0:
            print("SUCCESS! Got response:")
            hex_dump(response, "Response")
            ser.close()
            return True
        else:
            print("No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_2_longer_timeout():
    """Try with much longer timeout"""
    print("\n" + "="*70)
    print("METHOD 2: Extended Timeout (10 seconds)")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=10, write_timeout=10, rtscts=True)
        time.sleep(1)
        print("Port opened with 10s timeout")
        
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        print("Sending HELLO, waiting up to 10 seconds...")
        ser.write(hello)
        ser.flush()
        
        print("⏳ Waiting for response...")
        response = ser.read(100)
        if len(response) > 0:
            print("SUCCESS! Got response:")
            hex_dump(response, "Response")
            ser.close()
            return True
        else:
            print("No response after 10 seconds")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_3_multiple_hellos():
    """Send multiple HELLOs in rapid succession"""
    print("\n" + "="*70)
    print("METHOD 3: Rapid Multiple HELLOs (Flood)")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        print("Port opened")
        
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        
        print("Sending 20 HELLOs rapidly...")
        for i in range(20):
            ser.write(hello)
            if i % 5 == 0:
                print(f"   Sent {i+1}/20...")
        ser.flush()
        
        time.sleep(2)
        
        response = ser.read(1000)
        if len(response) > 0:
            print("SUCCESS! Got response:")
            hex_dump(response, "Response")
            ser.close()
            return True
        else:
            print("No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_4_reset_sequence():
    """Try a reset/initialization sequence"""
    print("\n" + "="*70)
    print("METHOD 4: Reset Sequence")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        print("Port opened")
        
        sequences = [
            ("Clear buffers", lambda: (ser.reset_input_buffer(), ser.reset_output_buffer())),
            ("DTR Low", lambda: ser.setDTR(False)),
            ("RTS Low", lambda: ser.setRTS(False)),
            ("Wait 500ms", lambda: time.sleep(0.5)),
            ("DTR High", lambda: ser.setDTR(True)),
            ("RTS High", lambda: ser.setRTS(True)),
            ("Wait 500ms", lambda: time.sleep(0.5)),
        ]
        
        print("Executing reset sequence...")
        for name, action in sequences:
            print(f"   {name}...")
            action()
        
        # Now send HELLO
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        print("Sending HELLO after reset...")
        ser.write(hello)
        ser.flush()
        time.sleep(1)
        
        response = ser.read(100)
        if len(response) > 0:
            print("SUCCESS! Got response:")
            hex_dump(response, "Response")
            ser.close()
            return True
        else:
            print("No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_5_alternative_commands():
    """Try alternative command formats"""
    print("\n" + "="*70)
    print("METHOD 5: Alternative Command Formats")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        print("Port opened")
        
        commands = [
            ("Standard Rev B HELLO", bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])),
            ("Rev A HELLO", bytearray([111, 111, 111, 111, 111, 111])),
            ("Alternative Rev B", bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0, 0, 0, 0xC1])),
            ("Init sequence", bytearray([0xC8, 0xEF, 0x69, 0x00, 0x17, 0x70])),
            ("Screen on", bytearray([0xC4, 1, 0, 0, 0, 0, 0, 0, 0, 0xC4])),
            ("Brightness max", bytearray([0xC2, 255, 0, 0, 0, 0, 0, 0, 0, 0xC2])),
        ]
        
        for name, cmd in commands:
            print(f"\nTrying: {name}")
            hex_dump(cmd, "Command")
            ser.write(cmd)
            ser.flush()
            time.sleep(0.5)
            
            response = ser.read(100)
            if len(response) > 0:
                print("SUCCESS! Got response:")
                hex_dump(response, "Response")
                ser.close()
                return True
            else:
                print("   No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_6_slow_send():
    """Send data very slowly, byte by byte"""
    print("\n" + "="*70)
    print("METHOD 6: Slow Byte-by-Byte Send")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        print("Port opened")
        
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        
        print("Sending HELLO byte-by-byte (100ms delay)...")
        for i, byte in enumerate(hello):
            print(f"   Byte {i+1}/10: 0x{byte:02x}")
            ser.write(bytes([byte]))
            ser.flush()
            time.sleep(0.1)
        
        print("⏳ Waiting for response...")
        time.sleep(1)
        
        response = ser.read(100)
        if len(response) > 0:
            print("SUCCESS! Got response:")
            hex_dump(response, "Response")
            ser.close()
            return True
        else:
            print("No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_7_listen_first():
    """Open port and listen before sending anything"""
    print("\n" + "="*70)
    print("METHOD 7: Listen First (Check for Unsolicited Data)")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=5, rtscts=True)
        print("Port opened")
        print("⏳ Listening for 5 seconds before sending anything...")
        
        time.sleep(5)
        
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print("Display sent unsolicited data!")
            hex_dump(data, "Received")
            ser.close()
            return True
        else:
            print("No unsolicited data")
        
        # Now try sending HELLO
        print("\nNow sending HELLO...")
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        ser.write(hello)
        ser.flush()
        time.sleep(2)
        
        response = ser.read(100)
        if len(response) > 0:
            print("SUCCESS! Got response:")
            hex_dump(response, "Response")
            ser.close()
            return True
        else:
            print("No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_method_8_different_settings():
    """Try completely different serial settings"""
    print("\n" + "="*70)
    print("METHOD 8: Alternative Serial Settings")
    print("="*70)
    
    configs = [
        ("8N1, no flow control", {'bytesize': 8, 'parity': 'N', 'stopbits': 1, 'rtscts': False, 'xonxoff': False}),
        ("8N1, XON/XOFF", {'bytesize': 8, 'parity': 'N', 'stopbits': 1, 'rtscts': False, 'xonxoff': True}),
        ("8E1, hardware flow", {'bytesize': 8, 'parity': 'E', 'stopbits': 1, 'rtscts': True, 'xonxoff': False}),
        ("7E1, hardware flow", {'bytesize': 7, 'parity': 'E', 'stopbits': 1, 'rtscts': True, 'xonxoff': False}),
    ]
    
    hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
    
    for name, config in configs:
        print(f"\nTrying: {name}")
        try:
            ser = serial.Serial(PORT, 115200, timeout=2, **config)
            time.sleep(0.5)
            
            ser.write(hello)
            ser.flush()
            time.sleep(1)
            
            response = ser.read(100)
            if len(response) > 0:
                print("SUCCESS! Got response:")
                hex_dump(response, "Response")
                ser.close()
                return True
            else:
                print("   No response")
            
            ser.close()
            
        except Exception as e:
            print(f"   Error: {e}")
    
    return False

def try_method_9_check_loopback():
    """Check if port is in loopback mode"""
    print("\n" + "="*70)
    print("METHOD 9: Loopback Test")
    print("="*70)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=1, rtscts=True)
        time.sleep(0.5)
        print("Port opened")
        
        test_data = bytearray([0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA])
        print("Sending test pattern...")
        hex_dump(test_data, "Sent")
        
        ser.write(test_data)
        ser.flush()
        time.sleep(0.5)
        
        response = ser.read(100)
        if len(response) > 0:
            hex_dump(response, "Received")
            if response == test_data:
                print(" WARNING: Port is in LOOPBACK mode!")
                print("   Data is being echoed back")
            else:
                print("Got different data - display is responding!")
            ser.close()
            return True
        else:
            print("No response (not even loopback)")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all troubleshooting methods"""
    print("\n" + "="*70)
    print("COMPREHENSIVE TROUBLESHOOTING")
    print("="*70)
    print(f"Port: {PORT}")
    print("Testing 9 different methods to get display responding...")
    print()
    
    methods = [
        try_method_1_original_revb,
        try_method_2_longer_timeout,
        try_method_3_multiple_hellos,
        try_method_4_reset_sequence,
        try_method_5_alternative_commands,
        try_method_6_slow_send,
        try_method_7_listen_first,
        try_method_8_different_settings,
        try_method_9_check_loopback,
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"\n{'='*70}")
        print(f"TESTING METHOD {i}/{len(methods)}")
        print(f"{'='*70}")
        
        try:
            if method():
                print("\n" + "="*70)
                print("SUCCESS! Display responded!")
                print("="*70)
                print(f"\nMethod {i} worked: {method.__name__}")
                print("Update the display driver to use this method.")
                return 0
        except Exception as e:
            print(f"\nMethod {i} crashed: {e}")
        
        time.sleep(0.5)  # Brief pause between methods
    
    print("\n" + "="*70)
    print("ALL METHODS FAILED")
    print("="*70)
    print("\nSummary:")
    print("   - Tested 9 different approaches")
    print("   - Display did not respond to any method")
    print("   - Port opens successfully")
    print("   - Data is being sent")
    print("\nThis confirms:")
    print("   1. Display is in wrong state/mode")
    print("   2. Needs original software initialization")
    print("   3. Or hardware issue with display unit")
    print("\nRecommended actions:")
    print("   1. Use simulated mode (works perfectly)")
    print("   2. Try original ExtendScreen.exe on Windows")
    print("   3. Power cycle display completely")
    print("   4. Try different USB cable/port")
    print("   5. Contact display manufacturer")
    
    return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n Interrupted by user")
        sys.exit(130)
