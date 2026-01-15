#!/usr/bin/env python3
"""
04 - Subscribe to Twist Messages

Demonstrates how to subscribe to geometry_msgs/msg/Twist messages.
Twist messages represent velocity in free space with linear and angular components.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("04 - Subscribe to Twist Messages")
    print("Using geometry_msgs/msg/Twist with automatic message loading\n")

    # Create subscriber
    def on_message(msg):
        # Use .x syntax directly - no dictionaries!
        linear = msg.linear
        angular = msg.angular
        print(f"Received Twist - Linear: ({linear.x:.2f}, {linear.y:.2f}, {linear.z:.2f}), "
              f"Angular: ({angular.x:.2f}, {angular.y:.2f}, {angular.z:.2f})")

    sub = ROS2Subscriber(
        topic="/cmd_vel",
        msg_type="geometry_msgs/msg/Twist",
        callback=on_message
    )

    try:
        print("Waiting for Twist messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
