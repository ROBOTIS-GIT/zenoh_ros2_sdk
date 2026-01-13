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

### `05_publish_joint_state.py`
Demonstrates how to publish `sensor_msgs/msg/JointState` messages, commonly used to report robot joint states (position, velocity, effort). Shows how to work with nested message types (Header, Time) and array fields.

**Usage:**
```bash
python3 examples/05_publish_joint_state.py
```

### `06_subscribe_joint_state.py`
Demonstrates how to subscribe to `sensor_msgs/msg/JointState` messages and access joint state information including joint names, positions, velocities, and efforts.

**Usage:**
```bash
python3 examples/06_subscribe_joint_state.py
```

### `07_service_server.py`
Demonstrates how to create a ROS2 service server using zenoh_ros2_sdk. This example creates an AddTwoInts service server that adds two integers. Shows automatic service type loading.

**Usage:**
```bash
python3 examples/07_service_server.py
```

### `08_service_client.py`
Demonstrates how to create a ROS2 service client using zenoh_ros2_sdk. This example creates an AddTwoInts service client and makes both synchronous and asynchronous service calls. Shows automatic service type loading.

**Usage:**
```bash
python3 examples/08_service_client.py
```

## Running Examples

Make sure you have:
1. Zenoh router (`zenohd`) running
2. Set the correct `domain_id` in the example (default is 30)
3. Set the correct `router_ip` if not using localhost

Each example is self-contained and uses the message registry to automatically load message definitions. You can copy and modify these examples for your own use cases.
