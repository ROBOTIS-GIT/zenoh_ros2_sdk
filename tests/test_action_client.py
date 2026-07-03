"""
Unit tests for ROS2ActionClient
"""
import pytest
from zenoh_ros2_sdk import ROS2ActionClient
from zenoh_ros2_sdk.session import ZenohSession
import zenoh_ros2_sdk.message_registry as _msg_registry_module

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
