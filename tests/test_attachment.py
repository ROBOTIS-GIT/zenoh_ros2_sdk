"""
Unit tests for attachment encoding/decoding.
"""

import pytest

from zenoh_ros2_sdk.attachment import Attachment


def test_attachment_roundtrip():
    att = Attachment(sequence_id=123, timestamp_ns=456, gid=b"\x01\x02\x03")
    b = att.to_bytes()
    att2 = Attachment.from_bytes(b)
    assert att2.sequence_id == 123
    assert att2.timestamp_ns == 456
    assert att2.gid == b"\x01\x02\x03"


def test_attachment_too_short():
    with pytest.raises(ValueError, match="too short"):
        Attachment.from_bytes(b"\x00" * 16)


def test_attachment_gid_len_too_long():
    # declare gid_len=10 but only provide 5 bytes
    b = (b"\x00" * 16) + bytes([10]) + (b"\x01" * 5)
    with pytest.raises(ValueError, match="truncated"):
        Attachment.from_bytes(b)


def test_attachment_gid_max_255():
    att = Attachment(sequence_id=1, timestamp_ns=2, gid=b"\x00" * 255)
    b = att.to_bytes()
    assert len(b) == 17 + 255


def test_attachment_gid_too_long_raises():
    att = Attachment(sequence_id=1, timestamp_ns=2, gid=b"\x00" * 256)
    with pytest.raises(ValueError, match="gid too long"):
        att.to_bytes()

