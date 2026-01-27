#!/usr/bin/env python3
"""
15 - Publish IMU Messages

Demonstrates how to publish sensor_msgs/msg/Imu messages to a ROS2 topic.
IMU messages contain orientation, angular velocity, and linear acceleration data.
"""
import time
import numpy as np
import math

from zenoh_ros2_sdk import ROS2Publisher, get_message_class


def main():
    print("15 - Publish IMU Messages")
    print("Publishing to /imu/imu_sensor_broadcaster/imu topic...\n")

    # Get message classes for easy object creation
    Header = get_message_class("std_msgs/msg/Header")
    Time = get_message_class("builtin_interfaces/msg/Time")
    Quaternion = get_message_class("geometry_msgs/msg/Quaternion")
    Vector3 = get_message_class("geometry_msgs/msg/Vector3")
    Imu = get_message_class("sensor_msgs/msg/Imu")

    if not all([Header, Time, Quaternion, Vector3, Imu]):
        print("Error: Failed to get message classes")
        return

    # Create publisher
    pub = ROS2Publisher(
        topic="/imu/imu_sensor_broadcaster/imu",
        msg_type="sensor_msgs/msg/Imu"
    )

    try:
        print("Publishing IMU messages...")
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

            # Simulate IMU data (in a real application, this would come from hardware)
            # Orientation: simple rotation around z-axis
            angle = counter * 0.1  # Slowly rotating
            orientation = Quaternion(
                x=0.0,
                y=0.0,
                z=math.sin(angle / 2.0),
                w=math.cos(angle / 2.0)
            )

            # Angular velocity: small rotation around z-axis
            angular_velocity = Vector3(
                x=0.0,
                y=0.0,
                z=0.1  # rad/s
            )

            # Linear acceleration: simulate gravity + small noise
            linear_acceleration = Vector3(
                x=0.0,
                y=0.0,
                z=9.81  # m/s^2 (gravity)
            )

            # Create covariance arrays (9x9 flattened to 1D)
            # -1.0 in first element means unknown/not estimated
            orientation_covariance = np.array([-1.0] + [0.0] * 8, dtype=np.float64)
            angular_velocity_covariance = np.array([-1.0] + [0.0] * 8, dtype=np.float64)
            linear_acceleration_covariance = np.array([-1.0] + [0.0] * 8, dtype=np.float64)

            # Publish IMU data
            pub.publish(
                header=header,
                orientation=orientation,
                orientation_covariance=orientation_covariance,
                angular_velocity=angular_velocity,
                angular_velocity_covariance=angular_velocity_covariance,
                linear_acceleration=linear_acceleration,
                linear_acceleration_covariance=linear_acceleration_covariance
            )

            print(f"Published IMU {counter}: "
                  f"orientation=[{orientation.x:.3f}, {orientation.y:.3f}, {orientation.z:.3f}, {orientation.w:.3f}], "
                  f"ang_vel=[{angular_velocity.x:.3f}, {angular_velocity.y:.3f}, {angular_velocity.z:.3f}], "
                  f"lin_acc=[{linear_acceleration.x:.3f}, {linear_acceleration.y:.3f}, {linear_acceleration.z:.3f}]")

            counter += 1
            time.sleep(0.1)  # 10 Hz

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        pub.close()
        print("Publisher closed")


if __name__ == "__main__":
    main()
