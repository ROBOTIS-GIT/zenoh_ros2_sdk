# zenoh-ros2-sdk

**Python SDK for ROS 2 communication via Zenoh - Use ROS 2 without ROS 2 environment

Enable ROS 2 topic publishing and subscribing in pure Python applications. Publishers and subscribers automatically appear in `ros2 topic list` and work seamlessly with existing ROS 2 nodes using rmw_zenoh.

## Features

- ✅ **No ROS 2 installation required** - Works with just Python and Zenoh
- ✅ **Appears in `ros2 topic list`** - Uses liveliness tokens for ROS 2 discovery
- ✅ **Automatic resource management** - GIDs, node IDs, entity IDs handled automatically
- ✅ **Session pooling** - Multiple publishers/subscribers share the same Zenoh session
- ✅ **Type registration** - Automatic message type registration
- ✅ **Clean API** - Simple, intuitive interface

## Quick Start

### Simple Publisher

```python
from zenoh_ros2_sdk import ROS2Publisher

pub = ROS2Publisher(
    topic="/chatter",
    msg_type="std_msgs/msg/String",
    msg_definition="string data\n",
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

def on_message(msg):
    print(f"Received: {msg.data}")

sub = ROS2Subscriber(
    topic="/chatter",
    msg_type="std_msgs/msg/String",
    msg_definition="string data\n",
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

See the `examples/` directory for self-contained example scripts:

- `simple_publisher.py` - Basic publisher example
- `simple_subscriber.py` - Basic subscriber example  
- `custom_message_type.py` - Using custom message types
- `multiple_publishers.py` - Multiple publishers sharing a session

Each example is self-contained and includes helper functions. You can copy and modify them for your use cases.

## Advanced Usage

### Custom Message Types

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

### Multiple Publishers

```python
pub1 = create_string_publisher("/topic1", domain_id=30)
pub2 = create_string_publisher("/topic2", domain_id=30)

# Both share the same Zenoh session automatically
pub1.publish(data="Message 1")
pub2.publish(data="Message 2")

pub1.close()
pub2.close()
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
# Simple publisher
python3 examples/simple_publisher.py

# Simple subscriber
python3 examples/simple_subscriber.py

# Custom message type
python3 examples/custom_message_type.py

# Multiple publishers
python3 examples/multiple_publishers.py
```

## Design Decisions

1. **Singleton Session**: All publishers/subscribers share one Zenoh session for efficiency
2. **Auto GID Generation**: Uses UUID4 for unique GIDs per publisher
3. **Liveliness Tokens**: Automatically declared so publishers appear in `ros2 topic list`
4. **Type Hash Lookup**: Common types have pre-computed hashes; custom types need to be provided
5. **Clean API**: Abstracts away Zenoh/rmw_zenoh complexity

## Future Improvements

- [ ] Automatic type hash computation
- [ ] Support for more message types out of the box
- [ ] Service client/server support
- [ ] Action support
- [ ] Better error handling and retry logic
- [ ] Connection pooling and reconnection
- [ ] QoS configuration options
