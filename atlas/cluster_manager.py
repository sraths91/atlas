"""
Fleet Server Cluster Manager - High Availability Support

This module enables running multiple fleet server instances in a cluster
for redundancy, load balancing, and high availability.

Features:
- Node registration and discovery
- Health monitoring and heartbeats
- Shared session storage
- Automatic failover
- Cluster status monitoring
"""
import json
import time
import socket
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Import cluster security
try:
    from .cluster_security import ClusterSecurity
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    ClusterSecurity = None
    logger.warning("Cluster security module not available")


class ClusterNode:
    """Represents a single node in the cluster"""
    
    def __init__(self, node_id: str, hostname: str, port: int, 
                 is_leader: bool = False, metadata: Optional[Dict] = None):
        self.node_id = node_id
        self.hostname = hostname
        self.port = port
        self.is_leader = is_leader
        self.metadata = metadata or {}
        self.last_heartbeat = datetime.now()
        self.status = 'active'
        self.version = '1.0.0'
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary"""
        return {
            'node_id': self.node_id,
            'hostname': self.hostname,
            'port': self.port,
            'is_leader': self.is_leader,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'metadata': self.metadata,
            'version': self.version,
            'url': f"https://{self.hostname}:{self.port}"
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ClusterNode':
        """Create node from dictionary"""
        node = ClusterNode(
            node_id=data['node_id'],
            hostname=data['hostname'],
            port=data['port'],
            is_leader=data.get('is_leader', False),
            metadata=data.get('metadata', {})
        )
        node.status = data.get('status', 'active')
        node.version = data.get('version', '1.0.0')
        if 'last_heartbeat' in data:
            node.last_heartbeat = datetime.fromisoformat(data['last_heartbeat'])
        return node


class ClusterManager:
    """
    Manages cluster operations for high availability
    
    Supports:
    - SQLite-based cluster state (shared via network filesystem)
    - Redis-based cluster state (recommended for production)
    - File-based cluster state (development/testing)
    """
    
    def __init__(self, node_id: str = None, cluster_config: Dict[str, Any] = None):
        """
        Initialize cluster manager
        
        Args:
            node_id: Unique identifier for this node (auto-generated if None)
            cluster_config: Cluster configuration dictionary
        """
        self.node_id = node_id or self._generate_node_id()
        self.config = cluster_config or {}
        self.enabled = self.config.get('enabled', False)
        
        # Cluster storage backend
        self.backend = self.config.get('backend', 'file')  # file, sqlite, redis
        state_path = self.config.get('state_path', '~/.fleet-cluster/cluster-state.json')
        self.state_path = str(Path(state_path).expanduser())
        
        # Heartbeat settings
        self.heartbeat_interval = self.config.get('heartbeat_interval', 10)  # seconds
        self.node_timeout = self.config.get('node_timeout', 30)  # seconds
        
        # Node info
        self.hostname = self.config.get('hostname') or socket.gethostname()
        self.port = self.config.get('port', 8778)
        
        # State
        self.nodes: Dict[str, ClusterNode] = {}
        self.lock = threading.Lock()
        self.running = False
        self.heartbeat_thread = None
        
        # Redis connection (if using Redis backend)
        self.redis_client = None
        if self.backend == 'redis':
            self._init_redis()
        
        # Initialize cluster security
        self.security = None
        cluster_secret = self.config.get('cluster_secret')
        if SECURITY_AVAILABLE and cluster_secret:
            self.security = ClusterSecurity(cluster_secret)
            security_status = self.security.get_security_status()
            logger.info(f"Cluster security: {security_status['authentication']}")
        elif self.enabled:
            logger.warning(" Cluster authentication DISABLED - nodes can join without verification!")
            logger.warning(" Add 'cluster_secret' to config for node authentication")
        
        # Initialize storage
        if self.enabled:
            self._init_storage()
            self._register_self()
        
        logger.info(f"Cluster manager initialized (node_id: {self.node_id}, enabled: {self.enabled})")
    
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        import uuid
        hostname = socket.gethostname()
        return f"{hostname}-{uuid.uuid4().hex[:8]}"
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            redis_host = self.config.get('redis_host', 'localhost')
            redis_port = self.config.get('redis_port', 6379)
            redis_db = self.config.get('redis_db', 0)
            redis_password = self.config.get('redis_password')
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except ImportError:
            logger.error("Redis backend selected but redis-py not installed. Install with: pip install redis")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False
    
    def _init_storage(self):
        """Initialize cluster state storage"""
        if self.backend == 'file':
            state_path = Path(self.state_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            if not state_path.exists():
                self._save_state({'nodes': {}})
    
    def _register_self(self):
        """Register this node in the cluster"""
        node = ClusterNode(
            node_id=self.node_id,
            hostname=self.hostname,
            port=self.port,
            metadata={
                'pid': os.getpid(),
                'started_at': datetime.now().isoformat()
            }
        )
        
        with self.lock:
            self.nodes[self.node_id] = node
            self._save_state()
        
        logger.info(f"Registered node in cluster: {self.node_id}")
    
    def _save_state(self, state: Optional[Dict] = None):
        """Save cluster state to backend"""
        if not self.enabled:
            return
        
        if state is None:
            state = {
                'nodes': {nid: node.to_dict() for nid, node in self.nodes.items()},
                'updated_at': datetime.now().isoformat()
            }
        
        try:
            if self.backend == 'file':
                with open(self.state_path, 'w') as f:
                    json.dump(state, f, indent=2)
            
            elif self.backend == 'redis' and self.redis_client:
                # Store each node as a separate Redis key with TTL
                for node_id, node_data in state.get('nodes', {}).items():
                    key = f"fleet:cluster:node:{node_id}"
                    
                    # Sign node data if security is enabled
                    if self.security:
                        node_data = self.security.sign_node_data(node_data)
                    
                    self.redis_client.setex(
                        key,
                        self.node_timeout * 2,  # TTL longer than timeout
                        json.dumps(node_data)
                    )
                # Store cluster metadata
                self.redis_client.set('fleet:cluster:updated_at', state.get('updated_at'))
        
        except Exception as e:
            logger.error(f"Failed to save cluster state: {e}")
    
    def _load_state(self) -> Dict[str, Any]:
        """Load cluster state from backend"""
        if not self.enabled:
            return {'nodes': {}}
        
        try:
            if self.backend == 'file':
                state_path = Path(self.state_path)
                if state_path.exists():
                    with open(state_path, 'r') as f:
                        return json.load(f)
            
            elif self.backend == 'redis' and self.redis_client:
                # Load all node keys
                nodes = {}
                for key in self.redis_client.keys('fleet:cluster:node:*'):
                    node_data = json.loads(self.redis_client.get(key))
                    
                    # Verify signature if security is enabled
                    if self.security:
                        valid, error = self.security.verify_node_data(node_data)
                        if not valid:
                            logger.warning(f"Rejecting node {node_data.get('node_id', 'unknown')}: {error}")
                            continue  # Skip invalid node
                        # Remove security metadata before using
                        node_data = {k: v for k, v in node_data.items() 
                                   if not k.startswith('_')}
                    
                    nodes[node_data['node_id']] = node_data
                
                updated_at = self.redis_client.get('fleet:cluster:updated_at')
                return {
                    'nodes': nodes,
                    'updated_at': updated_at
                }
        
        except Exception as e:
            logger.error(f"Failed to load cluster state: {e}")
        
        return {'nodes': {}}
    
    def update_heartbeat(self):
        """Update this node's heartbeat timestamp"""
        if not self.enabled:
            return
        
        with self.lock:
            if self.node_id in self.nodes:
                self.nodes[self.node_id].last_heartbeat = datetime.now()
                self.nodes[self.node_id].status = 'active'
                self._save_state()
    
    def get_active_nodes(self) -> List[ClusterNode]:
        """Get list of active nodes in the cluster"""
        if not self.enabled:
            return []
        
        # Reload state to get updates from other nodes
        state = self._load_state()
        
        with self.lock:
            # Update nodes from state
            for node_id, node_data in state.get('nodes', {}).items():
                if node_id not in self.nodes or node_id != self.node_id:
                    self.nodes[node_id] = ClusterNode.from_dict(node_data)
            
            # Check for expired nodes
            now = datetime.now()
            active_nodes = []
            
            for node in self.nodes.values():
                age = (now - node.last_heartbeat).total_seconds()
                if age < self.node_timeout:
                    node.status = 'active'
                    active_nodes.append(node)
                else:
                    node.status = 'inactive'
                    logger.warning(f"Node {node.node_id} appears inactive (last heartbeat: {age}s ago)")
            
            return active_nodes
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information"""
        if not self.enabled:
            return {
                'enabled': False,
                'message': 'Cluster mode not enabled'
            }
        
        active_nodes = self.get_active_nodes()
        
        return {
            'enabled': True,
            'node_id': self.node_id,
            'backend': self.backend,
            'total_nodes': len(self.nodes),
            'active_nodes': len(active_nodes),
            'inactive_nodes': len(self.nodes) - len(active_nodes),
            'nodes': [node.to_dict() for node in active_nodes],
            'this_node': {
                'node_id': self.node_id,
                'hostname': self.hostname,
                'port': self.port,
                'status': 'active'
            }
        }
    
    def _heartbeat_loop(self):
        """Background thread for sending heartbeats"""
        logger.info(f"Heartbeat thread started (interval: {self.heartbeat_interval}s)")
        
        while self.running:
            try:
                self.update_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(self.heartbeat_interval)
    
    def start(self):
        """Start cluster management (heartbeats, monitoring)"""
        if not self.enabled:
            logger.info("Cluster mode not enabled, skipping cluster management")
            return
        
        if self.running:
            logger.warning("Cluster manager already running")
            return
        
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        logger.info(f"Cluster manager started for node: {self.node_id}")
    
    def stop(self):
        """Stop cluster management"""
        if not self.enabled or not self.running:
            return
        
        logger.info("Stopping cluster manager...")
        self.running = False
        
        # Mark self as inactive
        with self.lock:
            if self.node_id in self.nodes:
                self.nodes[self.node_id].status = 'stopped'
                self._save_state()
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        logger.info("Cluster manager stopped")
    
    def get_best_node(self) -> Optional[ClusterNode]:
        """Get the best node for load balancing (simple round-robin)"""
        active_nodes = self.get_active_nodes()
        if not active_nodes:
            return None
        
        # Simple: return first active node (load balancer should handle distribution)
        return active_nodes[0]
    
    def is_healthy(self) -> bool:
        """Check if this node is healthy"""
        if not self.enabled:
            return True  # Single node mode is always "healthy"
        
        # Check if we can update heartbeat
        try:
            self.update_heartbeat()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global cluster manager instance
_cluster_manager = None


def init_cluster_manager(config: Dict[str, Any]) -> ClusterManager:
    """Initialize global cluster manager"""
    global _cluster_manager
    _cluster_manager = ClusterManager(cluster_config=config)
    return _cluster_manager


def get_cluster_manager() -> Optional[ClusterManager]:
    """Get global cluster manager instance"""
    return _cluster_manager
