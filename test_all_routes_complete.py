"""
Comprehensive test for ALL route modules extraction
Phase 4 Stage 4 - Complete Integration Test
"""
import sys
sys.path.insert(0, '/Users/samraths/CascadeProjects/windsurf-project-2-refactored')

from atlas.fleet.server.router import FleetRouter
from atlas.fleet.server.data_store import FleetDataStore
from atlas.fleet.server.auth import FleetAuthManager

# Import all route registration functions
from atlas.fleet.server.routes.agent_routes import register_agent_routes
from atlas.fleet.server.routes.dashboard_routes import register_dashboard_routes
from atlas.fleet.server.routes.machine_routes import register_machine_routes
from atlas.fleet.server.routes.cluster_routes import register_cluster_routes
from atlas.fleet.server.routes.analysis_routes import register_analysis_routes
from atlas.fleet.server.routes.admin_routes import register_admin_routes
from atlas.fleet.server.routes.ui_routes import register_ui_routes
from atlas.fleet.server.routes.e2ee_routes import register_e2ee_routes
from atlas.fleet.server.routes.package_routes import register_package_routes

print("=" * 80)
print("COMPREHENSIVE ROUTE EXTRACTION TEST")
print("=" * 80)

# Create instances
router = FleetRouter()
data_store = FleetDataStore()
auth_manager = FleetAuthManager()
encryption = None  # Optional
cluster_manager = None  # Optional (standalone mode)

# Register all routes
print("\nRegistering all route modules...")

register_agent_routes(router, data_store, auth_manager, encryption)
print("   agent_routes registered")

register_dashboard_routes(router, data_store, auth_manager)
print("   dashboard_routes registered")

register_machine_routes(router, data_store, auth_manager)
print("   machine_routes registered")

register_cluster_routes(router, cluster_manager, auth_manager)
print("   cluster_routes registered")

register_analysis_routes(router, data_store, auth_manager)
print("   analysis_routes registered")

register_admin_routes(router, auth_manager, encryption)
print("   admin_routes registered")

register_ui_routes(router, auth_manager)
print("   ui_routes registered")

register_e2ee_routes(router, data_store, auth_manager, encryption)
print("   e2ee_routes registered")

register_package_routes(router, data_store, auth_manager, cluster_manager)
print("   package_routes registered")

# Get all registered routes
routes = router.list_routes()

print(f"\nTotal routes registered: {len(routes)}")
print("=" * 80)

# Categorize routes by module
route_categories = {
    'Agent': [],
    'Dashboard': [],
    'Machine': [],
    'Cluster': [],
    'Analysis': [],
    'Admin': [],
    'UI': [],
    'E2EE': [],
    'Package': []
}

for method, pattern in routes:
    # Check from most specific to least specific
    if pattern == '/api/fleet/report' or (pattern.startswith('/api/fleet/command') and method == 'POST') or (pattern == '/api/fleet/widget-logs' and method == 'POST'):
        route_categories['Agent'].append((method, pattern))
    elif pattern.startswith('/api/fleet/commands/{'):
        route_categories['Agent'].append((method, pattern))
    elif pattern.startswith('/api/fleet/machine/{') or pattern.startswith('/api/fleet/history/{') or pattern.startswith('/api/fleet/recent-commands/{'):
        route_categories['Machine'].append((method, pattern))
    elif pattern in ['/api/fleet/machines', '/api/fleet/summary', '/api/fleet/server-resources', '/api/fleet/storage']:
        route_categories['Dashboard'].append((method, pattern))
    elif pattern.startswith('/api/fleet/cluster/'):
        route_categories['Cluster'].append((method, pattern))
    elif 'speedtest' in pattern or pattern.startswith('/api/fleet/network-analysis') or (pattern == '/api/fleet/widget-logs' and method == 'GET'):
        route_categories['Analysis'].append((method, pattern))
    elif 'encryption' in pattern or pattern == '/api/fleet/key-rotation-status':
        route_categories['E2EE'].append((method, pattern))
    elif pattern in ['/', '/login', '/logout', '/dashboard', '/settings', '/password-reset', '/reset-password', '/api/fleet/current-user', '/api/fleet/users', '/api/fleet/users/check-password-update', '/api/fleet/logout']:
        route_categories['UI'].append((method, pattern))
    elif pattern.startswith('/api/fleet/users/') or pattern in ['/api/fleet/cert-status', '/api/fleet/cert-info', '/api/fleet/update-certificate', '/api/fleet/verify-and-get-key', '/api/fleet/regenerate-key', '/api/fleet/e2ee-status']:
        route_categories['Admin'].append((method, pattern))
    elif 'package' in pattern or 'installer' in pattern or 'loadbalancer' in pattern or pattern == '/api/fleet/storage-info' or 'acme-challenge' in pattern:
        route_categories['Package'].append((method, pattern))

# Print categorized routes
print("\nRoutes by Module:")
print("=" * 80)

for category, cat_routes in route_categories.items():
    if cat_routes:
        print(f"\n{category} Routes ({len(cat_routes)}):")
        for method, pattern in sorted(cat_routes):
            print(f"   {method:6} {pattern}")

# Verify counts
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

expected_counts = {
    'Agent': 4,
    'Dashboard': 4,
    'Machine': 3,
    'Cluster': 4,
    'Analysis': 10,
    'Admin': 10,
    'UI': 12,
    'E2EE': 5,
    'Package': 7
}

all_passed = True
for category, expected in expected_counts.items():
    actual = len(route_categories[category])
    status = "" if actual == expected else ""
    if actual != expected:
        all_passed = False
    print(f"{status} {category:12} routes: {actual:2}/{expected:2}")

print("=" * 80)

# Calculate HTTP method breakdown
get_routes = [r for r in routes if r[0] == 'GET']
post_routes = [r for r in routes if r[0] == 'POST']

print(f"\n📈 HTTP Method Breakdown:")
print(f"   GET routes:  {len(get_routes)}")
print(f"   POST routes: {len(post_routes)}")
print(f"   Total:       {len(routes)}")

# Final assertions
assert len(routes) == 59, f"Expected 59 routes, got {len(routes)}"
assert all_passed, "Route count mismatch in one or more categories"

print("\n" + "=" * 80)
print("ALL ROUTES EXTRACTED SUCCESSFULLY!")
print("=" * 80)
print(f"9 route modules created")
print(f"59 routes registered and tested")
print(f"All route counts verified")
print(f"Phase 4 Stage 4 COMPLETE")
print("=" * 80)
