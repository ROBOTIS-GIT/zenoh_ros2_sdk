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
    last_t = [None]  # monotonic seconds

    def on_message(msg):
        """
        Callback function called when a CompressedImage message is received.
        """
        msg_count[0] += 1
        now = time.monotonic()

        # Instantaneous Hz (between last two messages)
        hz = None
        if last_t[0] is not None:
            dt = now - last_t[0]
            hz = (1.0 / dt) if dt > 0 else None
        last_t[0] = now

        # Header info
        stamp = msg.header.stamp
        frame_id = msg.header.frame_id

        # Compressed image info
        format_str = getattr(msg, "format", "")
        data_len = len(msg.data) if getattr(msg, "data", None) is not None else 0

        print(f"\n--- CompressedImage #{msg_count[0]} ---")
        if hz is not None:
            print(f"Rate: {hz:.2f} Hz")
        print(f"Timestamp: {stamp.sec}.{stamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Format: {format_str}")
        print(f"Data size: {data_len} bytes")

    # Create subscriber
    sub = ROS2Subscriber(
        topic="/zed/zed_node/left/image_rect_color/compressed",
        msg_type="sensor_msgs/msg/CompressedImage",
        callback=on_message
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