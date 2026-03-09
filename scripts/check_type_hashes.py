#!/usr/bin/env python3
"""
Developer tool: compare type hashes from live publishers with zenoh_ros2_sdk
computed hashes.

This script is intended for **debugging and validation** of type-hash behavior,
not as a stable public API. It uses the SDK's topic list and topic info
(via NodeStrategy: daemon when available, else in-process discovery) to get
topic types and publisher type hashes, then compares only for message types
supported by the SDK (packages defined in `zenoh_ros2_sdk._repositories`).
It skips unsupported namespaces (e.g. `action_msgs`) and message types the SDK
does not yet support.

Run from repo root (no ROS2 install required; uses Zenoh discovery):
  python3 scripts/check_type_hashes.py
  python3 scripts/check_type_hashes.py --router 127.0.0.1:7447 --domain-id 0

With the daemon running (`zenoh-ros2 daemon start`), discovery uses the daemon
and the script exits without delay. Use --no-daemon to force in-process
discovery.
"""
import argparse
import sys
from pathlib import Path

# Run from repo root so zenoh_ros2_sdk is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from zenoh_ros2_sdk.node.strategy import NodeStrategy
from zenoh_ros2_sdk._repositories import PACKAGE_TO_REPOSITORY
from zenoh_ros2_sdk.message_registry import get_registry
from zenoh_ros2_sdk.utils import get_type_hash, load_dependencies_recursive

# Packages we do not support (e.g. actions); skip type-hash comparison for these
UNSUPPORTED_PACKAGES = {"action_msgs"}


def is_supported_msg_type(msg_type: str) -> bool:
    """True if the message type belongs to a package supported by the SDK and we support it (excludes e.g. action_msgs)."""
    parts = msg_type.split("/")
    if len(parts) != 3:
        return False
    package = parts[0]
    if package in UNSUPPORTED_PACKAGES:
        return False
    return package in PACKAGE_TO_REPOSITORY


def compute_sdk_type_hash(msg_type: str, registry):
    """
    Compute type hash using SDK logic. Returns (hash_str, None) or (None, error).
    """
    msg_file = registry.get_msg_file_path(msg_type)
    if not msg_file or not msg_file.exists():
        return None, f"msg file not found for {msg_type}"
    try:
        with open(msg_file, "r") as f:
            msg_def = f.read()
    except Exception as e:
        return None, str(e)
    try:
        deps = load_dependencies_recursive(msg_type, msg_def, registry)
    except Exception as e:
        deps = {}
    try:
        h = get_type_hash(msg_type, msg_definition=msg_def, dependencies=deps)
        return h, None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Compare publisher type hashes with zenoh_ros2_sdk (supported msg types only).",
    )
    parser.add_argument(
        "--router",
        type=str,
        default="127.0.0.1:7447",
        help="Zenoh router endpoint (default: 127.0.0.1:7447)",
    )
    parser.add_argument(
        "--domain-id",
        type=int,
        default=None,
        help="ROS domain ID (default: ROS_DOMAIN_ID or 0)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Discovery timeout in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--no-daemon",
        action="store_true",
        help="Do not use the daemon; run discovery in-process (may delay exit)",
    )
    args = parser.parse_args()

    strategy = NodeStrategy(
        router=args.router,
        domain_id=args.domain_id,
        no_daemon=args.no_daemon,
    )

    print("Type hash check: publisher (zenoh-ros2 topic info -v) vs zenoh_ros2_sdk")
    print("Only supported message types (from _repositories) are compared.\n")

    try:
        topic_list = strategy.get_topic_names_and_types(
            timeout=args.timeout,
        )
    except Exception as e:
        print(f"Error listing topics: {e}")
        return 1

    if not topic_list:
        print("No topics found. Start some publishers and run again.")
        return 0

    registry = get_registry()
    # Collect (topic_name, topic_type, publisher_type_hash) from verbose info; dedupe by (type, hash)
    seen = set()
    results = []

    for topic_name, _types in topic_list:
        try:
            info = strategy.get_topic_info(
                topic_name,
                timeout=args.timeout,
                verbose=True,
            )
        except Exception:
            continue
        if not info or not info.get("publishers"):
            continue
        for pub in info["publishers"]:
            type_name = pub.get("topic_type")
            pub_hash = pub.get("type_hash")
            if not type_name or not pub_hash:
                continue
            key = (type_name, pub_hash)
            if key in seen:
                continue
            seen.add(key)
            if not is_supported_msg_type(type_name):
                continue
            sdk_hash, sdk_err = compute_sdk_type_hash(type_name, registry)
            if sdk_err:
                results.append((topic_name, type_name, pub_hash, None, sdk_err))
            else:
                match = pub_hash == sdk_hash
                results.append((topic_name, type_name, pub_hash, sdk_hash, None if match else "MISMATCH"))

    if not results:
        print("No supported message types found on any topic.")
        print("Supported packages:", ", ".join(sorted(PACKAGE_TO_REPOSITORY.keys())))
        return 0

    print(f"Comparing {len(results)} supported topic type(s):\n")
    all_ok = True
    for topic, type_name, pub_hash, sdk_hash, note in results:
        if note and note != "MISMATCH":
            print(f"  {type_name} (topic: {topic})")
            print(f"    Publisher hash: {pub_hash}")
            print(f"    Error: {note}\n")
            all_ok = False
            continue
        if note == "MISMATCH":
            print(f"  {type_name} (topic: {topic})")
            print(f"    Publisher hash: {pub_hash}")
            print(f"    SDK hash:       {sdk_hash}")
            print("    -> MISMATCH\n")
            all_ok = False
            continue
        print(f"  {type_name} (topic: {topic})")
        print(f"    Publisher hash: {pub_hash}")
        print(f"    SDK hash:       {sdk_hash}")
        print("    -> OK\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
