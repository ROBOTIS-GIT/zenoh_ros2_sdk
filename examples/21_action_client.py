#!/usr/bin/env python3
"""
21 - Action Client Example

Demonstrates how to use ROS2ActionClient to send goals, receive feedback,
retrieve results, and cancel goals using zenoh_ros2_sdk.

This example uses the standard example_interfaces/action/Fibonacci action.
Start the action server before running this script:

    ros2 run action_tutorials_py fibonacci_action_server

Or with a custom action server that provides the Fibonacci action.
"""
import time
from zenoh_ros2_sdk import ROS2ActionClient


def main():
    print("21 - Action Client Example")
    print("Connecting to Fibonacci action server...\n")

    client = ROS2ActionClient(
        action_name="/fibonacci",
        action_type="example_interfaces/action/Fibonacci",
        timeout=10.0,
    )

    try:
        # ------------------------------------------------------------------ #
        # 1. Synchronous send_goal with a feedback callback                  #
        # ------------------------------------------------------------------ #
        print("--- Sending goal (order=10) with feedback ---")

        feedback_msgs = []

        def on_feedback(msg):
            partial = list(msg.sequence)
            feedback_msgs.append(partial)
            print(f"  [feedback] partial sequence: {partial}")

        goal = client.send_goal(feedback_callback=on_feedback, order=10)

        if goal is None:
            print("Goal rejected or timed out.")
            return

        print(f"Goal accepted (id: {goal.goal_id.hex()})\n")

        # Block until the server returns the final result.
        result = goal.get_result(timeout=30.0)

        if result is not None:
            print(f"Result received: sequence = {list(result.result.sequence)}")
            print(f"Status: {result.status}\n")
        else:
            print("get_result timed out or failed.\n")

        # ------------------------------------------------------------------ #
        # 2. Asynchronous send_goal                                           #
        # ------------------------------------------------------------------ #
        print("--- Sending goal asynchronously (order=5) ---")

        def on_result(result):
            if result is None:
                print("  Async goal rejected or failed.")
                return
            print(f"  Async result: sequence = {list(result.result.sequence)}\n")

        client.send_goal_async(callback=on_result, order=5)

        # Give the server time to process the goal and return the result.
        time.sleep(5.0)

        # ------------------------------------------------------------------ #
        # 3. Cancel a goal mid-execution                                      #
        # ------------------------------------------------------------------ #
        print("--- Sending goal and then cancelling it (order=20) ---")

        goal = client.send_goal(order=20)

        if goal is not None:
            print(f"  Goal accepted (id: {goal.goal_id.hex()})")
            time.sleep(0.5)
            cancel_response = goal.cancel()
            if cancel_response is not None:
                goals_cancelling = getattr(cancel_response, "goals_canceling", None)
                n = len(goals_cancelling) if goals_cancelling is not None else "?"
                print(f"  Cancel request sent ({n} goal(s) cancelling).\n")
            else:
                print("  Cancel request timed out.\n")
        else:
            print("  Goal rejected or timed out.\n")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("Action client closed.")


if __name__ == "__main__":
    main()
