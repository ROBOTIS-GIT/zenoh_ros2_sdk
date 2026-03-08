#!/usr/bin/env python3
"""
20 - Subscribe to BatteryState Messages

Demonstrates how to subscribe to a ROS2 topic and receive `sensor_msgs/msg/BatteryState` messages.
BatteryState reports voltage, charge percentage, status, health, and optional cell-level data.

By default this example subscribes to `/battery_state`. You can override the topic name
by passing it as the first command-line argument:

  python3 examples/20_subscribe_battery_state.py /ai_worker/battery/left/state
"""
import sys
import math
import time

from zenoh_ros2_sdk import ROS2Subscriber


# BatteryState enum labels (sensor_msgs/msg/BatteryState.msg)
POWER_SUPPLY_STATUS = (
    "UNKNOWN", "CHARGING", "DISCHARGING", "NOT_CHARGING", "FULL"
)
POWER_SUPPLY_HEALTH = (
    "UNKNOWN", "GOOD", "OVERHEAT", "DEAD", "OVERVOLTAGE",
    "UNSPEC_FAILURE", "COLD", "WATCHDOG_TIMER_EXPIRE", "SAFETY_TIMER_EXPIRE"
)
POWER_SUPPLY_TECHNOLOGY = (
    "UNKNOWN", "NIMH", "LION", "LIPO", "LIFE", "NICD", "LIMN"
)


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "/battery_state"

    print("20 - Subscribe to BatteryState Messages")
    print(f"Subscribing to {topic} topic...\n")

    message_count = [0]  # Use list to allow modification in nested function

    def on_message(msg):
        """Callback function called when a BatteryState message is received."""
        message_count[0] += 1

        # Extract information from the message
        timestamp = msg.header.stamp
        frame_id = msg.header.frame_id
        voltage = msg.voltage
        temperature = msg.temperature
        current = msg.current
        charge = msg.charge
        capacity = msg.capacity
        design_capacity = msg.design_capacity
        percentage = msg.percentage
        status = msg.power_supply_status
        health = msg.power_supply_health
        technology = msg.power_supply_technology
        present = msg.present
        location = msg.location or "(not set)"
        serial_number = msg.serial_number or "(not set)"

        status_str = POWER_SUPPLY_STATUS[status] if status < len(POWER_SUPPLY_STATUS) else "?"
        health_str = POWER_SUPPLY_HEALTH[health] if health < len(POWER_SUPPLY_HEALTH) else "?"
        tech_str = POWER_SUPPLY_TECHNOLOGY[technology] if technology < len(POWER_SUPPLY_TECHNOLOGY) else "?"

        # Display received data
        print(f"\n--- BatteryState Message #{message_count[0]} ---")
        print(f"Timestamp: {timestamp.sec}.{timestamp.nanosec:09d}")
        print(f"Frame ID: {frame_id}")
        print(f"Present: {present}")
        print(f"Voltage: {voltage:.3f} V")
        print(f"Current: {current:.3f} A")
        print(f"Charge: {charge:.3f} Ah  |  Capacity: {capacity:.3f} Ah  |  Design: {design_capacity:.3f} Ah")
        print(f"Percentage: {percentage * 100:.1f}%")
        print(f"Temperature: {temperature:.1f} °C" if not math.isnan(temperature) else "Temperature: (NaN)")
        print(f"Status: {status_str}  |  Health: {health_str}  |  Technology: {tech_str}")
        print(f"Location: {location}  |  Serial: {serial_number}")
        if len(msg.cell_voltage) > 0:
            cells = ", ".join(f"{v:.2f}" for v in msg.cell_voltage[:8])
            if len(msg.cell_voltage) > 8:
                cells += f" ... (+{len(msg.cell_voltage) - 8} more)"
            print(f"Cell voltages (V): [{cells}]")

    # Create subscriber
    sub = ROS2Subscriber(
        topic=topic,
        msg_type="sensor_msgs/msg/BatteryState",
        callback=on_message,
    )

    try:
        print("Waiting for BatteryState messages... Press Ctrl+C to stop")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sub.close()
        print("Subscriber closed")


if __name__ == "__main__":
    main()
