#!/usr/bin/env python3
"""
Test that zenoh_ros2_sdk discovers topics published by ROS 2 nodes (rmw_zenoh) in Docker.

Usage:
  1. Start the ROS 2 + Zenoh container (see docker/README.md):
       docker run -d --name ros2-zenoh -p 7447:7447 <image>   # or docker compose up -d
  2. Wait a few seconds for the talker to register.
  3. Run this script (with zenoh_ros2_sdk installed):
       python scripts/test_sdk_discovery.py
       python scripts/test_sdk_discovery.py --router 127.0.0.1:7447

Exits 0 if /chatter is discovered with at least one publisher; non-zero otherwise.
"""

from __future__ import annotations

import argparse
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Test SDK discovery against ROS 2 Zenoh container")
    parser.add_argument(
        "--router",
        default="127.0.0.1:7447",
        help="Zenoh router endpoint (default: 127.0.0.1:7447)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Discovery timeout per attempt (default: 5.0)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=6,
        help="Number of attempts with 2s delay (default: 6)",
    )
    parser.add_argument(
        "--domain-id",
        type=int,
        default=0,
        help="ROS domain ID (default: 0)",
    )
    args = parser.parse_args()

    if ":" in args.router:
        host, port_str = args.router.rsplit(":", 1)
        port = int(port_str)
    else:
        host = args.router
        port = 7447

    try:
        from zenoh_ros2_sdk import get_topic_names_and_types, get_topic_info
    except ImportError as e:
        print("Error: zenoh_ros2_sdk not installed.", file=sys.stderr)
        print("Install with: pip install -e .", file=sys.stderr)
        return 1

    last_error = None
    for attempt in range(args.retries):
        try:
            topics = get_topic_names_and_types(
                domain_id=args.domain_id,
                router_ip=host,
                router_port=port,
                timeout=args.timeout,
                include_hidden_topics=True,
            )
            topic_names = [t[0] for t in topics]
            if "/chatter" not in topic_names:
                last_error = f"/chatter not in topic list: {topic_names}"
                if attempt < args.retries - 1:
                    time.sleep(2)
                    continue
                print("FAIL:", last_error, file=sys.stderr)
                return 1

            # Check types
            types_for_chatter = next((t[1] for t in topics if t[0] == "/chatter"), [])
            if not types_for_chatter:
                last_error = "/chatter has no types"
                print("FAIL:", last_error, file=sys.stderr)
                return 1
            if "std_msgs/msg/String" not in types_for_chatter:
                print("WARN: /chatter types:", types_for_chatter, "(expected std_msgs/msg/String)", file=sys.stderr)

            # Topic info and publisher count
            info = get_topic_info(
                "/chatter",
                domain_id=args.domain_id,
                router_ip=host,
                router_port=port,
                timeout=args.timeout,
                verbose=True,
            )
            if info is None:
                last_error = "get_topic_info('/chatter') returned None"
                print("FAIL:", last_error, file=sys.stderr)
                return 1
            if info.publisher_count < 1:
                last_error = f"expected at least 1 publisher, got {info.publisher_count}"
                print("FAIL:", last_error, file=sys.stderr)
                return 1

            print("OK: zenoh_ros2_sdk discovered /chatter")
            print(f"  Topics: {topic_names}")
            print(f"  /chatter types: {info.topic_types}")
            print(f"  Publisher count: {info.publisher_count}, Subscriber count: {info.subscriber_count}")
            if info.publishers:
                p = info.publishers[0]
                print(f"  First publisher: node={p.node_name}, namespace={p.node_namespace}, type={p.topic_type}")
            return 0
        except Exception as e:
            last_error = e
            if attempt < args.retries - 1:
                time.sleep(2)
                continue
            print("FAIL:", last_error, file=sys.stderr)
            raise
    assert last_error is not None
    print("FAIL:", last_error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
