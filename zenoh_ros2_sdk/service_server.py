"""
ROS2ServiceServer - ROS2 Service Server using Zenoh
"""
import zenoh
from zenoh import Encoding
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Callable, Tuple
import threading
from collections import deque

from .session import ZenohSession
from .utils import ros2_to_dds_type, compute_service_type_hash, load_dependencies_recursive
from .entity import EntityKind, NodeEntity, EndpointEntity
from .keyexpr import topic_keyexpr, node_liveliness_keyexpr, endpoint_liveliness_keyexpr
from .qos import QosProfile, DEFAULT_QOS_PROFILE
from .attachment import Attachment
from .message_registry import get_registry
from .logger import get_logger

logger = get_logger("service_server")


@dataclass(frozen=True, slots=True)
class ServiceRequestKey:
    """
    Correlation key for service requests, aligned with ros-z QueryKey and rmw_zenoh.
    """

    sequence_id: int
    gid: bytes


class ROS2ServiceServer:
    """ROS2 Service Server using Zenoh - receives requests and sends responses"""

    def __init__(
        self,
        service_name: str,
        srv_type: str,
        callback: Optional[Callable] = None,
        request_definition: str = "",
        response_definition: str = "",
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None,
        qos: Optional[object] = None,
        mode: str = "callback",
    ):
        """
        Create a ROS2 service server.

        Modes:
            - `mode="callback"` (default): `callback(request_msg) -> response_msg` is called and the server replies immediately.
            - `mode="queue"`: requests are queued; user calls `take_request()` then `send_response()` with the returned key.

        Attachments:
            Service requests **must** include an attachment (sequence_id + gid). The server uses this to:
            - correlate requests/responses
            - reply with an attachment that contains the same (sequence_id, gid) plus a new timestamp

        Args:
            service_name: ROS2 service name (e.g., "/add_two_ints")
            srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")
            callback: Callback function(request_msg) -> response_msg called when request is received
            request_definition: Request message definition text (empty to auto-load)
            response_definition: Response message definition text (empty to auto-load)
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Service type hash (auto-detected if None)
            qos: QoS used for liveliness discovery tokens.
                Accepts `QosProfile`, an encoded rmw_zenoh QoS string, or `None` for default.
            mode: `callback` or `queue`.

        Raises:
            ValueError: If `srv_type` format is invalid or if mode/callback is inconsistent.
            RuntimeError: If called queue-only APIs while not in queue mode.
        """
        if mode not in ("callback", "queue"):
            raise ValueError(f"Invalid mode: {mode}. Expected 'callback' or 'queue'")
        if mode == "callback" and callback is None:
            raise ValueError("callback must be provided when mode='callback'")

        self.service_name = service_name
        self.srv_type = srv_type
        self.callback = callback
        self.mode = mode
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_service_server_{uuid.uuid4().hex[:8]}"
        _, self.qos = self._normalize_qos(qos, default=DEFAULT_QOS_PROFILE, fallback=DEFAULT_QOS_PROFILE.encode())

        # Get or create shared session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)

        # Parse service type to get request and response types
        parts = srv_type.split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid service type format: {srv_type}. Expected format: namespace/srv/ServiceName")

        namespace_part, srv, service_name_part = parts
        self.request_type = f"{namespace_part}/srv/{service_name_part}_Request"
        self.response_type = f"{namespace_part}/srv/{service_name_part}_Response"

        # Register message types (will auto-load from registry if definitions are empty)
        # register_message_type will automatically detect service request/response types
        # and load the service type if needed (like publisher/subscriber do for messages)
        self.request_msg_class = self.session_mgr.register_message_type(request_definition, self.request_type)
        self.response_msg_class = self.session_mgr.register_message_type(response_definition, self.response_type)

        # Get the actual store type names (may be converted for service types)
        # rosbags converts srv/TypeName to srv/msg/TypeName
        self.request_store_type = self.session_mgr._registered_types.get(self.request_type, self.request_type)
        self.response_store_type = self.session_mgr._registered_types.get(self.response_type, self.response_type)

        # Get DDS type name (remove _Response suffix for service type)
        service_dds_type = ros2_to_dds_type(srv_type)
        if service_dds_type.endswith("_Request_"):
            service_dds_type = service_dds_type[:-9]
        elif service_dds_type.endswith("_Response_"):
            service_dds_type = service_dds_type[:-10]

        self.dds_type_name = service_dds_type

        # Get type hash if not provided
        if type_hash is None:
            # Get message definitions for hash computation
            hash_request_def = request_definition
            hash_response_def = response_definition

            if not hash_request_def or not hash_response_def:
                try:
                    registry = get_registry()

                    # get_srv_file_path returns the same .srv file for both request and response
                    # We need to read it and split by '---' to get request and response parts
                    if not hash_request_def or not hash_response_def:
                        srv_file = registry.get_srv_file_path(srv_type, is_request=True)
                        if srv_file and srv_file.exists():
                            with open(srv_file, 'r') as f:
                                srv_content = f.read()

                            # Split by '---' separator
                            # ROS2 .srv files MUST have a '---' separator between request and response
                            parts = srv_content.split('---', 1)
                            if len(parts) < 2:
                                raise ValueError(
                                    f"Invalid service definition file for {srv_type}: "
                                    "missing '---' separator between request and response. "
                                    f"File content: {repr(srv_content[:100])}"
                                )

                            if not hash_request_def:
                                hash_request_def = parts[0].strip()
                            if not hash_response_def:
                                hash_response_def = parts[1].strip()

                            # Validate that we got both parts
                            if not hash_request_def:
                                raise ValueError(
                                    f"Service definition file for {srv_type} has empty request definition"
                                )
                            if not hash_response_def:
                                raise ValueError(
                                    f"Service definition file for {srv_type} has empty response definition"
                                )
                except Exception as e:
                    # Re-raise with more context - don't silently swallow errors
                    raise RuntimeError(
                        f"Failed to load service definitions from registry for {srv_type}: {e}"
                    ) from e

            if not hash_request_def or not hash_response_def:
                raise ValueError(
                    f"Cannot compute type hash for {srv_type}: service definitions not provided. "
                    "Please provide request_definition and response_definition or ensure the service type is loaded in the registry."
                )

            # Get dependencies recursively
            dependencies = None
            try:
                registry = get_registry()
                # Load dependencies for both request and response using shared utility function
                req_deps = load_dependencies_recursive(self.request_type, hash_request_def, registry)
                resp_deps = load_dependencies_recursive(self.response_type, hash_response_def, registry)
                dependencies = {**req_deps, **resp_deps}
            except Exception as e:
                logger.debug(f"Could not load dependencies for {srv_type}: {e}")

            # For services, compute hash from the service type itself (not just request)
            # Services are represented as a type with request_message, response_message, and event_message fields
            type_hash = compute_service_type_hash(
                self.srv_type,
                request_definition=hash_request_def,
                response_definition=hash_response_def,
                dependencies=dependencies
            )

        self.type_hash = type_hash

        # Generate unique GID for this server
        self.server_gid = self.session_mgr.generate_gid()

        # Get node and entity IDs
        self.node_id = self.session_mgr.get_next_node_id()
        self.entity_id = self.session_mgr.get_next_entity_id()

        # Build keyexpr for service (used for queryable)
        self.keyexpr = topic_keyexpr(domain_id, service_name, self.dds_type_name, type_hash)
        logger.info(f"Service keyexpr: {self.keyexpr}")
        logger.info(f"Service type hash: {type_hash}")

        # Declare liveliness tokens
        self._declare_liveliness_tokens()

        # Create queryable for receiving requests
        queryable_ke = zenoh.KeyExpr(self.keyexpr)
        logger.info(f"Declaring queryable on keyexpr: {self.keyexpr}")

        # Zenoh Python API: declare_queryable(key_expr, handler=None, *, complete=None, allowed_origin=None)
        self.queryable = self.session_mgr.session.declare_queryable(
            queryable_ke,
            self._query_handler,
            complete=True
        )
        logger.info(f"Queryable declared successfully on: {self.keyexpr}")

        # Queue-mode state (ros-z style)
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._queue: deque[Tuple[ServiceRequestKey, object]] = deque()
        self._pending_queries: Dict[ServiceRequestKey, zenoh.Query] = {}

        self._closed = False

    @staticmethod
    def _normalize_qos(
        qos: Optional[object],
        *,
        default: QosProfile,
        fallback: str,
    ) -> tuple[QosProfile, str]:
        if qos is None:
            return default, fallback
        if isinstance(qos, QosProfile):
            return qos, qos.encode()
        if isinstance(qos, str):
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
            kind=EntityKind.SERVICE,
            name=self.service_name,
            dds_type_name=self.dds_type_name,
            type_hash=self.type_hash,
            qos=self.qos,
            gid=self.server_gid,
        )

        self.node_token = self.session_mgr.liveliness.declare_token(node_liveliness_keyexpr(node))
        self.service_token = self.session_mgr.liveliness.declare_token(endpoint_liveliness_keyexpr(ep))

    def _create_response_attachment(self, request_seq_num: int, request_gid: bytes) -> bytes:
        """Create rmw_zenoh attachment for service response (seq + new_ts + same_gid)."""
        timestamp_ns = int(time.time() * 1e9)
        return Attachment(sequence_id=request_seq_num, timestamp_ns=timestamp_ns, gid=request_gid).to_bytes()

    def take_request(self, timeout: Optional[float] = None) -> Tuple[ServiceRequestKey, object]:
        """
        Queue-mode API (ros-z style): block until a request is available, then return (key, request_msg).
        """
        if self.mode != "queue":
            raise RuntimeError("take_request() is only available when mode='queue'")
        with self._cv:
            if timeout is None:
                while not self._queue:
                    self._cv.wait()
            else:
                end = time.time() + timeout
                while not self._queue:
                    remaining = end - time.time()
                    if remaining <= 0:
                        raise TimeoutError("Timed out waiting for service request")
                    self._cv.wait(timeout=remaining)
            key, msg = self._queue.popleft()
            return key, msg

    def send_response(self, key: ServiceRequestKey, response_msg: object) -> None:
        """
        Queue-mode API (ros-z style): reply to a previously taken request using its correlation key.
        """
        if self.mode != "queue":
            raise RuntimeError("send_response() is only available when mode='queue'")
        with self._lock:
            query = self._pending_queries.pop(key, None)
        if query is None:
            raise KeyError(f"No pending query found for key={key}")

        response_cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(response_msg, self.response_store_type))
        response_attachment = self._create_response_attachment(key.sequence_id, key.gid)
        query.reply(
            zenoh.KeyExpr(self.keyexpr),
            zenoh.ZBytes(response_cdr_bytes),
            encoding=Encoding("application/cdr"),
            attachment=zenoh.ZBytes(response_attachment),
        )

    def _query_handler(self, query: zenoh.Query):
        """Handle incoming service request query"""
        # Keep logs at debug to avoid spamming in production.
        query_key = str(query.key_expr) if hasattr(query, 'key_expr') else 'unknown'
        logger.debug(f"Service request received. Query keyexpr: {query_key}, Expected: {self.keyexpr}")
        try:
            # Verified in-container: query.payload is a ZBytes and supports to_bytes().
            payload = getattr(query, "payload", None)
            if payload is None or not hasattr(payload, "to_bytes"):
                error_msg = (
                    "Service request has unsupported payload shape. Expected query.payload with to_bytes(). "
                    f"payload_type={type(payload)}"
                )
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            cdr_bytes = payload.to_bytes()
            if not cdr_bytes:
                error_msg = "Service request payload is empty"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            # Get attachment from query (required for response)
            # Following ros-z and rmw_zenoh pattern: response attachment includes
            # sequence number and GID from request, plus new timestamp
            # According to rmw_zenoh design, attachment is REQUIRED for service requests
            attachment = getattr(query, "attachment", None)
            if attachment is None or not hasattr(attachment, "to_bytes"):
                error_msg = "Service request attachment is None - attachment is required for service requests"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            # Parse attachment (strict)
            try:
                att = Attachment.from_bytes(attachment.to_bytes())
            except Exception as e:
                error_msg = f"Failed to parse service request attachment: {e}"
                logger.error(error_msg, exc_info=True)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            key = ServiceRequestKey(sequence_id=int(att.sequence_id), gid=bytes(att.gid))

            # Deserialize request (use store type name which may be converted)
            request_msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.request_store_type)

            if self.mode == "queue":
                # Store query for later response (ros-z style).
                with self._cv:
                    if key in self._pending_queries:
                        query.reply_err(zenoh.ZBytes(b"Duplicate service request key"))
                        return

                    # Enforce queue depth via QoS (KeepAll => unbounded)
                    qos_profile = QosProfile.decode(self.qos)
                    if qos_profile.history_kind != qos_profile.history_kind.KEEP_ALL and qos_profile.history_depth > 0:
                        while len(self._queue) >= qos_profile.history_depth:
                            dropped_key, _ = self._queue.popleft()
                            self._pending_queries.pop(dropped_key, None)
                            logger.warning(
                                "Service request queue depth reached; dropping oldest request. "
                                f"service={self.service_name} depth={qos_profile.history_depth}"
                            )

                    self._pending_queries[key] = query
                    self._queue.append((key, request_msg))
                    self._cv.notify()
                return

            # callback mode (default): call user callback and reply immediately
            try:
                response_msg = self.callback(request_msg)  # type: ignore[misc]
                if response_msg is None:
                    raise RuntimeError("Service callback returned None")

                response_cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(response_msg, self.response_store_type))
                response_attachment = self._create_response_attachment(key.sequence_id, key.gid)

                query.reply(
                    zenoh.KeyExpr(self.keyexpr),
                    zenoh.ZBytes(response_cdr_bytes),
                    encoding=Encoding("application/cdr"),
                    attachment=zenoh.ZBytes(response_attachment),
                )
            except Exception as e:
                logger.error(f"Error in service callback: {e}", exc_info=True)
                query.reply_err(zenoh.ZBytes(f"Service callback error: {str(e)}".encode()))

        except Exception as e:
            logger.error(f"Error handling service request: {e}", exc_info=True)
            try:
                query.reply_err(zenoh.ZBytes(f"Service handler error: {str(e)}".encode()))
            except Exception as reply_error:
                logger.debug(f"Failed to send error reply: {reply_error}")

    def close(self):
        """
        Close the service server and undeclare tokens.

        This method is idempotent - it's safe to call multiple times.
        """
        if hasattr(self, '_closed') and self._closed:
            return

        try:
            if hasattr(self, 'node_token') and self.node_token is not None:
                self.node_token.undeclare()
            if hasattr(self, 'service_token') and self.service_token is not None:
                self.service_token.undeclare()
            if hasattr(self, 'queryable') and self.queryable is not None:
                if hasattr(self.queryable, 'undeclare'):
                    self.queryable.undeclare()
                self.queryable = None
            self._closed = True
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Error during service server cleanup for service {self.service_name}: {e}")
            self._closed = True
        except Exception as e:
            logger.warning(f"Unexpected error during service server cleanup for service {self.service_name}: {e}")
            self._closed = True
