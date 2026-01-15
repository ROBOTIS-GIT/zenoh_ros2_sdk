# zenoh-ros2-sdk

**Python SDK for ROS 2 communication via Zenoh — use ROS 2 without a ROS 2 environment.**

This SDK lets pure-Python apps publish/subscribe to ROS 2 topics and offer/call ROS 2 services over Zenoh in a way that is compatible with `rmw_zenoh` discovery (topics/services show up in ROS tools).

## Quick start

Install:

```bash
pip install zenoh-ros2-sdk
```

Publish:

```python
from zenoh_ros2_sdk import ROS2Publisher

pub = ROS2Publisher(topic="/chatter", msg_type="std_msgs/msg/String", domain_id=30)
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
    callback=on_msg,
    domain_id=30,
)
```

## Where to go next

- **Getting Started**: installation, running a router, pub/sub and services (`getting-started.md`)
- **Concepts**: domain IDs, discovery tokens, key expressions, QoS (`concepts.md`)
- **Examples**: runnable scripts you can copy/paste (`examples.md`)
- **API Reference**: full API from docstrings (`api/index.md`)

