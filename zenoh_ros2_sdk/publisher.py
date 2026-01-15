"""
ROS2Publisher - ROS2 Publisher using Zenoh
"""
from zenoh import Encoding
import time
import struct
import uuid
from typing import Any, Optional

from .session import ZenohSession
from .utils import ros2_to_dds_type, get_type_hash, load_dependencies_recursive
from .entity import EntityKind, NodeEntity, EndpointEntity
from .keyexpr import topic_keyexpr, node_liveliness_keyexpr, endpoint_liveliness_keyexpr
from .qos import QosProfile, QosReliability, QosDurability, DEFAULT_QOS_PROFILE
from .message_registry import get_registry
from .logger import get_logger

logger = get_logger("publisher")


class ROS2Publisher:
    """ROS2 Publisher using Zenoh.

    This publisher:
    - Publishes CDR-encoded messages on a Zenoh key expression:
      `<domain_id>/<topic>/<dds_type_name>/<type_hash>`
    - Declares `@ros2_lv/.../NN` and `@ros2_lv/.../MP` liveliness tokens so it appears in ROS graph tools.
    """

    def __init__(
        self,
        topic: str,
        msg_type: str,
        msg_definition: str = "",
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None,
        qos: Optional[object] = None,
        strict_zenoh_qos: bool = False,
    ):
        """
        Create a ROS2 publisher.

        Args:
            topic: ROS2 topic name (e.g., "/chatter")
            msg_type: ROS2 message type (e.g., "std_msgs/msg/String")
            msg_definition: Message definition text (empty string to auto-load from registry)
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Message type hash (auto-detected if None)
            qos: QoS used for liveliness discovery tokens and (best-effort) Zenoh publisher settings.
                Accepts `QosProfile`, an encoded rmw_zenoh QoS string, or `None` for default.
            strict_zenoh_qos: If True, raise if the Zenoh Python API cannot apply QoS mapping
                (e.g., `congestion_control` / `express` options).

        Raises:
            ValueError: If the type hash cannot be computed because message definitions are missing.
            RuntimeError: If `strict_zenoh_qos=True` and QoS mapping cannot be applied.
        """
        self.topic = topic
        self.msg_type = msg_type
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_publisher_{uuid.uuid4().hex[:8]}"
        self.strict_zenoh_qos = strict_zenoh_qos
        # QoS is used both for liveliness tokens and (best-effort) mapping to Zenoh settings.
        self.qos_profile, self.qos = self._normalize_qos(qos, default=DEFAULT_QOS_PROFILE)

        # Get or create shared session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)

        # Register message type
        self.msg_class = self.session_mgr.register_message_type(msg_definition, msg_type)

        # Get DDS type name (convert ROS2 type to DDS format)
        self.dds_type_name = ros2_to_dds_type(msg_type)

        # Get type hash if not provided
        if type_hash is None:
            # Get message definition for hash computation
            hash_msg_definition = msg_definition
            if not hash_msg_definition:
                # Try to get from message registry
                try:
                    registry = get_registry()
                    msg_file = registry.get_msg_file_path(msg_type)
                    if msg_file and msg_file.exists():
                        with open(msg_file, 'r') as f:
                            hash_msg_definition = f.read()
                except Exception as e:
                    # Registry not available or file not found - will raise ValueError below
                    logger.debug(f"Could not load message definition from registry for {msg_type}: {e}")
                    pass

            if not hash_msg_definition:
                raise ValueError(
                    f"Cannot compute type hash for {msg_type}: message definition not provided. "
                    "Please provide msg_definition or ensure the message type is loaded in the registry."
                )

            # Get dependencies from message registry if available (recursively)
            dependencies = None
            try:
                registry = get_registry()
                # Load all dependencies recursively using shared utility function
                dependencies = load_dependencies_recursive(msg_type, hash_msg_definition, registry)
            except Exception as e:
                # If dependency loading fails, continue without dependencies
                # Type hash computation will still work, just without nested type info
                logger.debug(f"Could not load dependencies for {msg_type}: {e}")
                pass

            type_hash = get_type_hash(msg_type, msg_definition=hash_msg_definition, dependencies=dependencies)
        self.type_hash = type_hash

        # Generate unique GID for this publisher
        self.publisher_gid = self.session_mgr.generate_gid()

        # Get node and entity IDs
        self.node_id = self.session_mgr.get_next_node_id()
        self.entity_id = self.session_mgr.get_next_entity_id()

        # Build keyexpr
        self.keyexpr = topic_keyexpr(domain_id, topic, self.dds_type_name, type_hash)

        # Declare liveliness tokens
        self._declare_liveliness_tokens()

        # Create publisher
        self._put_extra_kwargs = {}
        self.pub = self._declare_zenoh_publisher(self.keyexpr)

        # Message counter
        self.sequence_number = 0
        self._closed = False

    def _declare_liveliness_tokens(self):
        """Declare liveliness tokens for ROS2 discovery"""
        node = NodeEntity(
            domain_id=self.domain_id,
            session_id=self.session_mgr.session_id,
            node_id=self.node_id,
            node_name=self.node_name,
            namespace=self.namespace,
        )
        ep = EndpointEntity(
            node=node,
            entity_id=self.entity_id,
            kind=EntityKind.PUBLISHER,
            name=self.topic,
            dds_type_name=self.dds_type_name,
            type_hash=self.type_hash,
            qos=self.qos,
            gid=self.publisher_gid,
        )

        self.node_token = self.session_mgr.liveliness.declare_token(node_liveliness_keyexpr(node))
        self.publisher_token = self.session_mgr.liveliness.declare_token(endpoint_liveliness_keyexpr(ep))

    @staticmethod
    def _normalize_qos(qos: Optional[object], *, default: QosProfile) -> tuple[QosProfile, str]:
        """
        Accept either:
        - QosProfile
        - encoded rmw_zenoh QoS string
        - None (use default)
        """
        if qos is None:
            prof = default
            return prof, prof.encode()
        if isinstance(qos, QosProfile):
            return qos, qos.encode()
        if isinstance(qos, str):
            # User provided an authoritative encoded QoS string. It must be parseable.
            return QosProfile.decode(qos), qos
        return default, default.encode()

    def _declare_zenoh_publisher(self, keyexpr: str):
        """
        Best-effort QoS -> Zenoh mapping (similar to ros-z):
        - Reliable => congestion_control=Block
        - BestEffort => congestion_control=Drop
        - TransientLocal => express=True
        - Volatile => express=False

        Zenoh Python APIs differ across versions; we attempt common kwargs and
        fall back to passing them at put-time (or not at all).
        """
        # Resolve Zenoh congestion control enum if available.
        cc = None
        try:
            import zenoh
            qos_mod = getattr(zenoh, "qos", None)
            cc_enum = getattr(qos_mod, "CongestionControl", None) if qos_mod is not None else None
            if cc_enum is not None:
                if self.qos_profile.reliability == QosReliability.RELIABLE:
                    cc = getattr(cc_enum, "Block", None) or getattr(cc_enum, "BLOCK", None)
                else:
                    cc = getattr(cc_enum, "Drop", None) or getattr(cc_enum, "DROP", None)
        except Exception:
            cc = None

        express = self.qos_profile.durability == QosDurability.TRANSIENT_LOCAL

        # Try passing options at declaration time.
        try:
            return self.session_mgr.session.declare_publisher(
                keyexpr,
                congestion_control=cc,
                express=express,
            )
        except TypeError:
            msg = (
                "Your Zenoh Python API does not support setting publisher QoS options "
                "(congestion_control/express) at declare-time. "
                "QoS token encoding will still be correct, but runtime QoS->Zenoh mapping may not be applied. "
                "Upgrade zenoh-python or set strict_zenoh_qos=False to continue with best-effort behavior."
            )
            if self.strict_zenoh_qos:
                raise RuntimeError(msg)
            logger.warning(msg)

            # Best-effort: fall back to plain publisher and attempt passing options at put-time.
            pub = self.session_mgr.session.declare_publisher(keyexpr)
            if cc is not None:
                self._put_extra_kwargs["congestion_control"] = cc
            self._put_extra_kwargs["express"] = express
            return pub

    def _create_attachment(self, seq_num: int, timestamp_ns: int) -> bytes:
        """Create rmw_zenoh attachment"""
        attachment = struct.pack('<Q', seq_num)  # sequence number
        attachment += struct.pack('<Q', timestamp_ns)  # timestamp
        attachment += struct.pack('B', len(self.publisher_gid))  # GID length
        attachment += self.publisher_gid  # GID
        return attachment

    def publish(self, **kwargs: Any) -> None:
        """
        Publish a message.

        Args:
            **kwargs: Message field values (e.g., data="hello" for String message)

        Raises:
            RuntimeError: If `strict_zenoh_qos=True` and QoS mapping cannot be applied by the Zenoh API.
        """
        # Create message instance
        msg = self.msg_class(**kwargs)

        # Serialize to CDR
        cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(msg, self.msg_type))

        # Create attachment
        timestamp_ns = int(time.time() * 1e9)
        attachment = self._create_attachment(self.sequence_number, timestamp_ns)

        # Publish (best-effort QoS passthrough for Zenoh implementations that accept it)
        try:
            self.pub.put(
                cdr_bytes,
                encoding=Encoding("application/cdr"),
                attachment=attachment,
                **self._put_extra_kwargs,
            )
        except TypeError:
            # Zenoh Python API version doesn't accept extra kwargs on put()
            if self._put_extra_kwargs:
                msg = (
                    "Your Zenoh Python API does not accept QoS-related kwargs on publisher.put(). "
                    f"Unable to apply requested QoS->Zenoh mapping at runtime. kwargs={list(self._put_extra_kwargs.keys())}"
                )
                if self.strict_zenoh_qos:
                    raise RuntimeError(msg)
                logger.warning(msg)
            self.pub.put(cdr_bytes, encoding=Encoding("application/cdr"), attachment=attachment)
        self.sequence_number += 1

    def close(self):
        """
        Close the publisher and undeclare tokens.

        This method is idempotent - it's safe to call multiple times.
        """
        # Check if already closed
        if hasattr(self, '_closed') and self._closed:
            return

        try:
            if hasattr(self, 'node_token') and self.node_token is not None:
                self.node_token.undeclare()
            if hasattr(self, 'publisher_token') and self.publisher_token is not None:
                self.publisher_token.undeclare()
            # Optionally undeclare the publisher itself (though tokens are the main cleanup)
            if hasattr(self, 'pub') and self.pub is not None:
                if hasattr(self.pub, 'undeclare'):
                    self.pub.undeclare()
                self.pub = None
            self._closed = True
        except (AttributeError, RuntimeError) as e:
            # AttributeError: token doesn't exist
            # RuntimeError: Zenoh runtime errors
            logger.debug(f"Error during publisher cleanup for topic {self.topic}: {e}")
            self._closed = True
        except Exception as e:
            # Catch any other unexpected exceptions during cleanup
            logger.warning(f"Unexpected error during publisher cleanup for topic {self.topic}: {e}")
            self._closed = True
