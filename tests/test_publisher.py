"""
Unit tests for ROS2Publisher
"""
import pytest
import time
from zenoh_ros2_sdk import ROS2Publisher
from zenoh_ros2_sdk.session import ZenohSession


class TestROS2Publisher:
    """Tests for ROS2Publisher class"""

    def test_publisher_creation(self):
        """Test creating a publisher"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0
        )

        assert pub.topic == "/test_topic"
        assert pub.msg_type == "std_msgs/msg/String"
        assert pub.domain_id == 0
        assert pub.node_name is not None

        pub.close()

    def test_publisher_custom_node_name(self):
        """Test publisher with custom node name"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            node_name="my_custom_node",
            domain_id=0
        )

        assert pub.node_name == "my_custom_node"

        pub.close()

    def test_publisher_namespace(self):
        """Test publisher with custom namespace"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            namespace="/my_namespace",
            domain_id=0
        )

        assert pub.namespace == "/my_namespace"

        pub.close()

    def test_publisher_domain_id(self):
        """Test publisher with custom domain ID"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=30
        )

        assert pub.domain_id == 30

        pub.close()

    def test_publisher_shared_session(self):
        """Test that multiple publishers share the same session"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub1 = ROS2Publisher(
            topic="/topic1",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0
        )

        pub2 = ROS2Publisher(
            topic="/topic2",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0
        )

        # Both should use the same session instance
        assert pub1.session_mgr is pub2.session_mgr

        pub1.close()
        pub2.close()

    def teardown_method(self):
        """Clean up after each test"""
        if ZenohSession._instance:
            try:
                ZenohSession._instance.close()
            except:
                pass
            ZenohSession._instance = None
