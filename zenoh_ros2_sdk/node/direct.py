"""
Direct path: call discovery in-process; return same shapes as daemon JSON for unified formatting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from zenoh_ros2_sdk import (
    get_topic_names_and_types,
    get_topic_info,
    get_service_names_and_types,
    get_service_info,
)
from zenoh_ros2_sdk.discovery import TopicInfo, ServiceInfo


def _topic_info_to_dict(info: TopicInfo) -> dict:
    """Convert TopicInfo to same dict shape as daemon JSON."""
    return {
        "topic_name": info.topic_name,
        "topic_types": info.topic_types,
        "publisher_count": info.publisher_count,
        "subscriber_count": info.subscriber_count,
        "publishers": [
            {
                "node_name": p.node_name,
                "node_namespace": p.node_namespace,
                "topic_type": p.topic_type,
                "type_hash": p.type_hash,
                "qos": p.qos,
            }
            for p in info.publishers
        ],
        "subscribers": [
            {
                "node_name": s.node_name,
                "node_namespace": s.node_namespace,
                "topic_type": s.topic_type,
                "type_hash": s.type_hash,
                "qos": s.qos,
            }
            for s in info.subscribers
        ],
    }


def _service_info_to_dict(info: ServiceInfo) -> dict:
    """Convert ServiceInfo to same dict shape as daemon JSON."""
    return {
        "service_name": info.service_name,
        "service_types": info.service_types,
        "server_count": info.server_count,
        "client_count": info.client_count,
        "servers": [
            {
                "node_name": s.node_name,
                "node_namespace": s.node_namespace,
                "service_type": s.service_type,
                "type_hash": s.type_hash,
                "qos": s.qos,
            }
            for s in info.servers
        ],
        "clients": [
            {
                "node_name": c.node_name,
                "node_namespace": c.node_namespace,
                "service_type": c.service_type,
                "type_hash": c.type_hash,
                "qos": c.qos,
            }
            for c in info.clients
        ],
    }


class DirectNode:
    """
    In-process discovery: no daemon. Return shapes match daemon client so topic_cli can format once.
    """

    def __init__(
        self,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
    ):
        self.router_ip = router_ip
        self.router_port = router_port

    def get_topic_names_and_types(
        self,
        domain_id: Optional[int] = None,
        timeout: float = 0.5,
        include_hidden_topics: bool = False,
    ) -> List[Tuple[str, List[str]]]:
        """Same shape as daemon: list of (topic_name, [type1, type2, ...])."""
        return get_topic_names_and_types(
            domain_id=domain_id,
            router_ip=self.router_ip,
            router_port=self.router_port,
            timeout=timeout,
            include_hidden_topics=include_hidden_topics,
        )

    def get_topic_info(
        self,
        topic_name: str,
        domain_id: Optional[int] = None,
        timeout: float = 0.5,
        verbose: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Same shape as daemon: dict or None if not found."""
        info = get_topic_info(
            topic_name,
            domain_id=domain_id,
            router_ip=self.router_ip,
            router_port=self.router_port,
            timeout=timeout,
            verbose=verbose,
        )
        if info is None:
            return None
        return _topic_info_to_dict(info)

    def get_service_names_and_types(
        self,
        domain_id: Optional[int] = None,
        timeout: float = 0.5,
        include_hidden_services: bool = False,
    ) -> List[Tuple[str, List[str]]]:
        """Same shape as daemon: list of (service_name, [type1, type2, ...])."""
        return get_service_names_and_types(
            domain_id=domain_id,
            router_ip=self.router_ip,
            router_port=self.router_port,
            timeout=timeout,
            include_hidden_services=include_hidden_services,
        )

    def get_service_info(
        self,
        service_name: str,
        domain_id: Optional[int] = None,
        timeout: float = 0.5,
        verbose: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Same shape as daemon: dict or None if not found."""
        info = get_service_info(
            service_name,
            domain_id=domain_id,
            router_ip=self.router_ip,
            router_port=self.router_port,
            timeout=timeout,
            verbose=verbose,
        )
        if info is None:
            return None
        return _service_info_to_dict(info)
