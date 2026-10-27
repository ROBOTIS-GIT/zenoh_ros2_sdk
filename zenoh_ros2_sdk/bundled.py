"""Offline standard telemetry definitions, available without opening a session."""
from pathlib import Path
import re
from typing import Dict, Optional

_ROOT = Path(__file__).with_name("bundled_messages")


def get_bundled_message_path(msg_type: str) -> Optional[Path]:
    """Return a packaged .msg path, or None for an unsupported/invalid type."""
    if not re.fullmatch(r"[A-Za-z_]\w*/msg/[A-Za-z_]\w*", msg_type):
        return None
    path = _ROOT / (msg_type + ".msg")
    return path if path.is_file() else None


def get_bundled_message_definitions() -> Dict[str, str]:
    """Return the bundled types and complete transitive payload dependencies.

    Keys use package/msg/Type names; values retain the upstream ROS Jazzy .msg
    definitions. This performs local file reads only: no Zenoh session, ROS
    installation, Git checkout, network request, or registry mutation is needed.
    Returned dictionaries are independent and can be passed to a codec/catalog.
    For type hashes, use utils.get_type_hash(name, definition, dependencies).
    """
    return {
        "/".join(path.relative_to(_ROOT).with_suffix("").parts): path.read_text()
        for path in sorted(_ROOT.glob("*/msg/*.msg"))
    }
