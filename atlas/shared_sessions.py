"""
Shared Session Storage for Cluster Mode

Provides shared session management across multiple server instances
to enable seamless user authentication in a cluster environment.

Supported backends:
- Redis (recommended for production)
- SQLite (shared via network filesystem)
- File-based (development only)
"""
import json
import time
import hashlib
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SessionStore:
    """Base class for session storage"""
    
    def create_session(self, username: str, session_data: Dict[str, Any] = None) -> str:
        """Create a new session and return session ID"""
        raise NotImplementedError
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID"""
        raise NotImplementedError
    
    def update_session(self, session_id: str, session_data: Dict[str, Any]):
        """Update session data"""
        raise NotImplementedError
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        raise NotImplementedError
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        raise NotImplementedError


class FileSessionStore(SessionStore):
    """File-based session storage (development only)"""

    def __init__(self, session_dir: str = '~/.fleet-cluster/sessions', ttl: int = 3600):
        self.session_dir = Path(session_dir).expanduser()
        self.ttl = ttl
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        logger.info(f"File-based session store initialized: {self.session_dir}")

    def _generate_session_id(self, username: str) -> str:
        """Generate session ID"""
        import uuid
        timestamp = str(time.time())
        data = f"{username}:{timestamp}:{uuid.uuid4().hex}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _session_path(self, session_id: str) -> Path:
        """Get file path for session"""
        return self.session_dir / f"{session_id}.json"
    
    def create_session(self, username: str, session_data: Dict[str, Any] = None) -> str:
        """Create new session"""
        session_id = self._generate_session_id(username)
        
        data = {
            'session_id': session_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=self.ttl)).isoformat(),
            'data': session_data or {}
        }
        
        with self.lock:
            with open(self._session_path(session_id), 'w') as f:
                json.dump(data, f)
        
        logger.debug(f"Created session for {username}: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_path = self._session_path(session_id)

        with self.lock:
            if not session_path.exists():
                return None

            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)

                # Check expiration
                expires_at = datetime.fromisoformat(data['expires_at'])
                if datetime.now() > expires_at:
                    session_path.unlink()
                    return None

                return data
            except Exception as e:
                logger.error(f"Error reading session {session_id}: {e}")
                return None
    
    def update_session(self, session_id: str, session_data: Dict[str, Any]):
        """Update session"""
        data = self.get_session(session_id)
        if data:
            data['data'].update(session_data)
            data['expires_at'] = (datetime.now() + timedelta(seconds=self.ttl)).isoformat()
            
            with self.lock:
                with open(self._session_path(session_id), 'w') as f:
                    json.dump(data, f)
    
    def delete_session(self, session_id: str):
        """Delete session"""
        session_path = self._session_path(session_id)
        with self.lock:
            if session_path.exists():
                session_path.unlink()
                logger.debug(f"Deleted session: {session_id}")

    def cleanup_expired(self):
        """Remove expired sessions"""
        now = datetime.now()
        count = 0

        with self.lock:
            for filepath in self.session_dir.glob('*.json'):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if now > expires_at:
                        filepath.unlink()
                        count += 1
                except Exception:
                    pass

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")


class SQLiteSessionStore(SessionStore):
    """SQLite-based session storage (shared filesystem)"""

    def __init__(self, db_path: str = '~/.fleet-cluster/sessions.db', ttl: int = 3600):
        db_path_obj = Path(db_path).expanduser()
        self.db_path = str(db_path_obj)
        self.ttl = ttl
        self.lock = threading.Lock()
        self._init_db()
        logger.info(f"SQLite session store initialized: {self.db_path}")

    def _init_db(self):
        """Initialize database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    data_json TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_expires ON sessions(expires_at)')
            conn.commit()
        finally:
            conn.close()
    
    def _generate_session_id(self, username: str) -> str:
        """Generate session ID"""
        import uuid
        timestamp = str(time.time())
        data = f"{username}:{timestamp}:{uuid.uuid4().hex}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def create_session(self, username: str, session_data: Dict[str, Any] = None) -> str:
        """Create new session"""
        session_id = self._generate_session_id(username)
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.ttl)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('''
                    INSERT INTO sessions (session_id, username, data_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    username,
                    json.dumps(session_data or {}),
                    now.isoformat(),
                    expires_at.isoformat()
                ))
                conn.commit()
            finally:
                conn.close()
        
        logger.debug(f"Created session for {username}: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.execute('''
                    SELECT * FROM sessions WHERE session_id = ? AND expires_at > ?
                ''', (session_id, datetime.now().isoformat()))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                return {
                    'session_id': row['session_id'],
                    'username': row['username'],
                    'created_at': row['created_at'],
                    'expires_at': row['expires_at'],
                    'data': json.loads(row['data_json']) if row['data_json'] else {}
                }
            finally:
                conn.close()
    
    def update_session(self, session_id: str, session_data: Dict[str, Any]):
        """Update session"""
        expires_at = datetime.now() + timedelta(seconds=self.ttl)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # Get existing data
                cur = conn.execute('SELECT data_json FROM sessions WHERE session_id = ?', (session_id,))
                row = cur.fetchone()
                if row:
                    existing_data = json.loads(row[0]) if row[0] else {}
                    existing_data.update(session_data)
                    
                    conn.execute('''
                        UPDATE sessions 
                        SET data_json = ?, expires_at = ?
                        WHERE session_id = ?
                    ''', (json.dumps(existing_data), expires_at.isoformat(), session_id))
                    conn.commit()
            finally:
                conn.close()
    
    def delete_session(self, session_id: str):
        """Delete session"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                conn.commit()
                logger.debug(f"Deleted session: {session_id}")
            finally:
                conn.close()
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cur = conn.execute('DELETE FROM sessions WHERE expires_at < ?', 
                                 (datetime.now().isoformat(),))
                count = cur.rowcount
                conn.commit()
                if count > 0:
                    logger.info(f"Cleaned up {count} expired sessions")
            finally:
                conn.close()


class RedisSessionStore(SessionStore):
    """Redis-based session storage (recommended for production)"""
    
    def __init__(self, redis_config: Dict[str, Any], ttl: int = 3600):
        self.ttl = ttl
        self.redis_client = None
        self._init_redis(redis_config)
        logger.info("Redis session store initialized")
    
    def _init_redis(self, config: Dict[str, Any]):
        """Initialize Redis connection"""
        try:
            import redis
            host = config.get('host', 'localhost')
            port = config.get('port', 6379)
            db = config.get('db', 0)
            password = config.get('password')
            
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except ImportError:
            logger.error("Redis backend selected but redis-py not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _generate_session_id(self, username: str) -> str:
        """Generate session ID"""
        import uuid
        timestamp = str(time.time())
        data = f"{username}:{timestamp}:{uuid.uuid4().hex}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def create_session(self, username: str, session_data: Dict[str, Any] = None) -> str:
        """Create new session"""
        session_id = self._generate_session_id(username)
        
        data = {
            'session_id': session_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'data': session_data or {}
        }
        
        key = f"fleet:session:{session_id}"
        self.redis_client.setex(key, self.ttl, json.dumps(data))
        
        logger.debug(f"Created session for {username}: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        key = f"fleet:session:{session_id}"
        data = self.redis_client.get(key)
        
        if not data:
            return None
        
        return json.loads(data)
    
    def update_session(self, session_id: str, session_data: Dict[str, Any]):
        """Update session"""
        data = self.get_session(session_id)
        if data:
            data['data'].update(session_data)
            key = f"fleet:session:{session_id}"
            self.redis_client.setex(key, self.ttl, json.dumps(data))
    
    def delete_session(self, session_id: str):
        """Delete session"""
        key = f"fleet:session:{session_id}"
        self.redis_client.delete(key)
        logger.debug(f"Deleted session: {session_id}")
    
    def cleanup_expired(self):
        """Redis automatically expires keys, no cleanup needed"""
        pass


def create_session_store(config: Dict[str, Any]) -> SessionStore:
    """
    Create session store based on configuration
    
    Args:
        config: Session configuration dict with 'backend' key
    
    Returns:
        SessionStore instance
    """
    backend = config.get('backend', 'file')
    ttl = config.get('ttl', 3600)
    
    if backend == 'redis':
        redis_config = config.get('redis', {})
        return RedisSessionStore(redis_config, ttl)
    
    elif backend == 'sqlite':
        db_path = config.get('db_path', '~/.fleet-cluster/sessions.db')
        return SQLiteSessionStore(db_path, ttl)
    
    else:  # file
        session_dir = config.get('session_dir', '~/.fleet-cluster/sessions')
        return FileSessionStore(session_dir, ttl)


# Global session store
_session_store = None


def init_session_store(config: Dict[str, Any]) -> SessionStore:
    """Initialize global session store"""
    global _session_store
    _session_store = create_session_store(config)
    return _session_store


def get_session_store() -> Optional[SessionStore]:
    """Get global session store instance"""
    return _session_store
