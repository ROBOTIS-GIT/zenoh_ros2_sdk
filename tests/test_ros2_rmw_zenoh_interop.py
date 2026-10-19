"""
ROS 2 Jazzy + rmw_zenoh_cpp interoperability tests.

These tests are intentionally gated because they require a ROS 2 environment,
rmw_zenoh_cpp, and a running rmw_zenohd router. The Docker runner in
docker/ros_jazzy_rmw_zenoh enables them.
"""

import os
import threading
import time
import uuid

import pytest

from zenoh_ros2_sdk import (
    ROS2ActionClient,
    ROS2Publisher,
    ROS2ServiceClient,
    ROS2ServiceServer,
    ROS2Subscriber,
    get_message_class,
    get_service_names_and_types,
    get_topic_names_and_types,
    load_service_type,
)
from zenoh_ros2_sdk.session import ZenohSession
import zenoh_ros2_sdk.message_registry as _msg_registry_module


pytestmark = pytest.mark.skipif(
    os.getenv("ZENOH_ROS2_RMW_ZENOH_INTEROP", "0") != "1",
    reason="Set ZENOH_ROS2_RMW_ZENOH_INTEROP=1 in a ROS 2 rmw_zenoh_cpp environment",
)

DOMAIN_ID = int(os.getenv("ROS_DOMAIN_ID", "42"))
ROUTER_IP = os.getenv("ZENOH_ROUTER_IP", "127.0.0.1")
ROUTER_PORT = int(os.getenv("ZENOH_ROUTER_PORT", "7447"))


def _wait_until(predicate, timeout=10.0, period=0.05, label="condition"):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            if predicate():
                return
        except Exception as exc:
            last_error = exc
        time.sleep(period)
    detail = f" last_error={last_error!r}" if last_error else ""
    raise AssertionError(f"Timed out waiting for {label}.{detail}")


@pytest.fixture(autouse=True)
def reset_sdk_session():
    if ZenohSession._instance is not None:
        ZenohSession._instance.close()
    ZenohSession._instance = None
    _msg_registry_module._registry = None
    yield
    if ZenohSession._instance is not None:
        ZenohSession._instance.close()
    ZenohSession._instance = None
    _msg_registry_module._registry = None


@pytest.fixture(scope="module")
def rclpy_module():
    import rclpy

    rclpy.init(args=None)
    yield rclpy
    rclpy.shutdown()


@pytest.fixture
def ros_executor(rclpy_module):
    from rclpy.executors import MultiThreadedExecutor

    executor = MultiThreadedExecutor(num_threads=4)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    nodes = []

    def create_node(name):
        node = rclpy_module.create_node(name)
        executor.add_node(node)
        nodes.append(node)
        return node

    yield create_node

    executor.shutdown()
    thread.join(timeout=2.0)
    for node in nodes:
        try:
            executor.remove_node(node)
        except Exception:
            pass
        node.destroy_node()


def test_ros_publisher_to_sdk_subscriber(ros_executor):
    from std_msgs.msg import String

    node = ros_executor("ros_pub_to_sdk_sub")
    publisher = node.create_publisher(String, "/interop/ros_to_sdk", 10)
    received = []

    subscriber = ROS2Subscriber(
        topic="/interop/ros_to_sdk",
        msg_type="std_msgs/msg/String",
        callback=lambda msg: received.append(msg.data),
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
    )

    _wait_until(lambda: publisher.get_subscription_count() > 0, label="ROS publisher to see SDK subscriber")

    for _ in range(20):
        publisher.publish(String(data="ros-to-sdk"))
        if "ros-to-sdk" in received:
            break
        time.sleep(0.1)

    subscriber.close()
    assert "ros-to-sdk" in received


def test_sdk_publisher_to_ros_subscriber(ros_executor):
    from std_msgs.msg import String

    node = ros_executor("sdk_pub_to_ros_sub")
    received = []
    node.create_subscription(
        String,
        "/interop/sdk_to_ros",
        lambda msg: received.append(msg.data),
        10,
    )

    publisher = ROS2Publisher(
        topic="/interop/sdk_to_ros",
        msg_type="std_msgs/msg/String",
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
    )

    _wait_until(
        lambda: "/interop/sdk_to_ros" in dict(node.get_topic_names_and_types()),
        label="ROS graph to see SDK publisher",
    )

    for _ in range(20):
        publisher.publish(data="sdk-to-ros")
        if "sdk-to-ros" in received:
            break
        time.sleep(0.1)

    publisher.close()
    assert "sdk-to-ros" in received


def test_sdk_discovers_ros_topic_and_ros_discovers_sdk_topic(ros_executor):
    from std_msgs.msg import String

    node = ros_executor("interop_topic_discovery")
    node.create_publisher(String, "/interop/ros_discovery_topic", 10)
    sdk_publisher = ROS2Publisher(
        topic="/interop/sdk_discovery_topic",
        msg_type="std_msgs/msg/String",
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
    )

    _wait_until(
        lambda: "/interop/ros_discovery_topic"
        in dict(
            get_topic_names_and_types(
                domain_id=DOMAIN_ID,
                router_ip=ROUTER_IP,
                router_port=ROUTER_PORT,
                timeout=0.5,
            )
        ),
        label="SDK discovery to see ROS topic",
    )
    _wait_until(
        lambda: "/interop/sdk_discovery_topic" in dict(node.get_topic_names_and_types()),
        label="ROS graph to see SDK topic",
    )

    sdk_publisher.close()


def test_ros_service_server_to_sdk_client(ros_executor):
    from example_interfaces.srv import AddTwoInts

    node = ros_executor("ros_service_to_sdk_client")

    def handle_request(request, response):
        response.sum = request.a + request.b
        return response

    node.create_service(AddTwoInts, "/interop/ros_add_two_ints", handle_request)

    client = ROS2ServiceClient(
        service_name="/interop/ros_add_two_ints",
        srv_type="example_interfaces/srv/AddTwoInts",
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
        timeout=5.0,
    )

    response = client.call(a=7, b=8)
    client.close()

    assert response is not None
    assert response.sum == 15


def test_sdk_service_server_to_ros_client(ros_executor):
    from example_interfaces.srv import AddTwoInts

    load_service_type("example_interfaces/srv/AddTwoInts")
    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")

    server = ROS2ServiceServer(
        service_name="/interop/sdk_add_two_ints",
        srv_type="example_interfaces/srv/AddTwoInts",
        callback=lambda request: Response(sum=request.a + request.b),
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
    )

    node = ros_executor("sdk_service_to_ros_client")
    client = node.create_client(AddTwoInts, "/interop/sdk_add_two_ints")
    _wait_until(client.service_is_ready, label="ROS client to see SDK service")

    request = AddTwoInts.Request()
    request.a = 11
    request.b = 12
    future = client.call_async(request)

    _wait_until(future.done, label="ROS client service response")
    server.close()

    assert future.result() is not None
    assert future.result().sum == 23


def test_sdk_discovers_ros_service_and_ros_discovers_sdk_service(ros_executor):
    from example_interfaces.srv import AddTwoInts

    node = ros_executor("interop_service_discovery")
    node.create_service(AddTwoInts, "/interop/ros_discovery_service", lambda req, resp: resp)

    load_service_type("example_interfaces/srv/AddTwoInts")
    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
    sdk_server = ROS2ServiceServer(
        service_name="/interop/sdk_discovery_service",
        srv_type="example_interfaces/srv/AddTwoInts",
        callback=lambda request: Response(sum=request.a + request.b),
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
    )

    _wait_until(
        lambda: "/interop/ros_discovery_service"
        in dict(
            get_service_names_and_types(
                domain_id=DOMAIN_ID,
                router_ip=ROUTER_IP,
                router_port=ROUTER_PORT,
                timeout=0.5,
            )
        ),
        label="SDK discovery to see ROS service",
    )
    _wait_until(
        lambda: "/interop/sdk_discovery_service" in dict(node.get_service_names_and_types()),
        label="ROS graph to see SDK service",
    )

    sdk_server.close()


def test_single_python_process_bridges_ros_and_sdk_topics_and_services(ros_executor):
    from example_interfaces.srv import AddTwoInts
    from std_msgs.msg import String

    suffix = f"case_{uuid.uuid4().hex[:8]}"
    node = ros_executor(f"interop_combined_bridge_{suffix}")
    resources = []

    ros_to_sdk_topic = f"/interop/combined/{suffix}/ros_to_sdk"
    sdk_to_ros_topic = f"/interop/combined/{suffix}/sdk_to_ros"
    ros_service = f"/interop/combined/{suffix}/ros_add_two_ints"
    sdk_service = f"/interop/combined/{suffix}/sdk_add_two_ints"

    try:
        ros_publisher = node.create_publisher(String, ros_to_sdk_topic, 10)
        sdk_received = []
        sdk_subscriber = ROS2Subscriber(
            topic=ros_to_sdk_topic,
            msg_type="std_msgs/msg/String",
            callback=lambda msg: sdk_received.append(msg.data),
            domain_id=DOMAIN_ID,
            router_ip=ROUTER_IP,
            router_port=ROUTER_PORT,
        )
        resources.append(sdk_subscriber)

        _wait_until(
            lambda: ros_publisher.get_subscription_count() > 0,
            label="ROS publisher to see SDK subscriber in combined bridge",
        )
        for _ in range(20):
            ros_publisher.publish(String(data="ros-to-sdk"))
            if sdk_received:
                break
            time.sleep(0.1)
        assert sdk_received == ["ros-to-sdk"]

        ros_received = []
        node.create_subscription(
            String,
            sdk_to_ros_topic,
            lambda msg: ros_received.append(msg.data),
            10,
        )
        sdk_publisher = ROS2Publisher(
            topic=sdk_to_ros_topic,
            msg_type="std_msgs/msg/String",
            domain_id=DOMAIN_ID,
            router_ip=ROUTER_IP,
            router_port=ROUTER_PORT,
        )
        resources.append(sdk_publisher)

        _wait_until(
            lambda: sdk_to_ros_topic in dict(node.get_topic_names_and_types()),
            label="ROS graph to see SDK publisher in combined bridge",
        )
        for _ in range(20):
            sdk_publisher.publish(data="sdk-to-ros")
            if ros_received:
                break
            time.sleep(0.1)
        assert ros_received == ["sdk-to-ros"]

        def handle_ros_service(request, response):
            response.sum = request.a + request.b
            return response

        node.create_service(AddTwoInts, ros_service, handle_ros_service)
        sdk_client = ROS2ServiceClient(
            service_name=ros_service,
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=DOMAIN_ID,
            router_ip=ROUTER_IP,
            router_port=ROUTER_PORT,
            timeout=5.0,
        )
        resources.append(sdk_client)

        response = sdk_client.call(a=17, b=25)
        assert response is not None
        assert response.sum == 42

        load_service_type("example_interfaces/srv/AddTwoInts")
        Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
        sdk_server = ROS2ServiceServer(
            service_name=sdk_service,
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=lambda request: Response(sum=request.a + request.b),
            domain_id=DOMAIN_ID,
            router_ip=ROUTER_IP,
            router_port=ROUTER_PORT,
        )
        resources.append(sdk_server)

        ros_client = node.create_client(AddTwoInts, sdk_service)
        _wait_until(
            ros_client.service_is_ready,
            label="ROS client to see SDK service in combined bridge",
        )
        request = AddTwoInts.Request()
        request.a = 19
        request.b = 23
        future = ros_client.call_async(request)

        _wait_until(
            future.done,
            label="ROS client service response in combined bridge",
        )
        assert future.result() is not None
        assert future.result().sum == 42
    finally:
        for resource in reversed(resources):
            resource.close()


def test_ros_action_server_to_sdk_action_client(ros_executor):
    from example_interfaces.action import Fibonacci
    from rclpy.action import ActionServer, CancelResponse

    node = ros_executor("ros_action_to_sdk_client")
    feedback_sequences = []

    def execute_callback(goal_handle):
        sequence = [0, 1]
        for _ in range(1, goal_handle.request.order):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = Fibonacci.Result()
                result.sequence = sequence
                return result
            sequence.append(sequence[-1] + sequence[-2])
            feedback = Fibonacci.Feedback()
            feedback.sequence = sequence
            goal_handle.publish_feedback(feedback)
            time.sleep(0.05)
        goal_handle.succeed()
        result = Fibonacci.Result()
        result.sequence = sequence
        return result

    action_server = ActionServer(
        node,
        Fibonacci,
        "/interop/fibonacci",
        execute_callback,
        cancel_callback=lambda goal_handle: CancelResponse.ACCEPT,
    )

    client = ROS2ActionClient(
        action_name="/interop/fibonacci",
        action_type="example_interfaces/action/Fibonacci",
        domain_id=DOMAIN_ID,
        router_ip=ROUTER_IP,
        router_port=ROUTER_PORT,
        timeout=5.0,
    )

    assert client.wait_for_server(timeout_sec=10.0)

    result = client.send_goal(
        order=5,
        feedback_callback=lambda msg: feedback_sequences.append(list(msg.feedback.sequence)),
        result_timeout=10.0,
    )

    assert result is not None
    assert result.status == 4
    assert list(result.result.sequence) == [0, 1, 1, 2, 3, 5]
    assert feedback_sequences

    goal_future = client.send_goal_async(order=25)
    goal_handle = goal_future.result(timeout=10.0)
    assert goal_handle is not None
    assert goal_handle.accepted

    time.sleep(0.2)
    cancel_response = goal_handle.cancel_goal()
    assert cancel_response is not None
    assert len(cancel_response.goals_canceling) >= 1

    cancel_result = goal_handle.get_result(timeout=10.0)
    assert cancel_result is not None
    assert cancel_result.status == 5

    client.close()
    action_server.destroy()
