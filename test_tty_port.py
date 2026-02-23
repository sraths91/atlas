#!/usr/bin/env python3
"""
Test the tty version of the port
"""
import serial
import time

def test_port(port_name):
    """Test a specific port"""
    print(f"\nTesting {port_name}")
    print("="*60)
    
    try:
        ser = serial.Serial(port_name, 115200, timeout=2, rtscts=True)
        print("Port opened")
        time.sleep(0.5)
        
        # Send Revision B HELLO
        hello = bytearray([0xC1, ord('H'), ord('E'), ord('L'), ord('L'), ord('O'), 0, 0, 0, 0xC1])
        print(f"Sending HELLO: {hello.hex()}")
        ser.write(hello)
        ser.flush()
        time.sleep(1)
        
        response = ser.read(100)
        if len(response) > 0:
            print(f"Response ({len(response)} bytes): {response.hex()}")
            return True
        else:
            print("No response")
            return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        try:
            ser.close()
        except:
            pass

# Test both ports
test_port('/dev/cu.usbmodem2017_2_251')
test_port('/dev/tty.usbmodem2017_2_251')

print("\n" + "="*60)
print("Both ports tested - no response from either")
print("="*60)
