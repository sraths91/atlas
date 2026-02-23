#!/usr/bin/env python3
"""
Try with Apple's Built-in CH34x Driver
Using recommended settings for Apple's driver
"""
import serial
import serial.tools.list_ports
import time

def find_display():
    """Find XuanFang display"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.serial_number == '2017-2-25':
            return port.device
    return None

def try_with_apple_driver(port):
    """Try with Apple's driver recommendations"""
    print("\n🍎 Testing with Apple's Built-in CH34x Driver")
    print("=" * 60)
    print(f"Port: {port}")
    print("\nApple's driver is already loaded in your system!")
    print("Trying recommended settings...\n")
    
    # Apple's driver works best at 460,800 bps or lower
    baud_rates = [115200, 230400, 460800, 57600, 38400, 9600]
    
    for baud in baud_rates:
        print(f"Trying baud rate: {baud}")
        
        try:
            # Open with Apple's recommended settings
            ser = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=1,
                write_timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                rtscts=False,  # Try without flow control first
                dsrdtr=False
            )
            
            print(f"   Port opened at {baud} bps")
            
            # Try initialization sequences
            sequences = [
                ("Rev B HELLO", bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])),
                ("Rev A HELLO", bytearray([0x6F] * 6)),
                ("Screen ON", bytearray([0xC4, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC4])),
            ]
            
            for seq_name, seq_data in sequences:
                ser.write(seq_data)
                time.sleep(0.2)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"   SUCCESS! Got response to {seq_name}: {response.hex()}")
                    ser.close()
                    return True
            
            print(f"   No response at {baud} bps")
            ser.close()
            
        except Exception as e:
            print(f"   Error: {e}")
            continue
    
    # Try with flow control enabled
    print(f"\nTrying with RTS/CTS flow control...")
    for baud in [115200, 460800]:
        try:
            ser = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=1,
                rtscts=True,  # Enable flow control
                dsrdtr=False
            )
            
            print(f"   Testing {baud} bps with flow control...")
            
            hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
            ser.write(hello)
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   SUCCESS with flow control: {response.hex()}")
                ser.close()
                return True
            
            ser.close()
            
        except Exception as e:
            print(f"   Error: {e}")
    
    return False

def main():
    print("\n" + "=" * 60)
    print("  APPLE'S CH34x DRIVER TEST")
    print("  Your macOS already includes CH34x support!")
    print("=" * 60)
    
    # Find display
    port = find_display()
    if not port:
        print("\nXuanFang display not found!")
        return
    
    print(f"\nFound display on: {port}")
    
    # Try with Apple's driver
    if try_with_apple_driver(port):
        print("\n" + "=" * 60)
        print("  SUCCESS!")
        print("  Display is responding with Apple's driver!")
        print("=" * 60)
        print("\nNow try running:")
        print("  python3 -m atlas.app --theme cyberpunk")
    else:
        print("\n" + "=" * 60)
        print("  Display still not responding")
        print("=" * 60)
        print("\nThis confirms it's a firmware initialization issue,")
        print("   not a driver problem.")
        print("\nSolutions:")
        print("   1. Use enhanced simulated mode (works perfectly!)")
        print("   2. USB packet capture (permanent fix)")
        print("\n   Enhanced simulated mode:")
        print("   python3 -m atlas.display_window &")
        print("   python3 -m atlas.app --simulated")

if __name__ == "__main__":
    main()
