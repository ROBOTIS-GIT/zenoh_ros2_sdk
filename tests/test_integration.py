"""
Integration tests for publisher-subscriber communication

Note: These tests require a Zenoh router (zenohd) to be running.
Set ZENOH_ROUTER_IP environment variable to specify router location.
"""
import pytest
import time
import os
from zenoh_ros2_sdk import ROS2Publisher, ROS2Subscriber
from zenoh_ros2_sdk.session import ZenohSession


# Check if integration tests should run
# Set ZENOH_TEST_INTEGRATION=1 to enable
RUN_INTEGRATION = os.getenv("ZENOH_TEST_INTEGRATION", "0") == "1"
ROUTER_IP = os.getenv("ZENOH_ROUTER_IP", "127.0.0.1")


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled. Set ZENOH_TEST_INTEGRATION=1")
class TestPublisherSubscriberIntegration:
    """Integration tests for publisher-subscriber communication"""
    
    def test_string_message_roundtrip(self):
        """Test publishing and receiving String messages"""
        # Reset singleton for clean test
        ZenohSession._instance = None
        
        received_messages = []
        
        def callback(msg):
            received_messages.append(msg.data)
        
        # Create subscriber
        sub = ROS2Subscriber(
            topic="/test/integration/string",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            callback=callback,
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        # Give subscriber time to set up
        time.sleep(0.5)
        
        # Create publisher
        pub = ROS2Publisher(
            topic="/test/integration/string",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        # Publish messages
        test_messages = ["Hello", "World", "Test"]
        for msg in test_messages:
            pub.publish(data=msg)
            time.sleep(0.1)
        
        # Wait for messages to be received
        time.sleep(1.0)
        
        # Clean up
        pub.close()
        sub.close()
        
        # Verify messages were received
        assert len(received_messages) >= len(test_messages)
        for msg in test_messages:
            assert msg in received_messages
    
    def test_int32_message_roundtrip(self):
        """Test publishing and receiving Int32 messages"""
        # Reset singleton for clean test
        ZenohSession._instance = None
        
        received_values = []
        
        def callback(msg):
            received_values.append(msg.data)
        
        # Create subscriber
        sub = ROS2Subscriber(
            topic="/test/integration/int32",
            msg_type="std_msgs/msg/Int32",
            msg_definition="int32 data\n",
            callback=callback,
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        # Give subscriber time to set up
        time.sleep(0.5)
        
        # Create publisher
        pub = ROS2Publisher(
            topic="/test/integration/int32",
            msg_type="std_msgs/msg/Int32",
            msg_definition="int32 data\n",
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        # Publish messages
        test_values = [1, 2, 3, 42, 100]
        for val in test_values:
            pub.publish(data=val)
            time.sleep(0.1)
        
        # Wait for messages to be received
        time.sleep(1.0)
        
        # Clean up
        pub.close()
        sub.close()
        
        # Verify messages were received
        assert len(received_values) >= len(test_values)
        for val in test_values:
            assert val in received_values
    
    def test_multiple_publishers_same_topic(self):
        """Test multiple publishers on the same topic"""
        # Reset singleton for clean test
        ZenohSession._instance = None
        
        received_messages = []
        
        def callback(msg):
            received_messages.append(msg.data)
        
        # Create subscriber
        sub = ROS2Subscriber(
            topic="/test/integration/multi",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            callback=callback,
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        time.sleep(0.5)
        
        # Create multiple publishers
        pub1 = ROS2Publisher(
            topic="/test/integration/multi",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        pub2 = ROS2Publisher(
            topic="/test/integration/multi",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0,
            router_ip=ROUTER_IP
        )
        
        # Publish from both
        pub1.publish(data="Publisher1")
        pub2.publish(data="Publisher2")
        
        time.sleep(1.0)
        
        # Clean up
        pub1.close()
        pub2.close()
        sub.close()
        
        # Should receive messages from both publishers
        assert len(received_messages) >= 2
    
    def teardown_method(self):
        """Clean up after each test"""
        if ZenohSession._instance:
            try:
                ZenohSession._instance.close()
            except:
                pass
            ZenohSession._instance = None
