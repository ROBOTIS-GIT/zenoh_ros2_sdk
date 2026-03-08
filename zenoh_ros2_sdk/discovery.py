"""
Topic discovery via Zenoh liveliness (ros2 topic list / ros2 topic info -v).

Uses the same @ros2_lv/... token format as rmw_zenoh_cpp / ros-z. Queries
liveliness for MP (publisher) and MS (subscriber) tokens to list topics and
optionally show verbose endpoint info.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .keyexpr import ADMIN_SPACE
from .entity import EntityKind
from .session import ZenohSession
from .utils import demangle_name, demangle_name_optional_leading_slash, dds_to_ros_type, resolve_domain_id
from .logger import get_logger

logger = get_logger("discovery")


# Liveliness keyexpr format (see keyexpr.endpoint_liveliness_keyexpr):
# @ros2_lv/<domain_id>/<session_id>/<node_id>/<entity_id>/<kind>/<enclave>/<namespace>/<node_name>/
# <qualified_name>/<dds_type_name>/<type_hash>/<qos>
_IDX_DOMAIN = 1
_IDX_SESSION = 2
_IDX_NODE_ID = 3
_IDX_ENTITY_ID = 4
_IDX_KIND = 5
_IDX_ENCLAVE = 6
_IDX_NAMESPACE = 7
_IDX_NODE_NAME = 8
_IDX_QUALIFIED_NAME = 9
_IDX_DDS_TYPE = 10
_IDX_TYPE_HASH = 11
_IDX_QOS = 12
_MIN_PARTS = 13


@dataclass
class TopicEndpointInfo:
    """Verbose info for one publisher or subscriber (ros2 topic info -v)."""

    node_name: str
    node_namespace: str
    topic_type: str
    type_hash: str
    qos: str
    gid: Optional[str] = None  # optional; not always in token


def _parse_liveliness_keyexpr(key_expr: str) -> Optional[dict]:
    """Parse a liveliness key expression into a dict. Returns None if format is invalid."""
    parts = str(key_expr).split("/")
    if len(parts) < _MIN_PARTS or parts[0] != ADMIN_SPACE:
        return None
    kind = parts[_IDX_KIND]
    if kind not in (
        EntityKind.PUBLISHER.value,
        EntityKind.SUBSCRIPTION.value,
        EntityKind.SERVICE.value,
        EntityKind.CLIENT.value,
    ):
        return None
    try:
        return {
            "domain_id": int(parts[_IDX_DOMAIN]),
            "session_id": parts[_IDX_SESSION],
            "node_id": int(parts[_IDX_NODE_ID]),
            "entity_id": int(parts[_IDX_ENTITY_ID]),
            "kind": kind,
            "enclave": parts[_IDX_ENCLAVE],
            "namespace": demangle_name_optional_leading_slash(parts[_IDX_NAMESPACE]),
            "node_name": demangle_name_optional_leading_slash(parts[_IDX_NODE_NAME]),
            "qualified_name": demangle_name(parts[_IDX_QUALIFIED_NAME]),
            "dds_type": parts[_IDX_DDS_TYPE],
            "type_hash": parts[_IDX_TYPE_HASH],
            "qos": parts[_IDX_QOS] if len(parts) > _IDX_QOS else "",
        }
    except (ValueError, IndexError):
        return None


def _query_liveliness(
    session: ZenohSession,
    domain_id: int,
    kind: str,
    timeout: float = 0.5,
) -> List[dict]:
    """Query liveliness for all endpoints of a given kind (MP or MS) in a domain."""
    # Pattern must match full keyexpr (rmw_zenoh design.md): 13 segments for endpoint tokens.
    # A single trailing * only matches one segment; use ** to match remaining segments.
    pattern = f"{ADMIN_SPACE}/{domain_id}/*/*/*/{kind}/**"
    results = []
    try:
        for reply in session.liveliness.get(pattern, timeout=timeout):
            if reply.ok is None:
                continue
            parsed = _parse_liveliness_keyexpr(str(reply.ok.key_expr))
            if parsed is not None:
                results.append(parsed)
    except Exception as e:
        logger.warning("Liveliness query failed for %s: %s", pattern, e)
    return results


def get_topic_names_and_types(
    domain_id: Optional[int] = None,
    router_ip: str = "127.0.0.1",
    router_port: int = 7447,
    timeout: float = 0.5,
    include_hidden_topics: bool = False,
) -> List[Tuple[str, List[str]]]:
    """
    List all topics and their types (ros2 topic list --show-types).

    Discovers topics by querying Zenoh liveliness for MP and MS tokens in the
    given domain. Returns a list of (topic_name, [type1, type2, ...]) with
    types in ROS2 form (e.g. std_msgs/msg/String).

    Args:
        domain_id: ROS domain ID (defaults to ROS_DOMAIN_ID or 0).
        router_ip: Zenoh router IP.
        router_port: Zenoh router port.
        timeout: Liveliness query timeout in seconds (default 0.5, same as ros2cli --spin-time).
        include_hidden_topics: If True, include hidden topics (names starting with /_).
            Default False to match ros2 topic list behavior.

    Returns:
        List of (topic_name, list of type strings), sorted by topic name.
    """
    domain_id = resolve_domain_id(domain_id)
    session = ZenohSession.get_instance(router_ip, router_port)

    # Collect (topic, type) from publishers and subscribers
    topic_types: dict[str, set[str]] = {}

    for kind in (EntityKind.PUBLISHER.value, EntityKind.SUBSCRIPTION.value):
        for parsed in _query_liveliness(session, domain_id, kind, timeout):
            name = parsed["qualified_name"]
            if not name or name == "/":
                continue
            if not include_hidden_topics and name.startswith("/_"):
                continue
            ros_type = dds_to_ros_type(parsed["dds_type"])
            topic_types.setdefault(name, set()).add(ros_type)

    out = [(topic, sorted(types)) for topic, types in sorted(topic_types.items())]
    return out


@dataclass
class TopicInfo:
    """Result of get_topic_info (ros2 topic info)."""

    topic_name: str
    topic_types: List[str]
    publisher_count: int
    subscriber_count: int
    publishers: List[TopicEndpointInfo] = field(default_factory=list)
    subscribers: List[TopicEndpointInfo] = field(default_factory=list)


def get_topic_info(
    topic_name: str,
    domain_id: Optional[int] = None,
    router_ip: str = "127.0.0.1",
    router_port: int = 7447,
    timeout: float = 0.5,
    verbose: bool = False,
) -> Optional[TopicInfo]:
    """
    Get info for a single topic (ros2 topic info [--verbose] <topic>).

    Args:
        topic_name: ROS topic name (e.g. /chatter).
        domain_id: ROS domain ID (defaults to ROS_DOMAIN_ID or 0).
        router_ip: Zenoh router IP.
        router_port: Zenoh router port.
        timeout: Liveliness query timeout in seconds (default 0.5, same as ros2cli --spin-time).
        verbose: If True, include publisher/subscriber details (node name, namespace, type, qos).

    Returns:
        TopicInfo or None if the topic is not found.
    """
    domain_id = resolve_domain_id(domain_id)
    session = ZenohSession.get_instance(router_ip, router_port)

    # Normalize topic for comparison: ensure leading /
    topic_normalized = topic_name if topic_name.startswith("/") else "/" + topic_name

    publishers: List[TopicEndpointInfo] = []
    subscribers: List[TopicEndpointInfo] = []
    types_seen: set[str] = set()
    pub_count = 0
    sub_count = 0

    for kind in (EntityKind.PUBLISHER.value, EntityKind.SUBSCRIPTION.value):
        for parsed in _query_liveliness(session, domain_id, kind, timeout):
            name = parsed["qualified_name"]
            if not name or name == "/":
                continue
            name_norm = name if name.startswith("/") else "/" + name
            if name_norm != topic_normalized:
                continue
            ros_type = dds_to_ros_type(parsed["dds_type"])
            types_seen.add(ros_type)
            if kind == EntityKind.PUBLISHER.value:
                pub_count += 1
                if verbose:
                    publishers.append(
                        TopicEndpointInfo(
                            node_name=parsed["node_name"],
                            node_namespace=parsed["namespace"],
                            topic_type=ros_type,
                            type_hash=parsed["type_hash"],
                            qos=parsed["qos"],
                        )
                    )
            else:
                sub_count += 1
                if verbose:
                    subscribers.append(
                        TopicEndpointInfo(
                            node_name=parsed["node_name"],
                            node_namespace=parsed["namespace"],
                            topic_type=ros_type,
                            type_hash=parsed["type_hash"],
                            qos=parsed["qos"],
                        )
                    )

    if not types_seen and pub_count == 0 and sub_count == 0:
        return None

    return TopicInfo(
        topic_name=topic_normalized,
        topic_types=sorted(types_seen),
        publisher_count=pub_count,
        subscriber_count=sub_count,
        publishers=publishers,
        subscribers=subscribers,
    )


@dataclass
class ServiceEndpointInfo:
    """Verbose info for one service server or client (ros2 service-style verbose info)."""

    node_name: str
    node_namespace: str
    service_type: str
    type_hash: str
    qos: str
    gid: Optional[str] = None  # optional; not always in token


@dataclass
class ServiceInfo:
    """Result of get_service_info (service discovery info)."""

    service_name: str
    service_types: List[str]
    server_count: int
    client_count: int
    servers: List[ServiceEndpointInfo] = field(default_factory=list)
    clients: List[ServiceEndpointInfo] = field(default_factory=list)


def get_service_names_and_types(
    domain_id: Optional[int] = None,
    router_ip: str = "127.0.0.1",
    router_port: int = 7447,
    timeout: float = 0.5,
    include_hidden_services: bool = False,
) -> List[Tuple[str, List[str]]]:
    """
    List all services and their types (like `ros2 service list` / `ros2 service list -t`).

    Discovers services by querying Zenoh liveliness for SS (service server) and SC
    (service client) tokens in the given domain. Returns a list of
    (service_name, [type1, type2, ...]) with types in ROS 2 form
    (e.g. example_interfaces/srv/AddTwoInts).
    """
    domain_id = resolve_domain_id(domain_id)
    session = ZenohSession.get_instance(router_ip, router_port)

    service_types: dict[str, set[str]] = {}

    for kind in (EntityKind.SERVICE.value, EntityKind.CLIENT.value):
        for parsed in _query_liveliness(session, domain_id, kind, timeout):
            name = parsed["qualified_name"]
            if not name or name == "/":
                continue
            if not include_hidden_services and name.startswith("/_"):
                continue
            ros_type = dds_to_ros_type(parsed["dds_type"])
            service_types.setdefault(name, set()).add(ros_type)

    return [(svc, sorted(types)) for svc, types in sorted(service_types.items())]


def get_service_info(
    service_name: str,
    domain_id: Optional[int] = None,
    router_ip: str = "127.0.0.1",
    router_port: int = 7447,
    timeout: float = 0.5,
    verbose: bool = False,
) -> Optional[ServiceInfo]:
    """
    Get info for a single service (discovery-only; server/client counts and types).
    """
    domain_id = resolve_domain_id(domain_id)
    session = ZenohSession.get_instance(router_ip, router_port)

    # Normalize service name: ensure leading /
    service_normalized = service_name if service_name.startswith("/") else "/" + service_name

    servers: List[ServiceEndpointInfo] = []
    clients: List[ServiceEndpointInfo] = []
    types_seen: set[str] = set()
    server_count = 0
    client_count = 0

    for kind in (EntityKind.SERVICE.value, EntityKind.CLIENT.value):
        for parsed in _query_liveliness(session, domain_id, kind, timeout):
            name = parsed["qualified_name"]
            if not name or name == "/":
                continue
            name_norm = name if name.startswith("/") else "/" + name
            if name_norm != service_normalized:
                continue
            ros_type = dds_to_ros_type(parsed["dds_type"])
            types_seen.add(ros_type)
            endpoint = ServiceEndpointInfo(
                node_name=parsed["node_name"],
                node_namespace=parsed["namespace"],
                service_type=ros_type,
                type_hash=parsed["type_hash"],
                qos=parsed["qos"],
            )
            if kind == EntityKind.SERVICE.value:
                server_count += 1
                if verbose:
                    servers.append(endpoint)
            else:
                client_count += 1
                if verbose:
                    clients.append(endpoint)

    if not types_seen and server_count == 0 and client_count == 0:
        return None

    return ServiceInfo(
        service_name=service_normalized,
        service_types=sorted(types_seen),
        server_count=server_count,
        client_count=client_count,
        servers=servers,
        clients=clients,
    )

