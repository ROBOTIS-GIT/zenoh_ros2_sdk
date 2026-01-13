"""
Unit tests for utility functions
"""
import os
from pathlib import Path
import pytest
from zenoh_ros2_sdk.utils import (
    ros2_to_dds_type, get_type_hash, mangle_name, compute_type_hash_from_msg,
    compute_service_type_hash
)
from zenoh_ros2_sdk.message_registry import get_registry


class TestRos2ToDdsType:
    """Tests for ROS2 to DDS type conversion"""

    def test_std_msgs_string(self):
        """Test conversion of std_msgs/msg/String"""
        result = ros2_to_dds_type("std_msgs/msg/String")
        assert result == "std_msgs::msg::dds_::String_"

    def test_std_msgs_int32(self):
        """Test conversion of std_msgs/msg/Int32"""
        result = ros2_to_dds_type("std_msgs/msg/Int32")
        assert result == "std_msgs::msg::dds_::Int32_"

    def test_custom_message(self):
        """Test conversion of custom message type"""
        result = ros2_to_dds_type("geometry_msgs/msg/Twist")
        assert result == "geometry_msgs::msg::dds_::Twist_"

    def test_invalid_format(self):
        """Test handling of invalid format"""
        result = ros2_to_dds_type("invalid")
        assert result == "invalid"


class TestGetTypeHash:
    """Tests for type hash computation"""

    def test_compute_hash_with_definition(self):
        """Test computing hash with message definition"""
        hash_val = get_type_hash("std_msgs/msg/String", msg_definition="string data\n")
        assert hash_val.startswith("RIHS01_")
        # RIHS01_ (7 chars) + 64 hex chars = 71 total
        assert len(hash_val) == 71
        # Verify it matches known hash
        assert hash_val == "RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18"

    def test_requires_definition(self):
        """Test that ValueError is raised when msg_definition is not provided"""
        with pytest.raises(ValueError, match="Message definition is required"):
            get_type_hash("unknown/msg/Type")

    def _get_message_file_path(self, msg_type: str) -> Path:
        """
        Get message file path from environment variable or message registry.

        Args:
            msg_type: ROS2 message type (e.g., "std_msgs/msg/String")

        Returns:
            Path to message file or None if not found
        """
        # Try environment variable first
        common_interfaces_path = os.getenv("COMMON_INTERFACES_PATH")
        if common_interfaces_path:
            parts = msg_type.split("/")
            if len(parts) == 3:
                namespace, msg, message_name = parts
                msg_path = Path(common_interfaces_path) / namespace / msg / f"{message_name}.msg"
                if msg_path.exists():
                    return msg_path

        # Try message registry as fallback
        try:
            registry = get_registry()
            msg_file = registry.get_msg_file_path(msg_type)
            if msg_file and Path(msg_file).exists():
                return Path(msg_file)
        except Exception:
            pass

        return None

    def test_string_hash_validation(self):
        """Test std_msgs/msg/String type hash validation against known ROS2 hash"""
        expected_hash = "RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18"

        # Get message file path
        string_msg_path = self._get_message_file_path("std_msgs/msg/String")
        if not string_msg_path or not string_msg_path.exists():
            pytest.skip("String.msg not found. Set COMMON_INTERFACES_PATH or ensure message registry is configured")

        with open(string_msg_path, 'r') as f:
            msg_def = f.read()

        computed_hash = compute_type_hash_from_msg("std_msgs/msg/String", msg_def)
        assert computed_hash == expected_hash, f"Hash mismatch! Expected: {expected_hash}, Computed: {computed_hash}"

    def test_twist_hash_validation(self):
        """Test geometry_msgs/msg/Twist type hash validation with dependencies"""
        expected_hash = "RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a"

        # Get message file paths
        twist_msg_path = self._get_message_file_path("geometry_msgs/msg/Twist")
        vector3_msg_path = self._get_message_file_path("geometry_msgs/msg/Vector3")

        if not twist_msg_path or not twist_msg_path.exists():
            pytest.skip("Twist.msg not found. Set COMMON_INTERFACES_PATH or ensure message registry is configured")
        if not vector3_msg_path or not vector3_msg_path.exists():
            pytest.skip("Vector3.msg not found. Set COMMON_INTERFACES_PATH or ensure message registry is configured")

        with open(twist_msg_path, 'r') as f:
            twist_def = f.read()
        with open(vector3_msg_path, 'r') as f:
            vector3_def = f.read()

        # Compute hash with Vector3 as dependency
        dependencies = {
            "geometry_msgs/msg/Vector3": vector3_def
        }

        computed_hash = compute_type_hash_from_msg(
            "geometry_msgs/msg/Twist",
            twist_def,
            dependencies=dependencies
        )
        assert computed_hash == expected_hash, f"Hash mismatch! Expected: {expected_hash}, Computed: {computed_hash}"


class TestMangleName:
    """Tests for name mangling"""

    def test_simple_topic(self):
        """Test mangling simple topic name"""
        assert mangle_name("/chatter") == "%chatter"

    def test_nested_topic(self):
        """Test mangling nested topic name"""
        assert mangle_name("/robot/sensor/data") == "%robot%sensor%data"

    def test_root_topic(self):
        """Test mangling root topic"""
        assert mangle_name("/") == "%"

    def test_empty_name(self):
        """Test mangling empty name"""
        assert mangle_name("") == "%"

    def test_no_slash(self):
        """Test mangling name without slashes"""
        assert mangle_name("chatter") == "chatter"


class TestServiceTypeHash:
    """Tests for service type hash computation"""

    def test_compute_service_type_hash_add_two_ints(self):
        """Test computing hash for example_interfaces/srv/AddTwoInts"""
        request_def = "int64 a\nint64 b"
        response_def = "int64 sum"

        computed_hash = compute_service_type_hash(
            "example_interfaces/srv/AddTwoInts",
            request_definition=request_def,
            response_definition=response_def
        )

        # Expected hash for example_interfaces/srv/AddTwoInts
        expected_hash = "RIHS01_e118de6bf5eeb66a2491b5bda11202e7b68f198d6f67922cf30364858239c81a"

        assert computed_hash == expected_hash, \
            f"Service hash mismatch! Expected: {expected_hash}, Computed: {computed_hash}"
        assert computed_hash.startswith("RIHS01_")
        assert len(computed_hash) == 71  # RIHS01_ + 64 hex chars

    def test_compute_service_type_hash_invalid_format(self):
        """Test that invalid service type format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid service type format"):
            compute_service_type_hash(
                "invalid_format",
                request_definition="int64 a",
                response_definition="int64 b"
            )

    def test_compute_service_type_hash_missing_definitions(self):
        """Test that missing definitions raise ValueError"""
        with pytest.raises(ValueError):
            compute_service_type_hash(
                "example_interfaces/srv/AddTwoInts",
                request_definition="",
                response_definition="int64 sum"
            )
        
        with pytest.raises(ValueError):
            compute_service_type_hash(
                "example_interfaces/srv/AddTwoInts",
                request_definition="int64 a",
                response_definition=""
            )

    def test_compute_service_type_hash_with_dependencies(self):
        """Test computing service hash with dependencies"""
        # This test verifies that dependencies are properly included
        request_def = "int64 a\nint64 b"
        response_def = "int64 sum"

        # Even with empty dependencies, hash should be computed
        computed_hash = compute_service_type_hash(
            "example_interfaces/srv/AddTwoInts",
            request_definition=request_def,
            response_definition=response_def,
            dependencies={}
        )

        # Should still match expected hash
        expected_hash = "RIHS01_e118de6bf5eeb66a2491b5bda11202e7b68f198d6f67922cf30364858239c81a"
        assert computed_hash == expected_hash
