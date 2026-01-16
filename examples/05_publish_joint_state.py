#!/usr/bin/env python3
"""
05 - Publish JointState Messages

Demonstrates how to publish sensor_msgs/msg/JointState messages to a ROS2 topic.
JointState messages are commonly used to report the state of robot joints.
"""
import time
import numpy as np

from zenoh_ros2_sdk import ROS2Publisher, get_message_class


def main():
    print("05 - Publish JointState Messages")
    print("Publishing to /joint_states topic...\n")

    # Get message classes for easy object creation
    Header = get_message_class("std_msgs/msg/Header")
    Time = get_message_class("builtin_interfaces/msg/Time")
    JointState = get_message_class("sensor_msgs/msg/JointState")

    if not all([Header, Time, JointState]):
        print("Error: Failed to get message classes")
        return

    # Create publisher
    pub = ROS2Publisher(
        topic="/joint_states",
        msg_type="sensor_msgs/msg/JointState"
    )

    # Example joint names (adjust to match your robot)
    joint_names = ["joint1", "joint2", "joint3", "joint4", "joint5"]

    try:
        print(f"Publishing JointState messages with {len(joint_names)} joints...")
        print("Press Ctrl+C to stop\n")

        counter = 0
        while True:
            # Get current time
            now = time.time()
            sec = int(now)
            nanosec = int((now - sec) * 1e9)

            # Create header with timestamp
            header = Header(
                stamp=Time(sec=sec, nanosec=nanosec),
                frame_id="base_link"
            )

            # Create joint state with example positions
            # In a real application, these would come from your robot hardware
            # Note: Arrays need to be numpy arrays for proper serialization
            positions = np.array([0.1 * counter + i * 0.1 for i in range(len(joint_names))], dtype=np.float64)
            velocities = np.array([0.05 for _ in range(len(joint_names))], dtype=np.float64)
            efforts = np.array([0.0 for _ in range(len(joint_names))], dtype=np.float64)

            # Publish joint state - pass fields as kwargs matching message structure
            pub.publish(
                header=header,
                name=joint_names,
                position=positions,
                velocity=velocities,
                effort=efforts
            )

            print(f"Published JointState {counter}: positions={[f'{p:.2f}' for p in positions]}")
            counter += 1
            time.sleep(0.1)  # 10 Hz

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        print("Publisher closed")


if __name__ == "__main__":
    main()
