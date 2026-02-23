#!/usr/bin/env python3
"""
ATLAS Agent Launcher
Starts the Fleet Agent with menu bar icon
Includes singleton check to prevent duplicate agents
"""

import sys
import os
import argparse
import threading
import logging
import time
import signal
import subprocess
from logging.handlers import TimedRotatingFileHandler

# Configure persistent logging with 7-day retention BEFORE any other imports
log_dir = os.path.expanduser('~/Library/Logs/FleetAgent')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'fleet_agent.log')

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler with 7-day retention (rotate daily, keep 7 backups)
file_handler = TimedRotatingFileHandler(
    log_file,
    when='midnight',
    interval=1,
    backupCount=7,
    encoding='utf-8'
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file} (7-day retention)")

# Add atlas to path and import AFTER logging is configured
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.live_widgets import start_live_widget_server


def kill_existing_agents():
    """Find and kill any existing ATLAS agent processes (except ourselves)"""
    my_pid = os.getpid()
    killed_count = 0
    
    try:
        # Find all agent processes
        result = subprocess.run(
            ['pgrep', '-f', 'start_atlas_agent.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
            
            for pid in pids:
                if pid != my_pid:
                    try:
                        logger.info(f"Killing existing agent process: {pid}")
                        os.kill(pid, signal.SIGTERM)
                        killed_count += 1
                    except ProcessLookupError:
                        pass  # Already dead
                    except PermissionError:
                        logger.warning(f"No permission to kill process {pid}")
            
            if killed_count > 0:
                # Give processes time to clean up
                time.sleep(2)
                
                # Force kill any that didn't respond to SIGTERM
                for pid in pids:
                    if pid != my_pid:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                
                logger.info(f"Killed {killed_count} existing agent process(es)")
    
    except Exception as e:
        logger.warning(f"Error checking for existing agents: {e}")
    
    return killed_count


def main():
    """Start ATLAS agent with menu bar icon"""
    parser = argparse.ArgumentParser(description='ATLAS Fleet Agent with Menu Bar Icon')
    parser.add_argument('--port', type=int, default=8767, help='Agent port (default: 8767)')
    parser.add_argument('--fleet-server', type=str, help='Fleet server URL (e.g., https://localhost:8768)')
    parser.add_argument('--machine-id', type=str, help='Machine ID for fleet reporting')
    parser.add_argument('--api-key', type=str, help='API key for fleet server')
    parser.add_argument('--no-menubar', action='store_true', help='Start without menu bar icon')
    parser.add_argument('--standalone', action='store_true', help='Run in standalone mode (no fleet connection)')
    parser.add_argument('--encryption-key', type=str, help='E2EE encryption key (shared with server)')
    
    args = parser.parse_args()
    
    # Kill any existing agent processes first (singleton check)
    killed = kill_existing_agents()
    if killed > 0:
        print(f"Stopped {killed} existing agent process(es)")

    # Standalone mode ignores fleet settings
    if args.standalone:
        args.fleet_server = None
        args.api_key = None
        args.encryption_key = None

    mode = "STANDALONE" if args.standalone or not args.fleet_server else "FLEET"
    print(f"Starting ATLAS Agent ({mode} mode)...")
    print("=" * 60)
    print(f"   Port: {args.port}")
    print(f"   Auth: macOS local user account")
    if args.fleet_server:
        print(f"   Fleet Server: {args.fleet_server}")
    if args.machine_id:
        print(f"   Machine ID: {args.machine_id}")
    print("=" * 60)

    # Save startup config so the menubar can restart the agent if needed
    import json
    config_dir = os.path.expanduser('~/.atlas')
    os.makedirs(config_dir, exist_ok=True)
    startup_config = {
        'port': args.port,
        'fleet_server': args.fleet_server,
        'machine_id': args.machine_id,
        'api_key': args.api_key,
        'encryption_key': args.encryption_key,
        'project_dir': os.path.dirname(os.path.abspath(__file__)),
        'python_path': sys.executable,
    }
    with open(os.path.join(config_dir, 'agent-startup.json'), 'w') as f:
        json.dump(startup_config, f, indent=2)
    logger.info(f"Saved startup config to {config_dir}/agent-startup.json")

    # Start agent server in background thread
    def start_agent():
        try:
            logger.info("Starting Fleet Agent server...")
            start_live_widget_server(
                port=args.port,
                fleet_server=args.fleet_server,
                machine_id=args.machine_id,
                api_key=args.api_key,
                encryption_key=args.encryption_key
            )
        except Exception as e:
            logger.error(f"Error starting agent server: {e}")
            sys.exit(1)
    
    agent_thread = threading.Thread(target=start_agent, daemon=True)
    agent_thread.start()
    
    # Wait for agent to start
    logger.info("Waiting for agent to initialize...")
    time.sleep(3)
    
    # Check if menu bar should be started
    if args.no_menubar:
        logger.info("Menu bar disabled, running in background mode")
        print("\nATLAS Agent running in background")
        print(f"   Dashboard: http://localhost:{args.port}")
        print("   Press Ctrl+C to stop\n")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 Stopping ATLAS Agent...")
            sys.exit(0)
    else:
        # Start menu bar app (blocks until quit)
        from atlas.menubar_agent import start_menubar_app
        logger.info("Starting menu bar app...")
        print("\nATLAS Agent started!")
        print(f"   Dashboard: http://localhost:{args.port}")
        print("   Menu bar icon: Check top-right corner of screen")
        print("   Click icon for options\n")

        try:
            start_menubar_app(
                fleet_server_url=args.fleet_server,
                agent_port=args.port
            )
        except KeyboardInterrupt:
            print("\n\n👋 Stopping ATLAS Agent...")
            sys.exit(0)


if __name__ == '__main__':
    main()
