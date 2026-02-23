"""
Quick test for UI routes extraction
"""
import sys
sys.path.insert(0, '/Users/samraths/CascadeProjects/windsurf-project-2-refactored')

from atlas.fleet.server.router import FleetRouter
from atlas.fleet.server.routes.ui_routes import register_ui_routes
from atlas.fleet.server.auth import FleetAuthManager

print("Testing UI routes...")

# Create instances
router = FleetRouter()
auth_manager = FleetAuthManager()

# Register UI routes
register_ui_routes(router, auth_manager)

# Check registered routes
routes = router.list_routes()
print(f"Registered {len(routes)} UI routes:")
for method, pattern in routes:
    print(f"   - {method} {pattern}")

# Expected 12 routes:
# GET /
# GET /login
# GET /logout
# GET /dashboard
# GET /settings
# GET /password-reset
# POST /login
# POST /reset-password
# POST /api/fleet/logout
# GET /api/fleet/current-user
# GET /api/fleet/users/check-password-update
# GET /api/fleet/users

# Categorize routes
page_routes = [(method, pattern) for method, pattern in routes
               if method == 'GET' and not pattern.startswith('/api/')]
auth_routes = [(method, pattern) for method, pattern in routes
               if pattern in ['/login', '/reset-password', '/api/fleet/logout'] and method == 'POST']
user_info_routes = [(method, pattern) for method, pattern in routes
                    if pattern.startswith('/api/fleet/') and ('user' in pattern or 'current' in pattern)]

assert len(routes) == 12, f"Expected 12 routes, got {len(routes)}"
assert len(page_routes) == 6, f"Expected 6 page routes, got {len(page_routes)}"
assert len(auth_routes) == 3, f"Expected 3 auth routes, got {len(auth_routes)}"
assert len(user_info_routes) == 3, f"Expected 3 user info routes, got {len(user_info_routes)}"

print("\nUI routes test passed!")
print(f"   Page routes (GET): {len(page_routes)}")
print(f"   Auth routes (POST): {len(auth_routes)}")
print(f"   User info routes (GET): {len(user_info_routes)}")
