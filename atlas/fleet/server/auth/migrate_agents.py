#!/usr/bin/env python3
"""
ATLAS Fleet Authentication - Agent Migration Script

Migrates existing agents from the global API key to per-agent API keys.

This script:
1. Reads all registered machines from the fleet data store
2. Creates individual API keys for each agent
3. Generates a migration report with new keys
4. Optionally outputs agent configuration files

Usage:
    python -m atlas.fleet.server.auth.migrate_agents
    python -m atlas.fleet.server.auth.migrate_agents --output-dir /path/to/configs
    python -m atlas.fleet.server.auth.migrate_agents --dry-run
"""
import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def get_db_path() -> str:
    """Get the default database path"""
    return str(Path.home() / '.fleet-data' / 'users.db')


def get_fleet_db_path() -> str:
    """Get the fleet data store path"""
    return str(Path.home() / '.fleet-data' / 'fleet.db')


def get_existing_agents(fleet_db_path: str) -> List[Dict]:
    """
    Get list of existing agents from the fleet data store.

    Returns list of dicts with machine_id, hostname, local_ip, last_seen
    """
    import sqlite3

    agents = []

    # Try SQLite-based data store
    if Path(fleet_db_path).exists():
        try:
            conn = sqlite3.connect(fleet_db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Check if machines table exists
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='machines'")
            if cur.fetchone():
                cur.execute("""
                    SELECT machine_id, hostname, local_ip, last_seen, status
                    FROM machines
                    ORDER BY last_seen DESC
                """)

                for row in cur.fetchall():
                    agents.append({
                        'machine_id': row['machine_id'],
                        'hostname': row['hostname'],
                        'local_ip': row['local_ip'],
                        'last_seen': row['last_seen'],
                        'status': row['status']
                    })

            conn.close()
        except Exception as e:
            print(f"Warning: Could not read from {fleet_db_path}: {e}")

    # Try JSON-based data store (fallback)
    json_path = Path.home() / '.fleet-data' / 'machines.json'
    if json_path.exists() and not agents:
        try:
            with open(json_path) as f:
                data = json.load(f)

            for machine_id, machine in data.items():
                info = machine.get('info', machine.get('machine_info', {}))
                agents.append({
                    'machine_id': machine_id,
                    'hostname': info.get('hostname', 'unknown'),
                    'local_ip': info.get('local_ip', 'unknown'),
                    'last_seen': machine.get('last_seen', ''),
                    'status': machine.get('status', 'unknown')
                })
        except Exception as e:
            print(f"Warning: Could not read from {json_path}: {e}")

    return agents


def create_agent_api_key(
    api_key_manager,
    machine_id: str,
    hostname: str,
    created_by: str = 'migration'
) -> Optional[Dict]:
    """Create an API key for an agent"""
    # Default scopes for agents
    agent_scopes = [
        'metrics:write',
        'commands:read',
        'widget_logs:write'
    ]

    agent_name = f"{hostname} ({machine_id[:8]})"

    try:
        result = api_key_manager.create_key(
            agent_name=agent_name,
            scopes=agent_scopes,
            created_by=created_by,
            agent_id=machine_id,
            expires_in_days=365,  # 1 year
            rate_limit_requests=1000,
            rate_limit_window=3600
        )
        return result
    except Exception as e:
        print(f"Error creating key for {machine_id}: {e}")
        return None


def generate_agent_config(
    machine_id: str,
    hostname: str,
    api_key: str,
    server_url: str = 'http://localhost:8778'
) -> Dict:
    """Generate agent configuration with new API key"""
    return {
        'machine_id': machine_id,
        'hostname': hostname,
        'server': {
            'url': server_url,
            'api_key': api_key
        },
        'reporting': {
            'interval_seconds': 60,
            'batch_size': 10
        },
        'generated_at': datetime.now().isoformat(),
        'generated_by': 'migration_script'
    }


def write_agent_config(output_dir: Path, machine_id: str, config: Dict) -> str:
    """Write agent configuration to file"""
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"agent-{machine_id[:8]}.json"
    filepath = output_dir / filename

    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2)

    return str(filepath)


def run_migration(
    db_path: str,
    fleet_db_path: str,
    output_dir: Optional[str],
    server_url: str,
    dry_run: bool,
    created_by: str
):
    """Run the migration process"""

    print("\n" + "=" * 60)
    print("ATLAS Fleet - Agent API Key Migration")
    print("=" * 60)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Get existing agents
    print("Scanning for existing agents...")
    agents = get_existing_agents(fleet_db_path)

    if not agents:
        print("\n❌ No agents found in the fleet data store.")
        print("   Make sure agents have reported to the fleet server at least once.")
        return

    print(f"\nFound {len(agents)} agents:")
    for agent in agents:
        status = '🟢' if agent.get('status') == 'online' else '🔴'
        print(f"  {status} {agent['hostname']} ({agent['machine_id'][:8]}...)")

    if dry_run:
        print("\n✅ Dry run complete. Run without --dry-run to create API keys.")
        return

    # Confirm migration
    print("\n" + "-" * 60)
    response = input("Create API keys for these agents? [y/N]: ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        return

    # Initialize API key manager
    from .api_key_manager import get_api_key_manager
    api_key_manager = get_api_key_manager(db_path)

    # Create API keys
    print("\nCreating API keys...")
    results = []
    configs = []

    for agent in agents:
        result = create_agent_api_key(
            api_key_manager,
            agent['machine_id'],
            agent['hostname'],
            created_by
        )

        if result:
            results.append({
                'machine_id': agent['machine_id'],
                'hostname': agent['hostname'],
                'key_id': result['id'],
                'api_key': result['key'],
                'key_prefix': result['key_prefix']
            })

            config = generate_agent_config(
                agent['machine_id'],
                agent['hostname'],
                result['key'],
                server_url
            )
            configs.append(config)

            print(f"  ✅ {agent['hostname']}: {result['key_prefix']}...")

    # Write config files if output directory specified
    if output_dir and configs:
        output_path = Path(output_dir)
        print(f"\nWriting configuration files to {output_path}...")

        for config in configs:
            filepath = write_agent_config(
                output_path,
                config['machine_id'],
                config
            )
            print(f"  📄 {filepath}")

    # Generate migration report
    report = {
        'migration_date': datetime.now().isoformat(),
        'total_agents': len(agents),
        'keys_created': len(results),
        'agents': results
    }

    report_path = Path.home() / '.fleet-data' / 'migration_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"\n  Agents processed: {len(agents)}")
    print(f"  API keys created: {len(results)}")
    print(f"  Report saved to:  {report_path}")

    if output_dir:
        print(f"  Config files in:  {output_dir}")

    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("  1. Distribute the new API keys to each agent")
    print("  2. Update agent configuration files")
    print("  3. Restart agents to use new keys")
    print("  4. After verification, revoke the global API key")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Migrate existing agents to per-agent API keys',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script migrates existing agents from a shared global API key
to individual per-agent API keys with scoped permissions.

The migration process:
  1. Scans the fleet data store for registered agents
  2. Creates a unique API key for each agent
  3. Generates configuration files for deployment
  4. Creates a migration report

After migration:
  - Deploy new configuration files to each agent
  - Restart agents to use new API keys
  - Verify agents are reporting successfully
  - Revoke the old global API key

Examples:
  # Dry run to see what would be migrated
  python -m atlas.fleet.server.auth.migrate_agents --dry-run

  # Run migration and output config files
  python -m atlas.fleet.server.auth.migrate_agents --output-dir ./agent-configs

  # Specify custom server URL
  python -m atlas.fleet.server.auth.migrate_agents --server-url https://fleet.example.com:8778
        """
    )

    parser.add_argument(
        '--db',
        default=get_db_path(),
        help='Path to auth database'
    )
    parser.add_argument(
        '--fleet-db',
        default=get_fleet_db_path(),
        help='Path to fleet data store'
    )
    parser.add_argument(
        '--output-dir',
        help='Directory to output agent configuration files'
    )
    parser.add_argument(
        '--server-url',
        default='http://localhost:8778',
        help='Fleet server URL for agent configs'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    parser.add_argument(
        '--created-by',
        default='migration',
        help='Username to record as key creator'
    )

    args = parser.parse_args()

    run_migration(
        db_path=args.db,
        fleet_db_path=args.fleet_db,
        output_dir=args.output_dir,
        server_url=args.server_url,
        dry_run=args.dry_run,
        created_by=args.created_by
    )


if __name__ == '__main__':
    main()
