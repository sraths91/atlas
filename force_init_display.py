#!/usr/bin/env python3
"""
Force Display Initialization
Aggressive initialization sequences to wake up XuanFang displays without original software
Based on reverse engineering and community findings
"""
import serial
import serial.tools.list_ports
import time
import sys

def find_display():
    """Find XuanFang display"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.serial_number == '2017-2-25':
            return port.device
    return None

def try_init_sequence(ser, name, sequence, delay=0.1):
    """Try an initialization sequence"""
    print(f"   Trying: {name}")
    try:
        ser.write(sequence)
        time.sleep(delay)
        response = ser.read(ser.in_waiting or 100)
        if response:
            print(f"   Got response: {response.hex()}")
            return True
        else:
            print(f"   No response")
            return False
    except Exception as e:
        print(f"   Error: {e}")
        return False

def aggressive_initialization(port):
    """Try aggressive initialization sequences"""
    print(f"\n🔥 AGGRESSIVE INITIALIZATION MODE")
    print("=" * 60)
    
    # Try multiple configurations
    configs = [
        {"baudrate": 115200, "rtscts": True, "dsrdtr": False},
        {"baudrate": 115200, "rtscts": False, "dsrdtr": True},
        {"baudrate": 115200, "rtscts": True, "dsrdtr": True},
        {"baudrate": 9600, "rtscts": True, "dsrdtr": False},
        {"baudrate": 57600, "rtscts": True, "dsrdtr": False},
    ]
    
    for i, config in enumerate(configs, 1):
        print(f"\nConfiguration {i}/{len(configs)}")
        print(f"   Baudrate: {config['baudrate']}, RTS/CTS: {config['rtscts']}, DSR/DTR: {config['dsrdtr']}")
        
        try:
            ser = serial.Serial(
                port=port,
                baudrate=config['baudrate'],
                timeout=1,
                write_timeout=1,
                rtscts=config['rtscts'],
                dsrdtr=config['dsrdtr']
            )
            
            # Sequence 1: Extended HELLO with variations
            sequences = [
                ("Standard Rev B HELLO", bytearray([0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0x00, 0xC1])),
                ("Rev B HELLO (framed)", bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])),
                ("Rev A HELLO", bytearray([0x6F] * 6)),
                ("Wake-up sequence", bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])),
                ("Init sequence 1", bytearray([0xC8, 0xEF, 0x69, 0x00, 0x17, 0x70])),
                ("Init sequence 2", bytearray([0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55])),
                ("Screen ON (Rev B)", bytearray([0xC4, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC4])),
                ("Screen ON (Rev A)", bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x6D])),
                ("Brightness Max", bytearray([0xC2, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC2])),
            ]
            
            for seq_name, seq_data in sequences:
                if try_init_sequence(ser, seq_name, seq_data, delay=0.2):
                    print(f"\nSUCCESS! Display responded to: {seq_name}")
                    print(f"   Config: {config}")
                    ser.close()
                    return True
            
            # Try rapid-fire HELLO
            print(f"\n   Trying: Rapid-fire HELLO (20x)")
            hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
            for j in range(20):
                ser.write(hello)
                time.sleep(0.05)
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"   Got response on attempt {j+1}: {response.hex()}")
                    ser.close()
                    return True
            print(f"   No response")
            
            # Try with DTR/RTS toggling
            print(f"\n   Trying: DTR/RTS toggle with commands")
            for _ in range(3):
                ser.dtr = False
                ser.rts = False
                time.sleep(0.1)
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                ser.write(hello)
                time.sleep(0.2)
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"   Got response: {response.hex()}")
                    ser.close()
                    return True
            print(f"   No response")
            
            ser.close()
            
        except Exception as e:
            print(f"   Error: {e}")
            continue
    
    return False

def try_usb_reset(port):
    """Try USB reset techniques"""
    print(f"\n🔌 USB RESET TECHNIQUES")
    print("=" * 60)
    
    try:
        # Open and close rapidly
        print("   Trying: Rapid open/close")
        for i in range(5):
            ser = serial.Serial(port, 115200, timeout=0.5)
            ser.close()
            time.sleep(0.1)
        print("   Completed")
        
        # Open with different settings
        print("   Trying: Different parity settings")
        for parity in [serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD]:
            try:
                ser = serial.Serial(port, 115200, timeout=0.5, parity=parity)
                hello = bytearray([0xC1, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00, 0x00, 0x00, 0xC1])
                ser.write(hello)
                time.sleep(0.2)
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"   Got response with parity {parity}: {response.hex()}")
                    ser.close()
                    return True
                ser.close()
            except:
                pass
        print("   No response")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def try_extended_protocol_variants(port):
    """Try extended protocol variants"""
    print(f"\nEXTENDED PROTOCOL VARIANTS")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1, rtscts=True)
        
        # XuanFang-specific sequences from community reports
        variants = [
            ("XuanFang Init 1", bytearray([0x5A, 0xA5, 0x00, 0x00, 0x00, 0x00])),
            ("XuanFang Init 2", bytearray([0xAB, 0xCD, 0xEF, 0x01, 0x02, 0x03])),
            ("Alternate HELLO 1", bytearray([0x48, 0x45, 0x4C, 0x4C, 0x4F])),  # No framing
            ("Alternate HELLO 2", bytearray([0xC1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC1])),
            ("Status Query", bytearray([0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0])),
            ("Version Query", bytearray([0xCF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xCF])),
        ]
        
        for name, seq in variants:
            if try_init_sequence(ser, name, seq, delay=0.3):
                print(f"\nSUCCESS! Display responded to: {name}")
                ser.close()
                return True
        
        ser.close()
        
    except Exception as e:
        print(f"   Error: {e}")
    
    return False

def main():
    print("\n" + "=" * 60)
    print("  FORCE DISPLAY INITIALIZATION")
    print("  Attempting to wake up XuanFang display without original software")
    print("=" * 60)
    
    # Find display
    port = find_display()
    if not port:
        print("\nXuanFang display not found!")
        print("   Make sure the display is connected.")
        sys.exit(1)
    
    print(f"\nFound display on: {port}")
    
    # Try different initialization methods
    methods = [
        ("Aggressive Initialization", lambda: aggressive_initialization(port)),
        ("USB Reset Techniques", lambda: try_usb_reset(port)),
        ("Extended Protocol Variants", lambda: try_extended_protocol_variants(port)),
    ]
    
    for method_name, method_func in methods:
        print(f"\n{'='*60}")
        print(f"  METHOD: {method_name}")
        print(f"{'='*60}")
        
        if method_func():
            print(f"\n{'='*60}")
            print("  SUCCESS!")
            print(f"  Display is now responding!")
            print(f"{'='*60}")
            print(f"\nNow try running:")
            print(f"  python3 -m atlas.app --theme cyberpunk")
            sys.exit(0)
    
    # If nothing worked
    print(f"\n{'='*60}")
    print("  ALL METHODS FAILED")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"   - Display detected: ")
    print(f"   - Port accessible: ")
    print(f"   - Display responding: ")
    print(f"\nNext Steps:")
    print(f"   1. Try running original ExtendScreen.exe on Windows once")
    print(f"   2. Power cycle the display (unplug for 30 seconds)")
    print(f"   3. Try a different USB port")
    print(f"   4. Use simulated mode: python3 -m atlas.app --simulated")
    print(f"\n   The display firmware may require the original software's")
    print(f"   specific initialization sequence that we haven't discovered yet.")

if __name__ == "__main__":
    main()
