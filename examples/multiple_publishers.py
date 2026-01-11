#!/usr/bin/env python3
"""
Multiple Publishers Example

Demonstrates how multiple publishers can share the same Zenoh session.
All publishers automatically share the session through the singleton pattern.
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
    print("Multiple Publishers Example")
    print("Creating two publishers that share the same Zenoh session...\n")
    
    # Create multiple publishers - they automatically share the session
    pub1 = create_string_publisher("/topic1", domain_id=30)
    pub2 = create_string_publisher("/topic2", domain_id=30)
    
    try:
        print("Publishing to both topics... Press Ctrl+C to stop\n")
        for i in range(5):
            pub1.publish(data=f"Topic1 message {i}")
            pub2.publish(data=f"Topic2 message {i}")
            print(f"Published to both topics: {i}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub1.close()
        pub2.close()
        print("All publishers closed")


if __name__ == "__main__":
    main()
