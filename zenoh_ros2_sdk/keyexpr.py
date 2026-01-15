"""
Key expression builders aligned with rmw_zenoh_cpp design.md and ros-z implementation.
"""

from __future__ import annotations

from .entity import EndpointEntity, EntityKind, NodeEntity
from .utils import mangle_name


ADMIN_SPACE = "@ros2_lv"


def topic_keyexpr(domain_id: int, fully_qualified_name: str, dds_type_name: str, type_hash: str) -> str:
    """
    Data-plane key expression for topics/services.

    Format:
      <domain_id>/<fully_qualified_name>/<type_name>/<type_hash>
    """
    return f"{domain_id}/{fully_qualified_name.lstrip('/')}/{dds_type_name}/{type_hash}"


def node_liveliness_keyexpr(node: NodeEntity) -> str:
    """
    Liveliness token for a node.

    Format:
      @ros2_lv/<domain_id>/<session_id>/<node_id>/<node_id>/NN/<enclave>/<namespace>/<node_name>
    """
    namespace = mangle_name(node.namespace)
    name = mangle_name(node.node_name)
    enclave = node.enclave if node.enclave else "%"
    return (
        f"{ADMIN_SPACE}/{node.domain_id}/{node.session_id}/"
        f"{node.node_id}/{node.node_id}/{EntityKind.NODE.value}/"
        f"{enclave}/{namespace}/{name}"
    )


def endpoint_liveliness_keyexpr(ep: EndpointEntity) -> str:
    """
    Liveliness token for a publisher/subscriber/service/client.

    Format:
      @ros2_lv/<domain_id>/<session_id>/<node_id>/<entity_id>/<kind>/<enclave>/<namespace>/<node_name>/
      <mangled_qualified_name>/<type_name>/<type_hash>/<qos>
    """
    node = ep.node
    namespace = mangle_name(node.namespace)
    node_name = mangle_name(node.node_name)
    qualified_name = mangle_name(ep.name)
    enclave = node.enclave if node.enclave else "%"
    return (
        f"{ADMIN_SPACE}/{node.domain_id}/{node.session_id}/"
        f"{node.node_id}/{ep.entity_id}/{ep.kind.value}/"
        f"{enclave}/{namespace}/{node_name}/"
        f"{qualified_name}/{ep.dds_type_name}/{ep.type_hash}/{ep.qos}"
    )

