# ros2cli vs zenoh_ros2_sdk topic list / info — Logic comparison

This document compares the **exact logic** of `ros2 topic list` and `ros2 topic info` in **ros2cli** (deps/ros2cli) with the **zenoh_ros2_sdk** implementation. It notes what matches, what differs, and the discovery detail that was aligned with rmw_zenoh.

**SDK CLI:** Topic commands are under the `zenoh-ros2` command: `zenoh-ros2 topic list`, `zenoh-ros2 topic info [-v] TOPIC`. Global options `--router`, `--domain-id`, `--timeout`, `--no-daemon` apply to all subcommands. When `--domain-id` is omitted, `ROS_DOMAIN_ID` from the environment is used (same as ros2cli).

---

## 1. ros2 topic list

### ros2cli (source: `ros2topic/verb/list.py` + `ros2topic/api/__init__.py`)

| Step | ros2cli behavior |
|------|------------------|
| **Data source** | `node.get_topic_names_and_types()` (rclpy Node — uses DDS/liveliness under the hood). |
| **Hidden topics** | `get_topic_names_and_types(node, include_hidden_topics)`. If `include_hidden_topics` is False, list is filtered: `[(n,t) for (n,t) in ... if not topic_or_service_is_hidden(n)]`. Hidden = topic name indicates “hidden” (e.g. leading `_` in FQN). |
| **CLI flag** | `--include-hidden-topics` is `action='store_true'` → **default False**. By default hidden topics are **excluded**. |
| **-c / --count-topics** | Prints `len(topic_names_and_types)` only. |
| **-v / --verbose** | For each topic, gets `pub_count = node.count_publishers(topic_name)`, `sub_count = node.count_subscribers(topic_name)`. Then prints **two sections**: (1) “Published topics:” — for each topic line `* topic_name [types] N publisher(s)` **only if pub_count > 0**; (2) “Subscribed topics:” — same but “N subscriber(s)” **only if sub_count > 0**. |
| **Default (no -v, no -t)** | One line per topic: `topic_name` only. |
| **-t / --show-types** | Same lines but append ` [type1, type2, ...]`. |

### zenoh_ros2_sdk (discovery + `zenoh-ros2 topic list`)

| Aspect | Implementation | Match? |
|--------|----------------|--------|
| **Data source** | Zenoh liveliness: query `@ros2_lv/<domain>/*/*/*/MP/**` and `@ros2_lv/<domain>/*/*/*/MS/**` (see rmw_zenoh design.md; `**` required to match full keyexpr). Parse keyexprs, aggregate by topic name and type. | ✅ Equivalent (different transport, same graph semantics). |
| **Hidden topics** | If `include_hidden_topics` is False, skip names starting with `/_`. | ✅ Aligned with “hidden = leading _” for FQN. |
| **Default include_hidden_topics** | False (store_true flag). | ✅ Same. |
| **-c / --count-topics** | Prints `len(topic_list)`. | ✅ Same. |
| **-v / --verbose** | Two sections “Published topics:” / “Subscribed topics:”; show line only if the corresponding count > 0; format `* topic_name [types] N publisher(s)` / `N subscriber(s)`. | ✅ Same. |
| **Default list output** | One line per topic: `topic_name`. | ✅ Same. |
| **-t / --show-types** | Appends ` [type1, type2, ...]`. | ✅ Same. |

---

## 2. ros2 topic info [ -v ] &lt;topic&gt;

### ros2cli (source: `ros2topic/verb/info.py`)

| Step | ros2cli behavior |
|------|------------------|
| **Topic name** | Optional positional. If missing: interactive selection from `get_topic_names(node, include_hidden_topics)`. |
| **Lookup** | `get_topic_names_and_types(node, include_hidden_topics=True)`. Loop to find `t_name == topic_name` → `topic_types`. If not found: return error string `"Unknown topic '%s'" % topic_name`. |
| **Output order** | (1) `Type: <type_str>`, (2) `Publisher count: %d`, (3) if verbose: for each publisher info `print(info)`, (4) `Subscription count: %d`, (5) if verbose: for each subscriber info `print(info)`. |
| **Type line** | `type_str = topic_types[0] if len(topic_types)==1 else topic_types`. `line_end = '\n\n'` if verbose else `'\n'`. |
| **Verbose info** | rclpy `TopicEndpointInfo`: node_name, node_namespace, topic_type, endpoint_gid, qos_profile, topic_type_hash. Printed via `print(info)`. |

### zenoh_ros2_sdk (discovery + `zenoh-ros2 topic info`)

| Aspect | Implementation | Match? |
|--------|----------------|--------|
| **Topic name** | Required positional (no interactive selection). | ⚠️ Difference: we do not implement interactive selection when topic is omitted. |
| **Lookup** | `get_topic_info(topic_name, ...)` queries liveliness with same `/**` pattern, filters by normalized topic name, aggregates types and counts. Returns None if no publishers, subscribers, or types. | ✅ Same idea. |
| **Unknown topic** | CLI prints `"Unknown topic '%s'"` to stderr and exits 1. | ✅ Same message. |
| **Output order** | Type → Publisher count → (if verbose) publisher details → Subscription count → (if verbose) subscriber details. | ✅ Same. |
| **Type line** | `type_str = topic_types[0] if len==1 else topic_types`; `line_end = '\n\n'` if verbose else `'\n'`. | ✅ Same. |
| **Exact strings** | “Publisher count: %d”, “Subscription count: %d”. | ✅ Same. |
| **Verbose fields** | We print: Node name, Node namespace, Topic type, Type hash, QoS (string). We do **not** have endpoint GID (not in liveliness keyexpr). | ✅ Same semantics where data exists. ⚠️ GID not shown. |

---

## 3. API layer: get_topic_names_and_types

### ros2cli

- **Signature**: `get_topic_names_and_types(*, node, include_hidden_topics=False)`.
- **Returns**: `list of (topic_name, list of type strings)` from `node.get_topic_names_and_types()`, then filtered by `topic_or_service_is_hidden` when `include_hidden_topics` is False.

### zenoh_ros2_sdk

- **Signature**: `get_topic_names_and_types(domain_id=None, router_ip=..., router_port=..., timeout=0.5, include_hidden_topics=False)`.
- **Returns**: `list of (topic_name, sorted list of type strings)`, sorted by topic name. Types in ROS 2 form (e.g. `std_msgs/msg/String`).
- **Behavior**: Same contract; default `include_hidden_topics=False` to match ros2cli. Default **timeout=0.5** matches ros2cli’s `--spin-time` (DirectNode `DEFAULT_TIMEOUT`, see `ros2cli/node/direct.py`).

---

## 4. Liveliness pattern (rmw_zenoh alignment)

Discovery uses the same liveliness keyexpr format as **rmw_zenoh** (see the rmw_zenoh design documentation in the upstream repository):

- Endpoint tokens have **13 segments**, e.g.  
  `@ros2_lv/<domain>/<session_id>/<node_id>/<entity_id>/MP/<enclave>/<namespace>/<node_name>/<mangled_topic>/<type_name>/<type_hash>/<qos>`
- A pattern with a single trailing `*` matches only **one** segment, so it would not match the full key.
- The SDK uses **`@ros2_lv/<domain>/*/*/*/MP/**`** and **`@ros2_lv/<domain>/*/*/*/MS/**`** so that `**` matches the remaining segments and full keyexprs are returned for parsing.

---

## 5. Intentional / environmental differences

- **No interactive topic selection** in `zenoh-ros2 topic info`: topic name is required (ros2cli can prompt when omitted).
- **No endpoint GID in verbose**: discovery is from Zenoh liveliness keyexprs only; GID is not part of the token format, so we do not print it.
- **Discovery scope**: rclpy uses ROS 2 DDS/liveliness; we use Zenoh liveliness only. We only see endpoints that declare `@ros2_lv/...` (this SDK, rmw_zenoh, ros-z). Behavior is aligned for that subset.

With the above, the SDK’s `zenoh-ros2 topic list` and `zenoh-ros2 topic info` behavior matches ros2cli’s logic and output format as closely as Zenoh-based discovery allows.
