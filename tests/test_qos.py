"""
Unit tests for QoS encode/decode compatibility.
"""

import pytest

from zenoh_ros2_sdk.qos import (
    QosProfile,
    QosReliability,
    QosDurability,
    QosHistoryKind,
    QosLiveliness,
    Duration,
    DURATION_INFINITE,
)


def test_qos_default_encodes_to_expected_string():
    # Default should match rmw_zenoh / ros-z convention.
    assert QosProfile().encode() == "::,10:,:,:,,"  # KeepLast(10), reliable, volatile, infinite, automatic


def test_qos_roundtrip_non_default():
    prof = QosProfile(
        reliability=QosReliability.BEST_EFFORT,
        durability=QosDurability.TRANSIENT_LOCAL,
        history_kind=QosHistoryKind.KEEP_LAST,
        history_depth=42,
        deadline=Duration(sec=1, nsec=2),
        lifespan=Duration(sec=3, nsec=4),
        liveliness=QosLiveliness.MANUAL_BY_TOPIC,
        liveliness_lease_duration=Duration(sec=5, nsec=6),
    )
    s = prof.encode()
    prof2 = QosProfile.decode(s)
    assert prof2 == prof


def test_qos_decode_incomplete_raises():
    with pytest.raises(ValueError, match="Incomplete QoS string"):
        QosProfile.decode("::,10")


def test_qos_infinite_constant_is_duration():
    assert isinstance(DURATION_INFINITE, Duration)

