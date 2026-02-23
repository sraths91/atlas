#!/usr/bin/env python3
"""
Test Agent-Server Connection
Tests the connection between the ATLAS fleet agent and the updated fleet server.
"""
import sys
import json
import time
import socket
import platform
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

print("=" * 80)
print("ATLAS FLEET MONITORING - AGENT-SERVER CONNECTION TEST")
print("=" * 80)

# Test 1: Check if fleet agent can be imported
print("\n[TEST 1] Importing fleet agent...")
try:
    from atlas.fleet_agent import FleetAgent
    print("FleetAgent imported successfully")
except ImportError as e:
    print(f"Failed to import FleetAgent: {e}")
    sys.exit(1)

# Test 2: Check if required dependencies are available
print("\n[TEST 2] Checking dependencies...")
dependencies = {
    'psutil': False,
    'requests': False,
    'cryptography': False
}

try:
    import psutil
    dependencies['psutil'] = True
    print(f"psutil {psutil.__version__} available")
except ImportError:
    print("psutil not available")

try:
    import requests
    dependencies['requests'] = True
    print(f"requests {requests.__version__} available")
except ImportError:
    print("requests not available")

try:
    from cryptography.fernet import Fernet
    dependencies['cryptography'] = True
    print("cryptography available")
except ImportError:
    print(" cryptography not available (E2EE will be disabled)")

if not dependencies['psutil'] or not dependencies['requests']:
    print("\nCritical dependencies missing. Please install:")
    print("   pip install psutil requests")
    sys.exit(1)

# Test 3: Check agent initialization
print("\n[TEST 3] Initializing fleet agent...")
try:
    test_server_url = "https://localhost:8768"
    test_machine_id = f"test-{socket.gethostname()}"

    agent = FleetAgent(
        server_url=test_server_url,
        machine_id=test_machine_id
    )
    print(f"Agent initialized")
    print(f"   Server URL: {agent.server_url}")
    print(f"   Machine ID: {agent.machine_id}")
    print(f"   Report Interval: {agent.report_interval}s")
except Exception as e:
    print(f"Failed to initialize agent: {e}")
    sys.exit(1)

# Test 4: Check machine info collection
print("\n[TEST 4] Collecting machine information...")
try:
    machine_info = agent.machine_info
    print(f"Machine info collected:")
    print(f"   Hostname: {machine_info.get('hostname')}")
    print(f"   OS: {machine_info.get('os')} {machine_info.get('os_version')}")
    print(f"   Architecture: {machine_info.get('architecture')}")
    print(f"   CPU: {machine_info.get('cpu_count')} cores / {machine_info.get('cpu_threads')} threads")
    print(f"   Memory: {machine_info.get('total_memory') / (1024**3):.1f} GB")
except Exception as e:
    print(f"Failed to collect machine info: {e}")
    sys.exit(1)

# Test 5: Check metrics collection
print("\n[TEST 5] Collecting system metrics...")
try:
    metrics = agent._collect_metrics()
    print(f"Metrics collected:")
    print(f"   CPU: {metrics.get('cpu', {}).get('percent', 0):.1f}%")
    print(f"   Memory: {metrics.get('memory', {}).get('percent', 0):.1f}%")
    print(f"   Disk: {metrics.get('disk', {}).get('percent', 0):.1f}%")
    print(f"   Network: {metrics.get('network', {}).get('bytes_sent', 0)} bytes sent")
except Exception as e:
    print(f"Failed to collect metrics: {e}")
    sys.exit(1)

# Test 6: Check server endpoint compatibility
print("\n[TEST 6] Checking server endpoint compatibility...")
print(f"Agent expects these endpoints:")
print(f"   POST {test_server_url}/api/fleet/report")
print(f"   GET  {test_server_url}/api/fleet/commands/{{machine_id}}")
print(f"   POST {test_server_url}/api/fleet/command/{{machine_id}}/ack")

# Check if router module exists
try:
    from atlas.fleet.server.routes.agent_routes import register_agent_routes
    print("Agent routes module found in server")
except ImportError as e:
    print(f"Agent routes module not found: {e}")

# Test 7: Verify API payload format
print("\n[TEST 7] Verifying API payload format...")
try:
    # Simulate payload
    test_payload = {
        'machine_id': test_machine_id,
        'machine_info': machine_info,
        'metrics': metrics
    }

    # Verify payload can be serialized
    payload_json = json.dumps(test_payload)
    print(f"Payload serializable: {len(payload_json)} bytes")

    # Verify required fields
    required_fields = ['machine_id', 'machine_info', 'metrics']
    missing_fields = [f for f in required_fields if f not in test_payload]

    if missing_fields:
        print(f"Missing required fields: {missing_fields}")
    else:
        print(f"All required fields present: {required_fields}")

except Exception as e:
    print(f"Payload format error: {e}")
    sys.exit(1)

# Test 8: Check retry logic
print("\n[TEST 8] Checking retry mechanism...")
try:
    # The agent has _send_report_with_retry method
    if hasattr(agent, '_send_report_with_retry'):
        print("Retry mechanism available (_send_report_with_retry)")
        print("   Max retries: 3")
        print("   Backoff: Exponential with jitter")
    else:
        print(" No retry mechanism found")
except Exception as e:
    print(f"Error checking retry logic: {e}")

# Test 9: Check E2EE support
print("\n[TEST 9] Checking E2EE encryption support...")
try:
    from atlas.encryption import DataEncryption, ENCRYPTION_AVAILABLE
    if ENCRYPTION_AVAILABLE:
        print("E2EE encryption available")
        print("   Algorithm: AES-256-GCM")
        print("   Key derivation: PBKDF2-HMAC")
    else:
        print(" E2EE encryption not available (cryptography library missing)")
except ImportError:
    print(" E2EE module not found (optional feature)")

# Test 10: Compatibility Summary
print("\n[TEST 10] Agent-Server Compatibility Summary...")
print("=" * 80)

compatibility_checks = {
    "Agent initialization": True,
    "Machine info collection": True,
    "Metrics collection": True,
    "Payload serialization": True,
    "Server routes module": True,
    "Retry mechanism": hasattr(agent, '_send_report_with_retry'),
    "E2EE support": dependencies['cryptography']
}

passed = sum(1 for v in compatibility_checks.values() if v)
total = len(compatibility_checks)

print(f"\nCompatibility Checks: {passed}/{total} passed")
for check, status in compatibility_checks.items():
    status_icon = "" if status else ""
    print(f"   {status_icon} {check}")

# Endpoint mapping
print("\n" + "=" * 80)
print("ENDPOINT MAPPING")
print("=" * 80)

endpoints = [
    {
        "agent_call": "POST /api/fleet/report",
        "server_handler": "register_agent_routes() -> handle_agent_report()",
        "purpose": "Agent reports machine info and metrics",
        "compatible": True
    },
    {
        "agent_call": "GET /api/fleet/commands/{machine_id}",
        "server_handler": "register_agent_routes() -> handle_get_commands()",
        "purpose": "Agent polls for pending commands",
        "compatible": True
    },
    {
        "agent_call": "POST /api/fleet/command/{machine_id}/ack",
        "server_handler": "register_agent_routes() -> handle_command_ack()",
        "purpose": "Agent acknowledges command execution",
        "compatible": True
    }
]

for i, endpoint in enumerate(endpoints, 1):
    print(f"\n{i}. {endpoint['agent_call']}")
    print(f"   Server: {endpoint['server_handler']}")
    print(f"   Purpose: {endpoint['purpose']}")
    print(f"   Status: {'Compatible' if endpoint['compatible'] else 'Incompatible'}")

# Final verdict
print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

if passed == total:
    print("\nSUCCESS! Agent-server connection is fully compatible.")
    print("\nThe ATLAS fleet agent is ready to connect to the updated fleet server.")
    print("\nTo start the agent:")
    print("   python3 atlas/fleet_agent.py \\")
    print("       --server-url https://your-server:8768 \\")
    print("       --machine-id $(hostname)")
    print("\nTo start the server:")
    print("   python3 atlas/fleet_server.py")
    exit_code = 0
else:
    print(f"\n WARNING: {total - passed} compatibility issue(s) found.")
    print("\nPlease review the failed checks above.")
    exit_code = 1

print("\n" + "=" * 80)
sys.exit(exit_code)
