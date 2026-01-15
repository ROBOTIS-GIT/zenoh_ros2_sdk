"""
Unit tests for key expression builders.
"""

from zenoh_ros2_sdk.keyexpr import topic_keyexpr, node_liveliness_keyexpr, endpoint_liveliness_keyexpr
from zenoh_ros2_sdk.entity import NodeEntity, EndpointEntity, EntityKind


def test_topic_keyexpr_format():
    assert (
        topic_keyexpr(30, "/chatter", "std_msgs::msg::dds_::String_", "RIHS01_deadbeef")
        == "30/chatter/std_msgs::msg::dds_::String_/RIHS01_deadbeef"
    )


def test_node_liveliness_keyexpr_mangles():
    node = NodeEntity(
        domain_id=30,
        session_id="abcd",
        node_id=1,
        node_name="my_node",
        namespace="/ns",
        enclave="%",
    )
    assert node_liveliness_keyexpr(node) == "@ros2_lv/30/abcd/1/1/NN/%/%ns/my_node"


def test_endpoint_liveliness_keyexpr_format():
    node = NodeEntity(domain_id=0, session_id="zid", node_id=0, node_name="n", namespace="/", enclave="%")
    ep = EndpointEntity(
        node=node,
        entity_id=7,
        kind=EntityKind.PUBLISHER,
        name="/cmd_vel",
        dds_type_name="geometry_msgs::msg::dds_::Twist_",
        type_hash="RIHS01_hash",
        qos="::,10:,:,:,," ,
        gid=None,
    )
    assert endpoint_liveliness_keyexpr(ep).startswith("@ros2_lv/0/zid/0/7/MP/%/%/n/")
    assert "/%cmd_vel/geometry_msgs::msg::dds_::Twist_/RIHS01_hash/::,10:,:,:,," in endpoint_liveliness_keyexpr(ep)

