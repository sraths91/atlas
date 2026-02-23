#!/usr/bin/env python3
"""Create initial admin user for Fleet Dashboard"""

import sys
import getpass
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from atlas.fleet_user_manager import FleetUserManager

def main():
    print("=" * 60)
    print("Fleet Dashboard - Create Admin User")
    print("=" * 60)
    print()
    
    user_manager = FleetUserManager()
    
    # Check if any users exist
    existing_users = user_manager.list_users()
    if existing_users:
        print(f" Warning: {len(existing_users)} user(s) already exist:")
        for user in existing_users:
            print(f"   - {user['username']} ({user['role']})")
        print()
        response = input("Do you want to create another admin user? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        print()
    
    # Get username
    while True:
        username = input("Enter admin username: ").strip()
        if not username:
            print("Username cannot be empty")
            continue
        if len(username) < 3:
            print("Username must be at least 3 characters")
            continue
        break
    
    # Get password
    while True:
        password = getpass.getpass("Enter password (min 8 characters): ")
        if len(password) < 8:
            print("Password must be at least 8 characters")
            continue
        
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords do not match")
            continue
        break
    
    # Create user
    print()
    print("Creating admin user...")
    success, message = user_manager.create_user(
        username=username,
        password=password,
        role='admin',
        created_by='setup_script'
    )
    
    if success:
        print(f"{message}")
        print()
        print("You can now log in to the Fleet Dashboard with:")
        print(f"   Username: {username}")
        print(f"   Password: (the password you just entered)")
        print()
        print("Access the dashboard at: http://192.168.50.191:8768/dashboard")
    else:
        print(f"{message}")
        sys.exit(1)

if __name__ == '__main__':
    main()
