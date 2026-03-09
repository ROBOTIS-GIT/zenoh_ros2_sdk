"""
Thin HTTP client for the zenoh-ros2 daemon (stdlib only).
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, Tuple
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import get_base_url, get_domain_id


def is_daemon_running(domain_id: Optional[int] = None) -> bool:
    """Return True if GET base_url/health returns 200."""
    base = get_base_url(domain_id)
    try:
        req = Request(f"{base}/health", method="GET")
        with urlopen(req, timeout=2) as r:
            return r.getcode() == 200
    except (URLError, OSError, ValueError):
        return False


def get_topic_list(
    domain_id: Optional[int] = None,
    timeout: float = 0.5,
    include_hidden: bool = False,
) -> List[Tuple[str, List[str]]]:
    """
    GET /topic/list from daemon. Returns list of (topic_name, [type1, type2, ...]).
    Raises on connection error or non-2xx.
    """
    if domain_id is None:
        domain_id = get_domain_id()
    base = get_base_url(domain_id)
    url = f"{base}/topic/list?domain_id={domain_id}&timeout={timeout}&include_hidden={'true' if include_hidden else 'false'}"
    req = Request(url, method="GET")
    with urlopen(req, timeout=max(3, timeout + 2)) as r:
        if r.getcode() != 200:
            raise RuntimeError(f"Daemon returned {r.getcode()}")
        data = json.loads(r.read().decode("utf-8"))
    return data.get("topics", [])


def get_topic_info(
    topic_name: str,
    domain_id: Optional[int] = None,
    timeout: float = 0.5,
    verbose: bool = False,
) -> Optional[dict]:
    """
    GET /topic/info from daemon. Returns dict or None if topic not found.
    Raises on connection error or non-2xx (except 200 with null body).
    """
    if domain_id is None:
        domain_id = get_domain_id()
    base = get_base_url(domain_id)
    url = f"{base}/topic/info?topic_name={quote(topic_name, safe='/')}&domain_id={domain_id}&timeout={timeout}&verbose={'true' if verbose else 'false'}"
    req = Request(url, method="GET")
    with urlopen(req, timeout=max(3, timeout + 2)) as r:
        if r.getcode() != 200:
            raise RuntimeError(f"Daemon returned {r.getcode()}")
        raw = r.read().decode("utf-8")
        data = json.loads(raw)
    return data


def get_service_list(
    domain_id: Optional[int] = None,
    timeout: float = 0.5,
    include_hidden: bool = False,
) -> List[Tuple[str, List[str]]]:
    """
    GET /service/list from daemon. Returns list of (service_name, [type1, type2, ...]).
    Raises on connection error or non-2xx.
    """
    if domain_id is None:
        domain_id = get_domain_id()
    base = get_base_url(domain_id)
    url = (
        f"{base}/service/list?domain_id={domain_id}"
        f"&timeout={timeout}"
        f"&include_hidden={'true' if include_hidden else 'false'}"
    )
    req = Request(url, method="GET")
    with urlopen(req, timeout=max(3, timeout + 2)) as r:
        if r.getcode() != 200:
            raise RuntimeError(f"Daemon returned {r.getcode()}")
        data = json.loads(r.read().decode("utf-8"))
    return data.get("services", [])


def get_service_info(
    service_name: str,
    domain_id: Optional[int] = None,
    timeout: float = 0.5,
    verbose: bool = False,
) -> Optional[dict]:
    """
    GET /service/info from daemon. Returns dict or None if service not found.
    Raises on connection error or non-2xx (except 200 with null body).
    """
    if domain_id is None:
        domain_id = get_domain_id()
    base = get_base_url(domain_id)
    url = (
        f"{base}/service/info?service_name={quote(service_name, safe='/')}"
        f"&domain_id={domain_id}&timeout={timeout}"
        f"&verbose={'true' if verbose else 'false'}"
    )
    req = Request(url, method="GET")
    with urlopen(req, timeout=max(3, timeout + 2)) as r:
        if r.getcode() != 200:
            raise RuntimeError(f"Daemon returned {r.getcode()}")
        raw = r.read().decode("utf-8")
        data = json.loads(raw)
    return data


def shutdown_daemon(domain_id: Optional[int] = None) -> None:
    """POST /shutdown. Does not wait for daemon process to exit."""
    base = get_base_url(domain_id)
    req = Request(f"{base}/shutdown", data=b"", method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=2) as r:
            r.read()
    except (URLError, OSError):
        pass  # daemon may already be shutting down
