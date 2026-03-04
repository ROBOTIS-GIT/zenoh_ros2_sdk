"""
Node strategy: use daemon client when available, else direct discovery (or spawn then direct).
"""

from .direct import DirectNode
from .strategy import NodeStrategy

__all__ = ["DirectNode", "NodeStrategy"]
