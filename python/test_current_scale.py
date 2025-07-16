#!/usr/bin/env python3
"""Test script to verify current scaling for Dynamixel motors."""
import argparse
import time
import numpy as np
from leap_hand_utils.dynamixel_client import DynamixelClient

def test_current_scaling(port: str, motor_id: int, test_current_ma: int = 100):
    """Test current scaling by writing and reading current values.
    
    Args:
        port: Dynamixel port (e.g. 'COM1', '/dev/ttyUSB0')
        motor_id: ID of the motor to test
        test_current_ma: Test current in mA (default: 100mA)
    """
    print(f"\nTesting current scaling with {test_current_ma}mA...")
    
    # Initialize client
    client = DynamixelClient(motor_ids=[motor_id], port=port)
    
    try:
        # Connect and enable torque
        client.connect()
        print("Connected to motor successfully")
        
        # First disable torque to allow current control
        client.set_torque_enabled([motor_id], False)
        time.sleep(0.1)
        
        # Write test current
        print(f"\nWriting current: {test_current_ma}mA")
        client.write_desired_cur([motor_id], np.array([test_current_ma]))
        time.sleep(0.5)  # Wait for current to stabilize
        
        # Read back multiple times to get stable reading
        readings = []
        for i in range(5):
            current = client.read_cur()
            readings.append(current[0])  # Get first motor's current
            time.sleep(0.1)
        
        avg_reading = np.mean(readings)
        print(f"\nResults:")
        print(f"Written current: {test_current_ma}mA")
        print(f"Read current (raw): {readings}")
        print(f"Average read current: {avg_reading:.2f}mA")
        print(f"Ratio (read/written): {avg_reading/test_current_ma:.3f}")
        
        if abs(avg_reading - test_current_ma) < 10:  # 10mA tolerance
            print("\nConclusion: NO scaling needed! (1:1 relationship)")
        elif abs(avg_reading/test_current_ma - 1.34) < 0.1:  # Check if ratio is close to 1.34
            print("\nConclusion: Current 1.34 scaling factor appears correct!")
        else:
            print(f"\nConclusion: Unexpected scaling factor: {avg_reading/test_current_ma:.3f}")
            print("Further investigation needed!")
            
    finally:
        # Clean up
        client.set_torque_enabled([motor_id], False)
        client.disconnect()
        print("\nTest completed and motor disconnected")

def main():
    parser = argparse.ArgumentParser(description='Test Dynamixel current scaling')
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0',
                      help='Dynamixel port (default: /dev/ttyUSB0)')
    parser.add_argument('--motor_id', type=int, required=True,
                      help='Motor ID to test')
    parser.add_argument('--current', type=int, default=100,
                      help='Test current in mA (default: 100)')
    
    args = parser.parse_args()
    
    test_current_scaling(args.port, args.motor_id, args.current)

if __name__ == '__main__':
    main() 