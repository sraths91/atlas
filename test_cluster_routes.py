"""
Quick test for cluster routes extraction
"""
import sys
sys.path.insert(0, '/Users/samraths/CascadeProjects/windsurf-project-2-refactored')

from atlas.fleet.server.router import FleetRouter
from atlas.fleet.server.routes.cluster_routes import register_cluster_routes
from atlas.fleet.server.auth import FleetAuthManager

print("Testing cluster routes...")

# Create instances
router = FleetRouter()
auth_manager = FleetAuthManager()
cluster_manager = None  # Standalone mode (no cluster)

# Register cluster routes
register_cluster_routes(router, cluster_manager, auth_manager)

# Check registered routes
routes = router.list_routes()
print(f"Registered {len(routes)} cluster routes:")
for method, pattern in routes:
    print(f"   - {method} {pattern}")

# Expected routes:
# GET /api/fleet/cluster/status
# GET /api/fleet/cluster/health
# GET /api/fleet/cluster/nodes
# GET /api/fleet/cluster/health-check

assert len(routes) == 4, f"Expected 4 routes, got {len(routes)}"
print("\nCluster routes test passed!")
