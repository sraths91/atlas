#!/bin/bash

# Fleet Dashboard Test Script
# Starts server and multiple simulated agents for testing

echo "🚀 Starting Fleet Dashboard Test Environment"
echo "=============================================="
echo ""

# Kill any existing processes
echo "Cleaning up existing processes..."
pkill -f "fleet_server"
pkill -f "fleet_agent"
sleep 2

# Start fleet server
echo "Starting fleet server on port 8768..."
python3 -m atlas.fleet_server --port 8768 &
SERVER_PID=$!
sleep 3

# Check if server started
if ! curl -s http://localhost:8768/api/fleet/summary > /dev/null; then
    echo "❌ Failed to start fleet server"
    exit 1
fi

echo "✅ Fleet server started (PID: $SERVER_PID)"
echo ""

# Start multiple test agents
echo "Starting test agents..."
for i in {1..3}; do
    python3 -m atlas.fleet_agent \
        --server http://localhost:8768 \
        --machine-id "TestMac-$i" \
        --interval 5 \
        > /dev/null 2>&1 &
    echo "  ✅ Agent $i started (TestMac-$i)"
    sleep 1
done

echo ""
echo "=============================================="
echo "✅ Fleet Dashboard is ready!"
echo ""
echo "📊 Dashboard: http://localhost:8768/dashboard"
echo "🔌 API: http://localhost:8768/api/fleet/summary"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=============================================="
echo ""

# Wait for interrupt
trap "echo ''; echo 'Stopping services...'; pkill -f 'fleet_server'; pkill -f 'fleet_agent'; echo '✅ All services stopped'; exit 0" INT

# Keep script running
while true; do
    sleep 1
done
