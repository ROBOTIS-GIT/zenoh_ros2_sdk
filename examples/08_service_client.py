#!/usr/bin/env python3
"""
08 - Service Client Example

Demonstrates how to create a ROS2 service client using zenoh_ros2_sdk.
This example creates an AddTwoInts service client and makes a call.
"""
import time
from zenoh_ros2_sdk import ROS2ServiceClient


def main():
    print("08 - Service Client Example")
    print("Creating AddTwoInts service client...\n")

    # Service type loading is automatic (no need to call load_service_type)
    # Create service client
    client = ROS2ServiceClient(
        service_name="/add_two_ints",
        srv_type="example_interfaces/srv/AddTwoInts",
        timeout=5.0
    )

    try:
        # Make a synchronous service call
        print("Calling service with a=5, b=3...")
        response = client.call(a=5, b=3)

        if response:
            print(f"Service call successful!")
            print(f"Response: sum = {response.sum}")
        else:
            print("Service call failed or timed out.")

        # Make another call
        print("\nCalling service with a=10, b=20...")
        response = client.call(a=10, b=20)

        if response:
            print(f"Service call successful!")
            print(f"Response: sum = {response.sum}")
        else:
            print("Service call failed or timed out.")

        # Example of async call
        print("\nMaking async service call with a=7, b=8...")

        def async_callback(response):
            if response:
                print(f"Async service call successful! Response: sum = {response.sum}")
            else:
                print("Async service call failed.")

        client.call_async(async_callback, a=7, b=8)

        # Wait for async response
        time.sleep(2)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("\nService client closed.")


if __name__ == "__main__":
    main()
