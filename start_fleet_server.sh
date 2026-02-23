#!/bin/bash
# Fleet Server Startup Script with SSL and E2EE

export FLEET_SSL_CERT=/Users/samraths/CascadeProjects/windsurf-project-2-refactored/fleet-server.crt
export FLEET_SSL_KEY=/Users/samraths/CascadeProjects/windsurf-project-2-refactored/fleet-server.key
export FLEET_ENCRYPTION_KEY="WAg5cS+XVux6qQDddvZs+zsPSLv110TbBUTqeuZWm44="

cd /Users/samraths/CascadeProjects/windsurf-project-2-refactored
exec python3 -m atlas.fleet_server --port 8778 --host 0.0.0.0
