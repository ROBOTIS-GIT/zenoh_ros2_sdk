"""
ROS2Publisher - ROS2 Publisher using Zenoh
"""
import zenoh
from zenoh import Encoding
import time
import struct
import uuid
from typing import Optional

from .session import ZenohSession
from .utils import ros2_to_dds_type, get_type_hash, mangle_name


class ROS2Publisher:
    """ROS2 Publisher using Zenoh - appears in ros2 topic list"""
    
    def __init__(
        self,
        topic: str,
        msg_type: str,
        msg_definition: str,
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None
    ):
        """
        Create a ROS2 publisher
        
        Args:
            topic: ROS2 topic name (e.g., "/chatter")
            msg_type: ROS2 message type (e.g., "std_msgs/msg/String")
            msg_definition: Message definition text
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Message type hash (auto-detected if None)
        """
        self.topic = topic
        self.msg_type = msg_type
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_publisher_{uuid.uuid4().hex[:8]}"
        
        # Get or create shared session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)
        
        # Register message type
        self.msg_class = self.session_mgr.register_message_type(msg_definition, msg_type)
        
        # Get DDS type name (convert ROS2 type to DDS format)
        self.dds_type_name = ros2_to_dds_type(msg_type)
        
        # Get type hash if not provided
        if type_hash is None:
            type_hash = get_type_hash(msg_type)
        self.type_hash = type_hash
        
        # Generate unique GID for this publisher
        self.publisher_gid = self.session_mgr.generate_gid()
        
        # Get node and entity IDs
        self.node_id = self.session_mgr.get_next_node_id()
        self.entity_id = self.session_mgr.get_next_entity_id()
        
        # Build keyexpr
        fully_qualified_name = topic.lstrip("/")
        self.keyexpr = f"{domain_id}/{fully_qualified_name}/{self.dds_type_name}/{type_hash}"
        
        # Declare liveliness tokens
        self._declare_liveliness_tokens()
        
        # Create publisher
        self.pub = self.session_mgr.session.declare_publisher(self.keyexpr)
        
        # Message counter
        self.sequence_number = 0
    
    def _declare_liveliness_tokens(self):
        """Declare liveliness tokens for ROS2 discovery"""
        mangled_enclave = "%"
        mangled_namespace = mangle_name(self.namespace)
        mangled_topic = mangle_name(self.topic)
        qos = "::,7:,:,:,,"  # Default QoS
        
        # Node token
        node_token_keyexpr = (
            f"@ros2_lv/{self.domain_id}/{self.session_mgr.session_id}/"
            f"{self.node_id}/{self.node_id}/NN/{mangled_enclave}/"
            f"{mangled_namespace}/{self.node_name}"
        )
        
        # Publisher token
        publisher_token_keyexpr = (
            f"@ros2_lv/{self.domain_id}/{self.session_mgr.session_id}/"
            f"{self.node_id}/{self.entity_id}/MP/{mangled_enclave}/"
            f"{mangled_namespace}/{self.node_name}/{mangled_topic}/"
            f"{self.dds_type_name}/{self.type_hash}/{qos}"
        )
        
        self.node_token = self.session_mgr.liveliness.declare_token(node_token_keyexpr)
        self.publisher_token = self.session_mgr.liveliness.declare_token(publisher_token_keyexpr)
    
    def _create_attachment(self, seq_num: int, timestamp_ns: int) -> bytes:
        """Create rmw_zenoh attachment"""
        attachment = struct.pack('<Q', seq_num)  # sequence number
        attachment += struct.pack('<Q', timestamp_ns)  # timestamp
        attachment += struct.pack('B', len(self.publisher_gid))  # GID length
        attachment += self.publisher_gid  # GID
        return attachment
    
    def publish(self, **kwargs):
        """
        Publish a message
        
        Args:
            **kwargs: Message field values (e.g., data="hello" for String message)
        """
        # Create message instance
        msg = self.msg_class(**kwargs)
        
        # Serialize to CDR
        cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(msg, self.msg_type))
        
        # Create attachment
        timestamp_ns = int(time.time() * 1e9)
        attachment = self._create_attachment(self.sequence_number, timestamp_ns)
        
        # Publish
        self.pub.put(cdr_bytes, encoding=Encoding("application/cdr"), attachment=attachment)
        self.sequence_number += 1
    
    def close(self):
        """Close the publisher and undeclare tokens"""
        try:
            self.node_token.undeclare()
            self.publisher_token.undeclare()
        except:
            pass
