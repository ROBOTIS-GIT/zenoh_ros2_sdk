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

from zenoh_ros2_sdk import get_topic_names_and_types, get_topic_info


def main():
    topic_filter = sys.argv[1] if len(sys.argv) > 1 else None

    print("19 - Discovery: topic list and topic info\n")
    print("Topics (with types):")
    topics = get_topic_names_and_types()
    if not topics:
        print("  (none discovered; ensure Zenoh router is running and publishers/subscribers exist)")
        return

    for name, types in topics:
        types_str = ", ".join(types)
        print(f"  {name}  [{types_str}]")

    # Show info for one topic
    if topic_filter:
        topic_name = topic_filter if topic_filter.startswith("/") else "/" + topic_filter
        show_info(topic_name)
    else:
        # Show info for first topic
        first_name = topics[0][0]
        print(f"\nTopic info for '{first_name}' (use: python3 examples/19_discovery_topic_list.py <topic>):")
        show_info(first_name)


def show_info(topic_name: str) -> None:
    info = get_topic_info(topic_name, verbose=True)
    if not info:
        print(f"  Unknown topic '{topic_name}'")
        return
    print(f"  Type: {info.topic_types[0] if len(info.topic_types) == 1 else info.topic_types}")
    print(f"  Publisher count: {info.publisher_count}")
    for p in info.publishers:
        print(f"    - node: {p.node_namespace}/{p.node_name}  type: {p.topic_type}  qos: {p.qos}")
    print(f"  Subscription count: {info.subscriber_count}")
    for s in info.subscribers:
        print(f"    - node: {s.node_namespace}/{s.node_name}  type: {s.topic_type}  qos: {s.qos}")


if __name__ == "__main__":
    main()
