"""
Entity models aligned with rmw_zenoh_cpp / ros-z concepts.

This module intentionally keeps *formatting* and *keyexpr construction* out of the
publisher/subscriber implementations so that:
- all liveliness tokens are consistent (NN/MP/MS/SS/SC)
- all topic/service key expressions are constructed in one place
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EntityKind(str, Enum):
    """Matches rmw_zenoh_cpp / ros-z entity kind strings."""

    NODE = "NN"
    PUBLISHER = "MP"
    SUBSCRIPTION = "MS"
    SERVICE = "SS"
    CLIENT = "SC"


@dataclass(frozen=True, slots=True)
class NodeEntity:
    domain_id: int
    session_id: str  # Zenoh session zid string
    node_id: int
    node_name: str
    namespace: str = "/"
    enclave: str = "%"  # SROS enclave (not fully supported; keep placeholder)


@dataclass(frozen=True, slots=True)
class EndpointEntity:
    """
    Represents a ROS graph endpoint (pub/sub/service/client) attached to a node.

    - For topics: `name` is the ROS topic name (e.g. "/chatter")
    - For services: `name` is the ROS service name (e.g. "/add_two_ints")
    """

    node: NodeEntity
    entity_id: int
    kind: EntityKind
    name: str
    dds_type_name: str
    type_hash: str
    qos: str
    gid: Optional[bytes] = None

