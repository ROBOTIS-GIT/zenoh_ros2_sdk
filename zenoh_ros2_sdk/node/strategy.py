"""
Strategy: use daemon client when available and router is default; else direct (with optional spawn).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from zenoh_ros2_sdk.daemon.client import (
    get_topic_list as daemon_get_topic_list,
    get_topic_info as daemon_get_topic_info,
    get_service_list as daemon_get_service_list,
    get_service_info as daemon_get_service_info,
    is_daemon_running,
)
from zenoh_ros2_sdk.daemon.spawn import spawn_daemon
from zenoh_ros2_sdk.node.direct import DirectNode

# Default router the daemon uses
DEFAULT_ROUTER_IP = "127.0.0.1"
DEFAULT_ROUTER_PORT = 7447


def _parse_router(router: str) -> Tuple[str, int]:
    if ":" in router:
        host, port = router.rsplit(":", 1)
        return host.strip(), int(port.strip())
    return router.strip(), DEFAULT_ROUTER_PORT


def _is_default_router(router: str) -> bool:
    ip, port = _parse_router(router)
    return ip == DEFAULT_ROUTER_IP and port == DEFAULT_ROUTER_PORT


class NodeStrategy:
    """
    If not no_daemon and daemon is running and router is default: use daemon client.
    Else: optionally spawn daemon; if it comes up, use daemon client for this run (fast).
    Else: use DirectNode for this run (slow exit due to session close).
    """

    def __init__(
        self,
        router: str = "127.0.0.1:7447",
        domain_id: Optional[int] = None,
        no_daemon: bool = False,
        spawn_if_missing: bool = True,
    ):
        self.router = router
        self.domain_id = domain_id
        self.no_daemon = no_daemon
        self.spawn_if_missing = spawn_if_missing
        self._direct: Optional[DirectNode] = None
        self._use_daemon: Optional[bool] = None

    def _resolve(self) -> bool:
        """True = use daemon client, False = use DirectNode."""
        if self._use_daemon is not None:
            return self._use_daemon
        if self.no_daemon or not _is_default_router(self.router):
            self._use_daemon = False
            self._direct = DirectNode(*_parse_router(self.router))
            return False
        if is_daemon_running(self.domain_id):
            self._use_daemon = True
            return True
        if self.spawn_if_missing:
            if spawn_daemon(domain_id=self.domain_id):
                # Daemon is up; use it for this run too so CLI exits fast (no session close)
                self._use_daemon = True
                return True
        self._use_daemon = False
        self._direct = DirectNode(*_parse_router(self.router))
        return False

    def _get_direct(self) -> DirectNode:
        if self._direct is None:
            self._resolve()
        assert self._direct is not None
        return self._direct

    def get_topic_names_and_types(
        self,
        timeout: float = 0.5,
        include_hidden_topics: bool = False,
    ) -> List[Tuple[str, List[str]]]:
        """Unified: list of (topic_name, [type1, type2, ...])."""
        if self._resolve():
            return daemon_get_topic_list(
                domain_id=self.domain_id,
                timeout=timeout,
                include_hidden=include_hidden_topics,
            )
        return self._get_direct().get_topic_names_and_types(
            domain_id=self.domain_id,
            timeout=timeout,
            include_hidden_topics=include_hidden_topics,
        )

    def get_topic_info(
        self,
        topic_name: str,
        timeout: float = 0.5,
        verbose: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Unified: dict or None if not found."""
        if self._resolve():
            return daemon_get_topic_info(
                topic_name,
                domain_id=self.domain_id,
                timeout=timeout,
                verbose=verbose,
            )
        return self._get_direct().get_topic_info(
            topic_name,
            domain_id=self.domain_id,
            timeout=timeout,
            verbose=verbose,
        )

    def get_service_names_and_types(
        self,
        timeout: float = 0.5,
        include_hidden_services: bool = False,
    ) -> List[Tuple[str, List[str]]]:
        """Unified service discovery: list of (service_name, [type1, type2, ...])."""
        if self._resolve():
            return daemon_get_service_list(
                domain_id=self.domain_id,
                timeout=timeout,
                include_hidden=include_hidden_services,
            )
        return self._get_direct().get_service_names_and_types(
            domain_id=self.domain_id,
            timeout=timeout,
            include_hidden_services=include_hidden_services,
        )

    def get_service_info(
        self,
        service_name: str,
        timeout: float = 0.5,
        verbose: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Unified: dict or None if service is not found."""
        if self._resolve():
            return daemon_get_service_info(
                service_name,
                domain_id=self.domain_id,
                timeout=timeout,
                verbose=verbose,
            )
        return self._get_direct().get_service_info(
            service_name,
            domain_id=self.domain_id,
            timeout=timeout,
            verbose=verbose,
        )
