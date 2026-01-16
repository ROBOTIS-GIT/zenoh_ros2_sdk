#!/usr/bin/env python3
"""
12 - Subscribe to JointTrajectory Messages

Demonstrates how to subscribe to a ROS2 topic and receive trajectory_msgs/msg/JointTrajectory messages.
JointTrajectory messages contain trajectory waypoints for robot joints, including positions,
velocities, accelerations, efforts, and timing information.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("12 - Subscribe to JointTrajectory Messages")
    print("Subscribing to /joint_trajectory topic...\n")

    message_count = [0]  # Use list to allow modification in nested function

    def on_message(msg):
        """Callback function called when a JointTrajectory message is received."""
        message_count[0] += 1

        # Extract header information
        timestamp = msg.header.stamp
        frame_id = msg.header.frame_id

        # Extract joint names
        joint_names = list(msg.joint_names) if hasattr(msg, 'joint_names') else []

        # Extract trajectory points
        points = list(msg.points) if hasattr(msg, 'points') else []

        # Display received data
        print(f"\n{'='*60}")
        print(f"JointTrajectory Message #{message_count[0]}")
        print(f"{'='*60}")
        print(f"Timestamp: {timestamp.sec}.{timestamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Number of joints: {len(joint_names)}")
        print(f"Joint names: {joint_names}")
        print(f"Number of trajectory points: {len(points)}")

        # Display each trajectory point
        for i, point in enumerate(points):
            positions = list(point.positions) if hasattr(point, 'positions') else []
            velocities = list(point.velocities) if hasattr(point, 'velocities') else []
            accelerations = list(point.accelerations) if hasattr(point, 'accelerations') else []
            efforts = list(point.effort) if hasattr(point, 'effort') else []

            # Get time_from_start
            if hasattr(point, 'time_from_start'):
                t = point.time_from_start
                time_str = f"{t.sec}.{t.nanosec:09d}s"
            else:
                time_str = "N/A"

            print(f"\n  Point {i + 1} (t={time_str}):")
            print(f"    Positions:     {[f'{p:.4f}' for p in positions]}")
            if velocities:
                print(f"    Velocities:    {[f'{v:.4f}' for v in velocities]}")
            if accelerations:
                print(f"    Accelerations: {[f'{a:.4f}' for a in accelerations]}")
            if efforts:
                print(f"    Efforts:       {[f'{e:.4f}' for e in efforts]}")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/joint_trajectory",
        msg_type="trajectory_msgs/msg/JointTrajectory",
        callback=on_message
    )

    try:
        print("Waiting for JointTrajectory messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
