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
            partial = list(msg.feedback.sequence)
            feedback_msgs.append(partial)
            print(f"  [feedback] partial sequence: {partial}")

        result = client.send_goal(
            feedback_callback=on_feedback,
            order=10,
            result_timeout=30.0,
        )

        if result is not None:
            print(f"Result received: sequence = {list(result.result.sequence)}")
            print(f"Status: {result.status}\n")
        else:
            print("Goal rejected, timed out, or failed.\n")

        # ------------------------------------------------------------------ #
        # 2. Asynchronous send_goal                                           #
        # ------------------------------------------------------------------ #
        print("--- Sending goal asynchronously (order=5) ---")

        def on_goal_response(future):
            goal = future.result()
            if goal is None or not goal.accepted:
                print("  Async goal rejected or timed out.")
                return
            result_future = goal.get_result_async(timeout=30.0)
            result = result_future.result()
            if result is None:
                print("  Async get_result timed out or failed.")
                return
            print(f"  Async result: sequence = {list(result.result.sequence)}\n")

        client.send_goal_async(order=5).add_done_callback(on_goal_response)

        # Give the server time to process the goal and return the result.
        time.sleep(5.0)

        # ------------------------------------------------------------------ #
        # 3. Cancel a goal mid-execution                                      #
        # ------------------------------------------------------------------ #
        print("--- Sending goal and then cancelling it (order=20) ---")

        goal_future = client.send_goal_async(order=20)
        goal = goal_future.result()

        if goal is not None and goal.accepted:
            print(f"  Goal accepted (id: {goal.goal_id.hex()})")
            time.sleep(0.5)
            cancel_response = goal.cancel_goal()
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
