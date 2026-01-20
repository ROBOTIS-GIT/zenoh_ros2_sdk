"""
ROS2Subscriber - ROS2 Subscriber using Zenoh
"""
import uuid
from typing import Optional, Callable

from .session import ZenohSession
from .utils import ros2_to_dds_type, get_type_hash, load_dependencies_recursive, resolve_domain_id
from .entity import EntityKind, NodeEntity, EndpointEntity
from .keyexpr import topic_keyexpr, node_liveliness_keyexpr, endpoint_liveliness_keyexpr
from .qos import QosProfile, QosDurability, DEFAULT_QOS_PROFILE
from .message_registry import get_registry
from .logger import get_logger

logger = get_logger("subscriber")


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
        domain_id: Optional[int] = None,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None,
        qos: Optional[object] = None,
    ):
        """
        Create a ROS2 subscriber

        Args:
            topic: ROS2 topic name (e.g. `/chatter`).
            msg_type: ROS2 message type (e.g. `std_msgs/msg/String`).
            callback: Callback function(msg) called when message is received
            msg_definition: Message definition text (empty string to auto-load from registry)
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID (defaults to ROS_DOMAIN_ID or 0)
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Message type hash (auto-detected if None)
            qos: QoS used for liveliness discovery tokens.
                Accepts `QosProfile`, an encoded rmw_zenoh QoS string, or `None` for default.

        Raises:
            ValueError: If the type hash cannot be computed because message definitions are missing.
            TypeError: If Zenoh delivers an unexpected payload type (see `_listener`).
        """
        self.topic = topic
        self.msg_type = msg_type
        self.callback = callback
        self.domain_id = resolve_domain_id(domain_id)
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_subscriber_{uuid.uuid4().hex[:8]}"
        # QoS is only used for liveliness discovery tokens. It does not affect the
        # data keyexpr subscription (which is topic/type-hash based).
        _, self.qos = self._normalize_qos(qos, default=DEFAULT_QOS_PROFILE, fallback=DEFAULT_QOS_PROFILE.encode())

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

        # Generate IDs used in ROS2 liveliness discovery (mirrors publisher/service patterns)
        self.subscriber_gid = self.session_mgr.generate_gid()
        self.node_id = self.session_mgr.get_next_node_id()
        self.entity_id = self.session_mgr.get_next_entity_id()

        # Build keyexpr
        self.keyexpr = topic_keyexpr(self.domain_id, topic, self.dds_type_name, type_hash)

        # Declare liveliness tokens so ROS2 nodes that publish-on-subscribe (e.g., image_transport)
        # will see this subscriber.
        self._declare_liveliness_tokens()

        # Create subscriber
        self.sub = self.session_mgr.session.declare_subscriber(self.keyexpr, self._listener)
        self._closed = False

        # For transient_local durability, query for cached/historical data
        # This mimics rmw_zenoh's AdvancedSubscriber behavior
        self.qos_profile, _ = self._normalize_qos(qos, default=DEFAULT_QOS_PROFILE, fallback=DEFAULT_QOS_PROFILE.encode())
        if self.qos_profile.durability == QosDurability.TRANSIENT_LOCAL:
            self._query_historical_data()

    @staticmethod
    def _normalize_qos(
        qos: Optional[object],
        *,
        default: QosProfile,
        fallback: str,
    ) -> tuple[QosProfile, str]:
        """
        Subscriber only needs the encoded QoS string for tokens, but we normalize
        similarly to publisher for API consistency.
        """
        if qos is None:
            return default, fallback
        if isinstance(qos, QosProfile):
            return qos, qos.encode()
        if isinstance(qos, str):
            # User provided an authoritative encoded QoS string. It must be parseable.
            return QosProfile.decode(qos), qos
        return default, fallback

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
            kind=EntityKind.SUBSCRIPTION,
            name=self.topic,
            dds_type_name=self.dds_type_name,
            type_hash=self.type_hash,
            qos=self.qos,
            gid=self.subscriber_gid,
        )

        self.node_token = self.session_mgr.liveliness.declare_token(node_liveliness_keyexpr(node))
        self.subscriber_token = self.session_mgr.liveliness.declare_token(endpoint_liveliness_keyexpr(ep))

    def _listener(self, sample):
        """Internal message listener"""
        self._process_sample(sample)

    def _process_sample(self, sample):
        """Process a Zenoh sample (from subscription or query reply)"""
        try:
            payload = getattr(sample, "payload", None)
            if payload is None:
                raise ValueError("Zenoh sample has no payload")

            # Verified in-container: sample.payload is a ZBytes and supports to_bytes().
            # Prefer to_bytes() because it is explicit and version-stable.
            if hasattr(payload, "to_bytes"):
                cdr_bytes = payload.to_bytes()
                if not isinstance(cdr_bytes, (bytes, bytearray)):
                    raise TypeError(
                        "Zenoh payload.to_bytes() returned a non-bytes value: "
                        f"type={type(cdr_bytes)}"
                    )
                cdr_bytes = bytes(cdr_bytes)
            elif isinstance(payload, (bytes, bytearray)):
                cdr_bytes = bytes(payload)
            elif isinstance(payload, memoryview):
                cdr_bytes = payload.tobytes()
            else:
                raise TypeError(
                    "Unsupported Zenoh payload type. Expected an object with to_bytes(), "
                    f"or bytes-like payload. Got type={type(payload)}. "
                    f"Has to_bytes={hasattr(payload, 'to_bytes')}. "
                    f"Payload repr={repr(payload)[:200]}"
                )

            if not cdr_bytes:
                raise ValueError("Received empty payload")

            msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.msg_type)
            self.callback(msg)
        except Exception as e:
            logger.error(f"Error deserializing message on topic {self.topic}: {e}", exc_info=True)

    def _query_historical_data(self):
        """Query for cached data from transient_local publishers.

        rmw_zenoh uses AdvancedPublisher which caches messages at:
            <key_expr>/@adv/pub/<zenoh_id>/<entity_id>/_

        The `_anyke` selector parameter allows replies on any key expression.
        Zenoh uses ';' as parameter separator (not '&').
        """
        publishers = self._discover_publishers()
        if not publishers:
            logger.debug(f"No transient_local publishers for {self.topic}")
            return

        max_samples = self.qos_profile.history_depth
        total_replies = 0

        for zenoh_id in publishers:
            # Query the AdvancedPublisher cache with _anyke to accept any reply key
            selector = f"{self.keyexpr}/@adv/pub/{zenoh_id}/**?_anyke;_max={max_samples}"

            try:
                for reply in self.session_mgr.session.get(selector, timeout=2.0):
                    if reply.ok is not None:
                        total_replies += 1
                        self._process_sample(reply.ok)
                    elif reply.err is not None:
                        logger.warning(f"Query error for {self.topic}: {reply.err}")
            except Exception as e:
                logger.warning(f"Failed to query publisher {zenoh_id}: {e}")

        if total_replies > 0:
            logger.debug(f"Received {total_replies} cached samples for {self.topic}")

    def _discover_publishers(self) -> list[str]:
        """Discover publishers for this topic via liveliness tokens.

        Returns:
            List of zenoh_id strings for each publisher found.
        """
        publishers = set()

        # rmw_zenoh liveliness token format:
        # @ros2_lv/<domain>/<zenoh_id>/<seq>/<entity_id>/MP/<gid_hi>/<gid_lo>/<node>/%<topic>/<dds_type>/<type_hash>/<qos>
        lv_pattern = (
            f"@ros2_lv/{self.domain_id}/*/*/*/MP/*/*/*"
            f"/%{self.topic.lstrip('/')}/{self.dds_type_name}/{self.type_hash}/*"
        )

        try:
            replies = self.session_mgr.liveliness.get(lv_pattern, timeout=2.0)
            for reply in replies:
                if reply.ok is not None:
                    parts = str(reply.ok.key_expr).split('/')
                    if len(parts) > 2:
                        publishers.add(parts[2])  # zenoh_id is at index 2
        except Exception as e:
            logger.warning(f"Failed to discover publishers for {self.topic}: {e}")

        return list(publishers)

    def close(self):
        """
        Close the subscriber and cleanup resources.

        This method is idempotent - it's safe to call multiple times.
        """
        # Check if already closed
        if hasattr(self, '_closed') and self._closed:
            return

        try:
            # Undeclare liveliness tokens first (best-effort)
            if hasattr(self, "subscriber_token") and self.subscriber_token is not None:
                self.subscriber_token.undeclare()
                self.subscriber_token = None
            if hasattr(self, "node_token") and self.node_token is not None:
                self.node_token.undeclare()
                self.node_token = None

            if hasattr(self, 'sub') and self.sub is not None:
                # Zenoh subscribers have an undeclare() method to explicitly remove them
                # This is the proper way to clean up a subscriber
                if hasattr(self.sub, 'undeclare'):
                    self.sub.undeclare()
                # Mark as closed
                self.sub = None
            self._closed = True
        except (AttributeError, RuntimeError) as e:
            # AttributeError: subscriber doesn't exist or undeclare method not available
            # RuntimeError: Zenoh runtime errors
            logger.debug(f"Error during subscriber cleanup for topic {self.topic}: {e}")
            # Mark as closed even if undeclare failed to prevent retry loops
            self._closed = True
        except Exception as e:
            # Catch any other unexpected exceptions during cleanup
            # Log at warning level since this is unexpected
            logger.warning(f"Unexpected error during subscriber cleanup for topic {self.topic}: {e}")
            self._closed = True
