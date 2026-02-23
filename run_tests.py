#!/usr/bin/env python3
"""
Test Runner for ATLAS Fleet Monitoring Platform

Phase 8: Testing Infrastructure

Runs all test suites and generates comprehensive reports.
"""
import sys
import subprocess
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

print("=" * 80)
print("ATLAS FLEET MONITORING PLATFORM - TEST SUITE")
print("=" * 80)

# Check if pytest is installed
try:
    import pytest
    print(f"\npytest {pytest.__version__} installed")
except ImportError:
    print("\npytest not installed. Install with: pip install pytest")
    sys.exit(1)

# Test configurations
test_configs = [
    {
        "name": "Unit Tests",
        "marker": "unit",
        "description": "Fast, isolated unit tests",
    },
    {
        "name": "Integration Tests",
        "marker": "integration",
        "description": "Component interaction tests",
    },
    {
        "name": "Security Tests",
        "marker": "security",
        "description": "Security and vulnerability tests",
    },
]

print("\n" + "=" * 80)
print("TEST SUITE OVERVIEW")
print("=" * 80)

for config in test_configs:
    print(f"\n{config['name']}")
    print(f"  Marker: -m {config['marker']}")
    print(f"  Description: {config['description']}")

print("\n" + "=" * 80)
print("RUNNING TESTS")
print("=" * 80)

results = {}
total_passed = 0
total_failed = 0

# Run each test suite
for config in test_configs:
    print(f"\n{'=' * 80}")
    print(f"Running: {config['name']}")
    print(f"{'=' * 80}\n")

    # Run pytest with specific marker
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-m",
            config["marker"],
            "tests/",
        ],
        capture_output=False,
        text=True,
    )

    results[config["name"]] = {
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
    }

    if result.returncode == 0:
        total_passed += 1
    else:
        total_failed += 1

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

for test_name, result in results.items():
    status = "PASSED" if result["passed"] else "FAILED"
    print(f"{test_name}: {status}")

print("\n" + "=" * 80)
print("OVERALL RESULTS")
print("=" * 80)
print(f"Test Suites Passed: {total_passed}/{len(test_configs)}")
print(f"Test Suites Failed: {total_failed}/{len(test_configs)}")

if total_failed == 0:
    print("\nALL TEST SUITES PASSED!")
    sys.exit(0)
else:
    print(f"\n {total_failed} TEST SUITE(S) FAILED")
    sys.exit(1)
