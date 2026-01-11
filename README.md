# zenoh-ros2-sdk

**Python SDK for ROS 2 communication via Zenoh - Use ROS 2 without ROS 2 environment**

Enable ROS 2 topic publishing and subscribing in pure Python applications. Publishers and subscribers automatically appear in `ros2 topic list` and work seamlessly with existing ROS 2 nodes using rmw_zenoh.

## Features

- ✅ **No ROS 2 installation required** - Works with just Python and Zenoh
- ✅ **Appears in `ros2 topic list`** - Uses liveliness tokens for ROS 2 discovery
- ✅ **Automatic resource management** - GIDs, node IDs, entity IDs handled automatically
- ✅ **Session pooling** - Multiple publishers/subscribers share the same Zenoh session
- ✅ **Automatic message loading** - Automatically downloads message definitions from Git repositories
- ✅ **Type hash computation** - Computes ROS2-compatible type hashes from message definitions
- ✅ **Type registration** - Automatic message type registration
- ✅ **Clean API** - Simple, intuitive interface

## Quick Start

### Simple Publisher

```python
from zenoh_ros2_sdk import ROS2Publisher, load_message_type

# Load message type (automatically downloads if needed)
load_message_type("std_msgs/msg/String")

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
from zenoh_ros2_sdk import ROS2Subscriber, load_message_type

# Load message type (automatically downloads if needed)
load_message_type("std_msgs/msg/String")

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

### Resource Management

- **GID Generation**: Uses UUID4 to generate unique 16-byte GIDs
- **Node IDs**: Auto-incremented per node
- **Entity IDs**: Auto-incremented per publisher/subscriber
- **Session Reuse**: All publishers/subscribers share the same Zenoh session

## Examples

See the `examples/` directory for self-contained example scripts (numbered in recommended learning order):

- `01_publish_string.py` - Basic publisher example with String messages
- `02_subscribe_string.py` - Basic subscriber example with String messages
- `03_publish_twist.py` - Publishing Twist messages (nested types)
- `04_subscribe_twist.py` - Subscribing to Twist messages (nested types)

Each example is self-contained and uses automatic message loading. You can copy and modify them for your use cases.

## Advanced Usage

### Using Message Registry (Recommended)

The SDK automatically downloads message definitions from Git repositories:

```python
from zenoh_ros2_sdk import ROS2Publisher, load_message_type, get_message_class

# Automatically loads message type and dependencies
load_message_type("geometry_msgs/msg/Twist")

# Get message classes for easy object creation
Vector3 = get_message_class("geometry_msgs/msg/Vector3")
Twist = get_message_class("geometry_msgs/msg/Twist")

# Create publisher - no need to provide msg_definition
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

## Requirements

- Python 3.8+
- `eclipse-zenoh` Python package (>=0.10.0)
- `rosbags` Python package (>=0.11.0, for message serialization)

### Optional Dependencies

For automatic message downloading from git repositories:
```bash
pip install zenoh-ros2-sdk[download]
# or
pip install GitPython>=3.1.18
```

## Installation

### From source

```bash
git clone https://github.com/robotis-git/zenoh_ros2_sdk.git
cd zenoh_ros2_sdk
pip install -e .
```

### Dependencies

```bash
pip install eclipse-zenoh rosbags
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
- [ ] Service client/server support
- [ ] Action support
- [ ] Better error handling and retry logic
- [ ] Connection pooling and reconnection
- [ ] QoS configuration options
