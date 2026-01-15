"""
Unit tests for ROS2ServiceServer
"""
import pytest
from zenoh_ros2_sdk import ROS2ServiceServer, get_message_class
from zenoh_ros2_sdk.session import ZenohSession


class TestROS2ServiceServer:
    """Tests for ROS2ServiceServer class"""

    def test_service_server_creation(self):
        """Test creating a service server"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        def callback(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback,
            domain_id=0
        )

        assert server.service_name == "/add_two_ints"
        assert server.srv_type == "example_interfaces/srv/AddTwoInts"
        assert server.domain_id == 0
        assert server.node_name is not None
        assert server.type_hash is not None
        assert server.type_hash.startswith("RIHS01_")
        assert len(server.type_hash) == 71  # RIHS01_ + 64 hex chars

        server.close()

    def test_service_server_custom_node_name(self):
        """Test service server with custom node name"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        def callback(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback,
            node_name="my_custom_server",
            domain_id=0
        )

        assert server.node_name == "my_custom_server"

        server.close()

    def test_service_server_namespace(self):
        """Test service server with custom namespace"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        def callback(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback,
            namespace="/my_namespace",
            domain_id=0
        )

        assert server.namespace == "/my_namespace"

        server.close()

    def test_service_server_domain_id(self):
        """Test service server with custom domain ID"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        def callback(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback,
            domain_id=30
        )

        assert server.domain_id == 30
        # Keyexpr should include domain ID
        assert server.keyexpr.startswith("30/")

        server.close()

    def test_service_server_type_hash(self):
        """Test that service server computes correct type hash"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        def callback(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback,
            domain_id=0
        )

        # Expected hash for example_interfaces/srv/AddTwoInts
        expected_hash = "RIHS01_e118de6bf5eeb66a2491b5bda11202e7b68f198d6f67922cf30364858239c81a"
        assert server.type_hash == expected_hash, \
            f"Type hash mismatch! Expected: {expected_hash}, Got: {server.type_hash}"

        server.close()

    def test_service_server_keyexpr_format(self):
        """Test that service server keyexpr has correct format"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        def callback(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback,
            domain_id=30
        )

        # Format: domain_id/service_name/dds_type/type_hash
        parts = server.keyexpr.split('/')
        assert len(parts) >= 4, f"Keyexpr should have at least 4 parts, got: {server.keyexpr}"
        assert parts[0] == "30", f"Domain ID should be 30, got: {parts[0]}"
        assert parts[1] == "add_two_ints", f"Service name should be 'add_two_ints', got: {parts[1]}"
        assert "example_interfaces::srv::dds_::AddTwoInts_" in parts[2], \
            f"DDS type should contain service type, got: {parts[2]}"
        assert parts[3].startswith("RIHS01_"), \
            f"Type hash should start with RIHS01_, got: {parts[3]}"

        server.close()

    def test_service_server_invalid_service_type(self):
        """Test that invalid service type raises ValueError"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        def callback(request):
            return None

        with pytest.raises(ValueError, match="Invalid service type format"):
            ROS2ServiceServer(
                service_name="/test",
                srv_type="invalid_format",
                callback=callback,
                domain_id=0
            )

    def test_service_server_callback_required(self):
        """Test that callback is required when mode='callback' (default)"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        with pytest.raises(ValueError, match="callback must be provided"):
            ROS2ServiceServer(
                service_name="/add_two_ints",
                srv_type="example_interfaces/srv/AddTwoInts",
                domain_id=0
                # Missing callback (default mode is 'callback')
            )

    def test_service_server_queue_mode_allows_no_callback(self):
        """Test that queue mode allows callback=None"""
        ZenohSession._instance = None

        server = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=None,
            domain_id=0,
            mode="queue",
        )
        assert server.mode == "queue"
        server.close()

    def test_service_server_shared_session(self):
        """Test that multiple service servers share the same session"""
        # Reset singleton for clean test
        ZenohSession._instance = None


        def callback1(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        def callback2(request):
            Response = get_message_class("example_interfaces/srv/AddTwoInts_Response")
            return Response(sum=request.a + request.b)

        server1 = ROS2ServiceServer(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback1,
            domain_id=0
        )

        server2 = ROS2ServiceServer(
            service_name="/another_service",
            srv_type="example_interfaces/srv/AddTwoInts",
            callback=callback2,
            domain_id=0
        )

        # Both should use the same session manager
        assert server1.session_mgr is server2.session_mgr

        server1.close()
        server2.close()
