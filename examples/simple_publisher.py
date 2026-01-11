#!/usr/bin/env python3
"""
Simple Publisher Example

Demonstrates how to publish String messages to a ROS2 topic.
"""
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zenoh_ros2_sdk import ROS2Publisher


def create_string_publisher(topic: str, domain_id: int = 0, router_ip: str = "127.0.0.1"):
    """Helper function to create a String message publisher"""
    return ROS2Publisher(
        topic=topic,
        msg_type="std_msgs/msg/String",
        msg_definition="string data\n",
        domain_id=domain_id,
        router_ip=router_ip
    )


def main():
    print("Simple String Publisher Example")
    print("Publishing to /chatter topic...\n")
    
    pub = create_string_publisher("/chatter", domain_id=30)
    
    try:
        for i in range(10):
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
