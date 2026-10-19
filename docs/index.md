# zenoh-ros2-sdk

**Python SDK for ROS 2 communication via Zenoh — use ROS 2 without a ROS 2 environment.**

This SDK lets pure-Python apps publish/subscribe to ROS 2 topics, offer/call ROS 2 services, and use ROS 2 action servers over Zenoh in a way that is compatible with `rmw_zenoh` discovery.

## Quick start

Install:

```bash
pip install zenoh-ros2-sdk
```

Publish:

```python
from zenoh_ros2_sdk import ROS2Publisher

pub = ROS2Publisher(topic="/chatter", msg_type="std_msgs/msg/String")
pub.publish(data="Hello from zenoh-ros2-sdk")
pub.close()
```

Subscribe:

```python
from zenoh_ros2_sdk import ROS2Subscriber

def on_msg(msg):
    print(msg.data)

sub = ROS2Subscriber(
    topic="/chatter",
    msg_type="std_msgs/msg/String",
    callback=on_msg
)
```

## Where to go next

- **Getting Started**: installation, running a router, pub/sub, services, and action clients (`getting-started.md`)
- **Topic list / topic info**: `zenoh-ros2` CLI and discovery API (`TOPIC_LIST_AND_INFO.md`)
- **Concepts**: domain IDs, discovery tokens, key expressions, QoS (`concepts.md`)
- **Examples**: runnable scripts you can copy/paste (`examples.md`)
- **API Reference**: full API from docstrings (`api/index.md`)
