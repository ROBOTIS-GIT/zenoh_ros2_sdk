"""
Integration tests for publisher-subscriber and service client-server communication

Note: These tests require a Zenoh router (zenohd) to be running.
Set ZENOH_ROUTER_IP environment variable to specify router location.
"""
import pytest
import time
import os
from zenoh_ros2_sdk import (
    ROS2Publisher, ROS2Subscriber, ROS2ServiceClient, ROS2ServiceServer,
    load_service_type, get_message_class
)
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


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled. Set ZENOH_TEST_INTEGRATION=1")
class TestServiceClientServerIntegration:
    """Integration tests for service client-server communication"""

    def test_add_two_ints_service_roundtrip(self):
        """Test service client-server communication with AddTwoInts"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        load_service_type("example_interfaces/srv/AddTwoInts")
        Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")

        # Track received requests
        received_requests = []

        def service_callback(request):
            """Service handler that adds two integers"""
            received_requests.append((request.a, request.b))
            sum_result = request.a + request.b
            return Response(sum=sum_result)

        # Create service server
        server = ROS2ServiceServer(
            service_name="/test/integration/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=service_callback,
            domain_id=0,
            router_ip=ROUTER_IP
        )

        # Give server time to set up
        time.sleep(0.5)

        # Create service client
        client = ROS2ServiceClient(
            service_name="/test/integration/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0,
            router_ip=ROUTER_IP,
            timeout=5.0
        )

        # Make service calls
        test_cases = [
            (5, 3, 8),
            (10, 20, 30),
            (100, 200, 300),
            (-5, 10, 5),
        ]

        received_responses = []
        for a, b, expected_sum in test_cases:
            response = client.call(a=a, b=b)
            if response:
                received_responses.append((a, b, response.sum))
                assert response.sum == expected_sum, \
                    f"Service call {a} + {b} = {response.sum}, expected {expected_sum}"
            else:
                pytest.fail(f"Service call failed for {a} + {b}")

        # Wait a bit for all requests to be processed
        time.sleep(0.5)

        # Clean up
        client.close()
        server.close()

        # Verify all requests were received
        assert len(received_requests) == len(test_cases), \
            f"Expected {len(test_cases)} requests, got {len(received_requests)}"
        assert len(received_responses) == len(test_cases), \
            f"Expected {len(test_cases)} responses, got {len(received_responses)}"

        # Verify request values
        for a, b, _ in test_cases:
            assert (a, b) in received_requests, f"Request ({a}, {b}) was not received"

    def test_service_timeout(self):
        """Test service client timeout when no server is available"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        load_service_type("example_interfaces/srv/AddTwoInts")

        # Create service client (no server running)
        client = ROS2ServiceClient(
            service_name="/test/integration/nonexistent",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0,
            router_ip=ROUTER_IP,
            timeout=1.0  # Short timeout
        )

        # Make a call - should timeout
        response = client.call(a=5, b=3)
        assert response is None, "Service call should timeout when no server is available"

        client.close()

    def test_service_async_call(self):
        """Test async service call"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        load_service_type("example_interfaces/srv/AddTwoInts")
        Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")

        def service_callback(request):
            """Service handler"""
            return Response(sum=request.a + request.b)

        # Create service server
        server = ROS2ServiceServer(
            service_name="/test/integration/async",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=service_callback,
            domain_id=0,
            router_ip=ROUTER_IP
        )

        time.sleep(0.5)

        # Create service client
        client = ROS2ServiceClient(
            service_name="/test/integration/async",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0,
            router_ip=ROUTER_IP,
            timeout=5.0
        )

        # Track async responses
        async_responses = []

        def async_callback(response):
            if response:
                async_responses.append(response.sum)

        # Make async call
        client.call_async(async_callback, a=7, b=8)

        # Wait for response
        time.sleep(1.0)

        # Clean up
        client.close()
        server.close()

        # Verify async response was received
        assert len(async_responses) == 1, f"Expected 1 async response, got {len(async_responses)}"
        assert async_responses[0] == 15, f"Expected sum=15, got {async_responses[0]}"

    def teardown_method(self):
        """Clean up after each test"""
        if ZenohSession._instance:
            try:
                ZenohSession._instance.close()
            except:
                pass
            ZenohSession._instance = None
