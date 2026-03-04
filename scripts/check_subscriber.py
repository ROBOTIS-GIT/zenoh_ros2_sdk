#!/usr/bin/env python3
"""
Check that the SDK subscriber receives messages from a ROS 2 talker (e.g. in Docker).

Usage:
  With the ros2-zenoh container running (talker on /chatter):
    python scripts/check_subscriber.py
    python scripts/check_subscriber.py --router 127.0.0.1:7447 --duration 15
"""
import argparse
import sys
import time

def main():
    parser = argparse.ArgumentParser(description="Run SDK subscriber and verify it receives messages")
    parser.add_argument("--router", default="127.0.0.1:7447", help="Zenoh router endpoint")
    parser.add_argument("--duration", type=float, default=10.0, help="Seconds to run (default: 10)")
    parser.add_argument("--topic", default="/chatter", help="Topic to subscribe to")
    args = parser.parse_args()

    if ":" in args.router:
        host, port_str = args.router.rsplit(":", 1)
        port = int(port_str)
    else:
        host = args.router
        port = 7447

    try:
        from zenoh_ros2_sdk import ROS2Subscriber
    except ImportError:
        print("Error: zenoh_ros2_sdk not installed.", file=sys.stderr)
        return 1

    received = []

    def on_message(msg):
        received.append(msg)
        print(f"  Received: {msg.data}")

    print(f"Creating subscriber: topic={args.topic}, msg_type=std_msgs/msg/String, router={host}:{port}")
    sub = ROS2Subscriber(
        topic=args.topic,
        msg_type="std_msgs/msg/String",
        callback=on_message,
        router_ip=host,
        router_port=port,
    )
    print(f"Subscribed to keyexpr: {sub.keyexpr}")
    print(f"Listening for {args.duration}s...")
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.duration:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    sub.close()
    count = len(received)
    print(f"\nTotal messages received: {count}")
    if count == 0:
        print("No messages received. Check that the talker is running and the router is reachable.", file=sys.stderr)
        return 1
    print("Subscriber is receiving correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
