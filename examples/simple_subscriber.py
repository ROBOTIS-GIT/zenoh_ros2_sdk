#!/usr/bin/env python3
"""
Simple Subscriber Example

Demonstrates how to subscribe to a ROS2 topic and receive String messages.
"""
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zenoh_ros2_sdk import ROS2Subscriber


def create_string_subscriber(topic: str, callback, domain_id: int = 0, router_ip: str = "127.0.0.1"):
    """Helper function to create a String message subscriber"""
    return ROS2Subscriber(
        topic=topic,
        msg_type="std_msgs/msg/String",
        msg_definition="string data\n",
        callback=callback,
        domain_id=domain_id,
        router_ip=router_ip
    )


def main():
    print("Simple String Subscriber Example")
    print("Subscribing to /chatter topic...\n")
    
    def on_message(msg):
        print(f"Received: {msg.data}")
    
    sub = create_string_subscriber("/chatter", on_message, domain_id=30)
    
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
