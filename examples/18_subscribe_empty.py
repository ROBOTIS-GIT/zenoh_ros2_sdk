#!/usr/bin/env python3
"""
18 - Subscribe to Empty Messages

Demonstrates how to subscribe to a ROS2 topic and receive std_msgs/msg/Empty messages.
Empty messages are used for signaling or triggering events where no data payload is needed.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("18 - Subscribe to Empty Messages")
    print("Subscribing to /trigger topic...\n")

    message_count = [0]  # Use list to allow modification in nested function

    def on_message(msg):
        """Callback function called when an Empty message is received."""
        message_count[0] += 1

        # Empty messages have no fields - just count them
        print(f"Received Empty message #{message_count[0]}")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/trigger",
        msg_type="std_msgs/msg/Empty",
        callback=on_message
    )

    try:
        print("Waiting for Empty messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
