"""
Unit tests for ROS2Subscriber
"""
import pytest
from zenoh_ros2_sdk import ROS2Subscriber
from zenoh_ros2_sdk.session import ZenohSession


class TestROS2Subscriber:
    """Tests for ROS2Subscriber class"""

    def test_subscriber_creation(self):
        """Test creating a subscriber"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        def callback(msg):
            pass

        sub = ROS2Subscriber(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            callback=callback,
            domain_id=0
        )

        assert sub.topic == "/test_topic"
        assert sub.msg_type == "std_msgs/msg/String"
        assert sub.domain_id == 0
        assert sub.node_name is not None

        sub.close()

    def test_subscriber_custom_node_name(self):
        """Test subscriber with custom node name"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        def callback(msg):
            pass

        sub = ROS2Subscriber(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            callback=callback,
            node_name="my_custom_subscriber",
            domain_id=0
        )

        assert sub.node_name == "my_custom_subscriber"

        sub.close()

    def test_subscriber_shared_session(self):
        """Test that multiple subscribers share the same session"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        def callback(msg):
            pass

        sub1 = ROS2Subscriber(
            topic="/topic1",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            callback=callback,
            domain_id=0
        )

        sub2 = ROS2Subscriber(
            topic="/topic2",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            callback=callback,
            domain_id=0
        )

        # Both should use the same session instance
        assert sub1.session_mgr is sub2.session_mgr

        sub1.close()
        sub2.close()

    def teardown_method(self):
        """Clean up after each test"""
        if ZenohSession._instance:
            try:
                ZenohSession._instance.close()
            except:
                pass
            ZenohSession._instance = None
