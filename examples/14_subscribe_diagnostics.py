#!/usr/bin/env python3
"""
14 - Subscribe to DiagnosticArray Messages

Demonstrates how to subscribe to a ROS2 topic and receive diagnostic_msgs/msg/DiagnosticArray messages.
DiagnosticArray messages contain diagnostic information from various system components, including
status levels (OK, WARN, ERROR, STALE), component names, messages, and key-value pairs.
"""
import time

from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("14 - Subscribe to DiagnosticArray Messages")
    print("Subscribing to /diagnostics topic...\n")

    message_count = [0]  # Use list to allow modification in nested function

    def on_message(msg):
        """Callback function called when a DiagnosticArray message is received."""
        message_count[0] += 1

        # Extract header information
        timestamp = msg.header.stamp
        frame_id = msg.header.frame_id

        # Extract status array
        statuses = list(msg.status) if hasattr(msg, 'status') else []

        # Display received data
        print(f"\n{'='*60}")
        print(f"DiagnosticArray Message #{message_count[0]}")
        print(f"{'='*60}")
        print(f"Timestamp: {timestamp.sec}.{timestamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Number of diagnostic statuses: {len(statuses)}")

        # Display each diagnostic status
        for i, status in enumerate(statuses):
            # Map level to string
            level_map = {
                0: "OK",
                1: "WARN",
                2: "ERROR",
                3: "STALE"
            }
            level = status.level if hasattr(status, 'level') else 0
            level_str = level_map.get(level, f"UNKNOWN({level})")

            name = status.name if hasattr(status, 'name') else "N/A"
            message = status.message if hasattr(status, 'message') else "N/A"
            hardware_id = status.hardware_id if hasattr(status, 'hardware_id') else "N/A"
            values = list(status.values) if hasattr(status, 'values') else []

            print(f"\n  Status {i + 1}:")
            print(f"    Level:       {level_str}")
            print(f"    Name:        {name}")
            print(f"    Hardware ID: {hardware_id}")
            print(f"    Message:     {message}")

            if values:
                print(f"    Values ({len(values)}):")
                for kv in values:
                    key = kv.key if hasattr(kv, 'key') else "N/A"
                    value = kv.value if hasattr(kv, 'value') else "N/A"
                    print(f"      {key}: {value}")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/diagnostics",
        msg_type="diagnostic_msgs/msg/DiagnosticArray",
        callback=on_message
    )

    try:
        print("Waiting for DiagnosticArray messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
