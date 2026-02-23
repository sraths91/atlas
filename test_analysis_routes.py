"""
Quick test for analysis routes extraction
"""
import sys
sys.path.insert(0, '/Users/samraths/CascadeProjects/windsurf-project-2-refactored')

from atlas.fleet.server.router import FleetRouter
from atlas.fleet.server.routes.analysis_routes import register_analysis_routes
from atlas.fleet.server.data_store import FleetDataStore
from atlas.fleet.server.auth import FleetAuthManager

print("Testing analysis routes...")

# Create instances
router = FleetRouter()
data_store = FleetDataStore()
auth_manager = FleetAuthManager()

# Register analysis routes
register_analysis_routes(router, data_store, auth_manager)

# Check registered routes
routes = router.list_routes()
print(f"Registered {len(routes)} analysis routes:")
for method, pattern in routes:
    print(f"   - {method} {pattern}")

# Expected 10 routes:
# GET /api/fleet/speedtest/summary
# GET /api/fleet/speedtest/machine
# GET /api/fleet/speedtest/comparison
# GET /api/fleet/speedtest/anomalies
# GET /api/fleet/speedtest/recent
# GET /api/fleet/speedtest/recent20
# GET /api/fleet/speedtest/subnet
# GET /api/fleet/network-analysis
# GET /api/fleet/network-analysis/{machine_id}
# GET /api/fleet/widget-logs

assert len(routes) == 10, f"Expected 10 routes, got {len(routes)}"
print("\nAnalysis routes test passed!")
print(f"   SpeedTest routes: 7")
print(f"   Network analysis routes: 2")
print(f"   Widget logs route: 1")
