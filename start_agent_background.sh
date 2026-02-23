#!/bin/bash
# Start the ATLAS agent as a background process without Dock icon

cd /Users/samraths/CascadeProjects/windsurf-project-2

# Get API key from config
API_KEY=$(python3 -c "from atlas.fleet_config import FleetConfig; c = FleetConfig(); print(c.get('server.api_key', ''))" 2>/dev/null)

if [ -z "$API_KEY" ]; then
    echo "❌ Failed to get API key. Run set_credentials.py first."
    exit 1
fi

# Kill any existing agent
lsof -i :8767 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2

# Start agent in background with nohup (no Dock icon)
nohup python3 -m atlas.live_widgets \
    --port 8767 \
    --fleet-server https://localhost:8768 \
    --api-key "$API_KEY" \
    > /tmp/atlas-agent.log 2>&1 &

echo "✅ Agent started in background (PID: $!)"
echo "   No Dock icon"
echo "   Log: tail -f /tmp/atlas-agent.log"
