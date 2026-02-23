#!/bin/bash

# Multi-Tenant Fleet Dashboard Demo
# Shows 3 different organizations running simultaneously

echo "🏢 Multi-Tenant Fleet Dashboard Demo"
echo "======================================"
echo ""
echo "This demo will start 3 separate fleet dashboards:"
echo "  • Acme Corp (Port 8768, Green theme)"
echo "  • Beta Systems (Port 8769, Cyan theme)"
echo "  • Gamma Networks (Port 8770, Magenta theme)"
echo ""

# Kill any existing processes
echo "Cleaning up..."
pkill -f "fleet_server"
pkill -f "fleet_agent"
sleep 2

# Create temp directory for configs
TEMP_DIR=$(mktemp -d)
echo "Using temp directory: $TEMP_DIR"

# Create Organization A config (Acme Corp)
cat > "$TEMP_DIR/acme-config.json" << 'EOF'
{
  "organization": {
    "name": "Acme Corp",
    "id": "acme-corp-001",
    "contact": "admin@acme.com"
  },
  "server": {
    "port": 8768,
    "host": "0.0.0.0",
    "api_key": "acme-secret-key-12345",
    "history_size": 1000
  },
  "agent": {
    "report_interval": 5,
    "retry_interval": 30,
    "timeout": 5
  },
  "branding": {
    "primary_color": "#00ff00",
    "secondary_color": "#0a0a0a",
    "dashboard_title": "Acme Corp Fleet"
  }
}
EOF

# Create Organization B config (Beta Systems)
cat > "$TEMP_DIR/beta-config.json" << 'EOF'
{
  "organization": {
    "name": "Beta Systems",
    "id": "beta-systems-002",
    "contact": "admin@beta.com"
  },
  "server": {
    "port": 8769,
    "host": "0.0.0.0",
    "api_key": "beta-secret-key-67890",
    "history_size": 1000
  },
  "agent": {
    "report_interval": 5,
    "retry_interval": 30,
    "timeout": 5
  },
  "branding": {
    "primary_color": "#00ffff",
    "secondary_color": "#0a0a0a",
    "dashboard_title": "Beta Systems Fleet"
  }
}
EOF

# Create Organization C config (Gamma Networks)
cat > "$TEMP_DIR/gamma-config.json" << 'EOF'
{
  "organization": {
    "name": "Gamma Networks",
    "id": "gamma-networks-003",
    "contact": "admin@gamma.com"
  },
  "server": {
    "port": 8770,
    "host": "0.0.0.0",
    "api_key": "gamma-secret-key-abcde",
    "history_size": 1000
  },
  "agent": {
    "report_interval": 5,
    "retry_interval": 30,
    "timeout": 5
  },
  "branding": {
    "primary_color": "#ff00ff",
    "secondary_color": "#0a0a0a",
    "dashboard_title": "Gamma Networks Fleet"
  }
}
EOF

echo ""
echo "Starting servers..."
echo ""

# Start Acme Corp server
python3 -m atlas.fleet_server --config "$TEMP_DIR/acme-config.json" > /dev/null 2>&1 &
ACME_PID=$!
sleep 2
echo "✅ Acme Corp server started (PID: $ACME_PID, Port: 8768)"

# Start Beta Systems server
python3 -m atlas.fleet_server --config "$TEMP_DIR/beta-config.json" > /dev/null 2>&1 &
BETA_PID=$!
sleep 2
echo "✅ Beta Systems server started (PID: $BETA_PID, Port: 8769)"

# Start Gamma Networks server
python3 -m atlas.fleet_server --config "$TEMP_DIR/gamma-config.json" > /dev/null 2>&1 &
GAMMA_PID=$!
sleep 2
echo "✅ Gamma Networks server started (PID: $GAMMA_PID, Port: 8770)"

echo ""
echo "Starting agents for each organization..."
echo ""

# Start 2 agents for Acme Corp
for i in {1..2}; do
    python3 -m atlas.fleet_agent \
        --server http://localhost:8768 \
        --machine-id "Acme-Mac-$i" \
        --api-key "acme-secret-key-12345" \
        --interval 5 \
        > /dev/null 2>&1 &
done
echo "  ✅ 2 agents for Acme Corp"

# Start 2 agents for Beta Systems
for i in {1..2}; do
    python3 -m atlas.fleet_agent \
        --server http://localhost:8769 \
        --machine-id "Beta-Mac-$i" \
        --api-key "beta-secret-key-67890" \
        --interval 5 \
        > /dev/null 2>&1 &
done
echo "  ✅ 2 agents for Beta Systems"

# Start 2 agents for Gamma Networks
for i in {1..2}; do
    python3 -m atlas.fleet_agent \
        --server http://localhost:8770 \
        --machine-id "Gamma-Mac-$i" \
        --api-key "gamma-secret-key-abcde" \
        --interval 5 \
        > /dev/null 2>&1 &
done
echo "  ✅ 2 agents for Gamma Networks"

sleep 3

echo ""
echo "======================================"
echo "✅ Multi-Tenant Demo Ready!"
echo "======================================"
echo ""
echo "🏢 Acme Corp Dashboard:"
echo "   http://localhost:8768/dashboard"
echo "   Theme: Green | Machines: 2"
echo ""
echo "🏢 Beta Systems Dashboard:"
echo "   http://localhost:8769/dashboard"
echo "   Theme: Cyan | Machines: 2"
echo ""
echo "🏢 Gamma Networks Dashboard:"
echo "   http://localhost:8770/dashboard"
echo "   Theme: Magenta | Machines: 2"
echo ""
echo "Each organization has:"
echo "  ✅ Isolated data"
echo "  ✅ Unique API keys"
echo "  ✅ Custom branding"
echo "  ✅ Independent configuration"
echo ""
echo "Press Ctrl+C to stop all services"
echo "======================================"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping all services..."
    pkill -f "fleet_server"
    pkill -f "fleet_agent"
    rm -rf "$TEMP_DIR"
    echo "✅ All services stopped"
    exit 0
}

trap cleanup INT

# Keep running
while true; do
    sleep 1
done
