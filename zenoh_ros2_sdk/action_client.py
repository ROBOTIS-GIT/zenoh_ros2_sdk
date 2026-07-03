"""
ROS2ActionClient - ROS2 Action Client using Zenoh
"""

import zenoh
from zenoh import Encoding
import time
import uuid
import threading
import numpy as np
from typing import Callable, Dict, Optional

from .session import ZenohSession
from .utils import (
    ros2_to_dds_type,
    compute_service_type_hash,
    compute_action_type_hashes,
    get_type_hash,
    load_dependencies_recursive,
    resolve_domain_id,
)
from .entity import EntityKind, NodeEntity, EndpointEntity
from .keyexpr import topic_keyexpr, node_liveliness_keyexpr, endpoint_liveliness_keyexpr
from .qos import QosProfile, DEFAULT_QOS_PROFILE
from .attachment import Attachment
from .message_registry import get_registry
from .logger import get_logger

logger = get_logger("action_client")


class ROS2ActionClient:
    """ROS2 Action Client using Zenoh.

    Maps a ROS2 action to 3 Zenoh queriers (send_goal, get_result, cancel_goal)
    and 2 Zenoh subscribers (feedback, status). Zenoh keyexprs follow the pattern
    ``{domain_id}/{action_name}/_action/{sub-topic}/{dds_type}/{type_hash}``.
    Liveliness tokens are published under ``@ros2_lv/`` for ROS 2 node and
    endpoint discovery.

    Always call ``close()`` when done. Zenoh creates non-daemon background threads
    for each subscriber, which block interpreter shutdown until the subscribers
    are undeclared.
    """

    class GoalHandle:
        """Handle for a submitted action goal returned by send_goal."""

        def __init__(
            self,
            goal_id: bytes,
            accepted: bool,
            client: "ROS2ActionClient",
        ):
            """Store the goal UUID and a back-reference to the owning client.

            Args:
                goal_id: 16-byte UUID identifying this goal.
                accepted: Whether the action server accepted the goal.
                client: Owning ROS2ActionClient used to issue follow-up queries.
            """
            self.goal_id = goal_id
            self.accepted = accepted
            self._client = client

        def get_result(self, timeout: Optional[float] = None) -> Optional[object]:
            """Block until the action server sends the result.

            Args:
                timeout: Maximum wait in seconds. None waits indefinitely.

            Returns:
                GetResult_Response object, or None on timeout or error.
            """
            return self._client._call_get_result(self.goal_id, timeout=timeout)

        def cancel(self) -> Optional[object]:
            """Request cancellation of this goal.

            Returns:
                CancelGoal_Response object, or None on timeout or error.
            """
            return self._client._call_cancel_goal(self.goal_id)

    def __init__(
        self,
        action_name: str,
        action_type: str,
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: Optional[int] = None,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        timeout: float = 10.0,
        qos: Optional[object] = None,
    ):
        """Create a ROS2 action client.

        Internally declares 1 node liveliness token, 3 service-client (SC)
        liveliness tokens, 2 subscription (MS) liveliness tokens, 3 Zenoh
        queriers, and 2 Zenoh subscribers.

        Args:
            action_name: ROS2 action name (e.g., ``"/fibonacci"``).
            action_type: ROS2 action type (e.g.,
                ``"example_interfaces/action/Fibonacci"``).
            node_name: Node name. Auto-generated as
                ``zenoh_action_client_<hex8>`` if None.
            namespace: ROS2 node namespace.
            domain_id: ROS domain ID. Defaults to ``$ROS_DOMAIN_ID`` or 0.
            router_ip: Zenoh router IP address.
            router_port: Zenoh router port.
            timeout: Timeout in seconds for send_goal and cancel_goal queries.
                get_result uses a 24-hour Zenoh-level timeout; callers control
                their own wait via ``GoalHandle.get_result(timeout=…)``.
            qos: QoS for liveliness discovery tokens. Accepts ``QosProfile``,
                an encoded rmw_zenoh QoS string, or None for the default profile.

        Raises:
            ValueError: If ``action_type`` is not in ``pkg/action/Name`` format.
            RuntimeError: If action definitions cannot be loaded from the registry.

        Examples:
            client = ROS2ActionClient(
                action_name="/fibonacci",
                action_type="example_interfaces/action/Fibonacci",
            )
            goal = client.send_goal(order=10)
            if goal:
                result = goal.get_result(timeout=30.0)
            client.close()
        """
        self.action_name = action_name
        self.action_type = action_type
        self.domain_id = resolve_domain_id(domain_id)
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_action_client_{uuid.uuid4().hex[:8]}"
        self.timeout = timeout
        _, self.qos = self._normalize_qos(
            qos, default=DEFAULT_QOS_PROFILE, fallback=DEFAULT_QOS_PROFILE.encode()
        )

        parts = action_type.split("/")
        if len(parts) != 3 or parts[1] != "action":
            raise ValueError(
                f"Invalid action type format: {action_type}. Expected: pkg/action/Name"
            )

        # Get or create shared Zenoh session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)

        # Load all action sub-types via the message registry
        registry = get_registry()
        try:
            registry.load_action_type(action_type)
        except Exception as e:
            raise RuntimeError(f"Failed to load action type {action_type}: {e}") from e

        # Synthesized type names
        self._send_goal_req_type = f"{action_type}_SendGoal_Request"
        self._send_goal_resp_type = f"{action_type}_SendGoal_Response"
        self._get_result_req_type = f"{action_type}_GetResult_Request"
        self._get_result_resp_type = f"{action_type}_GetResult_Response"
        self._cancel_goal_req_type = "action_msgs/srv/CancelGoal_Request"
        self._cancel_goal_resp_type = "action_msgs/srv/CancelGoal_Response"
        self._feedback_msg_type = f"{action_type}_FeedbackMessage"
        self._status_msg_type = "action_msgs/msg/GoalStatusArray"

        # Helper message classes for building nested request structs
        self._goal_class = self.session_mgr.register_message_type(
            None, f"{action_type}_Goal"
        )
        self._uuid_class = self.session_mgr.register_message_type(
            None, "unique_identifier_msgs/msg/UUID"
        )
        self._time_class = self.session_mgr.register_message_type(
            None, "builtin_interfaces/msg/Time"
        )
        self._goal_info_class = self.session_mgr.register_message_type(
            None, "action_msgs/msg/GoalInfo"
        )

        # Service/message request/response classes
        self._send_goal_req_class = self.session_mgr.register_message_type(
            None, self._send_goal_req_type
        )
        self._send_goal_resp_class = self.session_mgr.register_message_type(
            None, self._send_goal_resp_type
        )
        self._get_result_req_class = self.session_mgr.register_message_type(
            None, self._get_result_req_type
        )
        self._get_result_resp_class = self.session_mgr.register_message_type(
            None, self._get_result_resp_type
        )
        self._cancel_goal_req_class = self.session_mgr.register_message_type(
            None, self._cancel_goal_req_type
        )
        self._cancel_goal_resp_class = self.session_mgr.register_message_type(
            None, self._cancel_goal_resp_type
        )
        self._feedback_msg_class = self.session_mgr.register_message_type(
            None, self._feedback_msg_type
        )
        self._status_msg_class = self.session_mgr.register_message_type(
            None, self._status_msg_type
        )

        # Store type names (rosbags may remap srv/ types internally)
        _rt = self.session_mgr._registered_types
        self._send_goal_req_store = _rt.get(
            self._send_goal_req_type, self._send_goal_req_type
        )
        self._send_goal_resp_store = _rt.get(
            self._send_goal_resp_type, self._send_goal_resp_type
        )
        self._get_result_req_store = _rt.get(
            self._get_result_req_type, self._get_result_req_type
        )
        self._get_result_resp_store = _rt.get(
            self._get_result_resp_type, self._get_result_resp_type
        )
        self._cancel_goal_req_store = _rt.get(
            self._cancel_goal_req_type, self._cancel_goal_req_type
        )
        self._cancel_goal_resp_store = _rt.get(
            self._cancel_goal_resp_type, self._cancel_goal_resp_type
        )
        self._feedback_msg_store = _rt.get(
            self._feedback_msg_type, self._feedback_msg_type
        )
        self._status_msg_store = _rt.get(self._status_msg_type, self._status_msg_type)

        # Compute type hashes for all 5 endpoints
        hashes = self._compute_type_hashes(action_type, registry)
        self._send_goal_hash = hashes["send_goal"]
        self._get_result_hash = hashes["get_result"]
        self._feedback_hash = hashes["feedback_message"]
        self._cancel_goal_hash = hashes["cancel_goal"]
        self._status_hash = hashes["status"]

        # DDS type names
        # Action sub-services use ros2_to_dds_type on the service type (no suffix stripping
        # needed because we pass the bare service name, e.g. "pkg/action/Name_SendGoal").
        self._send_goal_dds = ros2_to_dds_type(f"{action_type}_SendGoal")
        self._get_result_dds = ros2_to_dds_type(f"{action_type}_GetResult")
        self._cancel_goal_dds = ros2_to_dds_type("action_msgs/srv/CancelGoal")
        self._feedback_dds = ros2_to_dds_type(f"{action_type}_FeedbackMessage")
        self._status_dds = ros2_to_dds_type("action_msgs/msg/GoalStatusArray")

        # Feedback routing: goal_id (bytes) → callback
        self._feedback_callbacks: Dict[bytes, Callable] = {}
        self._feedback_lock = threading.Lock()

        # Sequence numbers and state
        self._sequence_number = 1
        self._seq_lock = threading.Lock()
        self._closed = False

        # Per-endpoint GIDs and entity IDs
        self._send_goal_gid = self.session_mgr.generate_gid()
        self._get_result_gid = self.session_mgr.generate_gid()
        self._cancel_goal_gid = self.session_mgr.generate_gid()
        self._feedback_gid = self.session_mgr.generate_gid()
        self._status_gid = self.session_mgr.generate_gid()

        self.node_id = self.session_mgr.get_next_node_id()
        self._send_goal_entity_id = self.session_mgr.get_next_entity_id()
        self._get_result_entity_id = self.session_mgr.get_next_entity_id()
        self._cancel_goal_entity_id = self.session_mgr.get_next_entity_id()
        self._feedback_entity_id = self.session_mgr.get_next_entity_id()
        self._status_entity_id = self.session_mgr.get_next_entity_id()

        # Build Zenoh key expressions
        _send_goal_topic = f"{action_name}/_action/send_goal"
        _get_result_topic = f"{action_name}/_action/get_result"
        _cancel_goal_topic = f"{action_name}/_action/cancel_goal"
        _feedback_topic = f"{action_name}/_action/feedback"
        _status_topic = f"{action_name}/_action/status"

        self._send_goal_keyexpr = topic_keyexpr(
            self.domain_id, _send_goal_topic, self._send_goal_dds, self._send_goal_hash
        )
        self._get_result_keyexpr = topic_keyexpr(
            self.domain_id,
            _get_result_topic,
            self._get_result_dds,
            self._get_result_hash,
        )
        self._cancel_goal_keyexpr = topic_keyexpr(
            self.domain_id,
            _cancel_goal_topic,
            self._cancel_goal_dds,
            self._cancel_goal_hash,
        )
        self._feedback_keyexpr = topic_keyexpr(
            self.domain_id, _feedback_topic, self._feedback_dds, self._feedback_hash
        )
        self._status_keyexpr = topic_keyexpr(
            self.domain_id, _status_topic, self._status_dds, self._status_hash
        )

        # Declare liveliness tokens
        self._declare_liveliness_tokens(
            _send_goal_topic,
            _get_result_topic,
            _cancel_goal_topic,
            _feedback_topic,
            _status_topic,
        )

        # Declare queriers
        _timeout_ms = int(self.timeout * 1000)
        self._send_goal_querier = self.session_mgr.session.declare_querier(
            zenoh.KeyExpr(self._send_goal_keyexpr),
            target=zenoh.QueryTarget.ALL_COMPLETE,
            timeout=_timeout_ms,
            consolidation=zenoh.ConsolidationMode.NONE,
        )
        # get_result uses a 24-hour Zenoh timeout so the server can hold the
        # query open while the goal runs; Python-level timeouts are applied
        # independently in GoalHandle.get_result(timeout=…).
        self._get_result_querier = self.session_mgr.session.declare_querier(
            zenoh.KeyExpr(self._get_result_keyexpr),
            target=zenoh.QueryTarget.ALL_COMPLETE,
            timeout=86_400_000,
            consolidation=zenoh.ConsolidationMode.NONE,
        )
        self._cancel_goal_querier = self.session_mgr.session.declare_querier(
            zenoh.KeyExpr(self._cancel_goal_keyexpr),
            target=zenoh.QueryTarget.ALL_COMPLETE,
            timeout=_timeout_ms,
            consolidation=zenoh.ConsolidationMode.NONE,
        )

        # Declare subscribers
        self._feedback_sub = self.session_mgr.session.declare_subscriber(
            self._feedback_keyexpr, self._feedback_router
        )
        self._status_sub = self.session_mgr.session.declare_subscriber(
            self._status_keyexpr, self._status_listener
        )

    @staticmethod
    def _normalize_qos(
        qos: Optional[object],
        *,
        default: QosProfile,
        fallback: str,
    ) -> tuple[QosProfile, str]:
        """Normalize a qos argument to a (QosProfile, encoded_string) pair."""
        if qos is None:
            return default, fallback
        if isinstance(qos, QosProfile):
            return qos, qos.encode()
        if isinstance(qos, str):
            return QosProfile.decode(qos), qos
        return default, fallback

    def _compute_type_hashes(self, action_type: str, registry) -> dict:
        """Compute ROS2 type hashes for all 5 action endpoints."""
        action_file = registry.get_action_file_path(action_type)
        if not action_file or not action_file.exists():
            raise RuntimeError(f"Action file not found for {action_type}")

        with open(action_file, "r") as f:
            content = f.read()

        sections = content.split("---")
        if len(sections) != 3:
            raise ValueError(
                f"Invalid .action file for {action_type}: expected 3 sections, got {len(sections)}"
            )

        goal_def = sections[0].strip()
        result_def = sections[1].strip()
        feedback_def = sections[2].strip()

        # Gather dependencies for goal/result/feedback fields
        goal_deps = load_dependencies_recursive(
            f"{action_type}_Goal", goal_def, registry
        )
        result_deps = load_dependencies_recursive(
            f"{action_type}_Result", result_def, registry
        )
        feedback_deps = load_dependencies_recursive(
            f"{action_type}_Feedback", feedback_def, registry
        )
        action_deps = {**goal_deps, **result_deps, **feedback_deps}

        # Hashes for send_goal, get_result, feedback_message
        action_hashes = compute_action_type_hashes(
            action_type, goal_def, result_def, feedback_def, dependencies=action_deps
        )

        # Hash for cancel_goal (standard action_msgs/srv/CancelGoal)
        cancel_srv = "action_msgs/srv/CancelGoal"
        cancel_file = registry.get_srv_file_path(cancel_srv, is_request=True)
        if not cancel_file or not cancel_file.exists():
            raise RuntimeError(f"Service file not found for {cancel_srv}")
        with open(cancel_file, "r") as f:
            cancel_content = f.read()
        cancel_parts = cancel_content.split("---", 1)
        cancel_req_def = cancel_parts[0].strip()
        cancel_resp_def = cancel_parts[1].strip() if len(cancel_parts) > 1 else ""
        cancel_deps = {
            **load_dependencies_recursive(
                "action_msgs/srv/CancelGoal_Request", cancel_req_def, registry
            ),
            **load_dependencies_recursive(
                "action_msgs/srv/CancelGoal_Response", cancel_resp_def, registry
            ),
        }
        cancel_goal_hash = compute_service_type_hash(
            cancel_srv, cancel_req_def, cancel_resp_def, dependencies=cancel_deps
        )

        # Hash for status (action_msgs/msg/GoalStatusArray)
        status_msg = "action_msgs/msg/GoalStatusArray"
        status_file = registry.get_msg_file_path(status_msg)
        if not status_file or not status_file.exists():
            raise RuntimeError(f"Message file not found for {status_msg}")
        with open(status_file, "r") as f:
            status_def = f.read()
        status_deps = load_dependencies_recursive(status_msg, status_def, registry)
        status_hash = get_type_hash(
            status_msg, msg_definition=status_def, dependencies=status_deps
        )

        return {
            "send_goal": action_hashes["send_goal"],
            "get_result": action_hashes["get_result"],
            "feedback_message": action_hashes["feedback_message"],
            "cancel_goal": cancel_goal_hash,
            "status": status_hash,
        }

    def _declare_liveliness_tokens(
        self,
        send_goal_topic: str,
        get_result_topic: str,
        cancel_goal_topic: str,
        feedback_topic: str,
        status_topic: str,
    ):
        """Declare the node liveliness token and all 5 endpoint tokens."""
        node = NodeEntity(
            domain_id=self.domain_id,
            session_id=self.session_mgr.session_id,
            node_id=self.node_id,
            node_name=self.node_name,
            namespace=self.namespace,
        )
        self.node_token = self.session_mgr.liveliness.declare_token(
            node_liveliness_keyexpr(node)
        )

        def _sc(entity_id, name, dds_type, type_hash, gid):
            ep = EndpointEntity(
                node=node,
                entity_id=entity_id,
                kind=EntityKind.CLIENT,
                name=name,
                dds_type_name=dds_type,
                type_hash=type_hash,
                qos=self.qos,
                gid=gid,
            )
            return self.session_mgr.liveliness.declare_token(
                endpoint_liveliness_keyexpr(ep)
            )

        def _ms(entity_id, name, dds_type, type_hash, gid):
            ep = EndpointEntity(
                node=node,
                entity_id=entity_id,
                kind=EntityKind.SUBSCRIPTION,
                name=name,
                dds_type_name=dds_type,
                type_hash=type_hash,
                qos=self.qos,
                gid=gid,
            )
            return self.session_mgr.liveliness.declare_token(
                endpoint_liveliness_keyexpr(ep)
            )

        self._send_goal_token = _sc(
            self._send_goal_entity_id,
            send_goal_topic,
            self._send_goal_dds,
            self._send_goal_hash,
            self._send_goal_gid,
        )
        self._get_result_token = _sc(
            self._get_result_entity_id,
            get_result_topic,
            self._get_result_dds,
            self._get_result_hash,
            self._get_result_gid,
        )
        self._cancel_goal_token = _sc(
            self._cancel_goal_entity_id,
            cancel_goal_topic,
            self._cancel_goal_dds,
            self._cancel_goal_hash,
            self._cancel_goal_gid,
        )
        self._feedback_token = _ms(
            self._feedback_entity_id,
            feedback_topic,
            self._feedback_dds,
            self._feedback_hash,
            self._feedback_gid,
        )
        self._status_token = _ms(
            self._status_entity_id,
            status_topic,
            self._status_dds,
            self._status_hash,
            self._status_gid,
        )

    def _next_seq(self) -> int:
        """Return and increment the monotonic per-client CDR sequence number."""
        with self._seq_lock:
            seq = self._sequence_number
            self._sequence_number += 1
        return seq

    def _make_uuid_msg(self, goal_id_bytes: bytes):
        """Wrap 16 raw bytes into a UUID message object."""
        return self._uuid_class(uuid=np.frombuffer(goal_id_bytes, dtype=np.uint8))

    def _goal_id_to_key(self, uuid_msg) -> bytes:
        """Extract a hashable bytes key from a UUID message field."""
        raw = uuid_msg.uuid
        if hasattr(raw, "tobytes"):
            return raw.tobytes()
        return bytes(raw)

    def _serialize(self, msg, store_type: str) -> bytes:
        """Serialize a rosbags message to CDR bytes via the shared type store."""
        return bytes(self.session_mgr.store.serialize_cdr(msg, store_type))

    def _deserialize(self, cdr_bytes: bytes, store_type: str):
        """Deserialize CDR bytes into a rosbags message via the shared type store."""
        return self.session_mgr.store.deserialize_cdr(cdr_bytes, store_type)

    def _extract_reply_payload(self, reply) -> Optional[bytes]:
        """Return CDR bytes from a successful reply, or None on error."""
        if reply.err is not None:
            payload = getattr(reply.err, "payload", None)
            if payload is not None and hasattr(payload, "to_bytes"):
                logger.error(
                    f"Action reply error: {payload.to_bytes().decode('utf-8', errors='ignore')}"
                )
            return None
        if reply.ok is not None:
            payload = getattr(reply.ok, "payload", None)
            if payload is not None and hasattr(payload, "to_bytes"):
                return payload.to_bytes()
        logger.error("Reply has neither ok nor err")
        return None

    def _run_query(
        self,
        querier,
        payload_bytes: bytes,
        gid: bytes,
        resp_store_type: str,
        timeout: Optional[float],
    ) -> Optional[object]:
        """Send a Zenoh query and block until a response arrives or the timeout elapses."""
        attachment = Attachment(
            sequence_id=self._next_seq(),
            timestamp_ns=int(time.time() * 1e9),
            gid=gid,
        ).to_bytes()

        event = threading.Event()
        result: dict = {"response": None}

        def _on_reply(reply: zenoh.Reply):
            try:
                cdr = self._extract_reply_payload(reply)
                if cdr is not None:
                    result["response"] = self._deserialize(cdr, resp_store_type)
            except Exception as e:
                logger.error(f"Error processing action reply: {e}", exc_info=True)
            finally:
                event.set()

        querier.get(
            _on_reply,
            parameters="",
            payload=zenoh.ZBytes(payload_bytes),
            encoding=Encoding("application/cdr"),
            attachment=zenoh.ZBytes(attachment),
        )

        wait_secs = timeout if timeout is not None else self.timeout
        if event.wait(timeout=wait_secs):
            return result["response"]
        logger.warning(f"Action query timed out after {wait_secs}s")
        return None

    def _run_query_async(
        self,
        querier,
        payload_bytes: bytes,
        gid: bytes,
        resp_store_type: str,
        callback: Callable,
    ) -> None:
        """Send a Zenoh query and invoke a callback when the reply arrives."""
        attachment = Attachment(
            sequence_id=self._next_seq(),
            timestamp_ns=int(time.time() * 1e9),
            gid=gid,
        ).to_bytes()

        def _on_reply(reply: zenoh.Reply):
            try:
                cdr = self._extract_reply_payload(reply)
                callback(
                    self._deserialize(cdr, resp_store_type) if cdr is not None else None
                )
            except Exception as e:
                logger.error(f"Error processing async action reply: {e}", exc_info=True)
                callback(None)

        querier.get(
            _on_reply,
            parameters="",
            payload=zenoh.ZBytes(payload_bytes),
            encoding=Encoding("application/cdr"),
            attachment=zenoh.ZBytes(attachment),
        )

    def send_goal(
        self,
        feedback_callback: Optional[Callable] = None,
        **kwargs,
    ) -> Optional["ROS2ActionClient.GoalHandle"]:
        """Send a goal to the action server synchronously.

        Blocks until the server accepts or rejects the goal, or the client
        timeout elapses. If ``feedback_callback`` is provided it is registered
        before the query is sent so no feedback messages are missed.

        Args:
            feedback_callback: Optional callable invoked as
                ``feedback_callback(feedback_msg)`` for each feedback message
                published for this goal. Called from a Zenoh background thread.
            **kwargs: Goal field values forwarded to the Goal message constructor.

        Returns:
            GoalHandle if the server accepted the goal, or None if the goal was
            rejected or the request timed out.

        Examples:
            goal = client.send_goal(
                feedback_callback=lambda msg: print(msg),
                order=10,
            )
            if goal:
                result = goal.get_result(timeout=30.0)
        """
        goal_id = uuid.uuid4().bytes
        goal_id_key = bytes(goal_id)

        if feedback_callback is not None:
            with self._feedback_lock:
                self._feedback_callbacks[goal_id_key] = feedback_callback

        request = self._build_send_goal_request(goal_id, kwargs)
        payload = self._serialize(request, self._send_goal_req_store)
        response = self._run_query(
            self._send_goal_querier,
            payload,
            self._send_goal_gid,
            self._send_goal_resp_store,
            timeout=self.timeout,
        )

        if response is None or not response.accepted:
            with self._feedback_lock:
                self._feedback_callbacks.pop(goal_id_key, None)
            return None

        return ROS2ActionClient.GoalHandle(goal_id_key, accepted=True, client=self)

    def send_goal_async(
        self,
        callback: Callable,
        feedback_callback: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Send a goal to the action server asynchronously.

        Returns immediately. Both ``callback`` and ``feedback_callback`` are
        invoked from Zenoh background threads and must be thread-safe.

        Args:
            callback: Called with a GoalHandle when the goal is accepted, or
                with None when rejected or on error.
            feedback_callback: Optional callable invoked as
                ``feedback_callback(feedback_msg)`` for each feedback message
                published for this goal.
            **kwargs: Goal field values forwarded to the Goal message constructor.
        """
        goal_id = uuid.uuid4().bytes
        goal_id_key = bytes(goal_id)

        if feedback_callback is not None:
            with self._feedback_lock:
                self._feedback_callbacks[goal_id_key] = feedback_callback

        request = self._build_send_goal_request(goal_id, kwargs)
        payload = self._serialize(request, self._send_goal_req_store)

        def _on_response(response):
            if response is None or not response.accepted:
                with self._feedback_lock:
                    self._feedback_callbacks.pop(goal_id_key, None)
                callback(None)
            else:
                callback(
                    ROS2ActionClient.GoalHandle(goal_id_key, accepted=True, client=self)
                )

        self._run_query_async(
            self._send_goal_querier,
            payload,
            self._send_goal_gid,
            self._send_goal_resp_store,
            callback=_on_response,
        )

    def _build_send_goal_request(self, goal_id: bytes, goal_kwargs: dict):
        """Construct a SendGoal_Request message from raw goal_id bytes and goal fields."""
        uuid_msg = self._make_uuid_msg(goal_id)
        goal_msg = self._goal_class(**goal_kwargs)
        return self._send_goal_req_class(goal_id=uuid_msg, goal=goal_msg)

    def _call_get_result(
        self, goal_id: bytes, timeout: Optional[float] = None
    ) -> Optional[object]:
        """Build and send a GetResult_Request; block until the result arrives or timeout."""
        uuid_msg = self._make_uuid_msg(goal_id)
        request = self._get_result_req_class(goal_id=uuid_msg)
        payload = self._serialize(request, self._get_result_req_store)
        return self._run_query(
            self._get_result_querier,
            payload,
            self._get_result_gid,
            self._get_result_resp_store,
            timeout=timeout,
        )

    def _call_cancel_goal(self, goal_id: bytes) -> Optional[object]:
        """Build and send a CancelGoal_Request; block until the response arrives or timeout."""
        uuid_msg = self._make_uuid_msg(goal_id)
        stamp = self._time_class(sec=0, nanosec=0)
        goal_info = self._goal_info_class(goal_id=uuid_msg, stamp=stamp)
        request = self._cancel_goal_req_class(goal_info=goal_info)
        payload = self._serialize(request, self._cancel_goal_req_store)
        return self._run_query(
            self._cancel_goal_querier,
            payload,
            self._cancel_goal_gid,
            self._cancel_goal_resp_store,
            timeout=self.timeout,
        )

    def _feedback_router(self, sample) -> None:
        """Deserialize a FeedbackMessage and dispatch to the registered callback."""
        try:
            payload = getattr(sample, "payload", None)
            if payload is None or not hasattr(payload, "to_bytes"):
                return
            cdr_bytes = payload.to_bytes()
            if not cdr_bytes:
                return

            msg = self._deserialize(cdr_bytes, self._feedback_msg_store)

            goal_id_key = self._goal_id_to_key(msg.goal_id)
            with self._feedback_lock:
                cb = self._feedback_callbacks.get(goal_id_key)
            if cb is not None:
                cb(msg.feedback)
        except Exception as e:
            logger.error(f"Error in feedback router: {e}", exc_info=True)

    def _status_listener(self, sample) -> None:
        """Receive GoalStatusArray updates (no-op by default; subclass to override)."""
        pass

    def close(self) -> None:
        """Undeclare all liveliness tokens, queriers, and subscribers.

        Idempotent safe to call multiple times. Must be called when done to
        allow the process to exit cleanly; Zenoh creates non-daemon background
        threads for each subscriber that block interpreter shutdown until they
        are undeclared.
        """
        if getattr(self, "_closed", False):
            return

        tokens = [
            "node_token",
            "_send_goal_token",
            "_get_result_token",
            "_cancel_goal_token",
            "_feedback_token",
            "_status_token",
        ]
        queriers = ["_send_goal_querier", "_get_result_querier", "_cancel_goal_querier"]
        subscribers = ["_feedback_sub", "_status_sub"]

        try:
            for attr in tokens:
                tok = getattr(self, attr, None)
                if tok is not None:
                    tok.undeclare()
                    setattr(self, attr, None)

            for attr in queriers:
                q = getattr(self, attr, None)
                if q is not None:
                    if hasattr(q, "undeclare"):
                        q.undeclare()
                    setattr(self, attr, None)

            for attr in subscribers:
                s = getattr(self, attr, None)
                if s is not None:
                    if hasattr(s, "undeclare"):
                        s.undeclare()
                    setattr(self, attr, None)

            self._closed = True
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                f"Error during action client cleanup for {self.action_name}: {e}"
            )
            self._closed = True
        except Exception as e:
            logger.warning(
                f"Unexpected error during action client cleanup for {self.action_name}: {e}"
            )
            self._closed = True
