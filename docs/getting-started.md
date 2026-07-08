# Getting Started

This page is about using the **SDK** (pub/sub/services/action clients). If you want to build the documentation site itself, see `contributing/docs.md`.

## Install

From PyPI:

```bash
pip install zenoh-ros2-sdk
```

From source (editable):

```bash
pip install -e .
```

## Start a Zenoh router (optional but common)

Many setups use a local router. Execute the Zenoh router in a ROS2 environment:

```bash
ros2 run rmw_zenoh_cpp rmw_zenohd
```

If you are connecting to a remote router, pass `router_ip` / `router_port` when creating publishers, subscribers, service endpoints, or action clients.

## List topics and topic info

Without a ROS 2 install you can list topics and get topic info via the **`zenoh-ros2`** CLI:

```bash
zenoh-ros2 topic list -t              # list topics with types
zenoh-ros2 topic info -v /chatter      # verbose info for a topic
```

For fast topic list/info, start the daemon once: `zenoh-ros2 daemon start`; then `zenoh-ros2 topic list` returns quickly. See `DISCOVERY_CLOSE_DELAY.md` for why. Use `--no-daemon` to always run discovery in-process.

Or from Python:

```python
from zenoh_ros2_sdk import get_topic_names_and_types, get_topic_info

for name, types in get_topic_names_and_types():
    print(name, types)

info = get_topic_info("/chatter", verbose=True)
if info:
    print("Publishers:", info.publisher_count, "Subscribers:", info.subscriber_count)
```

See `TOPIC_LIST_AND_INFO.md` and `examples.md` for more examples.

## Publish a topic

```python
from zenoh_ros2_sdk import ROS2Publisher

pub = ROS2Publisher(
    topic="/chatter",
    msg_type="std_msgs/msg/String"
)
pub.publish(data="Hello World!")
pub.close()
```

## Subscribe to a topic

```python
from zenoh_ros2_sdk import ROS2Subscriber

def on_message(msg):
    print(f"Received: {msg.data}")

sub = ROS2Subscriber(
    topic="/chatter",
    msg_type="std_msgs/msg/String",
    callback=on_message
)
```

## Service server

```python
from zenoh_ros2_sdk import ROS2ServiceServer, get_message_class

def handler(request):
    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
    return Response(sum=request.a + request.b)

server = ROS2ServiceServer(
    service_name="/add_two_ints",
    srv_type="example_interfaces/srv/AddTwoInts",
    callback=handler
)
```

## Service client

```python
from zenoh_ros2_sdk import ROS2ServiceClient

client = ROS2ServiceClient(
    service_name="/add_two_ints",
    srv_type="example_interfaces/srv/AddTwoInts"
)

resp = client.call(a=5, b=3)
if resp:
    print(resp.sum)
client.close()
```

## Action client

`ROS2ActionClient` connects to an existing ROS 2 action server. Action server
support is not implemented in the SDK yet.

Start a ROS 2 action server, for example:

```bash
ros2 run action_tutorials_py fibonacci_action_server
```

Then send a goal from Python:

```python
from zenoh_ros2_sdk import ROS2ActionClient

client = ROS2ActionClient(
    action_name="/fibonacci",
    action_type="example_interfaces/action/Fibonacci"
)

result = client.send_goal(
    order=5,
    feedback_callback=lambda msg: print(msg.feedback.sequence),
    result_timeout=30.0,
)

if result:
    print(result.result.sequence)
client.close()
```

## Next steps

- For runnable scripts (including discovery, compressed image subscription, and action clients), see `examples.md`.
- For topic list / topic info (CLI and API), see `TOPIC_LIST_AND_INFO.md`.
- For how discovery/QoS/key-expressions work, see `concepts.md`.
