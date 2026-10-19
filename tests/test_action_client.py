"""
Unit tests for ROS2ActionClient
"""

from concurrent.futures import Future
from types import SimpleNamespace
import threading

import pytest
from zenoh_ros2_sdk import ROS2ActionClient
import zenoh_ros2_sdk.message_registry as _msg_registry_module
from zenoh_ros2_sdk.qos import (
    DEFAULT_QOS_PROFILE,
    DEFAULT_ACTION_FEEDBACK_QOS_PROFILE,
    DEFAULT_ACTION_STATUS_QOS_PROFILE,
)

_ACTION_TYPE = "example_interfaces/action/Fibonacci"
_ACTION_NAME = "/fibonacci"


class TestROS2ActionClient:
    """Tests for ROS2ActionClient class"""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the global message registry so each test starts with a clean store."""
        _msg_registry_module._registry = None
        yield
        _msg_registry_module._registry = None

    def test_action_client_creation(self):
        """Test creating an action client with default parameters"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client.action_name == _ACTION_NAME
        assert client.action_type == _ACTION_TYPE
        assert client.domain_id == 0
        assert client.node_name is not None
        assert client.node_name.startswith("zenoh_action_client_")

        client.close()

    def test_action_client_custom_node_name(self):
        """Test action client with custom node name"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            node_name="my_action_client",
            domain_id=0,
        )

        assert client.node_name == "my_action_client"

        client.close()

    def test_action_client_namespace(self):
        """Test action client with custom namespace"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            namespace="/my_namespace",
            domain_id=0,
        )

        assert client.namespace == "/my_namespace"

        client.close()

    def test_action_client_domain_id(self):
        """Test action client with custom domain ID reflected in all keyexprs"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=42,
        )

        assert client.domain_id == 42
        assert client._send_goal_keyexpr.startswith("42/")
        assert client._get_result_keyexpr.startswith("42/")
        assert client._cancel_goal_keyexpr.startswith("42/")
        assert client._feedback_keyexpr.startswith("42/")
        assert client._status_keyexpr.startswith("42/")

        client.close()

    def test_action_client_type_hashes_format(self):
        """Test that all 5 action endpoint type hashes have the RIHS01_ format"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        _expected_len = 71  # "RIHS01_" (7) + 64 hex chars

        for attr in (
            "_send_goal_hash",
            "_get_result_hash",
            "_feedback_hash",
            "_cancel_goal_hash",
            "_status_hash",
        ):
            h = getattr(client, attr)
            assert h.startswith("RIHS01_"), \
                f"{attr} should start with RIHS01_, got: {h}"
            assert len(h) == _expected_len, \
                f"{attr} should be {_expected_len} chars, got: {len(h)}"

        client.close()

    def test_action_client_send_goal_type_hash(self):
        """Test that all 5 action endpoint type hashes match known-good values"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client._send_goal_hash == \
            "RIHS01_d1a57fb2a4afe8c21e34fb10db206f16ce6729b28531141472df92277c55b557"
        assert client._get_result_hash == \
            "RIHS01_1b0de0d5d29dc955d92f546706568428632771db13ec84c15ec1c1a59f424a57"
        assert client._feedback_hash == \
            "RIHS01_c1de71afd52e49a89c53d8262366884185bc0a02f78ce051c4e46b0a7fe59bb2"
        assert client._cancel_goal_hash == \
            "RIHS01_573d8b0a534451d7bc2ac8c5ffde8ac14b8593b7001175d0cd6516dcbeb8689a"
        assert client._status_hash == \
            "RIHS01_6c1684b00f177d37438febe6e709fc4e2b0d4248dca4854946f9ed8b30cda83e"

        client.close()

    def test_action_client_keyexpr_format_send_goal(self):
        """Test that send_goal keyexpr has the correct format"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=30,
        )

        # Format: domain_id/action_name/_action/send_goal/dds_type/type_hash
        keyexpr = client._send_goal_keyexpr
        parts = keyexpr.split("/")
        assert parts[0] == "30", f"Domain ID should be 30, got: {parts[0]}"
        assert parts[1] == "fibonacci", f"Action name should be 'fibonacci', got: {parts[1]}"
        assert parts[2] == "_action"
        assert parts[3] == "send_goal"
        assert "example_interfaces::action::dds_::Fibonacci_SendGoal_" in keyexpr
        assert client._send_goal_hash in keyexpr

        client.close()

    def test_action_client_keyexpr_format_get_result(self):
        """Test that get_result keyexpr has the correct format"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=30,
        )

        keyexpr = client._get_result_keyexpr
        assert keyexpr.startswith("30/fibonacci/_action/get_result/")
        assert "example_interfaces::action::dds_::Fibonacci_GetResult_" in keyexpr
        assert client._get_result_hash in keyexpr

        client.close()

    def test_action_client_keyexpr_format_cancel_goal(self):
        """Test that cancel_goal keyexpr has the correct format"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=30,
        )

        keyexpr = client._cancel_goal_keyexpr
        assert keyexpr.startswith("30/fibonacci/_action/cancel_goal/")
        assert "action_msgs::srv::dds_::CancelGoal_" in keyexpr
        assert client._cancel_goal_hash in keyexpr

        client.close()

    def test_action_client_keyexpr_format_feedback(self):
        """Test that feedback keyexpr has the correct format"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=30,
        )

        keyexpr = client._feedback_keyexpr
        assert keyexpr.startswith("30/fibonacci/_action/feedback/")
        assert "example_interfaces::action::dds_::Fibonacci_FeedbackMessage_" in keyexpr
        assert client._feedback_hash in keyexpr

        client.close()

    def test_action_client_keyexpr_format_status(self):
        """Test that status keyexpr has the correct format"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=30,
        )

        keyexpr = client._status_keyexpr
        assert keyexpr.startswith("30/fibonacci/_action/status/")
        assert "action_msgs::msg::dds_::GoalStatusArray_" in keyexpr
        assert client._status_hash in keyexpr

        client.close()

    def test_action_client_dds_type_names(self):
        """Test that DDS type names follow the expected naming convention"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client._send_goal_dds == "example_interfaces::action::dds_::Fibonacci_SendGoal_"
        assert client._get_result_dds == "example_interfaces::action::dds_::Fibonacci_GetResult_"
        assert client._cancel_goal_dds == "action_msgs::srv::dds_::CancelGoal_"
        assert client._feedback_dds == "example_interfaces::action::dds_::Fibonacci_FeedbackMessage_"
        assert client._status_dds == "action_msgs::msg::dds_::GoalStatusArray_"

        client.close()

    def test_action_client_invalid_action_type_format(self):
        """Test that an invalid action type format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid action type format"):
            ROS2ActionClient(
                action_name=_ACTION_NAME,
                action_type="invalid_format",
                domain_id=0,
            )

    def test_action_client_invalid_action_type_no_action_segment(self):
        """Test that a type missing the 'action' segment raises ValueError"""
        with pytest.raises(ValueError, match="Invalid action type format"):
            ROS2ActionClient(
                action_name=_ACTION_NAME,
                action_type="example_interfaces/srv/Fibonacci",
                domain_id=0,
            )

    def test_action_client_timeout(self):
        """Test action client with custom timeout"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            timeout=5.0,
            domain_id=0,
        )

        assert client.timeout == 5.0

        client.close()

    def test_action_client_default_timeout(self):
        """Test that default timeout is applied"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client.timeout == 10.0

        client.close()

    def test_action_client_ros2_action_qos_defaults(self):
        """Test that action endpoint QoS defaults match rclpy/rcl_action."""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client.goal_service_qos == DEFAULT_QOS_PROFILE.encode()
        assert client.result_service_qos == DEFAULT_QOS_PROFILE.encode()
        assert client.cancel_service_qos == DEFAULT_QOS_PROFILE.encode()
        assert client.feedback_sub_qos == DEFAULT_ACTION_FEEDBACK_QOS_PROFILE.encode()
        assert client.status_sub_qos == DEFAULT_ACTION_STATUS_QOS_PROFILE.encode()

        client.close()

    def test_cancel_goal_request_serializes(self):
        """CancelGoal uses action_msgs/msg/GoalInfo, not a service-local fallback type."""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        uuid_msg = client._make_uuid_msg(bytes(range(16)))
        stamp = client._time_class(sec=0, nanosec=0)
        goal_info = client._goal_info_class(goal_id=uuid_msg, stamp=stamp)
        request = client._cancel_goal_req_class(goal_info=goal_info)

        payload = client._serialize(request, client._cancel_goal_req_store)

        assert payload

        client.close()

    def test_action_client_shared_session(self):
        """Test that multiple action clients share the same Zenoh session"""
        client1 = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )
        client2 = ROS2ActionClient(
            action_name="/navigate_to_pose",
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client1.session_mgr is client2.session_mgr

        client1.close()
        client2.close()

    def test_send_goal_returns_final_result(self):
        """Synchronous send_goal follows rclpy and returns the final result response."""
        client = object.__new__(ROS2ActionClient)
        result = object()

        class _Handle:
            accepted = True

            def get_result(self, timeout=None):
                assert timeout == 12.0
                return result

        future = Future()
        future.set_result(_Handle())
        calls = {}

        def _send_goal_async(goal=None, **kwargs):
            calls["goal"] = goal
            calls["kwargs"] = kwargs
            return future

        client.send_goal_async = _send_goal_async

        assert client.send_goal(order=10, result_timeout=12.0) is result
        assert calls["goal"] is None
        assert calls["kwargs"]["order"] == 10
        assert calls["kwargs"]["feedback_callback"] is None
        assert "timeout" in calls["kwargs"]

    def test_send_goal_returns_none_for_rejected_goal(self):
        """Synchronous send_goal does not request a result for rejected goals."""
        client = object.__new__(ROS2ActionClient)

        class _Handle:
            accepted = False

            def get_result(self, timeout=None):
                raise AssertionError("get_result should not be called")

        future = Future()
        future.set_result(_Handle())
        client.send_goal_async = lambda *args, **kwargs: future

        assert client.send_goal(order=10) is None

    def test_run_query_async_times_out_without_reply(self):
        """Async Zenoh queries complete even when Zenoh never calls the reply callback."""
        client = object.__new__(ROS2ActionClient)
        client._pending_futures = set()
        client._pending_lock = threading.Lock()
        client._closed = False
        client._sequence_numbers = {"send_goal": 1}
        client._seq_lock = threading.Lock()

        class _Querier:
            def get(self, *args, **kwargs):
                return None

        future = client._run_query_async(
            _Querier(),
            b"payload",
            b"gid",
            "send_goal",
            "response_type",
            timeout=0.01,
        )

        assert future.result(timeout=1.0) is None

    def test_run_query_async_completes_on_zenoh_error(self):
        """Async Zenoh query send errors complete the Future with None."""
        client = object.__new__(ROS2ActionClient)
        client._pending_futures = set()
        client._pending_lock = threading.Lock()
        client._closed = False
        client._sequence_numbers = {"send_goal": 1}
        client._seq_lock = threading.Lock()

        class _Querier:
            def get(self, *args, **kwargs):
                raise RuntimeError("boom")

        future = client._run_query_async(
            _Querier(),
            b"payload",
            b"gid",
            "send_goal",
            "response_type",
            timeout=1.0,
        )

        assert future.result(timeout=1.0) is None

    def test_feedback_router_passes_full_feedback_message(self):
        """Feedback callbacks receive FeedbackMessage, matching rclpy."""
        client = object.__new__(ROS2ActionClient)
        goal_id = bytes(range(16))
        received = []
        client._feedback_callbacks = {goal_id: received.append}
        client._feedback_lock = threading.Lock()
        client._feedback_msg_store = "feedback"
        feedback_msg = SimpleNamespace(
            goal_id=SimpleNamespace(uuid=goal_id),
            feedback=SimpleNamespace(sequence=[1, 1, 2]),
        )
        client._deserialize = lambda cdr, store: feedback_msg

        class _Payload:
            def to_bytes(self):
                return b"cdr"

        client._feedback_router(SimpleNamespace(payload=_Payload()))

        assert received == [feedback_msg]

    def test_status_listener_updates_and_removes_terminal_goal(self):
        """Terminal status updates clean active handles and feedback callbacks."""
        client = object.__new__(ROS2ActionClient)
        goal_id = bytes(range(16))
        handle = ROS2ActionClient.GoalHandle(goal_id, accepted=True, client=client)
        client._goal_handles = {goal_id: handle}
        client._goal_lock = threading.Lock()
        client._feedback_callbacks = {goal_id: lambda msg: None}
        client._feedback_lock = threading.Lock()
        client._status_msg_store = "status"
        status_msg = SimpleNamespace(
            status_list=[
                SimpleNamespace(
                    goal_info=SimpleNamespace(
                        goal_id=SimpleNamespace(uuid=goal_id),
                    ),
                    status=4,
                )
            ]
        )
        client._deserialize = lambda cdr, store: status_msg

        class _Payload:
            def to_bytes(self):
                return b"cdr"

        client._status_listener(SimpleNamespace(payload=_Payload()))

        assert handle.status == 4
        assert goal_id not in client._goal_handles
        assert goal_id not in client._feedback_callbacks

    def test_close_completes_pending_query_futures(self):
        """Closing the client completes pending action futures so callers do not hang."""
        client = object.__new__(ROS2ActionClient)
        future = Future()
        client._close_lock = threading.Lock()
        client._closed = False
        client._pending_futures = {future}
        client._pending_lock = threading.Lock()
        client._feedback_callbacks = {b"goal": lambda msg: None}
        client._feedback_lock = threading.Lock()
        client._goal_handles = {}
        client._goal_lock = threading.Lock()

        client.close()

        assert future.done()
        assert future.result() is None
        assert client._feedback_callbacks == {}

    def test_action_client_close_idempotent(self):
        """Test that close() can be called multiple times without error"""
        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        client.close()
        client.close()  # should not raise
        client.close()  # should not raise

    def test_action_client_goal_handle_attributes(self):
        """Test that GoalHandle has the expected attributes"""
        import uuid
        goal_id = uuid.uuid4().bytes

        client = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        handle = ROS2ActionClient.GoalHandle(
            goal_id=goal_id,
            accepted=True,
            client=client,
        )

        assert handle.goal_id == goal_id
        assert handle.accepted is True
        assert handle._client is client

        client.close()

    def test_action_client_node_id_and_entity_ids_are_unique(self):
        """Test that two action clients get distinct node/entity IDs"""
        client1 = ROS2ActionClient(
            action_name=_ACTION_NAME,
            action_type=_ACTION_TYPE,
            domain_id=0,
        )
        client2 = ROS2ActionClient(
            action_name="/navigate_to_pose",
            action_type=_ACTION_TYPE,
            domain_id=0,
        )

        assert client1.node_id != client2.node_id

        client1.close()
        client2.close()
