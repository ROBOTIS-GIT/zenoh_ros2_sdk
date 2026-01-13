"""
Unit tests for ROS2ServiceClient
"""
import pytest
import time
from zenoh_ros2_sdk import ROS2ServiceClient
from zenoh_ros2_sdk.session import ZenohSession


class TestROS2ServiceClient:
    """Tests for ROS2ServiceClient class"""

    def test_service_client_creation(self):
        """Test creating a service client"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0
        )

        assert client.service_name == "/add_two_ints"
        assert client.srv_type == "example_interfaces/srv/AddTwoInts"
        assert client.domain_id == 0
        assert client.node_name is not None
        assert client.type_hash is not None
        assert client.type_hash.startswith("RIHS01_")
        assert len(client.type_hash) == 71  # RIHS01_ + 64 hex chars

        client.close()

    def test_service_client_custom_node_name(self):
        """Test service client with custom node name"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            node_name="my_custom_client",
            domain_id=0
        )

        assert client.node_name == "my_custom_client"

        client.close()

    def test_service_client_namespace(self):
        """Test service client with custom namespace"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            namespace="/my_namespace",
            domain_id=0
        )

        assert client.namespace == "/my_namespace"

        client.close()

    def test_service_client_domain_id(self):
        """Test service client with custom domain ID"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=30
        )

        assert client.domain_id == 30
        # Keyexpr should include domain ID
        assert client.keyexpr.startswith("30/")

        client.close()

    def test_service_client_type_hash(self):
        """Test that service client computes correct type hash"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0
        )

        # Expected hash for example_interfaces/srv/AddTwoInts
        expected_hash = "RIHS01_e118de6bf5eeb66a2491b5bda11202e7b68f198d6f67922cf30364858239c81a"
        assert client.type_hash == expected_hash, \
            f"Type hash mismatch! Expected: {expected_hash}, Got: {client.type_hash}"

        client.close()

    def test_service_client_keyexpr_format(self):
        """Test that service client keyexpr has correct format"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=30
        )

        # Format: domain_id/service_name/dds_type/type_hash
        parts = client.keyexpr.split('/')
        assert len(parts) >= 4, f"Keyexpr should have at least 4 parts, got: {client.keyexpr}"
        assert parts[0] == "30", f"Domain ID should be 30, got: {parts[0]}"
        assert parts[1] == "add_two_ints", f"Service name should be 'add_two_ints', got: {parts[1]}"
        assert "example_interfaces::srv::dds_::AddTwoInts_" in parts[2], \
            f"DDS type should contain service type, got: {parts[2]}"
        assert parts[3].startswith("RIHS01_"), \
            f"Type hash should start with RIHS01_, got: {parts[3]}"

        client.close()

    def test_service_client_invalid_service_type(self):
        """Test that invalid service type raises ValueError"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        with pytest.raises(ValueError, match="Invalid service type format"):
            ROS2ServiceClient(
                service_name="/test",
                srv_type="invalid_format",
                domain_id=0
            )

    def test_service_client_timeout(self):
        """Test service client with custom timeout"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            timeout=5.0,
            domain_id=0
        )

        assert client.timeout == 5.0

        client.close()

    def test_service_client_shared_session(self):
        """Test that multiple service clients share the same session"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        client1 = ROS2ServiceClient(
            service_name="/add_two_ints",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0
        )

        client2 = ROS2ServiceClient(
            service_name="/another_service",
            srv_type="example_interfaces/srv/AddTwoInts",
            domain_id=0
        )

        # Both should use the same session manager
        assert client1.session_mgr is client2.session_mgr

        client1.close()
        client2.close()
