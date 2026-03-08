"""
CLI for ros2 service list / type-style discovery over Zenoh.

Used as the "service" subcommand of zenoh-ros2:
  zenoh-ros2 service list [-t] [--domain-id N] [--router IP:PORT]
  zenoh-ros2 service type SERVICE [--domain-id N] [--router IP:PORT]
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
    services = strategy.get_service_names_and_types(
        timeout=args.timeout,
        include_hidden_services=args.include_hidden_services,
    )
    if args.count_services:
        print(len(services))
        return 0
    if not services:
        return 0
    for name, types in services:
        msg = name
        if args.show_types and types:
            msg += " [" + ", ".join(types) + "]"
        print(msg)
    return 0


def cmd_type(args: argparse.Namespace) -> int:
    if not args.service_name:
        print("service_cli type: error: service name required", file=sys.stderr)
        return 1
    no_daemon = getattr(args, "no_daemon", False)
    strategy = NodeStrategy(
        router=args.router,
        domain_id=args.domain_id,
        no_daemon=no_daemon,
    )
    info = strategy.get_service_info(
        args.service_name,
        timeout=args.timeout,
        verbose=False,
    )
    if info is None:
        print(f"Unknown service '{args.service_name}'", file=sys.stderr)
        return 1
    types = info.get("service_types") or []
    # Match ros2 service type: print one type per line.
    for t in types:
        print(t)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="zenoh_ros2_sdk.service_cli",
        description="ros2 service list / type over Zenoh (liveliness-based discovery).",
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
    plist = sub.add_parser("list", help="List services (ros2 service list)")
    plist.add_argument("-t", "--show-types", action="store_true", help="Show service types")
    plist.add_argument("-c", "--count-services", action="store_true", help="Only print number of services")
    plist.add_argument(
        "--include-hidden-services",
        action="store_true",
        help="Include hidden services (default: exclude)",
    )
    plist.set_defaults(func=cmd_list)

    # type
    ptype = sub.add_parser("type", help="Service type (ros2 service type)")
    ptype.add_argument("service_name", nargs="?", help="Service name (e.g. /add_two_ints)")
    ptype.set_defaults(func=cmd_type)

    args = parser.parse_args()
    if args.domain_id is None:
        args.domain_id = resolve_domain_id(None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

