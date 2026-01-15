"""
Attachment utilities compatible with rmw_zenoh / ros-z.

Binary format (little-endian), matching our existing implementation:
  u64 sequence_number
  u64 timestamp_ns
  u8  gid_len
  u8[gid_len] gid

Used for:
- Topic publications (publisher attachment)
- Service requests/responses (required for correlation; server replies with the same sequence_id+gid)
"""

from __future__ import annotations

from dataclasses import dataclass
import struct


@dataclass(frozen=True, slots=True)
class Attachment:
    """Service/topic attachment compatible with rmw_zenoh.

    Attributes:
        sequence_id: Per-client/publisher sequence number.
        timestamp_ns: Source timestamp in nanoseconds.
        gid: Source GID (bytes, length <= 255).
    """
    sequence_id: int
    timestamp_ns: int
    gid: bytes

    def to_bytes(self) -> bytes:
        if not isinstance(self.gid, (bytes, bytearray)):
            raise TypeError(f"gid must be bytes, got {type(self.gid)}")
        gid_b = bytes(self.gid)
        if len(gid_b) > 255:
            raise ValueError(f"gid too long for attachment encoding: {len(gid_b)}")
        return (
            struct.pack("<Q", int(self.sequence_id))
            + struct.pack("<Q", int(self.timestamp_ns))
            + struct.pack("B", len(gid_b))
            + gid_b
        )

    @staticmethod
    def from_bytes(b: bytes) -> "Attachment":
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError(f"attachment must be bytes, got {type(b)}")
        b = bytes(b)
        if len(b) < 17:
            raise ValueError("attachment too short (need at least 17 bytes)")
        seq = struct.unpack("<Q", b[0:8])[0]
        ts = struct.unpack("<Q", b[8:16])[0]
        gid_len = struct.unpack("B", b[16:17])[0]
        if len(b) < 17 + gid_len:
            raise ValueError("attachment truncated (gid_len exceeds available bytes)")
        gid = b[17 : 17 + gid_len]
        return Attachment(sequence_id=seq, timestamp_ns=ts, gid=gid)

