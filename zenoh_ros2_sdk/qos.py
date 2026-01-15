"""
QoS model and encoding compatible with rmw_zenoh_cpp / ros-z.

rmw_zenoh encodes QoS into liveliness tokens as a compact string:

  <ReliabilityKind>:<DurabilityKind>:<HistoryKind>,<HistoryDepth>:
  <DeadlineSec,DeadlineNSec>:<LifespanSec,LifespanNSec>:<LivelinessKind,LivelinessSec,LivelinessNSec>

Empty fields mean "use default" (as in rmw_zenoh / ros-z).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class QosReliability(Enum):
    RELIABLE = 1
    BEST_EFFORT = 2


class QosDurability(Enum):
    TRANSIENT_LOCAL = 1
    VOLATILE = 2


class QosHistoryKind(Enum):
    KEEP_LAST = 1
    KEEP_ALL = 2


class QosLiveliness(Enum):
    AUTOMATIC = 1
    MANUAL_BY_NODE = 2
    MANUAL_BY_TOPIC = 3


@dataclass(frozen=True, slots=True)
class Duration:
    sec: int
    nsec: int


# Matches ros-z infinite duration (kept as a module-level constant; do not attach to frozen dataclass)
DURATION_INFINITE = Duration(sec=9223372036, nsec=854775807)


@dataclass(frozen=True, slots=True)
class QosProfile:
    """QoS profile compatible with rmw_zenoh / ros-z QoS token encoding.

    Notes:
        - This SDK primarily uses QoS to populate `@ros2_lv/.../<qos>` liveliness tokens.
        - Some QoS fields may not have a runtime effect unless the underlying Zenoh API supports it.
        - `encode()`/`decode()` implement the same compact format used by `rmw_zenoh_cpp` and `ros-z`.
    """
    reliability: QosReliability = QosReliability.RELIABLE
    durability: QosDurability = QosDurability.VOLATILE
    history_kind: QosHistoryKind = QosHistoryKind.KEEP_LAST
    history_depth: int = 10
    deadline: Duration = DURATION_INFINITE
    lifespan: Duration = DURATION_INFINITE
    liveliness: QosLiveliness = QosLiveliness.AUTOMATIC
    liveliness_lease_duration: Duration = DURATION_INFINITE

    def encode(self, *, default: Optional["QosProfile"] = None) -> str:
        """
        Encode into the rmw_zenoh QoS token format (compatible with ros-z).

        If `default` is provided, fields equal to `default` are elided (empty).
        """
        default = default or QosProfile()

        reliability = "" if self.reliability == default.reliability else str(self.reliability.value)
        durability = "" if self.durability == default.durability else str(self.durability.value)

        # History: <kind>,<depth>
        if self.history_kind == QosHistoryKind.KEEP_LAST:
            if (self.history_kind == default.history_kind) and (self.history_depth == default.history_depth):
                history = f",{self.history_depth}"
            elif self.history_kind == default.history_kind:
                history = f",{self.history_depth}"
            else:
                history = f"{self.history_kind.value},{self.history_depth}"
        else:
            # KEEP_ALL has no depth
            history = f"{self.history_kind.value},"

        def _encode_dur(d: Duration, d_default: Duration) -> str:
            if d == d_default:
                return ","
            return f"{d.sec},{d.nsec}"

        deadline = _encode_dur(self.deadline, default.deadline)
        lifespan = _encode_dur(self.lifespan, default.lifespan)

        if (self.liveliness == default.liveliness) and (self.liveliness_lease_duration == default.liveliness_lease_duration):
            liveliness = ",,"
        else:
            liveliness = f"{self.liveliness.value},{self.liveliness_lease_duration.sec},{self.liveliness_lease_duration.nsec}"

        return f"{reliability}:{durability}:{history}:{deadline}:{lifespan}:{liveliness}"

    @staticmethod
    def decode(encoded: str) -> "QosProfile":
        """
        Decode from the rmw_zenoh QoS token format.

        This is intentionally lenient and treats empty fields as defaults.
        """
        default = QosProfile()
        parts = (encoded or "").split(":")
        if len(parts) < 6:
            raise ValueError(f"Incomplete QoS string (expected 6 fields): {encoded!r}")

        def _rel(s: str) -> QosReliability:
            if s in ("", "0", "1"):
                return default.reliability
            if s == "2":
                return QosReliability.BEST_EFFORT
            raise ValueError(f"Invalid reliability: {s!r}")

        def _dur(s: str) -> QosDurability:
            if s in ("", "0", "2"):
                return default.durability
            if s == "1":
                return QosDurability.TRANSIENT_LOCAL
            raise ValueError(f"Invalid durability: {s!r}")

        def _history(s: str) -> Tuple[QosHistoryKind, int]:
            if s in ("", ","):
                return default.history_kind, default.history_depth
            kind_s, depth_s = (s.split(",", 1) + [""])[:2]
            # kind may be empty => default keep_last
            if kind_s in ("", "0", "1"):
                kind = QosHistoryKind.KEEP_LAST
                depth = int(depth_s) if depth_s != "" else default.history_depth
                return kind, depth
            if kind_s == "2":
                return QosHistoryKind.KEEP_ALL, 0
            raise ValueError(f"Invalid history: {s!r}")

        def _dur2(s: str, d_default: Duration) -> Duration:
            if s in ("", ","):
                return d_default
            sec_s, nsec_s = (s.split(",", 1) + [""])[:2]
            sec = int(sec_s) if sec_s != "" else d_default.sec
            nsec = int(nsec_s) if nsec_s != "" else d_default.nsec
            return Duration(sec=sec, nsec=nsec)

        def _liveliness(s: str) -> Tuple[QosLiveliness, Duration]:
            if s in ("", ",,"):
                return default.liveliness, default.liveliness_lease_duration
            kind_s, sec_s, nsec_s = (s.split(",", 2) + ["", ""])[:3]
            if kind_s in ("", "0", "1"):
                kind = QosLiveliness.AUTOMATIC
            elif kind_s == "2":
                kind = QosLiveliness.MANUAL_BY_NODE
            elif kind_s == "3":
                kind = QosLiveliness.MANUAL_BY_TOPIC
            else:
                kind = default.liveliness
            sec = int(sec_s) if sec_s != "" else default.liveliness_lease_duration.sec
            nsec = int(nsec_s) if nsec_s != "" else default.liveliness_lease_duration.nsec
            return kind, Duration(sec=sec, nsec=nsec)

        reliability = _rel(parts[0])
        durability = _dur(parts[1])
        history_kind, history_depth = _history(parts[2])
        deadline = _dur2(parts[3], default.deadline)
        lifespan = _dur2(parts[4], default.lifespan)
        liveliness, liveliness_lease_duration = _liveliness(parts[5])

        return QosProfile(
            reliability=reliability,
            durability=durability,
            history_kind=history_kind,
            history_depth=history_depth,
            deadline=deadline,
            lifespan=lifespan,
            liveliness=liveliness,
            liveliness_lease_duration=liveliness_lease_duration,
        )


DEFAULT_QOS_PROFILE = QosProfile()

