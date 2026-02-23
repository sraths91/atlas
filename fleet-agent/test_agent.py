#!/usr/bin/env python3
"""
Test script for Fleet Agent
"""
import sys
import time
import json
from fleet_agent import FleetAgent

def test_agent():
    print("Fleet Agent Test\n" + "="*50)
    
    # Create test configuration
    test_config = {
        'server_url': 'http://localhost:8768',
        'api_key': 'test-key',
        'interval': 5
    }
    
    # Create config file
    config_file = '/tmp/fleet-agent-test-config.json'
    with open(config_file, 'w') as f:
        json.dump(test_config, f)
    
    print(f"\nTest configuration:")
    print(f"  Server: {test_config['server_url']}")
    print(f"  Interval: {test_config['interval']}s")
    print(f"  Config file: {config_file}\n")
    
    # Initialize agent
    print("Initializing agent...")
    agent = FleetAgent(
        server_url=test_config['server_url'],
        api_key=test_config['api_key']
    )
    
    # Test metrics collection
    print("\nCollecting metrics...")
    metrics = agent._collect_metrics()
    
    print("\nCollected metrics:")
    print(f"  CPU: {metrics.get('cpu', {}).get('percent', 'N/A')}%")
    print(f"  Memory: {metrics.get('memory', {}).get('percent', 'N/A')}%")
    print(f"  Disk: {metrics.get('disk', {}).get('percent', 'N/A')}%")
    
    # Test agent status
    status = agent.get_status()
    print("\nAgent status:")
    print(f"  Machine ID: {status['machine_id']}")
    print(f"  Server URL: {status['server_url']}")
    print(f"  Running: {status['running']}")
    
    # Start agent for a short test
    print("\nStarting agent for 10 second test...")
    print("(Note: Connection will fail if server not running)")
    agent.start(interval=5)
    
    time.sleep(10)
    
    agent.stop()
    print("\n" + "="*50)
    print("Test completed successfully!")
    print("\nTo run with actual server:")
    print("  fleet-agent --server http://your-server:8768 --api-key KEY")

if __name__ == '__main__':
    try:
        test_agent()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
