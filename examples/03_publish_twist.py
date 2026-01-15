#!/usr/bin/env python3
"""
03 - Publish Twist Messages

Demonstrates how to publish geometry_msgs/msg/Twist messages.
Twist messages represent velocity in free space with linear and angular components.
"""
import time

from zenoh_ros2_sdk import ROS2Publisher, get_message_class


def main():
    print("03 - Publish Twist Messages")
    print("Using geometry_msgs/msg/Twist with automatic message loading\n")

    # Get message classes for easy object creation
    Vector3 = get_message_class("geometry_msgs/msg/Vector3")
    Twist = get_message_class("geometry_msgs/msg/Twist")

    if not Vector3 or not Twist:
        print("Error: Failed to get message classes")
        return

    # Create publisher
    pub = ROS2Publisher(
        topic="/cmd_vel",
        msg_type="geometry_msgs/msg/Twist"
    )

    try:
        print("Publishing Twist messages... Press Ctrl+C to stop\n")

        for i in range(60):
            # Create Vector3 objects using the message class
            linear = Vector3(x=0.5 + i * 0.1, y=0.0, z=0.0)
            angular = Vector3(x=0.0, y=0.0, z=0.2 + i * 0.05)

            # Create Twist message - clean and simple!
            pub.publish(linear=linear, angular=angular)
            print(f"Published Twist {i+1}: linear.x={linear.x:.2f}, angular.z={angular.z:.2f}")
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        print("Publisher closed")


if __name__ == "__main__":
    main()
