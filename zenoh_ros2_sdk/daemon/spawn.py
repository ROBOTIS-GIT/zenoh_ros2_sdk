"""
Spawn the zenoh-ros2 daemon as a subprocess and wait until it is ready.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Optional

from . import get_domain_id
from .client import is_daemon_running


def spawn_daemon(
    domain_id: Optional[int] = None,
    timeout: float = 10.0,
    debug: bool = False,
) -> bool:
    """
    Start the daemon as a subprocess. Wait until GET /health returns 200 or timeout.
    If the process exits before health succeeds (e.g. EADDRINUSE), treat as "already running"
    and return False.

    Returns:
        True if daemon was started and is responding; False if we assume it was already running
        (port in use or process exited immediately).
    """
    if domain_id is None:
        domain_id = get_domain_id()
    cmd = [sys.executable, "-m", "zenoh_ros2_sdk.daemon", "--timeout", "7200"]
    if debug:
        cmd.append("--debug")  # if we add that flag later
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL if not debug else None,
            stderr=subprocess.DEVNULL if not debug else None,
            env=None,  # inherit ROS_DOMAIN_ID
            start_new_session=True,
        )
    except Exception:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            # Exited (e.g. EADDRINUSE) -> already running
            return False
        if is_daemon_running(domain_id):
            return True
        time.sleep(0.05)
    proc.kill()
    proc.wait()
    return False
