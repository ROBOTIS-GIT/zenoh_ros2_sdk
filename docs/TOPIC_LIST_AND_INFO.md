# ros2 topic list and ros2 topic info -v

This document describes the **zenoh-ros2-sdk** implementation of `ros2 topic list` / `ros2 topic info -v`-style **topic discovery**, and the matching `ros2 service list` / `ros2 service type`-style **service discovery**, without a ROS 2 environment.

## What this project is

**zenoh-ros2-sdk** is a **Python SDK for ROS 2 communication over Zenoh**. It lets you:

- Publish and subscribe to ROS 2 topics from **pure Python** (no ROS 2 install).
- Use ROS 2 services (client/server).
- **List topics and get topic info** via the `zenoh-ros2` CLI or the Python discovery API.
- Have your publishers/subscribers **discoverable** by standard ROS 2 tools (e.g. `ros2 topic list`) when those tools run with **rmw_zenoh** and the same Zenoh router.

The SDK talks to a Zenoh router (e.g. `rmw_zenohd`). Discovery uses **liveliness tokens** under the admin space `@ros2_lv/...`, following the same format as **rmw_zenoh_cpp** and **ros-z** (ZettaScale). So any endpoint that declares these tokens (this SDK, ros-z nodes, or ROS 2 nodes via rmw_zenoh) appears in the same “ROS graph” over Zenoh.

## Implemented behavior (topics)

### 1. ros2 topic list

- **API**: `get_topic_names_and_types(domain_id=None, router_ip="127.0.0.1", router_port=7447, timeout=0.5, include_hidden_topics=False)`
  - **Returns**: `List[Tuple[str, List[str]]]` — each item is `(topic_name, [type1, type2, ...])` with types in ROS 2 form (e.g. `std_msgs/msg/String`).
  - **Default** `timeout=0.5` matches ros2cli’s discovery spin time (`--spin-time`). **Default** `include_hidden_topics=False` matches ros2 topic list (hidden = names starting with `/_`).
- **CLI**: `zenoh-ros2 topic list`
  - **Options**: `-t` / `--show-types`, `-v` / `--verbose` (pub/sub counts in two sections), `-c` / `--count-topics`, `--include-hidden-topics`.
  - **Global options** (before `topic`): `--router`, `--domain-id`, `--timeout`, `--no-daemon`. If `--domain-id` is omitted, `ROS_DOMAIN_ID` from the environment is used (same as ros2cli).

Discovery is implemented by querying Zenoh liveliness for **MP** (publisher) and **MS** (subscriber) tokens in the given domain (pattern `@ros2_lv/<domain>/*/*/*/MP/**` and `.../MS/**`), then aggregating by topic name and type.

### 2. ros2 topic info / ros2 topic info -v

- **API**: `get_topic_info(topic_name, domain_id=None, router_ip=..., router_port=..., timeout=0.5, verbose=False)`
  - **Returns**: `TopicInfo | None` with:
    - `topic_name`, `topic_types`, `publisher_count`, `subscriber_count`
    - If `verbose=True`: `publishers` and `subscribers` as lists of `TopicEndpointInfo` (node name, namespace, topic type, type hash, QoS).
- **CLI**: `zenoh-ros2 topic info [-v] TOPIC`
  - **Global options**: `--router`, `--domain-id`, `--timeout`, `--no-daemon`.

Same liveliness queries are used; for a given topic we filter by normalized topic name and optionally collect per-endpoint details.

## Implemented behavior (services)

### 3. ros2 service list / ros2 service list -t

- **API**: `get_service_names_and_types(domain_id=None, router_ip=\"127.0.0.1\", router_port=7447, timeout=0.5, include_hidden_services=False)`
  - **Returns**: `List[Tuple[str, List[str]]]` — each item is `(service_name, [type1, type2, ...])` with types in ROS 2 form (e.g. `example_interfaces/srv/AddTwoInts`).
  - `timeout` and `domain_id` semantics match the topic discovery helpers.
- **CLI**: `zenoh-ros2 service list`
  - **Options**: `-t` / `--show-types`, `-c` / `--count-services`, `--include-hidden-services`.
  - **Global options** (before `service`): `--router`, `--domain-id`, `--timeout`, `--no-daemon`.

Service discovery is implemented by querying Zenoh liveliness for **SS** (service server) and **SC** (service client) tokens in the given domain and aggregating by service name and type.

### 4. ros2 service type

- **API**: `get_service_info(service_name, domain_id=None, router_ip=..., router_port=..., timeout=0.5, verbose=False)`
  - **Returns**: `ServiceInfo | None` with:
    - `service_name`, `service_types`, `server_count`, `client_count`
    - If `verbose=True`: `servers` and `clients` as lists of `ServiceEndpointInfo` (node name, namespace, service type, type hash, QoS).
- **CLI**: `zenoh-ros2 service type SERVICE`

As with topics, the SDK normalizes names to start with `/` and filters liveliness entries by qualified name. Verbose service info is primarily useful for debugging, while `service type` is focused on printing just the type string(s) like `ros2 service type`.

## Reference repos

- **ros2cli**: https://github.com/ros2/ros2cli — reference for `ros2 topic list` / `ros2 topic info` and `ros2 service list` / `ros2 service type` behavior and output format.
- **ros-z**: https://github.com/ZettaScaleLabs/ros-z — parent / reference for rmw_zenoh and liveliness conventions used by this SDK.

## Files

- `zenoh_ros2_sdk/utils.py`: `dds_to_ros_type()`, `demangle_name()`.
- `zenoh_ros2_sdk/discovery.py`: `get_topic_names_and_types()`, `get_topic_info()`, `TopicInfo`, `TopicEndpointInfo`, and liveliness parsing.
- `zenoh_ros2_sdk/daemon/`: HTTP daemon (port 11620 + ROS_DOMAIN_ID; avoids ros2 daemon 11511+domain_id), `zenoh-ros2 daemon start|stop|status`. When the daemon is running, topic list/info use it and return quickly.
- `zenoh_ros2_sdk/node/`: `NodeStrategy` (daemon vs direct), `DirectNode`.
- `zenoh_ros2_sdk/topic_cli.py`: topic list/info handlers (invoked via `zenoh-ros2 topic`).
- `zenoh_ros2_sdk/cli.py`: main `zenoh-ros2` entry point.
- `zenoh_ros2_sdk/__init__.py`: exports for discovery API.

---

## Examples

### CLI (zenoh-ros2)

With a Zenoh router and some publishers/subscribers running:

```bash
# List topic names only
zenoh-ros2 topic list

# List with types
zenoh-ros2 topic list -t

# Verbose: two sections (Published topics / Subscribed topics) with counts
zenoh-ros2 topic list -v

# Only print the number of topics
zenoh-ros2 topic list -c

# Include hidden topics (names starting with /_)
zenoh-ros2 topic list --include-hidden-topics

# Daemon: start for fast topic list/info; use --no-daemon to run discovery in-process
zenoh-ros2 daemon start
zenoh-ros2 daemon status
zenoh-ros2 topic list -t
zenoh-ros2 --no-daemon topic list

# Use a different router or domain (--domain-id overrides ROS_DOMAIN_ID)
zenoh-ros2 --router 192.168.1.10:7447 --domain-id 1 topic list -t
zenoh-ros2 --timeout 5.0 topic info -v /chatter
```

### Python API: list topics

```python
from zenoh_ros2_sdk import get_topic_names_and_types

# Default: exclude hidden topics, local router
for name, types in get_topic_names_and_types():
    print(name, types)

# With options
for name, types in get_topic_names_and_types(
    domain_id=0,
    router_ip="127.0.0.1",
    router_port=7447,
    timeout=3.0,
    include_hidden_topics=True,
):
    print(f"{name}  [{', '.join(types)}]")
```

### Python API: topic info (simple)

```python
from zenoh_ros2_sdk import get_topic_info

info = get_topic_info("/chatter")
if info:
    print("Type:", info.topic_types)
    print("Publisher count:", info.publisher_count)
    print("Subscription count:", info.subscriber_count)
else:
    print("Topic not found")
```

### Python API: topic info (verbose)

```python
from zenoh_ros2_sdk import get_topic_info

info = get_topic_info("/chatter", verbose=True)
if info:
    print("Type:", info.topic_types)
    print("Publisher count:", info.publisher_count)
    for p in info.publishers:
        print("  ", p.node_name, p.node_namespace, p.topic_type, p.qos)
    print("Subscription count:", info.subscriber_count)
    for s in info.subscribers:
        print("  ", s.node_name, s.node_namespace, s.topic_type, s.qos)
```

### Runnable example script

See **`examples/19_discovery_topic_list.py`** for a script that lists topics and prints info for a given topic (or the first one found). This example uses `NodeStrategy`, so when the `zenoh-ros2` daemon is running (or auto-spawned) discovery runs via the daemon and the script exits quickly without the 10-second Zenoh session close delay described in `docs/ZENOH_CLOSE_PANIC.md`.
