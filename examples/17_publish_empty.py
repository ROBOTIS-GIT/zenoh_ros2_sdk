#!/usr/bin/env python3
"""
17 - Publish Empty Messages

Demonstrates how to publish std_msgs/msg/Empty messages to a ROS2 topic.
Empty messages are used for signaling or triggering events where no data payload is needed.
"""
import time

from zenoh_ros2_sdk import ROS2Publisher


def main():
    print("17 - Publish Empty Messages")
    print("Publishing to /trigger topic...\n")

    # Create publisher
    # Note: std_msgs/msg/Empty has no fields, so msg_definition is ""
    pub = ROS2Publisher(
        topic="/trigger",
        msg_type="std_msgs/msg/Empty"
    )

    try:
        print("Publishing Empty messages...")
        print("Press Ctrl+C to stop\n")

        counter = 0
        while True:
            # Publish empty message - no fields needed
            pub.publish()

            print(f"Published Empty #{counter}")
            counter += 1
            time.sleep(1.0)  # 1 Hz

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        print("Publisher closed")


if __name__ == "__main__":
    main()
