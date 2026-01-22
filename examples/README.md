# Examples

This directory contains self-contained example scripts demonstrating different use cases of the zenoh-ros2-sdk.

Examples are numbered in a recommended learning order, starting with simple cases and progressing to more complex message types.

## Available Examples

### [`01_publish_string.py`](01_publish_string.py)
Publishes String messages to a ROS2 topic. Demonstrates the basic publisher pattern with automatic message type loading.

**Usage:**
```bash
python3 examples/01_publish_string.py
```

### [`02_subscribe_string.py`](02_subscribe_string.py)
Subscribes to a ROS2 topic and receives String messages. Demonstrates the basic subscriber pattern with automatic message type loading.

**Usage:**
```bash
python3 examples/02_subscribe_string.py
```

### [`03_publish_twist.py`](03_publish_twist.py)
Demonstrates how to publish `geometry_msgs/msg/Twist` messages, commonly used for velocity commands in robotics. Shows how to work with nested message types (Vector3).

**Usage:**
```bash
python3 examples/03_publish_twist.py
```

### [`04_subscribe_twist.py`](04_subscribe_twist.py)
Demonstrates how to subscribe to `geometry_msgs/msg/Twist` messages and access nested message fields.

**Usage:**
```bash
python3 examples/04_subscribe_twist.py
```

### [`05_publish_joint_state.py`](05_publish_joint_state.py)
Demonstrates how to publish `sensor_msgs/msg/JointState` messages, commonly used to report robot joint states (position, velocity, effort). Shows how to work with nested message types (Header, Time) and array fields.

**Usage:**
```bash
python3 examples/05_publish_joint_state.py
```

### [`06_subscribe_joint_state.py`](06_subscribe_joint_state.py)
Demonstrates how to subscribe to `sensor_msgs/msg/JointState` messages and access joint state information including joint names, positions, velocities, and efforts.

**Usage:**
```bash
python3 examples/06_subscribe_joint_state.py
```

### [`07_service_server.py`](07_service_server.py)
Demonstrates how to create a ROS2 service server using zenoh_ros2_sdk. This example creates an AddTwoInts service server that adds two integers. Shows automatic service type loading.

**Usage:**
```bash
python3 examples/07_service_server.py
```

### [`08_service_client.py`](08_service_client.py)
Demonstrates how to create a ROS2 service client using zenoh_ros2_sdk. This example creates an AddTwoInts service client and makes both synchronous and asynchronous service calls. Shows automatic service type loading.

**Usage:**
```bash
python3 examples/08_service_client.py
```

### [`09_subscribe_compressed_image.py`](09_subscribe_compressed_image.py)
Demonstrates how to subscribe to `sensor_msgs/msg/CompressedImage` messages (camera stream example; ZED topic by default).

**Usage:**
```bash
python3 examples/09_subscribe_compressed_image.py
```

Note: this example uses a ZED topic and a non-local `router_ip` by default. Edit the script to match your setup.

### [`10_service_server_queue.py`](10_service_server_queue.py)
Demonstrates a service server in queue mode (ros-z style): `take_request()` / `send_response()` with a correlation key.

**Usage:**
```bash
python3 examples/10_service_server_queue.py
```

### [`11_publish_joint_trajectory.py`](11_publish_joint_trajectory.py)
Demonstrates how to publish `trajectory_msgs/msg/JointTrajectory` messages, commonly used to command robot joint movements along a trajectory. Shows how to work with nested message types (Header, JointTrajectoryPoint, Duration) and arrays of trajectory points.

**Usage:**
```bash
python3 examples/11_publish_joint_trajectory.py
```

### [`12_subscribe_joint_trajectory.py`](12_subscribe_joint_trajectory.py)
Demonstrates how to subscribe to `trajectory_msgs/msg/JointTrajectory` messages and access trajectory information including joint names, positions, velocities, accelerations, efforts, and timing for each waypoint.

**Usage:**
```bash
python3 examples/12_subscribe_joint_trajectory.py
```

### [`13_subscribe_robot_description.py`](13_subscribe_robot_description.py)
Demonstrates how to subscribe to the `/robot_description` topic and receive the URDF XML string. Uses **TRANSIENT_LOCAL** durability QoS to receive cached messages that were published before the subscriber started (like `ros2 topic echo` does).

**Usage:**
```bash
python3 examples/13_subscribe_robot_description.py
```

### [`14_subscribe_diagnostics.py`](14_subscribe_diagnostics.py)
Demonstrates how to subscribe to `diagnostic_msgs/msg/DiagnosticArray` messages and access diagnostic information from system components, including status levels (OK, WARN, ERROR, STALE), component names, messages, hardware IDs, and key-value pairs.

**Usage:**
```bash
python3 examples/14_subscribe_diagnostics.py
```

## Running Examples

Make sure you have:
1. Zenoh router running in a ROS2 environment:
   ```bash
   ros2 run rmw_zenoh_cpp rmw_zenohd
   ```
2. Set `ROS_DOMAIN_ID` if your ROS 2 domain is not 0
3. Set the correct `router_ip` if not using localhost

Each example is self-contained and uses the message registry to automatically load message definitions. You can copy and modify these examples for your own use cases.

## Debugging Pub/Sub Discovery (rmw_zenoh compatibility)

This SDK matches `rmw_zenoh_cpp`/`ros-z` conventions by using:

- **Data-plane key expressions** (payload transport):
  - `<domain_id>/<fully_qualified_name>/<dds_type_name>/<type_hash>`
- **Discovery-plane liveliness tokens** (ROS graph / publish-on-subscribe):
  - `@ros2_lv/<domain_id>/<session_id>/<node_id>/<entity_id>/<kind>/.../<qos>`

Entity kinds:
- `NN`: node
- `MP`: message publisher
- `MS`: message subscriber
- `SS`: service server
- `SC`: service client

If ROS tools can see a topic but you receive no data, confirm there is an `MS` token for that topic. Some publishers (notably camera/image pipelines) only start producing data after they discover at least one subscriber.

## QoS (rmw_zenoh / ros-z format)

This SDK uses the same compact QoS encoding as `rmw_zenoh_cpp` / `ros-z` for liveliness tokens:

`<Reliability>:<Durability>:<HistoryKind,HistoryDepth>:<DeadlineSec,DeadlineNSec>:<LifespanSec,LifespanNSec>:<LivelinessKind,LivelinessSec,LivelinessNSec>`

Examples:

- Default (KeepLast depth 10, reliable, volatile): `::,10:,:,:,,"`

You can pass either:
- the **encoded string** via `qos="::,10:,:,:,,"`, or
- a `QosProfile` object from `zenoh_ros2_sdk.qos`.
