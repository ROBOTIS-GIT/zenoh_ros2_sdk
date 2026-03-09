"""
Main CLI entry point: zenoh-ros2 (topic, and later service, node, etc.).

Usage:
  zenoh-ros2 [--router R] [--domain-id D] [--timeout T] topic list [-t] [-v] ...
  zenoh-ros2 topic info [-v] TOPIC
  # Later: zenoh-ros2 service list, zenoh-ros2 node list, ...
"""

from __future__ import annotations

import argparse
import sys

from . import topic_cli, service_cli
from .daemon.client import is_daemon_running, shutdown_daemon
from .daemon.spawn import spawn_daemon
from .utils import resolve_domain_id


def _add_global_args(parser: argparse.ArgumentParser) -> None:
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
        default=0.5,
        help="Discovery timeout in seconds (default: 0.5, same as ros2 topic list)",
    )
    parser.add_argument(
        "--no-daemon",
        action="store_true",
        help="Do not use the background daemon; run discovery in-process (slower exit)",
    )


def _cmd_daemon_start(args: argparse.Namespace) -> int:
    if spawn_daemon(domain_id=args.domain_id):
        print("Daemon started.")
        return 0
    if is_daemon_running(args.domain_id):
        print("Daemon already running.")
        return 0
    print("Failed to start daemon.", file=sys.stderr)
    return 1


def _cmd_daemon_stop(args: argparse.Namespace) -> int:
    if not is_daemon_running(args.domain_id):
        print("Daemon is not running.")
        return 0
    shutdown_daemon(args.domain_id)
    print("Daemon shutdown requested.")
    return 0


def _cmd_daemon_status(args: argparse.Namespace) -> int:
    if is_daemon_running(args.domain_id):
        print("daemon is running")
        return 0
    print("daemon is not running")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="zenoh-ros2",
        description="ROS 2 over Zenoh CLI (topics, and later services, nodes, ...).",
    )
    _add_global_args(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    # daemon subcommand
    daemon_p = sub.add_parser("daemon", help="Background daemon (start, stop, status)")
    daemon_sub = daemon_p.add_subparsers(dest="daemon_command", required=True)
    d_start = daemon_sub.add_parser("start", help="Start the daemon in the background")
    d_start.set_defaults(func=_cmd_daemon_start)
    d_stop = daemon_sub.add_parser("stop", help="Stop the daemon (POST /shutdown)")
    d_stop.set_defaults(func=_cmd_daemon_stop)
    d_status = daemon_sub.add_parser("status", help="Check if daemon is running")
    d_status.set_defaults(func=_cmd_daemon_status)

    # topic subcommand
    topic_p = sub.add_parser("topic", help="Topic-related commands (list, info)")
    topic_sub = topic_p.add_subparsers(dest="topic_command", required=True)

    # topic list
    plist = topic_sub.add_parser("list", help="List topics (ros2 topic list)")
    plist.add_argument("-t", "--show-types", action="store_true", help="Show topic types")
    plist.add_argument("-v", "--verbose", action="store_true", help="Show publisher/subscriber counts per topic")
    plist.add_argument("-c", "--count-topics", action="store_true", help="Only print number of topics")
    plist.add_argument("--include-hidden-topics", action="store_true", help="Include hidden topics (default: exclude)")
    plist.set_defaults(func=topic_cli.cmd_list)

    # topic info
    pinfo = topic_sub.add_parser("info", help="Topic info (ros2 topic info)")
    pinfo.add_argument("topic_name", nargs="?", help="Topic name (e.g. /chatter)")
    pinfo.add_argument("-v", "--verbose", action="store_true", help="Print detailed publisher/subscriber info")
    pinfo.set_defaults(func=topic_cli.cmd_info)

    # service subcommand
    service_p = sub.add_parser("service", help="Service-related commands (list, type)")
    service_sub = service_p.add_subparsers(dest="service_command", required=True)

    # service list
    slist = service_sub.add_parser("list", help="List services (ros2 service list)")
    slist.add_argument("-t", "--show-types", action="store_true", help="Show service types")
    slist.add_argument("-c", "--count-services", action="store_true", help="Only print number of services")
    slist.add_argument(
        "--include-hidden-services",
        action="store_true",
        help="Include hidden services (default: exclude)",
    )
    slist.set_defaults(func=service_cli.cmd_list)

    # service type
    stype = service_sub.add_parser("type", help="Service type (ros2 service type)")
    stype.add_argument("service_name", nargs="?", help="Service name (e.g. /add_two_ints)")
    stype.set_defaults(func=service_cli.cmd_type)

    args = parser.parse_args()
    # Apply ROS_DOMAIN_ID when --domain-id not set (ros2cli behavior)
    if getattr(args, "domain_id", None) is None:
        args.domain_id = resolve_domain_id(None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
