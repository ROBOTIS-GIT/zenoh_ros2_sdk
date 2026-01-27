#!/usr/bin/env python3
"""
16 - Subscribe to IMU Messages

Demonstrates how to subscribe to a ROS2 topic and receive sensor_msgs/msg/Imu messages.
IMU messages contain orientation, angular velocity, and linear acceleration data.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("16 - Subscribe to IMU Messages")
    print("Subscribing to /imu/imu_sensor_broadcaster/imu topic...\n")

    message_count = [0]  # Use list to allow modification in nested function
    last_t = [None]  # For calculating message rate

    def on_message(msg):
        """Callback function called when an IMU message is received."""
        message_count[0] += 1
        now = time.monotonic()

        # Calculate message rate
        hz = None
        if last_t[0] is not None:
            dt = now - last_t[0]
            hz = (1.0 / dt) if dt > 0 else None
        last_t[0] = now

        # Extract information from the message
        timestamp = msg.header.stamp
        frame_id = msg.header.frame_id
        orientation = msg.orientation
        angular_velocity = msg.angular_velocity
        linear_acceleration = msg.linear_acceleration

        # Display received data
        print(f"\n--- IMU Message #{message_count[0]} ---")
        if hz is not None:
            print(f"Rate: {hz:.2f} Hz")
        print(f"Timestamp: {timestamp.sec}.{timestamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Orientation (quaternion): x={orientation.x:.4f}, y={orientation.y:.4f}, "
              f"z={orientation.z:.4f}, w={orientation.w:.4f}")
        print(f"Angular Velocity: x={angular_velocity.x:.4f}, y={angular_velocity.y:.4f}, "
              f"z={angular_velocity.z:.4f} rad/s")
        print(f"Linear Acceleration: x={linear_acceleration.x:.4f}, y={linear_acceleration.y:.4f}, "
              f"z={linear_acceleration.z:.4f} m/s²")

        # Check if orientation is valid (quaternion should be normalized)
        quat_norm = (orientation.x**2 + orientation.y**2 + 
                     orientation.z**2 + orientation.w**2)**0.5
        if abs(quat_norm - 1.0) > 0.01:
            print(f"  WARNING: Quaternion not normalized! Norm={quat_norm:.4f}")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/imu/imu_sensor_broadcaster/imu",
        msg_type="sensor_msgs/msg/Imu",
        callback=on_message
    )

    try:
        print("Waiting for IMU messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
