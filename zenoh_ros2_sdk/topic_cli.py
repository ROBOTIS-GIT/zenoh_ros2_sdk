"""
CLI for ros2 topic list and ros2 topic info -v (Zenoh liveliness-based).

Used as the "topic" subcommand of zenoh-ros2:
  zenoh-ros2 topic list [-t] [-v] [--domain-id N] [--router IP:PORT]
  zenoh-ros2 topic info [-v] TOPIC [--domain-id N] [--router IP:PORT]

Can also be run standalone: python -m zenoh_ros2_sdk.topic_cli list ...
"""

from __future__ import annotations

import argparse
import sys

from zenoh_ros2_sdk.node.strategy import NodeStrategy
from zenoh_ros2_sdk.utils import resolve_domain_id


def cmd_list(args: argparse.Namespace) -> int:
    no_daemon = getattr(args, "no_daemon", False)
    strategy = NodeStrategy(
        router=args.router,
        domain_id=args.domain_id,
        no_daemon=no_daemon,
    )
    topic_list = strategy.get_topic_names_and_types(
        timeout=args.timeout,
        include_hidden_topics=args.include_hidden_topics,
    )
    if args.count_topics:
        print(len(topic_list))
        return 0
    if not topic_list:
        return 0
    if args.verbose:
        topic_info = []
        for topic_name, topic_types in topic_list:
            info = strategy.get_topic_info(
                topic_name,
                timeout=args.timeout,
                verbose=True,
            )
            if info:
                topic_info.append((
                    topic_name,
                    info["topic_types"],
                    info["publisher_count"],
                    info["subscriber_count"],
                ))
        lines_pub = []
        lines_sub = []
        for (topic_name, topic_types, pub_count, sub_count) in topic_info:
            types_str = ", ".join(topic_types)
            if pub_count:
                count_str = str(pub_count) + " publisher" + ("s" if pub_count > 1 else "")
                lines_pub.append(f" * {topic_name} [{types_str}] {count_str}")
            if sub_count:
                count_str = str(sub_count) + " subscriber" + ("s" if sub_count > 1 else "")
                lines_sub.append(f" * {topic_name} [{types_str}] {count_str}")
        if lines_pub:
            print("Published topics:")
            for line in lines_pub:
                print(line)
        if lines_sub:
            print("Subscribed topics:")
            for line in lines_sub:
                print(line)
        return 0
    for topic_name, topic_types in topic_list:
        msg = topic_name
        if args.show_types:
            msg += " [" + ", ".join(topic_types) + "]"
        print(msg)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    if not args.topic_name:
        print("topic_cli info: error: topic name required", file=sys.stderr)
        return 1
    no_daemon = getattr(args, "no_daemon", False)
    strategy = NodeStrategy(
        router=args.router,
        domain_id=args.domain_id,
        no_daemon=no_daemon,
    )
    info = strategy.get_topic_info(
        args.topic_name,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    if info is None:
        print(f"Unknown topic '{args.topic_name}'", file=sys.stderr)
        return 1
    line_end = "\n\n" if args.verbose else "\n"
    topic_types = info["topic_types"]
    type_str = topic_types[0] if len(topic_types) == 1 else topic_types
    print("Type: %s" % type_str, end=line_end)
    print("Publisher count: %d" % info["publisher_count"], end=line_end)
    if args.verbose and info.get("publishers"):
        for p in info["publishers"]:
            print("  Node name: %s" % p["node_name"])
            print("  Node namespace: %s" % p["node_namespace"])
            print("  Topic type: %s" % p["topic_type"])
            print("  Type hash: %s" % p["type_hash"])
            print("  QoS: %s" % p["qos"])
            print()
    print("Subscription count: %d" % info["subscriber_count"], end=line_end)
    if args.verbose and info.get("subscribers"):
        for s in info["subscribers"]:
            print("  Node name: %s" % s["node_name"])
            print("  Node namespace: %s" % s["node_namespace"])
            print("  Topic type: %s" % s["topic_type"])
            print("  Type hash: %s" % s["type_hash"])
            print("  QoS: %s" % s["qos"])
            print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="zenoh_ros2_sdk.topic_cli",
        description="ros2 topic list / info over Zenoh (liveliness-based discovery).",
    )
    parser.add_argument(
        "--domain-id",
        type=int,
        default=None,
        help="ROS domain ID (default: ROS_DOMAIN_ID or 0)",
    )
    parser.add_argument(
        "--router",
        type=str,
        default="127.0.0.1:7447",
        help="Zenoh router endpoint (default: 127.0.0.1:7447)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Discovery timeout in seconds (default: 2.0)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    plist = sub.add_parser("list", help="List topics (ros2 topic list)")
    plist.add_argument("-t", "--show-types", action="store_true", help="Show topic types")
    plist.add_argument("-v", "--verbose", action="store_true", help="Show publisher/subscriber counts per topic")
    plist.add_argument("-c", "--count-topics", action="store_true", help="Only print number of topics")
    plist.add_argument("--include-hidden-topics", action="store_true", help="Include hidden topics (default: exclude)")
    plist.set_defaults(func=cmd_list)

    # info
    pinfo = sub.add_parser("info", help="Topic info (ros2 topic info)")
    pinfo.add_argument("topic_name", nargs="?", help="Topic name (e.g. /chatter)")
    pinfo.add_argument("-v", "--verbose", action="store_true", help="Print detailed publisher/subscriber info")
    pinfo.set_defaults(func=cmd_info)

    args = parser.parse_args()
    # Apply ROS_DOMAIN_ID when --domain-id not set (same as ros2cli)
    if args.domain_id is None:
        args.domain_id = resolve_domain_id(None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
