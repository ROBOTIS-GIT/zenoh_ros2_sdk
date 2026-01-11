#!/usr/bin/env python3
"""
01 - Publish String Messages

Demonstrates how to publish String messages to a ROS2 topic.
"""
import time

from zenoh_ros2_sdk import ROS2Publisher, load_message_type, get_message_class


def main():
    print("01 - Publish String Messages")
    print("Publishing to /chatter topic...\n")
    
    # Load String message type automatically
    if not load_message_type("std_msgs/msg/String"):
        print("Error: Failed to load String message type")
        return
    
    # Get message class for easy object creation
    StringMsg = get_message_class("std_msgs/msg/String")
    if not StringMsg:
        print("Error: Failed to get String message class")
        return
    
    # Create publisher - msg_definition is optional, will auto-load from registry
    pub = ROS2Publisher(
        topic="/chatter",
        msg_type="std_msgs/msg/String",
        domain_id=30
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
