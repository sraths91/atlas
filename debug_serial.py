#!/usr/bin/env python3
"""
Serial Communication Debugger for XuanFang Display
Tests different serial configurations and protocols
"""
import serial
import time
import sys

PORT = '/dev/cu.usbmodem2017_2_251'

def test_serial_config(baudrate, rtscts, timeout):
    """Test a specific serial configuration"""
    print(f"\n{'='*60}")
    print(f"Testing: baudrate={baudrate}, rtscts={rtscts}, timeout={timeout}")
    print(f"{'='*60}")
    
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=timeout,
            rtscts=rtscts
        )
        
        print(f"Serial port opened successfully")
        time.sleep(0.5)
        
        # Test 1: Revision B HELLO
        print("\nTest 1: Sending Revision B HELLO command...")
        hello_b = bytearray([
            0xC1,  # Command
            ord('H'), ord('E'), ord('L'), ord('L'), ord('O'),  # HELLO
            0x00, 0x00, 0x00,  # Padding
            0xC1   # Command end
        ])
        print(f"   Sending: {hello_b.hex()}")
        ser.write(hello_b)
        ser.flush()
        time.sleep(0.5)
        
        # Try to read response
        response = ser.read(100)
        if len(response) > 0:
            print(f"   Response ({len(response)} bytes): {response.hex()}")
            print(f"   ASCII: {response}")
        else:
            print(f"   No response")
        
        # Clear buffer
        ser.reset_input_buffer()
        time.sleep(0.2)
        
        # Test 2: Revision A HELLO
        print("\nTest 2: Sending Revision A HELLO command...")
        hello_a = bytearray([111, 111, 111, 111, 111, 111])
        print(f"   Sending: {hello_a.hex()}")
        ser.write(hello_a)
        ser.flush()
        time.sleep(0.5)
        
        response = ser.read(100)
        if len(response) > 0:
            print(f"   Response ({len(response)} bytes): {response.hex()}")
        else:
            print(f"   No response")
        
        # Clear buffer
        ser.reset_input_buffer()
        time.sleep(0.2)
        
        # Test 3: Simple test bytes
        print("\nTest 3: Sending simple test pattern...")
        test_pattern = bytearray([0x55, 0xAA, 0x55, 0xAA])
        print(f"   Sending: {test_pattern.hex()}")
        ser.write(test_pattern)
        ser.flush()
        time.sleep(0.5)
        
        response = ser.read(100)
        if len(response) > 0:
            print(f"   Response ({len(response)} bytes): {response.hex()}")
        else:
            print(f"   No response")
        
        # Test 4: Check if anything is in the buffer
        print("\nTest 4: Checking for any data in buffer...")
        time.sleep(1)
        waiting = ser.in_waiting
        if waiting > 0:
            print(f"   Found {waiting} bytes waiting")
            data = ser.read(waiting)
            print(f"   Data: {data.hex()}")
        else:
            print(f"   No data in buffer")
        
        ser.close()
        print(f"\nConfiguration test complete")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_without_rtscts():
    """Test without hardware flow control"""
    print("\n" + "="*60)
    print("SPECIAL TEST: Without hardware flow control")
    print("="*60)
    
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=115200,
            timeout=2,
            write_timeout=2,
            rtscts=False,  # No hardware flow control
            xonxoff=False,
            dsrdtr=False
        )
        
        print(f"Serial port opened (no flow control)")
        time.sleep(0.5)
        
        # Send Revision B HELLO
        print("\nSending Revision B HELLO...")
        hello_b = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0x00, 0x00, 0x00, 0xC1])
        print(f"   Bytes: {hello_b.hex()}")
        ser.write(hello_b)
        ser.flush()
        time.sleep(1)
        
        response = ser.read(100)
        if len(response) > 0:
            print(f"   Response: {response.hex()}")
        else:
            print(f"   No response")
        
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

def test_alternative_baudrates():
    """Test different baud rates"""
    baudrates = [9600, 19200, 38400, 57600, 115200]
    
    print("\n" + "="*60)
    print("TESTING DIFFERENT BAUD RATES")
    print("="*60)
    
    for baud in baudrates:
        print(f"\nTesting {baud} baud...")
        try:
            ser = serial.Serial(
                port=PORT,
                baudrate=baud,
                timeout=1,
                rtscts=True
            )
            
            time.sleep(0.3)
            
            # Send simple HELLO
            hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0x00, 0x00, 0x00, 0xC1])
            ser.write(hello)
            ser.flush()
            time.sleep(0.5)
            
            response = ser.read(50)
            if len(response) > 0:
                print(f"   Got response at {baud} baud: {response.hex()}")
            else:
                print(f"   No response at {baud} baud")
            
            ser.close()
            
        except Exception as e:
            print(f"   Error at {baud}: {e}")

def test_read_existing_data():
    """Just open port and see if display is sending anything"""
    print("\n" + "="*60)
    print("PASSIVE TEST: Listening for any data from display")
    print("="*60)
    
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=115200,
            timeout=5,
            rtscts=True
        )
        
        print("Port opened, listening for 5 seconds...")
        time.sleep(5)
        
        waiting = ser.in_waiting
        if waiting > 0:
            print(f"Display sent {waiting} bytes!")
            data = ser.read(waiting)
            print(f"   Hex: {data.hex()}")
            print(f"   ASCII: {data}")
        else:
            print("No data received from display")
        
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all diagnostic tests"""
    print("\nXuanFang Display Serial Communication Debugger")
    print(f"Port: {PORT}")
    print("\nThis will test various serial configurations to find what works.\n")
    
    # Test 1: Standard configuration
    test_serial_config(baudrate=115200, rtscts=True, timeout=2)
    
    # Test 2: Without hardware flow control
    test_without_rtscts()
    
    # Test 3: Different baud rates
    test_alternative_baudrates()
    
    # Test 4: Passive listening
    test_read_existing_data()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("\nIf any test showed a response, that configuration works!")
    print("Update the display driver with the working settings.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Interrupted by user")
        sys.exit(0)
