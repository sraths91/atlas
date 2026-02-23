"""
Quick test for admin routes extraction
"""
import sys
sys.path.insert(0, '/Users/samraths/CascadeProjects/windsurf-project-2-refactored')

from atlas.fleet.server.router import FleetRouter
from atlas.fleet.server.routes.admin_routes import register_admin_routes
from atlas.fleet.server.auth import FleetAuthManager

print("Testing admin routes...")

# Create instances
router = FleetRouter()
auth_manager = FleetAuthManager()
encryption = None  # No encryption for test

# Register admin routes
register_admin_routes(router, auth_manager, encryption)

# Check registered routes
routes = router.list_routes()
print(f"Registered {len(routes)} admin routes:")

# Categorize routes
user_routes = [(m, p) for m, p in routes if '/users/' in p]
cert_routes = [(m, p) for m, p in routes if 'cert' in p]
key_routes = [(m, p) for m, p in routes if 'key' in p or 'e2ee' in p]

print(f"\n   User Management routes ({len(user_routes)}):")
for method, pattern in user_routes:
    print(f"      {method} {pattern}")

print(f"\n   Certificate routes ({len(cert_routes)}):")
for method, pattern in cert_routes:
    print(f"      {method} {pattern}")

print(f"\n   API Key & E2EE routes ({len(key_routes)}):")
for method, pattern in key_routes:
    print(f"      {method} {pattern}")

# Expected 10 routes:
# User Management: create, change-password, delete, force-update-password (4)
# Certificates: cert-status, cert-info, update-certificate (3)
# API Keys: verify-and-get-key, regenerate-key (2)
# E2EE: e2ee-status (1)

assert len(routes) == 10, f"Expected 10 routes, got {len(routes)}"
assert len(user_routes) == 4, f"Expected 4 user routes, got {len(user_routes)}"
assert len(cert_routes) == 3, f"Expected 3 cert routes, got {len(cert_routes)}"
assert len(key_routes) == 3, f"Expected 3 key/e2ee routes, got {len(key_routes)}"

print("\nAdmin routes test passed!")
print(f"   Total: {len(routes)} routes")
