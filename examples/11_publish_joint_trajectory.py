#!/usr/bin/env python3
"""
11 - Publish JointTrajectory Messages

Demonstrates how to publish trajectory_msgs/msg/JointTrajectory messages to a ROS2 topic.
JointTrajectory messages are commonly used to command robot joint movements along a trajectory,
specifying positions, velocities, accelerations, and efforts at each time point.
"""
import time
import numpy as np

from zenoh_ros2_sdk import ROS2Publisher, get_message_class


def main():
    print("11 - Publish JointTrajectory Messages")
    print("Publishing to /joint_trajectory topic...\n")

    # Get message classes for easy object creation
    Header = get_message_class("std_msgs/msg/Header")
    Time = get_message_class("builtin_interfaces/msg/Time")
    Duration = get_message_class("builtin_interfaces/msg/Duration")
    JointTrajectory = get_message_class("trajectory_msgs/msg/JointTrajectory")
    JointTrajectoryPoint = get_message_class("trajectory_msgs/msg/JointTrajectoryPoint")

    if not all([Header, Time, Duration, JointTrajectory, JointTrajectoryPoint]):
        print("Error: Failed to get message classes")
        return

    # Create publisher
    pub = ROS2Publisher(
        topic="/joint_trajectory",
        msg_type="trajectory_msgs/msg/JointTrajectory"
    )

    # Example joint names (adjust to match your robot)
    joint_names = ["joint1", "joint2", "joint3", "joint4", "joint5"]
    num_joints = len(joint_names)

    try:
        print(f"Publishing JointTrajectory messages with {num_joints} joints...")
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

            # Create trajectory points
            # In a real application, these would come from motion planning
            points = []

            # Point 1: Start position (t=0s)
            point1 = JointTrajectoryPoint(
                positions=np.array([0.0] * num_joints, dtype=np.float64),
                velocities=np.array([0.0] * num_joints, dtype=np.float64),
                accelerations=np.array([0.0] * num_joints, dtype=np.float64),
                effort=np.array([0.0] * num_joints, dtype=np.float64),
                time_from_start=Duration(sec=0, nanosec=0)
            )
            points.append(point1)

            # Point 2: Intermediate position (t=1s)
            point2 = JointTrajectoryPoint(
                positions=np.array([0.5 + 0.1 * counter] * num_joints, dtype=np.float64),
                velocities=np.array([0.5] * num_joints, dtype=np.float64),
                accelerations=np.array([0.1] * num_joints, dtype=np.float64),
                effort=np.array([0.0] * num_joints, dtype=np.float64),
                time_from_start=Duration(sec=1, nanosec=0)
            )
            points.append(point2)

            # Point 3: End position (t=2s)
            point3 = JointTrajectoryPoint(
                positions=np.array([1.0 + 0.1 * counter] * num_joints, dtype=np.float64),
                velocities=np.array([0.0] * num_joints, dtype=np.float64),
                accelerations=np.array([0.0] * num_joints, dtype=np.float64),
                effort=np.array([0.0] * num_joints, dtype=np.float64),
                time_from_start=Duration(sec=2, nanosec=0)
            )
            points.append(point3)

            # Publish joint trajectory
            pub.publish(
                header=header,
                joint_names=joint_names,
                points=points
            )

            print(f"Published JointTrajectory {counter}: {len(points)} points, "
                  f"target positions={[f'{p:.2f}' for p in point3.positions]}")
            counter += 1
            time.sleep(1.0)  # 1 Hz (typical for trajectory commands)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        print("Publisher closed")


if __name__ == "__main__":
    main()
