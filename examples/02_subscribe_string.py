#!/usr/bin/env python3
"""
02 - Subscribe to String Messages

Demonstrates how to subscribe to a ROS2 topic and receive String messages.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("02 - Subscribe to String Messages")
    print("Subscribing to /chatter topic...\n")

    def on_message(msg):
        print(f"Received: {msg.data}")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/chatter",
        msg_type="std_msgs/msg/String",
        callback=on_message
    )

    try:
        print("Waiting for messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
