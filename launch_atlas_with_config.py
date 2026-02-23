#!/usr/bin/env python3
"""
ATLAS Agent Launcher with Auto-Config
Automatically loads API key and settings from encrypted config
Includes singleton check to prevent duplicate agents
"""

import sys
import os
import subprocess
import logging
import signal
import time
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

# Add to path and import AFTER logging is configured
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.fleet_config_encryption import EncryptedConfigManager


def kill_existing_agents():
    """Find and kill any existing ATLAS agent processes (except ourselves)"""
    my_pid = os.getpid()
    killed_count = 0
    
    try:
        # Find all agent processes
        result = subprocess.run(
            ['pgrep', '-f', 'start_atlas_agent.py|launch_atlas_with_config.py'],
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


def get_config_values():
    """Load configuration from encrypted config file"""
    try:
        config_path = os.path.expanduser('~/.fleet-config.json')
        
        if not os.path.exists(config_path + '.encrypted'):
            logger.error("No encrypted config found at: %s.encrypted", config_path)
            logger.error("Please run: python3 repair_credentials.py")
            return None
        
        manager = EncryptedConfigManager(config_path)
        config = manager.decrypt_config()
        
        if not config:
            logger.error("Failed to decrypt config")
            return None
        
        return config
        
    except Exception as e:
        logger.error("Error loading config: %s", e)
        return None


def main():
    """Launch ATLAS agent with config from encrypted file"""
    
    print("=" * 70)
    print("ATLAS AGENT LAUNCHER")
    print("=" * 70)
    print()
    
    # Kill any existing agent processes first (singleton check)
    killed = kill_existing_agents()
    if killed > 0:
        print(f"Stopped {killed} existing agent process(es)")
        print()
    
    # Load config
    logger.info("Loading configuration...")
    config = get_config_values()
    
    import socket
    machine_id = socket.gethostname().split('.')[0]
    
    if not config:
        print("\n No fleet configuration found - starting in STANDALONE mode")
        print("   Local dashboard will be available at http://localhost:8767")
        print("   To connect to fleet server, run: python3 repair_credentials.py")
        print()
        print("=" * 70)
        print()
        
        # Build standalone command (no fleet connection)
        cmd = [
            sys.executable,
            'start_atlas_agent.py',
            '--machine-id', machine_id,
            '--standalone'
        ]
    else:
        # Extract values
        server_config = config.get('server', {})
        api_key = server_config.get('api_key')
        fleet_server = server_config.get('fleet_server_url', 'https://localhost:8768')
        
        # Get machine ID from config or hostname
        machine_id = config.get('machine_id') or machine_id
        
        if not api_key:
            logger.warning("No API key found - starting in standalone mode")
            print("\n No API key configured - starting in STANDALONE mode")
            cmd = [
                sys.executable,
                'start_atlas_agent.py',
                '--machine-id', machine_id,
                '--standalone'
            ]
        else:
            # Get encryption key for E2EE
            encryption_key = server_config.get('encryption_key')
            
            # Display configuration
            print("Configuration loaded successfully")
            print()
            print(f"Fleet Server:  {fleet_server}")
            print(f"Machine ID:    {machine_id}")
            print(f"API Key:       {api_key[:20]}...{api_key[-10:]}")
            if encryption_key:
                print(f"E2EE:          Enabled")
            else:
                print(f"E2EE:          Disabled (data sent unencrypted)")
            print()
            print("=" * 70)
            print()
            
            # Build command with fleet connection
            cmd = [
                sys.executable,
                'start_atlas_agent.py',
                '--fleet-server', fleet_server,
                '--machine-id', machine_id,
                '--api-key', api_key
            ]
            
            # Add encryption key if configured
            if encryption_key:
                cmd.extend(['--encryption-key', encryption_key])
    
    logger.info("Starting ATLAS agent...")
    
    try:
        # Replace current process with the agent
        os.execvp(sys.executable, cmd)
    except Exception as e:
        logger.error("Failed to start agent: %s", e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
