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
