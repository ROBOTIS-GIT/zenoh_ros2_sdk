#!/usr/bin/env python3
"""
10 - Service Server (Queue mode)

Demonstrates ros-z style service handling:
- server enqueues requests (take_request)
- user sends response later (send_response) using a correlation key

Service:
  /add_two_ints
Type:
  example_interfaces/srv/AddTwoInts
"""

import time

from zenoh_ros2_sdk import ROS2ServiceServer, get_message_class


def main():
    print("10 - Service Server (Queue mode)")

    # In queue mode, callback is optional; you manage the request/response loop yourself.
    server = ROS2ServiceServer(
        service_name="/add_two_ints",
        srv_type="example_interfaces/srv/AddTwoInts",
        callback=None,
        mode="queue"
    )

    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")

    try:
        print("Waiting for service requests... Ctrl+C to stop")
        while True:
            try:
                key, req = server.take_request(timeout=1.0)
            except TimeoutError:
                # no request within timeout; keep waiting
                continue

            print(f"Got request: a={req.a} b={req.b} key={key}")
            resp = Response(sum=req.a + req.b)
            server.send_response(key, resp)
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        server.close()


if __name__ == "__main__":
    main()

