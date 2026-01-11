"""
ROS2Subscriber - ROS2 Subscriber using Zenoh
"""
import uuid
from typing import Optional, Callable

from .session import ZenohSession
from .utils import ros2_to_dds_type, get_type_hash


class ROS2Subscriber:
    """ROS2 Subscriber using Zenoh"""
    
    def __init__(
        self,
        topic: str,
        msg_type: str,
        callback: Callable,
        msg_definition: str = "",
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None
    ):
        """
        Create a ROS2 subscriber
        
        Args:
            topic: ROS2 topic name
            msg_type: ROS2 message type
            callback: Callback function(msg) called when message is received
            msg_definition: Message definition text (empty string to auto-load from registry)
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Message type hash (auto-detected if None)
        """
        self.topic = topic
        self.msg_type = msg_type
        self.callback = callback
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_subscriber_{uuid.uuid4().hex[:8]}"
        
        # Get or create shared session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)
        
        # Register message type
        self.session_mgr.register_message_type(msg_definition, msg_type)
        
        # Get DDS type name
        self.dds_type_name = ros2_to_dds_type(msg_type)
        
        # Get type hash if not provided
        if type_hash is None:
            # Get message definition for hash computation
            hash_msg_definition = msg_definition
            if not hash_msg_definition:
                # Try to get from message registry
                try:
                    from .message_registry import get_registry
                    registry = get_registry()
                    msg_file = registry.get_msg_file_path(msg_type)
                    if msg_file and msg_file.exists():
                        with open(msg_file, 'r') as f:
                            hash_msg_definition = f.read()
                except Exception:
                    pass
            
            if not hash_msg_definition:
                raise ValueError(
                    f"Cannot compute type hash for {msg_type}: message definition not provided. "
                    "Please provide msg_definition or ensure the message type is loaded in the registry."
                )
            
            # Get dependencies from message registry if available
            dependencies = None
            try:
                from .message_registry import get_registry
                registry = get_registry()
                # Extract dependencies - for nested types, we need to load them
            except Exception:
                pass
            
            type_hash = get_type_hash(msg_type, msg_definition=hash_msg_definition, dependencies=dependencies)
        self.type_hash = type_hash
        
        # Build keyexpr
        fully_qualified_name = topic.lstrip("/")
        self.keyexpr = f"{domain_id}/{fully_qualified_name}/{self.dds_type_name}/{type_hash}"
        
        # Create subscriber
        self.sub = self.session_mgr.session.declare_subscriber(self.keyexpr, self._listener)
    
    def _listener(self, sample):
        """Internal message listener"""
        try:
            cdr_bytes = bytes(sample.payload)
            msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.msg_type)
            self.callback(msg)
        except Exception as e:
            print(f"Error deserializing message: {e}")
    
    def close(self):
        """Close the subscriber"""
        # Subscriber will be closed when session closes
        pass
