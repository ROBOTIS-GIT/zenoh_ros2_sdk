"""
Integration test for zenoh_ros2_sdk queue-mode service server.
"""

import threading
import uuid

import pytest

from zenoh_ros2_sdk import ROS2ServiceClient, ROS2ServiceServer, get_message_class


def test_service_queue_mode_end_to_end():
    # Unique service name to avoid cross-test interference
    service_name = f"/add_two_ints_{uuid.uuid4().hex[:8]}"
    srv_type = "example_interfaces/srv/AddTwoInts"

    Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")

    server = ROS2ServiceServer(
        service_name=service_name,
        srv_type=srv_type,
        callback=None,
        domain_id=0,
        mode="queue",
    )

    # Run server loop in background: take request and send response.
    def server_loop():
        key, req = server.take_request(timeout=5.0)
        resp = Response(sum=req.a + req.b)
        server.send_response(key, resp)

    t = threading.Thread(target=server_loop, daemon=True)
    t.start()

    client = ROS2ServiceClient(service_name=service_name, srv_type=srv_type, domain_id=0, timeout=5.0)
    resp = client.call(a=2, b=3)

    client.close()
    server.close()
    t.join(timeout=2.0)

    assert resp is not None
    assert resp.sum == 5

