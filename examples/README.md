# Examples

This directory contains self-contained example scripts demonstrating different use cases of the zenoh-ros2-sdk.

## Available Examples

### `simple_publisher.py`
Publishes String messages to a ROS2 topic. Shows the basic publisher pattern.

**Usage:**
```bash
python3 examples/simple_publisher.py
```

### `simple_subscriber.py`
Subscribes to a ROS2 topic and receives String messages. Shows the basic subscriber pattern.

**Usage:**
```bash
python3 examples/simple_subscriber.py
```

### `custom_message_type.py`
Demonstrates how to use custom message types (Int32 in this example). Shows both publishing and subscribing to custom types.

**Usage:**
```bash
python3 examples/custom_message_type.py
```

### `multiple_publishers.py`
Shows how multiple publishers automatically share the same Zenoh session through the singleton pattern.

**Usage:**
```bash
python3 examples/multiple_publishers.py
```

## Running Examples

Make sure you have:
1. Zenoh router (`zenohd`) running
2. Set the correct `domain_id` in the example (default is 30)
3. Set the correct `router_ip` if not using localhost

Each example is self-contained and includes helper functions where needed. You can copy and modify these examples for your own use cases.
