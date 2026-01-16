#!/usr/bin/env python3
"""
01 - Publish String Messages

Demonstrates how to publish String messages to a ROS2 topic.
"""
import time

from zenoh_ros2_sdk import ROS2Publisher


def main():
    print("01 - Publish String Messages")
    print("Publishing to /chatter topic...\n")

    # Create publisher
    pub = ROS2Publisher(
        topic="/chatter",
        msg_type="std_msgs/msg/String"
    )

    try:
        for i in range(60):
            pub.publish(data=f"Hello World: {i}")
            print(f"Published: Hello World: {i}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        print("Publisher closed")


if __name__ == "__main__":
    main()
