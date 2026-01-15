#!/usr/bin/env python3
"""
07 - Service Server Example

Demonstrates how to create a ROS2 service server using zenoh_ros2_sdk.
This example creates an AddTwoInts service server.
"""
import time
from zenoh_ros2_sdk import ROS2ServiceServer, get_message_class


def add_two_ints_handler(request):
    """
    Service callback function that adds two integers.

    Args:
        request: Service request message (AddTwoInts_Request)

    Returns:
        Service response message (AddTwoInts_Response)
    """
    # Get the response message class
    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")

    # Calculate sum
    sum_result = request.a + request.b

    print(f"Received request: a={request.a}, b={request.b}")
    print(f"Sending response: sum={sum_result}")

    # Create and return response
    return Response(sum=sum_result)


def main():
    print("07 - Service Server Example")
    print("Creating AddTwoInts service server...\n")

    # Service type loading is automatic (no need to call load_service_type)
    # Create service server
    server = ROS2ServiceServer(
        service_name="/add_two_ints",
        srv_type="example_interfaces/srv/AddTwoInts",
        callback=add_two_ints_handler
    )

    print("Service server is running. Waiting for requests...")
    print("Press Ctrl+C to stop.\n")

    try:
        # Keep the server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down service server...")
    finally:
        server.close()
        print("Service server closed.")


if __name__ == "__main__":
    main()
