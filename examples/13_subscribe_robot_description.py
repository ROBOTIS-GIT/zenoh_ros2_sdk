#!/usr/bin/env python3
"""
13 - Subscribe to Robot Description

Demonstrates how to subscribe to the /robot_description topic and receive the URDF XML string.
The robot_description topic is commonly used in ROS2 to publish the URDF (Unified Robot
Description Format) of a robot, which describes its physical structure, joints, and links.

This example uses TRANSIENT_LOCAL durability QoS to receive the cached robot description
that was published before the subscriber started (like `ros2 topic echo` does).
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber
from zenoh_ros2_sdk.qos import QosProfile, QosDurability


def main():
    print("13 - Subscribe to Robot Description")
    print("Subscribing to /robot_description topic with TRANSIENT_LOCAL durability...\n")

    message_count = [0]  # Use list to allow modification in nested function

    def on_message(msg):
        """Callback function called when a robot description message is received."""
        message_count[0] += 1

        urdf_data = msg.data

        # Display received data
        print(f"\n--- Robot Description Message #{message_count[0]} ---")
        print(f"URDF length: {len(urdf_data)} characters")
        print(f"URDF content:\n{urdf_data}")

        # Extract robot name if present
        if "<robot" in urdf_data and 'name="' in urdf_data:
            start = urdf_data.find('name="', urdf_data.find("<robot")) + 6
            end = urdf_data.find('"', start)
            if start > 5 and end > start:
                robot_name = urdf_data[start:end]
                print(f"\nRobot name: {robot_name}")

    # Create subscriber with TRANSIENT_LOCAL durability
    # This allows receiving cached messages from publishers that published before
    # the subscriber started (required for /robot_description which publishes once)
    qos = QosProfile(durability=QosDurability.TRANSIENT_LOCAL)

    sub = ROS2Subscriber(
        topic="/robot_description",
        msg_type="std_msgs/msg/String",
        callback=on_message,
        qos=qos
    )

    try:
        print("Waiting for robot description... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
