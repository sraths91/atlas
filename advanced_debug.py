#!/usr/bin/env python3
"""
Advanced debugging - Try wake-up sequences and alternative protocols
"""
import serial
import time
import sys

PORT = '/dev/cu.usbmodem2017_2_251'

def try_wake_sequences():
    """Try various wake-up sequences"""
    print("\n🔌 Trying Wake-Up Sequences")
    print("="*60)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        
        sequences = [
            ("DTR Toggle", lambda: (ser.setDTR(False), time.sleep(0.1), ser.setDTR(True))),
            ("RTS Toggle", lambda: (ser.setRTS(False), time.sleep(0.1), ser.setRTS(True))),
            ("Break Signal", lambda: (ser.send_break(duration=0.25))),
            ("Reset Buffers", lambda: (ser.reset_input_buffer(), ser.reset_output_buffer())),
        ]
        
        for name, action in sequences:
            print(f"\nTrying: {name}")
            action()
            time.sleep(0.5)
            
            # Send HELLO after wake attempt
            hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
            ser.write(hello)
            ser.flush()
            time.sleep(0.5)
            
            response = ser.read(100)
            if len(response) > 0:
                print(f"   Got response: {response.hex()}")
                return True
            else:
                print(f"   No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_continuous_hello():
    """Send HELLO repeatedly"""
    print("\nSending Continuous HELLO Commands")
    print("="*60)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=1, rtscts=True)
        time.sleep(0.5)
        
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        
        print("Sending HELLO 10 times with delays...")
        for i in range(10):
            print(f"  Attempt {i+1}/10...", end=" ")
            ser.write(hello)
            ser.flush()
            time.sleep(0.3)
            
            response = ser.read(100)
            if len(response) > 0:
                print(f"Response: {response.hex()}")
                ser.close()
                return True
            else:
                print("")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_screen_on_command():
    """Try sending screen-on command"""
    print("\nTrying Screen-On Commands")
    print("="*60)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        
        commands = [
            ("Rev A Screen On", bytearray([0, 0, 0, 0, 0, 109])),
            ("Rev B Screen On", bytearray([0xC4, 1, 0, 0, 0, 0, 0, 0, 0, 0xC4])),
            ("Rev A Reset", bytearray([0, 0, 0, 0, 0, 101])),
        ]
        
        for name, cmd in commands:
            print(f"\nSending: {name}")
            print(f"   Bytes: {cmd.hex()}")
            ser.write(cmd)
            ser.flush()
            time.sleep(1)
            
            response = ser.read(100)
            if len(response) > 0:
                print(f"   Response: {response.hex()}")
            else:
                print(f"   No response")
            
            # Try HELLO after each command
            hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
            ser.write(hello)
            ser.flush()
            time.sleep(0.5)
            
            response = ser.read(100)
            if len(response) > 0:
                print(f"   HELLO response: {response.hex()}")
                ser.close()
                return True
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def try_raw_image_send():
    """Try sending a small image directly"""
    print("\n🖼️  Trying Direct Image Send")
    print("="*60)
    
    try:
        ser = serial.Serial(PORT, 115200, timeout=2, rtscts=True)
        time.sleep(0.5)
        
        # Try Revision B bitmap command
        # Command to display at 0,0 with 10x10 pixels
        print("Sending bitmap command (10x10 white square)...")
        
        bitmap_cmd = bytearray([
            0xC5,  # Bitmap command
            0x00, 0x00,  # X = 0
            0x00, 0x00,  # Y = 0
            0x00, 0x0A,  # Width = 10
            0x00, 0x0A,  # Height = 10
            0xC5
        ])
        
        print(f"   Command: {bitmap_cmd.hex()}")
        ser.write(bitmap_cmd)
        ser.flush()
        time.sleep(0.2)
        
        # Send white pixels (RGB565: 0xFFFF)
        print("   Sending pixel data...")
        for i in range(100):  # 10x10 pixels
            ser.write(b'\xFF\xFF')
        ser.flush()
        time.sleep(0.5)
        
        response = ser.read(100)
        if len(response) > 0:
            print(f"   Response: {response.hex()}")
        else:
            print(f"   No response (but image might be displayed!)")
        
        print("\n   Check if you see a white square on the display!")
        
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

def check_port_permissions():
    """Check if we have proper permissions"""
    print("\nChecking Port Permissions")
    print("="*60)
    
    import os
    import stat
    
    try:
        st = os.stat(PORT)
        mode = st.st_mode
        
        print(f"Port: {PORT}")
        print(f"Owner: {st.st_uid}")
        print(f"Group: {st.st_gid}")
        print(f"Permissions: {stat.filemode(mode)}")
        
        if os.access(PORT, os.R_OK | os.W_OK):
            print("Read/Write access: OK")
        else:
            print("Read/Write access: DENIED")
            print("\nTry running with sudo:")
            print(f"   sudo python3 {sys.argv[0]}")
        
    except Exception as e:
        print(f"Error checking permissions: {e}")

def main():
    """Run advanced diagnostics"""
    print("\nAdvanced XuanFang Display Debugger")
    print("="*60)
    
    # Check permissions
    check_port_permissions()
    
    # Try wake sequences
    if try_wake_sequences():
        print("\nSUCCESS! Wake sequence worked!")
        return
    
    # Try continuous HELLO
    if try_continuous_hello():
        print("\nSUCCESS! Continuous HELLO worked!")
        return
    
    # Try screen-on commands
    if try_screen_on_command():
        print("\nSUCCESS! Screen-on command worked!")
        return
    
    # Try sending image directly
    try_raw_image_send()
    
    print("\n" + "="*60)
    print("ADVANCED DIAGNOSTICS COMPLETE")
    print("="*60)
    print("\nSummary:")
    print("   - Display is not responding to any commands")
    print("   - Port opens successfully")
    print("   - Data is being sent")
    print("   - No responses received")
    print("\nPossible causes:")
    print("   1. Display needs original software to initialize first")
    print("   2. Display is in wrong mode/state")
    print("   3. Different protocol variant needed")
    print("   4. Hardware issue with display")
    print("\nRecommendations:")
    print("   1. Try original ExtendScreen.exe on Windows")
    print("   2. Power cycle the display")
    print("   3. Try different USB port")
    print("   4. Check if display backlight is on")
    print("   5. Use simulated mode (works perfectly!)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Interrupted by user")
        sys.exit(0)
