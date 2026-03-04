# Examples

The repo contains runnable scripts in `examples/` (numbered in recommended learning order).

Start a router in a ROS2 environment:

```bash
ros2 run rmw_zenoh_cpp rmw_zenohd
```

Run an example:

```bash
python3 examples/01_publish_string.py
python3 examples/02_subscribe_string.py
```

For the full list (including services, queue-mode services, and compressed image subscription), see `examples/README.md`.

---

## Topic list and topic info (discovery)

You can list topics and get topic info **without a ROS 2 install** using the **`zenoh-ros2`** CLI or the Python API.

### CLI

After `pip install zenoh-ros2-sdk`, the `zenoh-ros2` command is available:

```bash
zenoh-ros2 topic list                    # topic names only
zenoh-ros2 topic list -t                 # with types
zenoh-ros2 topic list -v                 # verbose (published / subscribed sections)
zenoh-ros2 topic list -c                 # count only
zenoh-ros2 topic info /chatter           # info for one topic
zenoh-ros2 topic info -v /chatter        # verbose (publisher/subscriber details)
zenoh-ros2 --router 127.0.0.1:7447 topic list -t
zenoh-ros2 --domain-id 1 --timeout 5 topic info -v /my_topic
zenoh-ros2 daemon start
zenoh-ros2 --no-daemon topic list
```

### Python API

```python
from zenoh_ros2_sdk import get_topic_names_and_types, get_topic_info

# List all topics (and types)
for name, types in get_topic_names_and_types():
    print(name, types)

# Info for one topic
info = get_topic_info("/chatter", verbose=True)
if info:
    print("Type:", info.topic_types)
    print("Publishers:", info.publisher_count, "Subscribers:", info.subscriber_count)
    for p in info.publishers:
        print("  Publisher:", p.node_name, p.node_namespace, p.topic_type)
```

### Runnable discovery example

```bash
python3 examples/19_discovery_topic_list.py
```

Optional: pass a topic name to show info for that topic only:

```bash
python3 examples/19_discovery_topic_list.py /chatter
```

See **`docs/TOPIC_LIST_AND_INFO.md`** for full API and CLI options.
