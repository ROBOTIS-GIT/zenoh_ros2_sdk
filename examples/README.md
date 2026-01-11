# Examples

This directory contains self-contained example scripts demonstrating different use cases of the zenoh-ros2-sdk.

Examples are numbered in a recommended learning order, starting with simple cases and progressing to more complex message types.

## Available Examples

### `01_publish_string.py`
Publishes String messages to a ROS2 topic. Demonstrates the basic publisher pattern with automatic message type loading.

**Usage:**
```bash
python3 examples/01_publish_string.py
```

### `02_subscribe_string.py`
Subscribes to a ROS2 topic and receives String messages. Demonstrates the basic subscriber pattern with automatic message type loading.

**Usage:**
```bash
python3 examples/02_subscribe_string.py
```

### `03_publish_twist.py`
Demonstrates how to publish `geometry_msgs/msg/Twist` messages, commonly used for velocity commands in robotics. Shows how to work with nested message types (Vector3).

**Usage:**
```bash
python3 examples/03_publish_twist.py
```

### `04_subscribe_twist.py`
Demonstrates how to subscribe to `geometry_msgs/msg/Twist` messages and access nested message fields.

**Usage:**
```bash
python3 examples/04_subscribe_twist.py
```

## Running Examples

Make sure you have:
1. Zenoh router (`zenohd`) running
2. Set the correct `domain_id` in the example (default is 30)
3. Set the correct `router_ip` if not using localhost

Each example is self-contained and uses the message registry to automatically load message definitions. You can copy and modify these examples for your own use cases.
