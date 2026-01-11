"""
ZenohSession - Manages shared Zenoh session and type store
"""
import zenoh
import uuid
import threading
from rosbags.typesys import get_types_from_msg, get_typestore, Stores
from .message_registry import get_registry


class ZenohSession:
    """Manages a shared Zenoh session and type store"""
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, router_ip: str = "127.0.0.1", router_port: int = 7447):
        self.router_ip = router_ip
        self.router_port = router_port
        self.conf = zenoh.Config()
        self.conf.insert_json5("connect/endpoints", f'["tcp/{router_ip}:{router_port}"]')
        self.session = zenoh.open(self.conf)
        self.store = get_typestore(Stores.EMPTY)
        self._registered_types = {}
        self._node_counter = 0
        self._entity_counter = 0
        self._lock = threading.Lock()
        
        # Get session ID
        session_info = self.session.info
        self.session_id = str(session_info.zid())
        self.liveliness = self.session.liveliness()
    
    @classmethod
    def get_instance(cls, router_ip: str = "127.0.0.1", router_port: int = 7447):
        """Get or create singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(router_ip, router_port)
        return cls._instance
    
    def register_message_type(self, msg_definition: str, ros2_type_name: str):
        """Register a ROS2 message type"""
        if ros2_type_name not in self._registered_types:
            # If msg_definition is empty, try to load from message registry
            if not msg_definition.strip():
                registry = get_registry()
                if registry.is_loaded(ros2_type_name):
                    # Already loaded, just return the class
                    return self.store.types.get(ros2_type_name)
                elif registry.load_message_type(ros2_type_name):
                    # Successfully loaded from registry
                    return self.store.types.get(ros2_type_name)
                else:
                    raise ValueError(f"Message type {ros2_type_name} not found in registry and no definition provided")
            
            types = get_types_from_msg(msg_definition, ros2_type_name)
            self.store.register(types)
            self._registered_types[ros2_type_name] = types
        return self.store.types[ros2_type_name]
    
    def get_next_node_id(self):
        """Get next available node ID"""
        with self._lock:
            node_id = self._node_counter
            self._node_counter += 1
            return node_id
    
    def get_next_entity_id(self):
        """Get next available entity ID"""
        with self._lock:
            entity_id = self._entity_counter
            self._entity_counter += 1
            return entity_id
    
    def generate_gid(self) -> bytes:
        """Generate a unique GID (16 bytes)"""
        # Use UUID to generate unique GID
        uuid_bytes = uuid.uuid4().bytes
        return uuid_bytes
    
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
            self._instance = None
