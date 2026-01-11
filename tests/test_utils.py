"""
Unit tests for utility functions
"""
import pytest
from zenoh_ros2_sdk.utils import ros2_to_dds_type, get_type_hash, mangle_name


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
    """Tests for type hash lookup"""
    
    def test_known_type(self):
        """Test getting hash for known type"""
        hash_val = get_type_hash("std_msgs/msg/String")
        assert hash_val.startswith("RIHS01_")
        # RIHS01_ (7 chars) + 64 hex chars = 71 total
        assert len(hash_val) == 71
    
    def test_unknown_type(self):
        """Test getting hash for unknown type (returns placeholder)"""
        hash_val = get_type_hash("unknown/msg/Type")
        assert hash_val.startswith("RIHS01_")
        assert hash_val == "RIHS01_0000000000000000000000000000000000000000000000000000000000000000"


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
