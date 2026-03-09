"""
Tests for topic discovery (get_topic_names_and_types, get_topic_info).

Tests parsing of liveliness key expressions without a live Zenoh session.
"""

import pytest
from zenoh_ros2_sdk.discovery import _parse_liveliness_keyexpr
from zenoh_ros2_sdk.entity import EntityKind


class TestParseLivelinessKeyexpr:
    """Test parsing of @ros2_lv/... liveliness key expressions."""

    def test_parse_publisher_token(self):
        # Format: @ros2_lv/domain/session/node_id/entity_id/kind/enclave/namespace/node_name/qualified_name/dds_type/type_hash/qos
        key = (
            "@ros2_lv/0/0x1234/1/2/MP/%/%/my_pub_node/%chatter/"
            "std_msgs::msg::dds_::String_/abc123/::,10:,:,:,,"
        )
        parsed = _parse_liveliness_keyexpr(key)
        assert parsed is not None
        assert parsed["domain_id"] == 0
        assert parsed["session_id"] == "0x1234"
        assert parsed["node_id"] == 1
        assert parsed["entity_id"] == 2
        assert parsed["kind"] == EntityKind.PUBLISHER.value
        assert parsed["qualified_name"] == "/chatter"
        assert parsed["dds_type"] == "std_msgs::msg::dds_::String_"
        assert parsed["type_hash"] == "abc123"
        assert parsed["node_name"] == "my_pub_node"

    def test_parse_subscriber_token(self):
        key = (
            "@ros2_lv/0/sid/2/3/MS/%/%/sub_node/%cmd_vel/"
            "geometry_msgs::msg::dds_::Twist_/hash456/::,10:,:,:,,"
        )
        parsed = _parse_liveliness_keyexpr(key)
        assert parsed is not None
        assert parsed["kind"] == EntityKind.SUBSCRIPTION.value
        assert parsed["qualified_name"] == "/cmd_vel"
        assert parsed["dds_type"] == "geometry_msgs::msg::dds_::Twist_"
        assert parsed["node_name"] == "sub_node"

    def test_invalid_prefix_returns_none(self):
        assert _parse_liveliness_keyexpr("other/0/1/2/3/MP/%/%/n/%t/a/b/c") is None

    def test_service_kind_parsed(self):
        # Services now use SS (server) / SC (client) kinds for discovery
        key = "@ros2_lv/0/0/1/1/SS/%/%/node/%add_two_ints/example_interfaces::srv::dds_::AddTwoInts_/h/q"
        parsed = _parse_liveliness_keyexpr(key)
        assert parsed is not None
        assert parsed["kind"] == EntityKind.SERVICE.value
        assert parsed["qualified_name"] == "/add_two_ints"
        assert parsed["dds_type"] == "example_interfaces::srv::dds_::AddTwoInts_"

    def test_too_few_parts_returns_none(self):
        assert _parse_liveliness_keyexpr("@ros2_lv/0/1/2") is None
