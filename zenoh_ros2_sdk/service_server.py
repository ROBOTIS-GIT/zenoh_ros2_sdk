"""
ROS2ServiceServer - ROS2 Service Server using Zenoh
"""
import zenoh
from zenoh import Encoding
import struct
import time
import uuid
from typing import Optional, Dict, Callable

from .session import ZenohSession
from .utils import ros2_to_dds_type, compute_service_type_hash, mangle_name, load_dependencies_recursive
from .message_registry import get_registry
from .logger import get_logger

logger = get_logger("service_server")


class ROS2ServiceServer:
    """ROS2 Service Server using Zenoh - receives requests and sends responses"""

    def __init__(
        self,
        service_name: str,
        srv_type: str,
        callback: Callable,
        request_definition: str = "",
        response_definition: str = "",
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None
    ):
        """
        Create a ROS2 service server

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
        """
        self.service_name = service_name
        self.srv_type = srv_type
        self.callback = callback
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_service_server_{uuid.uuid4().hex[:8]}"

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
        fully_qualified_name = service_name.lstrip("/")
        self.keyexpr = f"{domain_id}/{fully_qualified_name}/{self.dds_type_name}/{type_hash}"
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

        self._closed = False

    def _declare_liveliness_tokens(self):
        """Declare liveliness tokens for ROS2 discovery"""
        mangled_enclave = "%"
        mangled_namespace = mangle_name(self.namespace)
        mangled_service = mangle_name(self.service_name)
        qos = "::,7:,:,:,,"  # Default QoS

        # Node token
        node_token_keyexpr = (
            f"@ros2_lv/{self.domain_id}/{self.session_mgr.session_id}/"
            f"{self.node_id}/{self.node_id}/NN/{mangled_enclave}/"
            f"{mangled_namespace}/{self.node_name}"
        )

        # Service token (SS = Service Server, not MS)
        service_token_keyexpr = (
            f"@ros2_lv/{self.domain_id}/{self.session_mgr.session_id}/"
            f"{self.node_id}/{self.entity_id}/SS/{mangled_enclave}/"
            f"{mangled_namespace}/{self.node_name}/{mangled_service}/"
            f"{self.dds_type_name}/{self.type_hash}/{qos}"
        )

        self.node_token = self.session_mgr.liveliness.declare_token(node_token_keyexpr)
        self.service_token = self.session_mgr.liveliness.declare_token(service_token_keyexpr)

    def _parse_attachment(self, attachment: bytes) -> Optional[Dict]:
        """Parse rmw_zenoh attachment from service request"""
        try:
            if len(attachment) < 17:  # Minimum size: 8 (seq) + 8 (timestamp) + 1 (gid_len)
                return None

            seq_num = struct.unpack('<Q', attachment[0:8])[0]
            timestamp_ns = struct.unpack('<Q', attachment[8:16])[0]
            gid_len = struct.unpack('B', attachment[16:17])[0]

            if len(attachment) < 17 + gid_len:
                return None

            gid = attachment[17:17+gid_len]

            return {
                "sequence_id": seq_num,
                "timestamp_ns": timestamp_ns,
                "gid": gid
            }
        except Exception as e:
            logger.error(f"Error parsing attachment: {e}")
            return None

    def _create_response_attachment(self, request_seq_num: int, request_gid: bytes) -> bytes:
        """Create rmw_zenoh attachment for service response

        Following rmw_zenoh design: includes sequence number from request,
        new timestamp for reply, and client GID from request.
        """
        timestamp_ns = int(time.time() * 1e9)  # Current timestamp for reply
        attachment = struct.pack('<Q', request_seq_num)  # sequence number from request
        attachment += struct.pack('<Q', timestamp_ns)  # timestamp for reply
        attachment += struct.pack('B', len(request_gid))  # GID length
        attachment += request_gid  # GID from request
        return attachment

    def _query_handler(self, query: zenoh.Query):
        """Handle incoming service request query"""
        # Log query details for debugging
        query_key = str(query.key_expr) if hasattr(query, 'key_expr') else 'unknown'
        logger.info(f"Service request received! Query keyexpr: {query_key}, Expected: {self.keyexpr}")
        try:
            # Get request payload from query
            # Following ros-z pattern: query.payload().unwrap().to_bytes()
            # In Zenoh Python API, payload should be available via query.payload
            cdr_bytes = None
            if not hasattr(query, 'payload'):
                error_msg = "Query object has no 'payload' attribute - invalid Zenoh Query object"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            payload = query.payload
            if payload is None:
                error_msg = "Service request has no payload"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            # Extract bytes from payload
            if isinstance(payload, zenoh.ZBytes):
                cdr_bytes = bytes(payload)
            elif isinstance(payload, (bytes, bytearray)):
                cdr_bytes = bytes(payload)
            elif hasattr(payload, 'to_bytes'):
                cdr_bytes = bytes(payload.to_bytes())
            else:
                error_msg = f"Unknown payload type: {type(payload)}. Expected zenoh.ZBytes, bytes, or object with to_bytes() method"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            if cdr_bytes is None or len(cdr_bytes) == 0:
                error_msg = "Service request payload is empty"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            # Get attachment from query (required for response)
            # Following ros-z and rmw_zenoh pattern: response attachment includes
            # sequence number and GID from request, plus new timestamp
            # According to rmw_zenoh design, attachment is REQUIRED for service requests
            if not hasattr(query, 'attachment'):
                error_msg = "Service request has no attachment attribute - invalid request format"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            attachment = query.attachment
            if attachment is None:
                error_msg = "Service request attachment is None - attachment is required for service requests"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            # Parse attachment
            try:
                attachment_data = self._parse_attachment(bytes(attachment))
            except Exception as e:
                error_msg = f"Failed to parse service request attachment: {e}"
                logger.error(error_msg, exc_info=True)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            if attachment_data is None:
                error_msg = "Service request attachment parsing returned None - invalid attachment format"
                logger.error(error_msg)
                query.reply_err(zenoh.ZBytes(error_msg.encode()))
                return

            # Deserialize request (use store type name which may be converted)
            request_msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.request_store_type)

            # Call user callback
            try:
                response_msg = self.callback(request_msg)

                if response_msg is None:
                    error_msg = "Service callback returned None"
                    logger.error(error_msg)
                    query.reply_err(zenoh.ZBytes(error_msg.encode()))
                    return

                # Serialize response (use store type name which may be converted)
                response_cdr_bytes = bytes(self.session_mgr.store.serialize_cdr(response_msg, self.response_store_type))

                # Create response attachment (following rmw_zenoh design)
                # Include sequence number and GID from request, plus new timestamp
                # attachment_data is guaranteed to be valid at this point
                response_attachment = self._create_response_attachment(
                    attachment_data["sequence_id"],
                    attachment_data["gid"]
                )

                # Send response
                # Following ros-z pattern: query.reply(&self.key_expr, msg.serialize()).attachment(attachment)
                # Zenoh Python API: reply(key_expr, payload, *, encoding=None, attachment=None, ...)
                query.reply(
                    zenoh.KeyExpr(self.keyexpr),
                    zenoh.ZBytes(response_cdr_bytes),
                    encoding=Encoding("application/cdr"),
                    attachment=zenoh.ZBytes(response_attachment) if response_attachment else None
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
