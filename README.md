# zenoh-ros2-sdk

**Python SDK for ROS 2 communication via Zenoh - Use ROS 2 without ROS 2 environment**

Enable ROS 2 topic publishing and subscribing in pure Python applications. Publishers and subscribers automatically appear in `ros2 topic list` and work seamlessly with existing ROS 2 nodes using rmw_zenoh.

## Documentation

- **Docs (GitHub Pages)**: [robotis-git.github.io/zenoh_ros2_sdk](https://robotis-git.github.io/zenoh_ros2_sdk/)
- **API Reference (in this repo)**: [`docs/api/`](docs/api/)

## Features

- ✅ **No ROS 2 installation required** - Works with just Python and Zenoh
- ✅ **Appears in `ros2 topic list`** - Uses liveliness tokens for ROS 2 discovery
- ✅ **Automatic resource management** - GIDs, node IDs, entity IDs handled automatically
- ✅ **Session pooling** - Multiple publishers/subscribers share the same Zenoh session
- ✅ **Automatic message/service loading** - Automatically downloads message and service definitions from Git repositories
- ✅ **Type hash computation** - Computes ROS2-compatible type hashes from message/service definitions
- ✅ **Type registration** - Automatic message and service type registration
- ✅ **Service support** - Create service clients and servers with automatic type loading
- ✅ **Clean API** - Simple, intuitive interface

## Quick Start

### Install

```bash
pip install zenoh-ros2-sdk
```

### Simple Publisher

```python
from zenoh_ros2_sdk import ROS2Publisher

# Message type loading is automatic (no need to call load_message_type)
# Create publisher - msg_definition is optional, auto-loads from registry
pub = ROS2Publisher(
    topic="/chatter",
    msg_type="std_msgs/msg/String",
    domain_id=30
)

# Publish messages
pub.publish(data="Hello World!")
pub.publish(data="Another message")

pub.close()
```

### Simple Subscriber

```python
from zenoh_ros2_sdk import ROS2Subscriber

# Message type loading is automatic (no need to call load_message_type)
def on_message(msg):
    print(f"Received: {msg.data}")

# Create subscriber - msg_definition is optional, auto-loads from registry
sub = ROS2Subscriber(
    topic="/chatter",
    msg_type="std_msgs/msg/String",
    callback=on_message,
    domain_id=30
)

# Keep running
import time
time.sleep(10)

sub.close()
```

### Simple Service Server

```python
from zenoh_ros2_sdk import ROS2ServiceServer, get_message_class

# Service type loading is automatic (no need to call load_service_type)
def service_handler(request):
    # Get response message class
    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
    # Process request and return response
    return Response(sum=request.a + request.b)

# Create service server
server = ROS2ServiceServer(
    service_name="/add_two_ints",
    srv_type="example_interfaces/srv/AddTwoInts",
    callback=service_handler,
    domain_id=30
)

# Keep running
import time
time.sleep(10)

server.close()
```

### Simple Service Client

```python
from zenoh_ros2_sdk import ROS2ServiceClient

# Service type loading is automatic (no need to call load_service_type)
# Create service client
client = ROS2ServiceClient(
    service_name="/add_two_ints",
    srv_type="example_interfaces/srv/AddTwoInts",
    domain_id=30
)

# Make synchronous service call
response = client.call(a=5, b=3)
if response:
    print(f"Sum: {response.sum}")

# Make asynchronous service call
def callback(response):
    if response:
        print(f"Sum: {response.sum}")

client.call_async(callback, a=10, b=20)

client.close()
```

## Architecture

### Key Components

1. **ZenohSession** (Singleton)
   - Manages shared Zenoh session
   - Handles type registration
   - Generates unique GIDs
   - Manages node/entity ID counters

2. **ROS2Publisher**
   - Creates publisher with liveliness tokens
   - Handles attachments (sequence, timestamp, GID)
   - Appears in `ros2 topic list`

3. **ROS2Subscriber**
   - Subscribes to topics
   - Deserializes CDR messages
   - Calls user callback

4. **ROS2ServiceClient**
   - Creates service client with liveliness tokens
   - Sends requests using Zenoh queries
   - Receives responses asynchronously
   - Supports both synchronous and asynchronous calls

5. **ROS2ServiceServer**
   - Creates service server with liveliness tokens
   - Receives requests via Zenoh queryable
   - Calls user callback with request
   - Sends response back to client

### Resource Management

- **GID Generation**: Uses UUID4 to generate unique 16-byte GIDs
- **Node IDs**: Auto-incremented per node
- **Entity IDs**: Auto-incremented per publisher/subscriber
- **Session Reuse**: All publishers/subscribers share the same Zenoh session

## Examples

See the [`examples/`](examples/) folder (and [`examples/README.md`](examples/README.md)) for self-contained example scripts (numbered in recommended learning order):

- [`01_publish_string.py`](examples/01_publish_string.py) - Basic publisher example with String messages
- [`02_subscribe_string.py`](examples/02_subscribe_string.py) - Basic subscriber example with String messages
- [`03_publish_twist.py`](examples/03_publish_twist.py) - Publishing Twist messages (nested types)
- [`04_subscribe_twist.py`](examples/04_subscribe_twist.py) - Subscribing to Twist messages (nested types)
- [`05_publish_joint_state.py`](examples/05_publish_joint_state.py) - Publishing JointState messages (arrays and nested types)
- [`06_subscribe_joint_state.py`](examples/06_subscribe_joint_state.py) - Subscribing to JointState messages (arrays and nested types)
- [`07_service_server.py`](examples/07_service_server.py) - Service server example (AddTwoInts service)
- [`08_service_client.py`](examples/08_service_client.py) - Service client example (synchronous and asynchronous calls)
- [`09_subscribe_compressed_image.py`](examples/09_subscribe_compressed_image.py) - Subscribe to CompressedImage messages (camera stream example; ZED topic by default)
- [`10_service_server_queue.py`](examples/10_service_server_queue.py) - Service server example (queue mode; ros-z style: `take_request()` / `send_response()`)

Each example is self-contained and uses automatic message/service type loading. You can copy and modify them for your use cases.

## Advanced Usage

### Using Message Registry (Recommended)

The SDK automatically downloads message definitions from Git repositories. Message types are loaded automatically when creating publishers/subscribers:

```python
from zenoh_ros2_sdk import ROS2Publisher, get_message_class

# Message type loading is automatic - no need to call load_message_type
# Get message classes for easy object creation
Vector3 = get_message_class("geometry_msgs/msg/Vector3")
Twist = get_message_class("geometry_msgs/msg/Twist")

# Create publisher - message type is automatically loaded
pub = ROS2Publisher(
    topic="/cmd_vel",
    msg_type="geometry_msgs/msg/Twist",
    domain_id=30
)

# Create message objects
linear = Vector3(x=0.5, y=0.0, z=0.0)
angular = Vector3(x=0.0, y=0.0, z=0.2)
pub.publish(linear=linear, angular=angular)

pub.close()
```

### Manual Message Definitions

You can still provide message definitions manually if needed:

```python
from zenoh_ros2_sdk import ROS2Publisher

pub = ROS2Publisher(
    topic="/counter",
    msg_type="std_msgs/msg/Int32",
    msg_definition="int32 data\n",
    domain_id=30
)

pub.publish(data=42)
pub.close()
```

## Configuration

### Parameters

- `domain_id`: ROS domain ID (default: 0)
- `router_ip`: Zenoh router IP address
- `router_port`: Zenoh router port
- `node_name`: Custom node name (auto-generated if not provided)
- `namespace`: Node namespace (default: "/")

### Zenoh configuration override (advanced)

You can override the Zenoh session configuration using the `ZENOH_CONFIG_OVERRIDE`
environment variable (a semicolon-separated list of `path=value` entries). This is
useful for enabling features like shared memory transport or forcing client mode:

```bash
export ZENOH_CONFIG_OVERRIDE='transport/shared_memory/enabled=true;mode="client";connect/endpoints=["tcp/192.168.6.2:7447"]'
```

Notes:
- Values are parsed as **JSON5**. If the value is a string, it must be quoted (e.g., `mode="client"`).

## Requirements

- Python 3.8+
- `eclipse-zenoh` Python package (>=0.10.0)
- `rosbags` Python package (>=0.11.0, for message serialization)
- `GitPython` Python package (>=3.1.18, for automatic message downloading from git repositories)
- `tqdm` Python package (>=4.64.0, for download progress indicators)

### Optional Dependencies

For development and testing:
```bash
# From PyPI:
pip install "zenoh-ros2-sdk[dev]"

# From source:
pip install -e ".[dev]"
```

## Installation

### From PyPI

```bash
pip install zenoh-ros2-sdk
```

### From source

```bash
git clone https://github.com/robotis-git/zenoh_ros2_sdk.git
cd zenoh_ros2_sdk
pip install -e .
```

### Install dependencies separately

If installing from source, you can install dependencies separately:
```bash
pip install eclipse-zenoh>=0.10.0 rosbags>=0.11.0 GitPython>=3.1.18 tqdm>=4.64.0
```

## Running Examples

```bash
# Publish String messages
python3 examples/01_publish_string.py

# Subscribe to String messages
python3 examples/02_subscribe_string.py

# Publish Twist messages
python3 examples/03_publish_twist.py

# Subscribe to Twist messages
python3 examples/04_subscribe_twist.py

# Publish JointState messages
python3 examples/05_publish_joint_state.py

# Subscribe to JointState messages
python3 examples/06_subscribe_joint_state.py

# Run service server
python3 examples/07_service_server.py

# Run service client (in another terminal)
python3 examples/08_service_client.py

# Subscribe to CompressedImage (edit topic/router_ip in the script if needed)
python3 examples/09_subscribe_compressed_image.py

# Service server (queue mode)
python3 examples/10_service_server_queue.py
```

## Design Decisions

1. **Singleton Session**: All publishers/subscribers share one Zenoh session for efficiency
2. **Auto GID Generation**: Uses UUID4 for unique GIDs per publisher
3. **Liveliness Tokens**: Automatically declared so publishers appear in `ros2 topic list`
4. **Type Hash Computation**: Automatically computes ROS2-compatible type hashes from message definitions using the same algorithm as ROS2
5. **Message Registry**: Automatically downloads message definitions from Git repositories and caches them locally
6. **Clean API**: Abstracts away Zenoh/rmw_zenoh complexity

## Future Improvements

- [ ] Support for more message types out of the box
- [ ] Action support
- [ ] Better error handling and retry logic
- [ ] Connection pooling and reconnection
- [ ] QoS configuration options
