"""
zenoh-ros2 daemon: HTTP server holding one Zenoh session for fast topic list/info.

Port: 11620 + ROS_DOMAIN_ID (avoids ros2 daemon 11511+domain_id). Bind 127.0.0.1. Serves JSON over HTTP.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from zenoh_ros2_sdk import (
    ZenohSession,
    get_topic_info,
    get_topic_names_and_types,
    get_service_names_and_types,
    get_service_info,
)


def get_domain_id() -> int:
    """ROS domain ID from env or 0."""
    v = os.environ.get("ROS_DOMAIN_ID", "").strip()
    return int(v) if v else 0


def get_port(domain_id: Optional[int] = None) -> int:
    """Daemon port: 11620 + domain_id (avoids ros2 daemon 11511+domain_id)."""
    if domain_id is None:
        domain_id = get_domain_id()
    return 11620 + domain_id


def get_base_url(domain_id: Optional[int] = None) -> str:
    """Base URL for daemon (e.g. http://127.0.0.1:11620)."""
    return f"http://127.0.0.1:{get_port(domain_id)}"


# Default router for daemon (only one session)
DEFAULT_ROUTER_IP = "127.0.0.1"
DEFAULT_ROUTER_PORT = 7447


def _topic_info_to_dict(info) -> dict:
    """Convert TopicInfo to JSON-serializable dict."""
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


def _service_info_to_dict(info) -> dict:
    """Convert ServiceInfo to JSON-serializable dict."""
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


class DaemonHandler(BaseHTTPRequestHandler):
    """HTTP request handler for daemon routes."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass  # quiet by default

    def _parse_body(self) -> Optional[dict]:
        """Read JSON body for POST; return None if empty or invalid."""
        content_length = self.headers.get("Content-Length")
        if not content_length:
            return None
        try:
            n = int(content_length)
        except ValueError:
            return None
        if n <= 0:
            return None
        try:
            body = self.rfile.read(n).decode("utf-8")
            return json.loads(body) if body.strip() else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _send_json(self, data, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        payload = json.dumps(data).encode("utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_json(self, message: str, status: int = 400):
        self._send_json({"error": message}, status=status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query, keep_blank_values=True)
        if hasattr(self.server, "last_activity"):
            self.server.last_activity = time.time()

        def get_one(key: str, default=None):
            v = qs.get(key, [default])
            return v[0] if v else default

        if path == "/" or path == "/health":
            self._send_json({"status": "ok"})
            return

        if path == "/topic/list":
            domain_id = get_one("domain_id")
            domain_id = int(domain_id) if domain_id is not None else get_domain_id()
            timeout = get_one("timeout", "0.5")
            timeout = float(timeout) if timeout else 0.5
            include_hidden = get_one("include_hidden", "").lower() in ("1", "true", "yes")
            try:
                topics = get_topic_names_and_types(
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=timeout,
                    include_hidden_topics=include_hidden,
                )
                self._send_json({"topics": topics})
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        if path == "/topic/info":
            topic_name = get_one("topic_name")
            if not topic_name:
                self._send_error_json("topic_name required", status=400)
                return
            timeout = get_one("timeout", "0.5")
            timeout = float(timeout) if timeout else 0.5
            verbose = get_one("verbose", "").lower() in ("1", "true", "yes")
            domain_id = get_one("domain_id")
            domain_id = int(domain_id) if domain_id is not None else get_domain_id()
            try:
                info = get_topic_info(
                    topic_name,
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=timeout,
                    verbose=verbose,
                )
                if info is None:
                    self._send_json(None)
                else:
                    self._send_json(_topic_info_to_dict(info))
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        if path == "/service/list":
            domain_id = get_one("domain_id")
            domain_id = int(domain_id) if domain_id is not None else get_domain_id()
            timeout = get_one("timeout", "0.5")
            timeout = float(timeout) if timeout else 0.5
            include_hidden = get_one("include_hidden", "").lower() in ("1", "true", "yes")
            try:
                services = get_service_names_and_types(
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=timeout,
                    include_hidden_services=include_hidden,
                )
                self._send_json({"services": services})
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        if path == "/service/info":
            service_name = get_one("service_name")
            if not service_name:
                self._send_error_json("service_name required", status=400)
                return
            timeout = get_one("timeout", "0.5")
            timeout = float(timeout) if timeout else 0.5
            verbose = get_one("verbose", "").lower() in ("1", "true", "yes")
            domain_id = get_one("domain_id")
            domain_id = int(domain_id) if domain_id is not None else get_domain_id()
            try:
                info = get_service_info(
                    service_name,
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=timeout,
                    verbose=verbose,
                )
                if info is None:
                    self._send_json(None)
                else:
                    self._send_json(_service_info_to_dict(info))
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        self._send_error_json("Not Found", status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        body = self._parse_body() or {}
        if hasattr(self.server, "last_activity"):
            self.server.last_activity = time.time()

        if path == "/shutdown":
            self._send_json({"status": "ok"})
            self.server.shutdown_requested = True
            return

        if path == "/topic/list":
            domain_id = body.get("domain_id")
            if domain_id is None:
                domain_id = get_domain_id()
            timeout = body.get("timeout", 0.5)
            include_hidden = body.get("include_hidden", False)
            try:
                topics = get_topic_names_and_types(
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=float(timeout),
                    include_hidden_topics=bool(include_hidden),
                )
                self._send_json({"topics": topics})
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        if path == "/topic/info":
            topic_name = body.get("topic_name")
            if not topic_name:
                self._send_error_json("topic_name required", status=400)
                return
            timeout = body.get("timeout", 0.5)
            verbose = body.get("verbose", False)
            domain_id = body.get("domain_id")
            if domain_id is None:
                domain_id = get_domain_id()
            try:
                info = get_topic_info(
                    topic_name,
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=float(timeout),
                    verbose=bool(verbose),
                )
                if info is None:
                    self._send_json(None)
                else:
                    self._send_json(_topic_info_to_dict(info))
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        if path == "/service/list":
            domain_id = body.get("domain_id")
            if domain_id is None:
                domain_id = get_domain_id()
            timeout = body.get("timeout", 0.5)
            include_hidden = body.get("include_hidden", False)
            try:
                services = get_service_names_and_types(
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=float(timeout),
                    include_hidden_services=bool(include_hidden),
                )
                self._send_json({"services": services})
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        if path == "/service/info":
            service_name = body.get("service_name")
            if not service_name:
                self._send_error_json("service_name required", status=400)
                return
            timeout = body.get("timeout", 0.5)
            verbose = body.get("verbose", False)
            domain_id = body.get("domain_id")
            if domain_id is None:
                domain_id = get_domain_id()
            try:
                info = get_service_info(
                    service_name,
                    domain_id=domain_id,
                    router_ip=DEFAULT_ROUTER_IP,
                    router_port=DEFAULT_ROUTER_PORT,
                    timeout=float(timeout),
                    verbose=bool(verbose),
                )
                if info is None:
                    self._send_json(None)
                else:
                    self._send_json(_service_info_to_dict(info))
            except Exception as e:
                self._send_error_json(str(e), status=500)
            return

        self._send_error_json("Not Found", status=404)


def serve(
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    inactivity_timeout: int = 2 * 60 * 60,
) -> None:
    """
    Run the daemon HTTP server. Creates one ZenohSession (default router) and serves
    /health, /topic/list, /topic/info, /service/list, /service/info, /shutdown.
    """
    if port is None:
        port = get_port()
    # Create session once so it's warm for all requests
    ZenohSession.get_instance(DEFAULT_ROUTER_IP, DEFAULT_ROUTER_PORT)

    server = HTTPServer((host, port), DaemonHandler)
    server.shutdown_requested = False
    server.timeout = 0.2
    server.last_activity = time.time()

    def timeout_check():
        if inactivity_timeout > 0 and time.time() - server.last_activity > inactivity_timeout:
            return True
        return server.shutdown_requested

    try:
        while not server.shutdown_requested:
            server.handle_request()
            if timeout_check():
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="zenoh-ros2 daemon (HTTP + JSON)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=2 * 60 * 60,
        metavar="N",
        help="Shutdown after N seconds of inactivity (default: 2 hours)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port (default: 11512 + ROS_DOMAIN_ID)",
    )
    args = parser.parse_args(argv)

    port = args.port if args.port is not None else get_port()
    host = "127.0.0.1"

    try:
        serve(host=host, port=port, inactivity_timeout=args.timeout)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print("Daemon already running (port in use)", file=sys.stderr)
            return 1
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
