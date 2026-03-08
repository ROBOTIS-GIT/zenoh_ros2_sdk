#!/usr/bin/env python3
"""
19 - Discovery: topic list and topic info

Demonstrates the discovery API: list all topics (with types and counts) and
optionally show verbose info for a specific topic. Equivalent to:
  zenoh-ros2 topic list -t -v
  zenoh-ros2 topic info -v TOPIC

Usage:
  python3 examples/19_discovery_topic_list.py              # list all topics, then info for first topic
  python3 examples/19_discovery_topic_list.py /chatter    # list all, then info for /chatter only
"""
import sys

from zenoh_ros2_sdk.node.strategy import NodeStrategy


def main():
    topic_filter = sys.argv[1] if len(sys.argv) > 1 else None

    print("19 - Discovery: topic list and topic info\n")

    strategy = NodeStrategy()

    print("Topics (with types):")
    topics = strategy.get_topic_names_and_types()
    if not topics:
        print("  (none discovered; ensure Zenoh router is running and publishers/subscribers exist)")
        return

    for name, types in topics:
        types_str = ", ".join(types)
        print(f"  {name}  [{types_str}]")

    # Show info for topic(s)
    if topic_filter:
        topic_name = topic_filter if topic_filter.startswith("/") else "/" + topic_filter
        print(f"\nTopic info for '{topic_name}' (use: python3 examples/19_discovery_topic_list.py <topic>):")
        show_info(strategy, topic_name)
    else:
        for name, _ in topics:
            print(f"\nTopic info for '{name}' (use: python3 examples/19_discovery_topic_list.py <topic>):")
            show_info(strategy, name)


def show_info(strategy: NodeStrategy, topic_name: str) -> None:
    info = strategy.get_topic_info(topic_name, timeout=0.5, verbose=True)
    if not info:
        print(f"  Unknown topic '{topic_name}'")
        return
    topic_types = info["topic_types"]
    type_str = topic_types[0] if len(topic_types) == 1 else topic_types
    print(f"  Type: {type_str}")
    print(f"  Publisher count: {info['publisher_count']}")
    for p in info.get("publishers", []):
        print(
            f"    - node: {p['node_namespace']}/{p['node_name']}  "
            f"type: {p['topic_type']}  qos: {p['qos']}"
        )
    print(f"  Subscription count: {info['subscriber_count']}")
    for s in info.get("subscribers", []):
        print(
            f"    - node: {s['node_namespace']}/{s['node_name']}  "
            f"type: {s['topic_type']}  qos: {s['qos']}"
        )


if __name__ == "__main__":
    main()
