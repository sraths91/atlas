#!/bin/bash
# Restart Fleet Server with HTTPS/TLS fix

echo "=== Restarting Fleet Server with HTTPS Fix ==="
echo ""

# Kill all Python processes
echo "Stopping all services..."
killall -9 Python 2>/dev/null
sleep 3

# Check if ports are free
if lsof -i :8768 >/dev/null 2>&1; then
    echo "⚠️  Port 8768 still in use, attempting to free it..."
    lsof -i :8768 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null
    sleep 2
fi

if lsof -i :8767 >/dev/null 2>&1; then
    echo "⚠️  Port 8767 still in use, attempting to free it..."
    lsof -i :8767 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null
    sleep 2
fi

echo ""
echo "Starting Fleet Server with HTTPS..."
cd /Users/samraths/CascadeProjects/windsurf-project-2
python3 -m atlas.fleet_server --port 8768 --host 0.0.0.0 > /tmp/fleet_https.log 2>&1 &
FLEET_PID=$!

sleep 5

# Check if Fleet Server started
if lsof -i :8768 >/dev/null 2>&1; then
    echo "✅ Fleet Server started (PID: $FLEET_PID)"
    echo ""
    
    # Test HTTPS connection
    echo "Testing HTTPS connection..."
    if curl -k -s https://localhost:8768/ | head -1 | grep -q "DOCTYPE"; then
        echo "✅ HTTPS is working!"
    else
        echo "⚠️  HTTPS test failed, checking logs..."
        tail -20 /tmp/fleet_https.log
    fi
else
    echo "❌ Fleet Server failed to start"
    echo "Checking logs..."
    tail -20 /tmp/fleet_https.log
    exit 1
fi

echo ""
echo "Starting Agent with HTTPS..."
python3 -m atlas.live_widgets --port 8767 --fleet-server https://localhost:8768 --api-key sQ2X6577YL24Ev0lQFQoAwsiKD73SLcQ_VbG0ZUpbWU > /tmp/agent_https.log 2>&1 &
AGENT_PID=$!

sleep 5

# Check if Agent started
if lsof -i :8767 >/dev/null 2>&1; then
    echo "✅ Agent started (PID: $AGENT_PID)"
    
    # Wait a bit for connection
    sleep 10
    
    # Check agent logs for connection errors
    if grep -q "SSL\|TLS.*error\|wrong version" /tmp/agent_https.log; then
        echo "⚠️  Agent has SSL connection issues:"
        grep -i "ssl\|tls\|error" /tmp/agent_https.log | tail -5
    else
        echo "✅ Agent appears to be connected"
    fi
else
    echo "❌ Agent failed to start"
    tail -20 /tmp/agent_https.log
    exit 1
fi

echo ""
echo "=== Status ==="
echo "Fleet Server: https://localhost:8768/dashboard"
echo "Agent:        http://localhost:8767"
echo ""
echo "Fleet Log:    tail -f /tmp/fleet_https.log"
echo "Agent Log:    tail -f /tmp/agent_https.log"
echo ""
echo "Credentials:"
echo "  Username: admin"
echo "  Password: AtlasShrugged2025!"
