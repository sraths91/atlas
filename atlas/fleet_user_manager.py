"""
Fleet User Management System
Handles user creation, authentication, password reset, and brute force protection
"""

import json
import sqlite3
import hashlib
import secrets
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

# Import bcrypt for secure password hashing
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("bcrypt not available - using fallback SHA-256 (NOT RECOMMENDED for production)")

logger = logging.getLogger(__name__)

# Session storage (in-memory fallback when JWT is unavailable)
active_sessions = {}


def _get_jwt_manager():
    """Lazy-load JWT manager. Returns None if unavailable."""
    try:
        from atlas.fleet.server.auth.jwt_manager import get_jwt_manager
        return get_jwt_manager()
    except (ImportError, Exception):
        return None


class FleetUserManager:
    """Manages fleet server users with authentication and security features"""
    
    def __init__(self, db_path: str = "~/.fleet-data/users.db"):
        db_path_obj = Path(db_path).expanduser()
        self.db_path = str(db_path_obj)
        self._init_db()
        self.login_attempts = {}  # Track failed login attempts
        self.max_attempts = 5
        self.lockout_duration = 300  # 5 minutes in seconds

    def _init_db(self):
        """Initialize user database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    reset_token TEXT,
                    reset_token_expires TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ip_address TEXT,
                    success INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Create index for faster lookups
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_login_attempts_timestamp 
                ON login_attempts(timestamp)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def _hash_password(self, password: str, salt: str = None) -> str:
        """
        Hash password using bcrypt (recommended) or SHA-256 (fallback)

        For bcrypt: salt parameter is ignored (bcrypt generates its own)
        For SHA-256 fallback: salt parameter is required
        """
        if BCRYPT_AVAILABLE:
            # Use bcrypt with 12 rounds (2^12 = 4096 iterations)
            # bcrypt automatically generates and stores salt in the hash
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
            return hashed.decode('utf-8')  # Store as string in database
        else:
            # Fallback to SHA-256 (NOT RECOMMENDED for production)
            if not salt:
                raise ValueError("Salt required for SHA-256 fallback")
            return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    def _verify_password(self, password: str, stored_hash: str, stored_salt: str = None) -> bool:
        """
        Verify password against stored hash

        Supports both bcrypt hashes and legacy SHA-256 hashes
        """
        if BCRYPT_AVAILABLE and stored_hash.startswith('$2b$'):
            # bcrypt hash (starts with $2b$ or $2a$)
            try:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            except Exception as e:
                logger.error(f"Error verifying bcrypt password: {e}")
                return False
        else:
            # Legacy SHA-256 hash or fallback
            if not stored_salt:
                logger.error("Cannot verify password: salt missing for SHA-256 hash")
                return False
            computed_hash = hashlib.sha256(f"{password}{stored_salt}".encode()).hexdigest()
            return computed_hash == stored_hash

    def _generate_salt(self) -> str:
        """Generate random salt (only used for SHA-256 fallback)"""
        return secrets.token_hex(32)
    
    def validate_password_complexity(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password meets complexity requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one symbol
        
        Returns: (is_valid, list_of_missing_requirements)
        """
        missing = []
        
        if len(password) < 12:
            missing.append(f"At least 12 characters (currently {len(password)})")
        
        if not re.search(r'[A-Z]', password):
            missing.append("At least one uppercase letter (A-Z)")
        
        if not re.search(r'[a-z]', password):
            missing.append("At least one lowercase letter (a-z)")
        
        if not re.search(r'[0-9]', password):
            missing.append("At least one number (0-9)")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'"\\|,.<>/?`~]', password):
            missing.append("At least one symbol (!@#$%^&*()_+-=[]{}etc.)")
        
        return len(missing) == 0, missing
    
    def _check_brute_force(self, username: str, ip_address: str = None) -> Tuple[bool, Optional[int]]:
        """
        Check if user/IP is locked out due to brute force attempts
        Returns: (is_locked, seconds_remaining)
        """
        key = f"{username}:{ip_address}" if ip_address else username
        
        if key in self.login_attempts:
            attempts, lockout_until = self.login_attempts[key]
            
            # Check if still locked out
            if time.time() < lockout_until:
                remaining = int(lockout_until - time.time())
                return True, remaining
            else:
                # Lockout expired, clear attempts
                del self.login_attempts[key]
        
        return False, None
    
    def _record_login_attempt(self, username: str, success: bool, ip_address: str = None):
        """Record login attempt and update brute force tracking"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO login_attempts (username, ip_address, success, timestamp)
                VALUES (?, ?, ?, ?)
            """, (username, ip_address, 1 if success else 0, datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()
        
        if not success:
            key = f"{username}:{ip_address}" if ip_address else username
            
            if key in self.login_attempts:
                attempts, _ = self.login_attempts[key]
                attempts += 1
            else:
                attempts = 1
            
            if attempts >= self.max_attempts:
                lockout_until = time.time() + self.lockout_duration
                self.login_attempts[key] = (attempts, lockout_until)
                logger.warning(f"Account locked due to brute force: {username} from {ip_address}")
            else:
                self.login_attempts[key] = (attempts, 0)
        else:
            # Clear failed attempts on successful login
            key = f"{username}:{ip_address}" if ip_address else username
            if key in self.login_attempts:
                del self.login_attempts[key]
    
    def create_user(self, username: str, password: str, role: str = "admin", 
                   created_by: str = None) -> Tuple[bool, str]:
        """
        Create a new user
        Returns: (success, message)
        """
        if not username or not password:
            return False, "Username and password are required"
        
        # Validate password complexity
        is_valid, missing = self.validate_password_complexity(password)
        if not is_valid:
            error_msg = "Password does not meet complexity requirements:\n" + "\n".join(f"  • {req}" for req in missing)
            return False, error_msg
        
        if role not in ["admin", "viewer"]:
            return False, "Role must be 'admin' or 'viewer'"
        
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                return False, "Username already exists"
            
            # Create user
            # For bcrypt, salt is embedded in hash; for SHA-256 fallback, we need separate salt
            salt = "" if BCRYPT_AVAILABLE else self._generate_salt()
            password_hash = self._hash_password(password, salt if salt else None)
            
            # Check if needs_password_update column exists
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'needs_password_update' in columns:
                cur.execute("""
                    INSERT INTO users (username, password_hash, salt, role, created_at, is_active, needs_password_update)
                    VALUES (?, ?, ?, ?, ?, 1, 0)
                """, (username, password_hash, salt, role, datetime.now().isoformat()))
            else:
                cur.execute("""
                    INSERT INTO users (username, password_hash, salt, role, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (username, password_hash, salt, role, datetime.now().isoformat()))
            
            conn.commit()
            logger.info(f"User created: {username} (role: {role}) by {created_by or 'system'}")
            return True, "User created successfully"
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error creating user: {str(e)}"
        finally:
            conn.close()
    
    def authenticate(self, username: str, password: str, ip_address: str = None) -> Tuple[bool, str]:
        """
        Authenticate user
        Returns: (success, message)
        """
        # Check brute force protection
        is_locked, remaining = self._check_brute_force(username, ip_address)
        if is_locked:
            return False, f"Account locked. Try again in {remaining} seconds"
        
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT password_hash, salt, is_active 
                FROM users 
                WHERE username = ?
            """, (username,))
            
            result = cur.fetchone()
            if not result:
                self._record_login_attempt(username, False, ip_address)
                return False, "Invalid username or password"
            
            password_hash, salt, is_active = result
            
            if not is_active:
                self._record_login_attempt(username, False, ip_address)
                return False, "Account is disabled"
            
            # Verify password using new method (supports both bcrypt and legacy SHA-256)
            if self._verify_password(password, password_hash, salt):
                # Update last login
                cur.execute("""
                    UPDATE users SET last_login = ? WHERE username = ?
                """, (datetime.now().isoformat(), username))
                conn.commit()

                self._record_login_attempt(username, True, ip_address)
                return True, "Authentication successful"
            else:
                self._record_login_attempt(username, False, ip_address)
                return False, "Invalid username or password"
        finally:
            conn.close()
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password
        Returns: (success, message)
        """
        # Validate password complexity
        is_valid, missing = self.validate_password_complexity(new_password)
        if not is_valid:
            error_msg = "Password does not meet complexity requirements:\n" + "\n".join(f"  • {req}" for req in missing)
            return False, error_msg
        
        # Verify old password
        success, msg = self.authenticate(username, old_password)
        if not success:
            return False, "Current password is incorrect"
        
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Generate new salt and hash
            # For bcrypt, salt is embedded in hash; for SHA-256 fallback, we need separate salt
            salt = "" if BCRYPT_AVAILABLE else self._generate_salt()
            password_hash = self._hash_password(new_password, salt if salt else None)
            
            # Check if needs_password_update column exists
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'needs_password_update' in columns:
                cur.execute("""
                    UPDATE users 
                    SET password_hash = ?, salt = ?, needs_password_update = 0
                    WHERE username = ?
                """, (password_hash, salt, username))
            else:
                cur.execute("""
                    UPDATE users 
                    SET password_hash = ?, salt = ?
                    WHERE username = ?
                """, (password_hash, salt, username))
            
            conn.commit()
            logger.info(f"Password changed for user: {username}")
            return True, "Password changed successfully"
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False, f"Error changing password: {str(e)}"
        finally:
            conn.close()
    
    def generate_reset_token(self, username: str) -> Tuple[bool, Optional[str], str]:
        """
        Generate password reset token
        Returns: (success, token, message)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cur.fetchone():
                return False, None, "User not found"
            
            # Generate token
            token = secrets.token_urlsafe(32)
            expires = (datetime.now() + timedelta(hours=1)).isoformat()
            
            cur.execute("""
                UPDATE users 
                SET reset_token = ?, reset_token_expires = ?
                WHERE username = ?
            """, (token, expires, username))
            
            conn.commit()
            logger.info(f"Reset token generated for user: {username}")
            return True, token, "Reset token generated"
        except Exception as e:
            logger.error(f"Error generating reset token: {e}")
            return False, None, f"Error: {str(e)}"
        finally:
            conn.close()
    
    def reset_password_with_token(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset password using token
        Returns: (success, message)
        """
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters"
        
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Find user with valid token
            cur.execute("""
                SELECT username, reset_token_expires 
                FROM users 
                WHERE reset_token = ?
            """, (token,))
            
            result = cur.fetchone()
            if not result:
                return False, "Invalid reset token"
            
            username, expires = result
            
            # Check if token expired
            if datetime.fromisoformat(expires) < datetime.now():
                return False, "Reset token has expired"
            
            # Update password
            salt = self._generate_salt()
            password_hash = self._hash_password(new_password, salt)
            
            cur.execute("""
                UPDATE users 
                SET password_hash = ?, salt = ?, reset_token = NULL, reset_token_expires = NULL
                WHERE username = ?
            """, (password_hash, salt, username))
            
            conn.commit()
            logger.info(f"Password reset for user: {username}")
            return True, "Password reset successfully"
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, f"Error: {str(e)}"
        finally:
            conn.close()
    
    def list_users(self) -> List[Dict]:
        """Get list of all users"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT username, role, created_at, last_login, is_active
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = []
            for row in cur.fetchall():
                users.append({
                    'username': row[0],
                    'role': row[1],
                    'created_at': row[2],
                    'last_login': row[3],
                    'is_active': bool(row[4])
                })
            return users
        finally:
            conn.close()
    
    def delete_user(self, username: str, deleted_by: str = None) -> Tuple[bool, str]:
        """
        Delete a user
        Returns: (success, message)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cur.fetchone():
                return False, "User not found"
            
            # Don't allow deleting the last admin
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
            admin_count = cur.fetchone()[0]
            
            cur.execute("SELECT role FROM users WHERE username = ?", (username,))
            user_role = cur.fetchone()[0]
            
            if user_role == 'admin' and admin_count <= 1:
                return False, "Cannot delete the last admin user"
            
            cur.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            
            logger.info(f"User deleted: {username} by {deleted_by or 'system'}")
            return True, "User deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, f"Error: {str(e)}"
        finally:
            conn.close()
    
    def check_password_needs_update(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user's password needs update by checking a flag in database
        Returns: (needs_update, reason)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Check if needs_password_update column exists, if not add it
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'needs_password_update' not in columns:
                # Add column and mark all existing users as needing update
                cur.execute("ALTER TABLE users ADD COLUMN needs_password_update INTEGER DEFAULT 1")
                conn.commit()
            
            # Check if user needs password update
            cur.execute("SELECT needs_password_update FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            
            if not row:
                return False, None
            
            needs_update = bool(row[0])
            
            if needs_update:
                return True, "Password does not meet current security requirements"
            
            return False, None
        finally:
            conn.close()
    
    def force_password_update(self, username: str, new_password: str, updated_by: str = None) -> Tuple[bool, str]:
        """
        Force update a user's password (admin function, bypasses old password check)
        Returns: (success, message)
        """
        # Validate password complexity
        is_valid, missing = self.validate_password_complexity(new_password)
        if not is_valid:
            error_msg = "Password does not meet complexity requirements:\n" + "\n".join(f"  • {req}" for req in missing)
            return False, error_msg
        
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cur.fetchone():
                return False, "User not found"
            
            # Update password
            salt = self._generate_salt()
            password_hash = self._hash_password(new_password, salt)
            
            # Check if needs_password_update column exists
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'needs_password_update' in columns:
                cur.execute("""
                    UPDATE users 
                    SET password_hash = ?, salt = ?, needs_password_update = 0
                    WHERE username = ?
                """, (password_hash, salt, username))
            else:
                cur.execute("""
                    UPDATE users 
                    SET password_hash = ?, salt = ?
                    WHERE username = ?
                """, (password_hash, salt, username))
            
            conn.commit()
            logger.info(f"Password force updated for: {username} by {updated_by or 'system'}")
            return True, "Password updated successfully"
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False, f"Error: {str(e)}"
        finally:
            conn.close()
    
    def create_session(self, username: str) -> str:
        """Create a new session for a user and return session token.

        Uses JWT if available (signed, survives restarts), falls back to in-memory.
        """
        jwt_mgr = _get_jwt_manager()
        if jwt_mgr is not None:
            try:
                conn = sqlite3.connect(self.db_path)
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT role FROM users WHERE username = ?", (username,))
                    row = cur.fetchone()
                    role = row[0] if row else 'viewer'
                finally:
                    conn.close()

                token_pair = jwt_mgr.create_token_pair(
                    user_id=username,
                    role=role,
                    scopes=[f'{role}:all'],
                )
                logger.info(f"JWT session created for user: {username}")
                return token_pair.access_token
            except Exception as e:
                logger.warning(f"JWT session creation failed, using fallback: {e}")

        # Fallback: in-memory session token
        session_token = secrets.token_urlsafe(32)
        active_sessions[session_token] = {
            'username': username,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        logger.info(f"In-memory session created for user: {username}")
        return session_token
    
    def validate_session(self, session_token: str, max_age_minutes: int = 480) -> Tuple[bool, Optional[str]]:
        """
        Validate a session token. Checks JWT first, then in-memory fallback.
        Returns: (is_valid, username)
        """
        if not session_token:
            return False, None

        # Try JWT validation first
        jwt_mgr = _get_jwt_manager()
        if jwt_mgr is not None:
            claims = jwt_mgr.validate_access_token(session_token)
            if claims is not None:
                return True, claims.user_id

        # Fallback: check in-memory sessions
        if session_token not in active_sessions:
            return False, None

        session = active_sessions[session_token]
        age = datetime.now() - session['last_activity']

        if age.total_seconds() > (max_age_minutes * 60):
            del active_sessions[session_token]
            return False, None

        session['last_activity'] = datetime.now()
        return True, session['username']
    
    def destroy_session(self, session_token: str):
        """Destroy a session (revoke JWT or remove from memory)."""
        # Try JWT revocation
        jwt_mgr = _get_jwt_manager()
        if jwt_mgr is not None:
            try:
                jwt_mgr.revoke_token(session_token, reason="logout")
            except Exception:
                pass

        # Also clean in-memory fallback
        if session_token in active_sessions:
            username = active_sessions[session_token]['username']
            del active_sessions[session_token]
            logger.info(f"Session destroyed for user: {username}")
    
    def get_login_history(self, username: str = None, limit: int = 50) -> List[Dict]:
        """Get login attempt history"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            if username:
                cur.execute("""
                    SELECT username, ip_address, success, timestamp
                    FROM login_attempts
                    WHERE username = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (username, limit))
            else:
                cur.execute("""
                    SELECT username, ip_address, success, timestamp
                    FROM login_attempts
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            history = []
            for row in cur.fetchall():
                history.append({
                    'username': row[0],
                    'ip_address': row[1],
                    'success': bool(row[2]),
                    'timestamp': row[3]
                })
            return history
        finally:
            conn.close()

    def verify_password(self, username: str, password: str, ip_address: str = None) -> Optional[Dict]:
        """
        Verify password and return user info if valid.

        This method is used by the JWT authentication system to verify
        credentials and get user details in one call.

        Args:
            username: The username to authenticate
            password: The password to verify
            ip_address: Optional IP address for brute force tracking

        Returns:
            Dict with user info (username, role) if valid, None otherwise
        """
        # Check brute force protection
        is_locked, remaining = self._check_brute_force(username, ip_address)
        if is_locked:
            logger.warning(f"Login attempt blocked - account locked: {username}")
            return None

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT password_hash, salt, role, is_active
                FROM users
                WHERE username = ?
            """, (username,))

            result = cur.fetchone()
            if not result:
                self._record_login_attempt(username, False, ip_address)
                return None

            password_hash, salt, role, is_active = result

            if not is_active:
                self._record_login_attempt(username, False, ip_address)
                return None

            # Verify password
            if self._verify_password(password, password_hash, salt):
                # Update last login
                cur.execute("""
                    UPDATE users SET last_login = ? WHERE username = ?
                """, (datetime.now().isoformat(), username))
                conn.commit()

                self._record_login_attempt(username, True, ip_address)
                return {
                    'username': username,
                    'role': role
                }
            else:
                self._record_login_attempt(username, False, ip_address)
                return None
        finally:
            conn.close()

    def get_session(self, session_token: str) -> Optional[Dict]:
        """
        Get session info by token. Checks JWT first, then in-memory.

        Returns:
            Dict with session info if valid, None otherwise
        """
        if not session_token:
            return None

        # Try JWT validation first
        jwt_mgr = _get_jwt_manager()
        if jwt_mgr is not None:
            claims = jwt_mgr.validate_access_token(session_token)
            if claims is not None:
                return {
                    'username': claims.user_id,
                    'role': claims.role,
                    'is_valid': True,
                    'created_at': claims.iat.isoformat() if hasattr(claims, 'iat') and claims.iat else datetime.now().isoformat(),
                    'last_activity': datetime.now().isoformat(),
                }

        # Fallback: in-memory session
        if session_token not in active_sessions:
            return None

        session = active_sessions[session_token]
        age = datetime.now() - session['last_activity']

        if age.total_seconds() > (480 * 60):
            del active_sessions[session_token]
            return None

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT role FROM users WHERE username = ?", (session['username'],))
            row = cur.fetchone()
            role = row[0] if row else 'viewer'
        finally:
            conn.close()

        session['last_activity'] = datetime.now()

        return {
            'username': session['username'],
            'role': role,
            'is_valid': True,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
        }
