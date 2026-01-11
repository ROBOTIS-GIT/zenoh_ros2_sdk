#!/usr/bin/env python3
"""
Custom Message Type Example

Demonstrates how to publish/subscribe to custom ROS2 message types.
This example uses std_msgs/msg/Int32.
"""
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zenoh_ros2_sdk import ROS2Publisher, ROS2Subscriber


def main():
    print("Custom Message Type Example")
    print("Using std_msgs/msg/Int32\n")
    
    # Create publisher for Int32 messages
    pub = ROS2Publisher(
        topic="/counter",
        msg_type="std_msgs/msg/Int32",
        msg_definition="int32 data\n",
        domain_id=30
    )
    
    # Create subscriber for Int32 messages
    def on_message(msg):
        print(f"Received counter value: {msg.data}")
    
    sub = ROS2Subscriber(
        topic="/counter",
        msg_type="std_msgs/msg/Int32",
        msg_definition="int32 data\n",
        callback=on_message,
        domain_id=30
    )
    
    try:
        print("Publishing and receiving Int32 messages... Press Ctrl+C to stop\n")
        for i in range(10):
            pub.publish(data=i)
            print(f"Published: {i}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        sub.close()
        print("Publisher and subscriber closed")


if __name__ == "__main__":
    main()
