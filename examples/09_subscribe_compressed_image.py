#!/usr/bin/env python3
"""
09 - Subscribe to Compressed Image Messages

Subscribes to the ZED left camera compressed image topic:
  /zed/zed_node/left/image_rect_color/compressed

Message type:
  sensor_msgs/msg/CompressedImage
"""

import time
from zenoh_ros2_sdk import ROS2Subscriber


def main():
    print("09 - Subscribe to Compressed Image Messages")
    print("Subscribing to /zed/zed_node/left/image_rect_color/compressed ...\n")

    msg_count = [0]

    def on_message(msg):
        """
        Callback function called when a CompressedImage message is received.
        """
        msg_count[0] += 1

        # Header info
        stamp = msg.header.stamp
        frame_id = msg.header.frame_id

        # Compressed image info
        format_str = getattr(msg, "format", "")
        data_len = len(msg.data) if getattr(msg, "data", None) is not None else 0

        print(f"\n--- CompressedImage #{msg_count[0]} ---")
        print(f"Timestamp: {stamp.sec}.{stamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Format: {format_str}")
        print(f"Data size: {data_len} bytes")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/zed/zed_node/left/image_rect_color/compressed",
        msg_type="sensor_msgs/msg/CompressedImage",
        callback=on_message,
        router_ip="192.168.6.2",
        domain_id=30,  # adjust if your ROS 2 domain is different
    )

    try:
        print("Waiting for CompressedImage messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()