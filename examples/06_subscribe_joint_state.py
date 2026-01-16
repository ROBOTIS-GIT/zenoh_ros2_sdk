#!/usr/bin/env python3
"""
06 - Subscribe to JointState Messages

Demonstrates how to subscribe to a ROS2 topic and receive sensor_msgs/msg/JointState messages.
JointState messages contain the state (position, velocity, effort) of robot joints.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("06 - Subscribe to JointState Messages")
    print("Subscribing to /joint_states topic...\n")

    message_count = [0]  # Use list to allow modification in nested function

    def on_message(msg):
        """Callback function called when a JointState message is received."""
        message_count[0] += 1

        # Extract information from the message
        timestamp = msg.header.stamp
        frame_id = msg.header.frame_id
        joint_names = list(msg.name) if hasattr(msg, 'name') else []
        positions = list(msg.position) if hasattr(msg, 'position') else []
        velocities = list(msg.velocity) if hasattr(msg, 'velocity') else []
        efforts = list(msg.effort) if hasattr(msg, 'effort') else []

        # Display received data
        print(f"\n--- JointState Message #{message_count[0]} ---")
        print(f"Timestamp: {timestamp.sec}.{timestamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Number of joints: {len(joint_names)}")

        if joint_names:
            print("\nJoint States:")
            for i, name in enumerate(joint_names):
                pos = positions[i] if i < len(positions) else None
                vel = velocities[i] if i < len(velocities) else None
                eff = efforts[i] if i < len(efforts) else None

                pos_str = f"{pos:.4f}" if pos is not None else "N/A"
                vel_str = f"{vel:.4f}" if vel is not None else "N/A"
                eff_str = f"{eff:.4f}" if eff is not None else "N/A"

                print(f"  {name}: pos={pos_str}, vel={vel_str}, eff={eff_str}")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/joint_states",
        msg_type="sensor_msgs/msg/JointState",
        callback=on_message
    )

    try:
        print("Waiting for JointState messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
