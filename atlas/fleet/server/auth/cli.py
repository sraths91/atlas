#!/usr/bin/env python3
"""
ATLAS Fleet Authentication - CLI Management Tools

Command-line interface for managing:
- API Keys (create, list, revoke, rotate)
- OAuth2 Clients (register, list, deactivate)
- Scopes (list available scopes)
- Token cleanup

Usage:
    python -m atlas.fleet.server.auth.cli api-key create --name "agent-1" --scopes metrics:write
    python -m atlas.fleet.server.auth.cli api-key list
    python -m atlas.fleet.server.auth.cli api-key revoke <key_id>
    python -m atlas.fleet.server.auth.cli oauth create --name "My App" --redirect-uri https://example.com/callback
    python -m atlas.fleet.server.auth.cli oauth list
    python -m atlas.fleet.server.auth.cli scopes list
    python -m atlas.fleet.server.auth.cli cleanup
"""
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List


def get_db_path() -> str:
    """Get the default database path"""
    return str(Path.home() / '.fleet-data' / 'users.db')


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display"""
    if not dt_str:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return dt_str


def print_table(headers: List[str], rows: List[List[str]], widths: Optional[List[int]] = None):
    """Print a formatted table"""
    if not widths:
        widths = [max(len(str(row[i])) for row in [headers] + rows) + 2 for i in range(len(headers))]

    # Header
    header_row = ''.join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_row)
    print('-' * len(header_row))

    # Rows
    for row in rows:
        print(''.join(str(c).ljust(w) for c, w in zip(row, widths)))


# API Key Commands

def cmd_api_key_create(args):
    """Create a new API key"""
    from .api_key_manager import get_api_key_manager

    manager = get_api_key_manager(args.db)

    scopes = args.scopes.split(',') if args.scopes else ['metrics:write']

    result = manager.create_key(
        agent_name=args.name,
        scopes=scopes,
        created_by=args.created_by or 'cli',
        agent_id=args.agent_id,
        expires_in_days=args.expires_days,
        rate_limit_requests=args.rate_limit,
        rate_limit_window=args.rate_window
    )

    print("\nAPI Key Created Successfully!")
    print("=" * 50)
    print(f"Key ID:      {result['id']}")
    print(f"Agent Name:  {result['agent_name']}")
    print(f"API Key:     {result['key']}")
    print(f"Prefix:      {result['key_prefix']}")
    print(f"Scopes:      {', '.join(result['scopes'])}")
    print(f"Expires:     {format_datetime(result.get('expires_at', 'Never'))}")
    print("=" * 50)
    print("\n⚠️  Save this key securely! It cannot be retrieved later.\n")


def cmd_api_key_list(args):
    """List all API keys"""
    from .api_key_manager import get_api_key_manager

    manager = get_api_key_manager(args.db)
    keys = manager.list_keys(include_revoked=args.include_revoked)

    if not keys:
        print("No API keys found.")
        return

    print(f"\nAPI Keys ({len(keys)} total)")
    print("=" * 100)

    rows = []
    for key in keys:
        status = '🔴 Revoked' if key.get('is_revoked') else '🟢 Active'
        rows.append([
            key['id'][:8] + '...',
            key['agent_name'],
            key['key_prefix'],
            ', '.join(key.get('scopes', []))[:30],
            str(key.get('use_count', 0)),
            format_datetime(key.get('last_used_at')),
            status
        ])

    print_table(
        ['ID', 'Agent Name', 'Prefix', 'Scopes', 'Uses', 'Last Used', 'Status'],
        rows,
        [12, 20, 15, 32, 8, 18, 12]
    )
    print()


def cmd_api_key_revoke(args):
    """Revoke an API key"""
    from .api_key_manager import get_api_key_manager

    manager = get_api_key_manager(args.db)
    success = manager.revoke_key(args.key_id, args.revoked_by or 'cli', args.reason or 'CLI revocation')

    if success:
        print(f"✅ API key {args.key_id} has been revoked.")
    else:
        print(f"❌ Failed to revoke API key {args.key_id}. Key not found or already revoked.")
        sys.exit(1)


def cmd_api_key_rotate(args):
    """Rotate an API key"""
    from .api_key_manager import get_api_key_manager

    manager = get_api_key_manager(args.db)
    result = manager.rotate_key(args.key_id, args.rotated_by or 'cli')

    if result:
        print("\nAPI Key Rotated Successfully!")
        print("=" * 50)
        print(f"New Key ID:  {result['id']}")
        print(f"New API Key: {result['key']}")
        print(f"New Prefix:  {result['key_prefix']}")
        print("=" * 50)
        print("\n⚠️  The old key is now invalid. Update your agent configuration.\n")
    else:
        print(f"❌ Failed to rotate API key {args.key_id}. Key not found or already revoked.")
        sys.exit(1)


def cmd_api_key_info(args):
    """Get detailed info about an API key"""
    from .api_key_manager import get_api_key_manager

    manager = get_api_key_manager(args.db)
    keys = manager.list_keys(include_revoked=True)

    key = next((k for k in keys if k['id'] == args.key_id or k['id'].startswith(args.key_id)), None)

    if not key:
        print(f"❌ API key {args.key_id} not found.")
        sys.exit(1)

    print(f"\nAPI Key Details")
    print("=" * 50)
    print(f"ID:              {key['id']}")
    print(f"Agent Name:      {key['agent_name']}")
    print(f"Agent ID:        {key.get('agent_id', 'N/A')}")
    print(f"Prefix:          {key['key_prefix']}")
    print(f"Scopes:          {', '.join(key.get('scopes', []))}")
    print(f"Created By:      {key.get('created_by', 'Unknown')}")
    print(f"Created At:      {format_datetime(key.get('created_at'))}")
    print(f"Expires At:      {format_datetime(key.get('expires_at')) or 'Never'}")
    print(f"Last Used:       {format_datetime(key.get('last_used_at'))}")
    print(f"Use Count:       {key.get('use_count', 0)}")
    print(f"Rate Limit:      {key.get('rate_limit_requests', 'N/A')} / {key.get('rate_limit_window', 'N/A')}s")
    print(f"Status:          {'Revoked' if key.get('is_revoked') else 'Active'}")
    if key.get('is_revoked'):
        print(f"Revoked At:      {format_datetime(key.get('revoked_at'))}")
        print(f"Revoked By:      {key.get('revoked_by', 'Unknown')}")
        print(f"Revoke Reason:   {key.get('revoked_reason', 'N/A')}")
    print("=" * 50)


# OAuth2 Commands

def cmd_oauth_create(args):
    """Register a new OAuth2 client"""
    from .oauth2_manager import get_oauth2_manager

    manager = get_oauth2_manager(args.db)

    redirect_uris = args.redirect_uri if args.redirect_uri else ['http://localhost:8080/callback']
    scopes = args.scopes.split(',') if args.scopes else ['metrics:read']

    result = manager.register_client(
        client_name=args.name,
        client_type=args.type,
        redirect_uris=redirect_uris,
        allowed_scopes=scopes,
        created_by=args.created_by or 'cli'
    )

    print("\nOAuth2 Client Registered Successfully!")
    print("=" * 60)
    print(f"Client ID:     {result['client_id']}")
    print(f"Client Name:   {result['client_name']}")
    print(f"Client Type:   {result['client_type']}")
    if 'client_secret' in result:
        print(f"Client Secret: {result['client_secret']}")
    print(f"Redirect URIs: {', '.join(result['redirect_uris'])}")
    print(f"Scopes:        {', '.join(result['allowed_scopes'])}")
    print("=" * 60)
    if 'client_secret' in result:
        print("\n⚠️  Save the client secret securely! It cannot be retrieved later.\n")


def cmd_oauth_list(args):
    """List OAuth2 clients"""
    from .oauth2_manager import get_oauth2_manager

    manager = get_oauth2_manager(args.db)
    clients = manager.list_clients(include_inactive=args.include_inactive)

    if not clients:
        print("No OAuth2 clients found.")
        return

    print(f"\nOAuth2 Clients ({len(clients)} total)")
    print("=" * 100)

    rows = []
    for client in clients:
        status = '🔴 Inactive' if not client.get('is_active') else '🟢 Active'
        rows.append([
            client['client_id'][:20] + '...',
            client['client_name'][:20],
            client['client_type'],
            ', '.join(client.get('allowed_scopes', []))[:25],
            format_datetime(client.get('created_at')),
            status
        ])

    print_table(
        ['Client ID', 'Name', 'Type', 'Scopes', 'Created', 'Status'],
        rows,
        [24, 22, 14, 27, 18, 12]
    )
    print()


def cmd_oauth_deactivate(args):
    """Deactivate an OAuth2 client"""
    from .oauth2_manager import get_oauth2_manager

    manager = get_oauth2_manager(args.db)
    success = manager.deactivate_client(args.client_id)

    if success:
        print(f"✅ OAuth2 client {args.client_id} has been deactivated.")
    else:
        print(f"❌ Failed to deactivate client {args.client_id}. Client not found.")
        sys.exit(1)


def cmd_oauth_info(args):
    """Get detailed info about an OAuth2 client"""
    from .oauth2_manager import get_oauth2_manager

    manager = get_oauth2_manager(args.db)
    client = manager.get_client(args.client_id)

    if not client:
        print(f"❌ OAuth2 client {args.client_id} not found.")
        sys.exit(1)

    print(f"\nOAuth2 Client Details")
    print("=" * 50)
    print(f"Client ID:       {client['client_id']}")
    print(f"Client Name:     {client['client_name']}")
    print(f"Client Type:     {client['client_type']}")
    print(f"Redirect URIs:   {', '.join(client.get('redirect_uris', []))}")
    print(f"Allowed Scopes:  {', '.join(client.get('allowed_scopes', []))}")
    print(f"Created By:      {client.get('created_by', 'Unknown')}")
    print(f"Created At:      {format_datetime(client.get('created_at'))}")
    print(f"Status:          {'Active' if client.get('is_active') else 'Inactive'}")
    print("=" * 50)


# Scope Commands

def cmd_scopes_list(args):
    """List all available scopes"""
    from .scopes import get_scope_validator

    validator = get_scope_validator(args.db)
    scopes = validator.get_all_scopes()

    if not scopes:
        print("No scopes defined.")
        return

    print(f"\nAvailable Scopes ({len(scopes)} total)")
    print("=" * 90)

    rows = []
    for scope in scopes:
        sensitive = '🔒' if scope.get('is_sensitive') else ''
        rows.append([
            scope['scope'],
            scope['display_name'],
            scope['category'],
            scope['description'][:35] + '...' if len(scope.get('description', '')) > 35 else scope.get('description', ''),
            sensitive
        ])

    print_table(
        ['Scope', 'Display Name', 'Category', 'Description', ''],
        rows,
        [20, 20, 12, 38, 3]
    )
    print("\n🔒 = Sensitive scope\n")


# Cleanup Commands

def cmd_cleanup(args):
    """Clean up expired tokens and codes"""
    print("Running auth cleanup...")

    total_deleted = 0

    # JWT cleanup
    try:
        from .jwt_manager import get_jwt_manager
        jwt = get_jwt_manager(args.db)
        if jwt:
            deleted = jwt.cleanup_expired()
            print(f"  JWT tokens cleaned: {deleted}")
            total_deleted += deleted
    except ImportError:
        print("  JWT cleanup skipped (PyJWT not installed)")

    # OAuth2 cleanup
    try:
        from .oauth2_manager import get_oauth2_manager
        oauth = get_oauth2_manager(args.db)
        if oauth:
            deleted = oauth.cleanup_expired()
            print(f"  OAuth2 codes cleaned: {deleted}")
            total_deleted += deleted
    except Exception as e:
        print(f"  OAuth2 cleanup error: {e}")

    print(f"\n✅ Cleanup complete. Total items removed: {total_deleted}")


# Main CLI

def main():
    parser = argparse.ArgumentParser(
        description='ATLAS Fleet Authentication CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create an API key for an agent
  %(prog)s api-key create --name "office-mac-1" --scopes metrics:write,commands:read

  # List all API keys
  %(prog)s api-key list

  # Revoke an API key
  %(prog)s api-key revoke abc123

  # Register an OAuth2 client
  %(prog)s oauth create --name "Dashboard App" --redirect-uri https://app.example.com/callback

  # List available scopes
  %(prog)s scopes list

  # Run cleanup
  %(prog)s cleanup
        """
    )

    parser.add_argument('--db', default=get_db_path(), help='Path to database file')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # API Key commands
    api_key_parser = subparsers.add_parser('api-key', help='Manage API keys')
    api_key_subparsers = api_key_parser.add_subparsers(dest='action')

    # api-key create
    create_parser = api_key_subparsers.add_parser('create', help='Create a new API key')
    create_parser.add_argument('--name', required=True, help='Agent name')
    create_parser.add_argument('--scopes', help='Comma-separated scopes')
    create_parser.add_argument('--agent-id', help='Agent ID')
    create_parser.add_argument('--created-by', help='Creator username')
    create_parser.add_argument('--expires-days', type=int, default=365, help='Days until expiration')
    create_parser.add_argument('--rate-limit', type=int, default=1000, help='Rate limit requests')
    create_parser.add_argument('--rate-window', type=int, default=3600, help='Rate limit window (seconds)')
    create_parser.set_defaults(func=cmd_api_key_create)

    # api-key list
    list_parser = api_key_subparsers.add_parser('list', help='List API keys')
    list_parser.add_argument('--include-revoked', action='store_true', help='Include revoked keys')
    list_parser.set_defaults(func=cmd_api_key_list)

    # api-key revoke
    revoke_parser = api_key_subparsers.add_parser('revoke', help='Revoke an API key')
    revoke_parser.add_argument('key_id', help='API key ID')
    revoke_parser.add_argument('--revoked-by', help='Revoker username')
    revoke_parser.add_argument('--reason', help='Revocation reason')
    revoke_parser.set_defaults(func=cmd_api_key_revoke)

    # api-key rotate
    rotate_parser = api_key_subparsers.add_parser('rotate', help='Rotate an API key')
    rotate_parser.add_argument('key_id', help='API key ID')
    rotate_parser.add_argument('--rotated-by', help='Rotator username')
    rotate_parser.set_defaults(func=cmd_api_key_rotate)

    # api-key info
    info_parser = api_key_subparsers.add_parser('info', help='Get API key details')
    info_parser.add_argument('key_id', help='API key ID')
    info_parser.set_defaults(func=cmd_api_key_info)

    # OAuth commands
    oauth_parser = subparsers.add_parser('oauth', help='Manage OAuth2 clients')
    oauth_subparsers = oauth_parser.add_subparsers(dest='action')

    # oauth create
    oauth_create_parser = oauth_subparsers.add_parser('create', help='Register an OAuth2 client')
    oauth_create_parser.add_argument('--name', required=True, help='Client name')
    oauth_create_parser.add_argument('--type', choices=['confidential', 'public'], default='confidential', help='Client type')
    oauth_create_parser.add_argument('--redirect-uri', action='append', help='Redirect URI (can specify multiple)')
    oauth_create_parser.add_argument('--scopes', help='Comma-separated allowed scopes')
    oauth_create_parser.add_argument('--created-by', help='Creator username')
    oauth_create_parser.set_defaults(func=cmd_oauth_create)

    # oauth list
    oauth_list_parser = oauth_subparsers.add_parser('list', help='List OAuth2 clients')
    oauth_list_parser.add_argument('--include-inactive', action='store_true', help='Include inactive clients')
    oauth_list_parser.set_defaults(func=cmd_oauth_list)

    # oauth deactivate
    oauth_deactivate_parser = oauth_subparsers.add_parser('deactivate', help='Deactivate an OAuth2 client')
    oauth_deactivate_parser.add_argument('client_id', help='Client ID')
    oauth_deactivate_parser.set_defaults(func=cmd_oauth_deactivate)

    # oauth info
    oauth_info_parser = oauth_subparsers.add_parser('info', help='Get OAuth2 client details')
    oauth_info_parser.add_argument('client_id', help='Client ID')
    oauth_info_parser.set_defaults(func=cmd_oauth_info)

    # Scopes commands
    scopes_parser = subparsers.add_parser('scopes', help='Manage scopes')
    scopes_subparsers = scopes_parser.add_subparsers(dest='action')

    scopes_list_parser = scopes_subparsers.add_parser('list', help='List available scopes')
    scopes_list_parser.set_defaults(func=cmd_scopes_list)

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up expired tokens')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        # Print subcommand help
        if args.command == 'api-key':
            api_key_parser.print_help()
        elif args.command == 'oauth':
            oauth_parser.print_help()
        elif args.command == 'scopes':
            scopes_parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
