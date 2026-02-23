#!/usr/bin/env python3
"""
Import speed test logs from JSON file into the speed test aggregator database
"""

import json
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from atlas.fleet_speedtest_aggregator import SpeedTestAggregator


def import_from_json_file(json_file_path: str):
    """Import speed test logs from a JSON file"""
    
    print(f"📂 Reading speed test logs from: {json_file_path}")
    
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid JSON file: {e}")
        return False
    
    # Handle different JSON formats
    logs = []
    
    if isinstance(data, list):
        logs = data
    elif isinstance(data, dict):
        if 'logs' in data:
            logs = data['logs']
        elif 'results' in data:
            logs = data['results']
        else:
            logs = [data]  # Single log entry
    
    print(f"Found {len(logs)} log entries")
    
    # Filter for speedtest logs
    speedtest_logs = []
    for log in logs:
        if isinstance(log, dict):
            # Check if it's a speedtest log
            if log.get('widget_type') == 'speedtest' or 'download' in str(log).lower():
                speedtest_logs.append(log)
    
    print(f"Found {len(speedtest_logs)} speed test entries")
    
    if not speedtest_logs:
        print("No speed test data found in the file")
        print("\nExpected format:")
        print("  - Array of widget logs with widget_type='speedtest'")
        print("  - Or direct speed test result objects")
        return False
    
    # Import into aggregator
    aggregator = SpeedTestAggregator()
    imported_count = 0
    error_count = 0
    
    for log in speedtest_logs:
        try:
            # Extract machine_id and data
            if 'machine_id' in log:
                machine_id = log['machine_id']
                
                # Get the speed test data
                if 'data_json' in log:
                    if isinstance(log['data_json'], str):
                        speedtest_data = json.loads(log['data_json'])
                    else:
                        speedtest_data = log['data_json']
                elif 'data' in log:
                    speedtest_data = log['data']
                else:
                    speedtest_data = log
                
                # Store the result
                aggregator.store_speedtest_result(machine_id, speedtest_data)
                imported_count += 1
                
            elif 'download' in log or 'upload' in log:
                # Direct speed test result without machine_id
                # Try to infer machine_id
                machine_id = log.get('machine', log.get('host', 'Unknown'))
                aggregator.store_speedtest_result(machine_id, log)
                imported_count += 1
                
        except Exception as e:
            print(f" Error importing log: {e}")
            error_count += 1
    
    print(f"\nSuccessfully imported {imported_count} speed test results")
    if error_count > 0:
        print(f" {error_count} entries had errors")
    
    return imported_count > 0


def export_instructions():
    """Print instructions for exporting speed test data"""
    print("\n" + "="*60)
    print("HOW TO EXPORT SPEED TEST DATA FROM DASHBOARD")
    print("="*60)
    print("\n1. Open your Fleet Dashboard:")
    print("   https://192.168.50.191:8768/dashboard")
    print("\n2. Click the hamburger menu () in the top right")
    print("\n3. Select: Export Speedtest Logs")
    print("\n4. Save the file (e.g., fleet_speedtest_logs.json)")
    print("\n5. Run this script with the file:")
    print("   python3 import_speedtest_logs.py /path/to/fleet_speedtest_logs.json")
    print("\n" + "="*60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No file specified")
        print("\nUsage:")
        print("  python3 import_speedtest_logs.py <json_file>")
        print("\nExample:")
        print("  python3 import_speedtest_logs.py ~/Downloads/fleet_speedtest_logs.json")
        export_instructions()
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not Path(json_file).exists():
        print(f"File not found: {json_file}")
        export_instructions()
        sys.exit(1)
    
    success = import_from_json_file(json_file)
    
    if success:
        print("\nImport complete!")
        print("\nRefresh your dashboard to see the imported speed test data.")
        sys.exit(0)
    else:
        print("\nImport failed")
        export_instructions()
        sys.exit(1)
