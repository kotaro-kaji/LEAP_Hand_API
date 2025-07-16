#!/usr/bin/env python3
"""
CSV loading functionality test script
Tests the CSV file monitoring and current limit loading without requiring LEAP Hand hardware
"""

import csv
import os
import time
from datetime import datetime
from typing import List, Dict


class MockDynamixelClient:
    """Mock DynamixelClient for testing without hardware"""
    
    def __init__(self, motors: List[int], port: str, baudrate: int):
        self.motors = motors
        self.port = port
        self.baudrate = baudrate
        self.current_limits = {}
        print(f"Mock DynamixelClient initialized: motors={motors}, port={port}, baudrate={baudrate}")
    
    def connect(self):
        print("Mock DynamixelClient connected")
    
    def sync_write(self, motor_ids: List[int], values: List[int], address: int, size: int):
        if address == 102:  # Current limit address
            for motor_id, value in zip(motor_ids, values):
                self.current_limits[motor_id] = value
                print(f"Mock: Set motor {motor_id} current limit to {value}mA")
        else:
            print(f"Mock: sync_write called with motor_ids={motor_ids}, values={values}, address={address}, size={size}")


class TestLeapNode:
    """Test version of LeapNode without hardware dependencies"""
    
    def __init__(self):
        self.motors = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        
        # Mock DynamixelClient
        self.dxl_client = MockDynamixelClient(self.motors, '/dev/ttyUSB0', 4000000)
        self.dxl_client.connect()
        
        # CSV file monitoring
        self.csv_file_path = 'current_limits.csv'
        self.last_modified_time = 0
        self.current_limits_dict = {}
        
        print("TestLeapNode initialized successfully")

    def load_current_limits_from_csv(self):
        """CSVファイルからcurrent limitを読み込み、ファイルが更新された場合のみモーターに設定する"""
        try:
            # ファイルの最終更新時刻をチェック
            current_modified_time = os.path.getmtime(self.csv_file_path)
            
            # ファイルが更新されていない場合は何もしない
            if current_modified_time <= self.last_modified_time:
                return False
            
            # CSVファイルを読み込み
            new_limits_dict = {}
            with open(self.csv_file_path, 'r') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    motor_id = int(row['motor_id'])
                    current_limit = int(row['current_limit'])
                    new_limits_dict[motor_id] = current_limit
            
            # 変更があった場合のみモーターに設定
            if new_limits_dict != self.current_limits_dict:
                print(f"\nCSV file updated at {datetime.fromtimestamp(current_modified_time)}")
                print("Setting new current limits:")
                
                for motor_id, current_limit in new_limits_dict.items():
                    if motor_id in self.motors:
                        self.dxl_client.sync_write([motor_id], [current_limit], 102, 2)
                        print(f"  Motor {motor_id}: {current_limit}mA")
                
                self.current_limits_dict = new_limits_dict
                self.last_modified_time = current_modified_time
                return True
            
            self.last_modified_time = current_modified_time
            return False
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return False


def test_csv_format():
    """Test CSV file format validation"""
    print("=== CSV Format Test ===")
    
    try:
        with open('current_limits.csv', 'r') as file:
            csv_reader = csv.DictReader(file)
            
            # Check if required columns exist
            required_columns = ['motor_id', 'current_limit', 'description']
            if not all(col in csv_reader.fieldnames for col in required_columns):
                print("ERROR: Missing required columns")
                return False
            
            # Check data
            motor_ids = set()
            for row in csv_reader:
                motor_id = int(row['motor_id'])
                current_limit = int(row['current_limit'])
                description = row['description']
                
                if motor_id in motor_ids:
                    print(f"ERROR: Duplicate motor_id {motor_id}")
                    return False
                
                motor_ids.add(motor_id)
                
                if current_limit < 0 or current_limit > 1000:
                    print(f"WARNING: Unusual current_limit {current_limit} for motor {motor_id}")
                
                print(f"Motor {motor_id}: {current_limit}mA - {description}")
            
            print(f"CSV format validation passed. Found {len(motor_ids)} motors.")
            return True
            
    except Exception as e:
        print(f"ERROR: CSV format validation failed: {e}")
        return False


def main():
    """Main function for continuous CSV monitoring"""
    print("=== CSV Loading Test - Continuous Monitoring ===")
    
    # Test CSV format first
    if not test_csv_format():
        print("CSV format validation failed. Exiting.")
        return
    
    # Initialize test node
    test_node = TestLeapNode()
    
    print("\nStarting continuous monitoring...")
    print("Modify current_limits.csv to test file update detection")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        while True:
            # Check for CSV updates
            updated = test_node.load_current_limits_from_csv()
            
            if not updated:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No file update detected")
            
            # Sleep for 1 second
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("\nFinal current limits in mock client:")
        for motor_id, limit in sorted(test_node.dxl_client.current_limits.items()):
            print(f"  Motor {motor_id}: {limit}mA")


if __name__ == "__main__":
    main() 