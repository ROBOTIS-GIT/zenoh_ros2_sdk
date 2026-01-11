#!/usr/bin/env python3
"""
02 - Subscribe to String Messages

Demonstrates how to subscribe to a ROS2 topic and receive String messages.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber, load_message_type, get_message_class


def main():
    print("02 - Subscribe to String Messages")
    print("Subscribing to /chatter topic...\n")
    
    # Load String message type automatically
    if not load_message_type("std_msgs/msg/String"):
        print("Error: Failed to load String message type")
        return
    
    # Get message class (optional, for type checking)
    StringMsg = get_message_class("std_msgs/msg/String")
    if not StringMsg:
        print("Error: Failed to get String message class")
        return
    
    def on_message(msg):
        print(f"Received: {msg.data}")
    
    # Create subscriber - msg_definition is optional, will auto-load from registry
    sub = ROS2Subscriber(
        topic="/chatter",
        msg_type="std_msgs/msg/String",
        callback=on_message,
        domain_id=30
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
