"""
ROS2ServiceClient - ROS2 Service Client using Zenoh
"""
import zenoh
from zenoh import Encoding
import time
import struct
import uuid
import threading
from typing import Any, Callable, Optional

from .session import ZenohSession
from .utils import ros2_to_dds_type, compute_service_type_hash, load_dependencies_recursive
from .entity import EntityKind, NodeEntity, EndpointEntity
from .keyexpr import topic_keyexpr, node_liveliness_keyexpr, endpoint_liveliness_keyexpr
from .qos import QosProfile, DEFAULT_QOS_PROFILE
from .attachment import Attachment
from .message_registry import get_registry
from .logger import get_logger

logger = get_logger("service_client")


class ROS2ServiceClient:
    """ROS2 Service Client using Zenoh - sends requests and receives responses"""

    def __init__(
        self,
        service_name: str,
        srv_type: str,
        request_definition: str = "",
        response_definition: str = "",
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None,
        timeout: float = 10.0,
        qos: Optional[object] = None,
    ):
        """
        Create a ROS2 service client.

        This client sends requests using Zenoh queries and expects:
        - `Reply.ok` to be a Zenoh `Sample` with `.payload.to_bytes()`
        - `Reply.err` to be a Zenoh `ReplyError` with `.payload.to_bytes()`

        Args:
            service_name: ROS2 service name (e.g., "/add_two_ints")
            srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")
            request_definition: Request message definition text (empty to auto-load)
            response_definition: Response message definition text (empty to auto-load)
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Service type hash (auto-detected if None)
            timeout: Timeout for service calls in seconds (default: 10.0)
            qos: QoS used for liveliness discovery tokens.
                Accepts `QosProfile`, an encoded rmw_zenoh QoS string, or `None` for default.

        Raises:
            ValueError: If `srv_type` format is invalid.
            RuntimeError: If service definitions cannot be loaded to compute the type hash.
        """
        self.service_name = service_name
        self.srv_type = srv_type
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_service_client_{uuid.uuid4().hex[:8]}"
        self.timeout = timeout
        _, self.qos = self._normalize_qos(qos, default=DEFAULT_QOS_PROFILE, fallback=DEFAULT_QOS_PROFILE.encode())

        # Get or create shared session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)

        # Parse service type to get request and response types
        # Service types are like "example_interfaces/srv/AddTwoInts"
        # Request type: "example_interfaces/srv/AddTwoInts_Request"
        # Response type: "example_interfaces/srv/AddTwoInts_Response"
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

        # Get DDS type name (remove _Request suffix for service type)
        # Service type name should be without Request_ or Response_ suffix
        service_dds_type = ros2_to_dds_type(srv_type)
        # Remove the last underscore and Request/Response suffix if present
        if service_dds_type.endswith("_Request_"):
            service_dds_type = service_dds_type[:-9]  # Remove "_Request_"
        elif service_dds_type.endswith("_Response_"):
            service_dds_type = service_dds_type[:-10]  # Remove "_Response_"

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

        # Generate unique GID for this client
        self.client_gid = self.session_mgr.generate_gid()

        # Get node and entity IDs
        self.node_id = self.session_mgr.get_next_node_id()
        self.entity_id = self.session_mgr.get_next_entity_id()

        # Build keyexpr for service (used for queries)
        # Format: domain_id/service_name/dds_type_name/type_hash
        self.keyexpr = topic_keyexpr(domain_id, service_name, self.dds_type_name, type_hash)

        # Declare liveliness tokens
        self._declare_liveliness_tokens()

        # Create querier for sending requests
        # Zenoh Python API: declare_querier(key_expr, *, target=None, consolidation=None, timeout=None, ...)
        querier_ke = zenoh.KeyExpr(self.keyexpr)

        self.querier = self.session_mgr.session.declare_querier(
            querier_ke,
            target=zenoh.QueryTarget.ALL_COMPLETE,
            timeout=int(self.timeout * 1000),
            consolidation=zenoh.ConsolidationMode.NONE
        )

        # Sequence tracking
        self.sequence_number = 1
        self._lock = threading.Lock()
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
            kind=EntityKind.CLIENT,
            name=self.service_name,
            dds_type_name=self.dds_type_name,
            type_hash=self.type_hash,
            qos=self.qos,
            gid=self.client_gid,
        )

        self.node_token = self.session_mgr.liveliness.declare_token(node_liveliness_keyexpr(node))
        self.client_token = self.session_mgr.liveliness.declare_token(endpoint_liveliness_keyexpr(ep))

    def _create_attachment(self, seq_num: int, timestamp_ns: int) -> bytes:
        """Create rmw_zenoh attachment for service request"""
        return Attachment(sequence_id=seq_num, timestamp_ns=timestamp_ns, gid=self.client_gid).to_bytes()

    def call(self, **kwargs: Any) -> Optional[object]:
        """
        Call the service synchronously

        Args:
            **kwargs: Request field values

        Returns:
            Response message object or None if timeout/error
        """
        # Create request message instance
        request_msg = self.request_msg_class(**kwargs)

        # Serialize to CDR (use store type name which may be converted)
        cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(request_msg, self.request_store_type))

        # Create attachment
        timestamp_ns = int(time.time() * 1e9)
        sequence_id = self.sequence_number
        self.sequence_number += 1
        attachment = self._create_attachment(sequence_id, timestamp_ns)

        # Response event for synchronization
        response_event = threading.Event()
        response_data = {"response": None, "error": None}

        def reply_callback(reply: zenoh.Reply):
            """Callback for receiving service response"""
            try:
                # Verified in-container:
                # - reply.ok is a builtins.Sample, with ok.payload: ZBytes
                # - reply.err is a builtins.ReplyError, with err.payload: ZBytes
                if reply.err is not None:
                    err = reply.err
                    payload = getattr(err, "payload", None)
                    if payload is None or not hasattr(payload, "to_bytes"):
                        raise TypeError(
                            "Unexpected ReplyError shape. Expected err.payload with to_bytes(). "
                            f"err_type={type(err)} payload_type={type(payload)}"
                        )
                    error_msg = payload.to_bytes().decode("utf-8", errors="ignore")
                    logger.error(f"Service call failed: {error_msg}")
                    response_data["error"] = error_msg
                    response_event.set()
                    return

                if reply.ok is not None:
                    ok = reply.ok
                    payload = getattr(ok, "payload", None)
                    if payload is None or not hasattr(payload, "to_bytes"):
                        raise TypeError(
                            "Unexpected Reply ok shape. Expected ok.payload with to_bytes(). "
                            f"ok_type={type(ok)} payload_type={type(payload)}"
                        )
                    cdr_bytes = payload.to_bytes()

                    # Deserialize response (use store type name which may be converted)
                    response_msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.response_store_type)
                    response_data["response"] = response_msg
                    response_event.set()
                else:
                    logger.error("Reply has neither ok nor err")
                    response_data["error"] = "Invalid reply format"
                    response_event.set()
            except Exception as e:
                logger.error(f"Error processing service response: {e}", exc_info=True)
                response_data["error"] = str(e)
                response_event.set()

        # Send request using querier
        # Zenoh Python API: get(handler=None, *, parameters=None, payload=None, encoding=None, attachment=None, ...)
        self.querier.get(
            reply_callback,
            parameters="",
            payload=zenoh.ZBytes(cdr_bytes),
            encoding=Encoding("application/cdr"),
            attachment=zenoh.ZBytes(attachment)
        )

        # querier.get() doesn't return a result code in Python API - it's fire-and-forget
        # Errors will be reported in the reply_callback

        # Wait for response with timeout
        if response_event.wait(timeout=self.timeout):
            if response_data["error"]:
                logger.error(f"Service call error: {response_data['error']}")
                return None
            return response_data["response"]
        else:
            logger.warning(f"Service call timed out after {self.timeout} seconds")
            return None

    def call_async(self, callback: Callable, **kwargs: Any) -> None:
        """
        Call the service asynchronously

        Args:
            callback: Callback function(response_msg) called when response is received
            **kwargs: Request field values
        """
        # Create request message instance
        request_msg = self.request_msg_class(**kwargs)

        # Serialize to CDR (use store type name which may be converted)
        cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(request_msg, self.request_store_type))

        # Create attachment
        timestamp_ns = int(time.time() * 1e9)
        sequence_id = self.sequence_number
        self.sequence_number += 1
        attachment = self._create_attachment(sequence_id, timestamp_ns)

        def reply_callback(reply: zenoh.Reply):
            """Callback for receiving service response"""
            try:
                if reply.err is not None:
                    err = reply.err
                    payload = getattr(err, "payload", None)
                    if payload is None or not hasattr(payload, "to_bytes"):
                        raise TypeError(
                            "Unexpected ReplyError shape. Expected err.payload with to_bytes(). "
                            f"err_type={type(err)} payload_type={type(payload)}"
                        )
                    error_msg = payload.to_bytes().decode("utf-8", errors="ignore")
                    logger.error(f"Async service call failed: {error_msg}")
                    callback(None)
                    return

                if reply.ok is not None:
                    ok = reply.ok
                    payload = getattr(ok, "payload", None)
                    if payload is None or not hasattr(payload, "to_bytes"):
                        raise TypeError(
                            "Unexpected Reply ok shape. Expected ok.payload with to_bytes(). "
                            f"ok_type={type(ok)} payload_type={type(payload)}"
                        )
                    cdr_bytes = payload.to_bytes()

                    # Deserialize response (use store type name which may be converted)
                    response_msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.response_store_type)
                    callback(response_msg)
                else:
                    logger.error("Reply has neither ok nor err")
                    callback(None)
            except Exception as e:
                logger.error(f"Error processing async service response: {e}", exc_info=True)
                callback(None)

        # Send request using querier
        # Zenoh Python API: get(handler=None, *, parameters=None, payload=None, encoding=None, attachment=None, ...)
        # querier.get() doesn't return a result code in Python API - it's fire-and-forget
        # Errors will be reported in the reply_callback
        self.querier.get(
            reply_callback,
            parameters="",
            payload=zenoh.ZBytes(cdr_bytes),
            encoding=Encoding("application/cdr"),
            attachment=zenoh.ZBytes(attachment)
        )

    def close(self):
        """
        Close the service client and undeclare tokens.

        This method is idempotent - it's safe to call multiple times.
        """
        if hasattr(self, '_closed') and self._closed:
            return

        try:
            if hasattr(self, 'node_token') and self.node_token is not None:
                self.node_token.undeclare()
            if hasattr(self, 'client_token') and self.client_token is not None:
                self.client_token.undeclare()
            if hasattr(self, 'querier') and self.querier is not None:
                if hasattr(self.querier, 'undeclare'):
                    self.querier.undeclare()
                self.querier = None
            self._closed = True
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Error during service client cleanup for service {self.service_name}: {e}")
            self._closed = True
        except Exception as e:
            logger.warning(f"Unexpected error during service client cleanup for service {self.service_name}: {e}")
            self._closed = True
