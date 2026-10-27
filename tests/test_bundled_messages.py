"""Offline defaults and ROS Jazzy wire compatibility for telemetry types."""
from unittest.mock import patch
import numpy as np
import pytest
from rosbags.typesys import Stores, get_typestore, get_types_from_msg
from zenoh_ros2_sdk import get_bundled_message_definitions, MessageRegistry
from zenoh_ros2_sdk.bundled import get_bundled_message_path
from zenoh_ros2_sdk.utils import get_type_hash

# ROS-generated type hashes from installed Jazzy type-description JSON files.
HASHES = {
    'sensor_msgs/msg/Imu': 'RIHS01_7d9a00ff131080897a5ec7e26e315954b8eae3353c3f995c55faf71574000b5b',
    'sensor_msgs/msg/JointState': 'RIHS01_a13ee3a330e346c9d87b5aa18d24e11690752bd33a0350f11c5882bc9179260e',
}

@pytest.mark.parametrize('name', HASHES)
def test_default_telemetry_is_offline_and_hash_matches_ros(name, tmp_path):
    with patch('zenoh_ros2_sdk.message_registry.get_message_file_path', side_effect=AssertionError('network fallback')), \
         patch('zenoh_ros2_sdk.session.ZenohSession.get_instance', side_effect=AssertionError('session opened')):
        registry = MessageRegistry(str(tmp_path))
        definitions = get_bundled_message_definitions()
        for dep, text in definitions.items():
            assert registry.get_msg_file_path(dep).read_text() == text
        assert get_type_hash(name, definitions[name], definitions) == HASHES[name]


def test_local_override_precedes_bundle(tmp_path):
    path = tmp_path / 'sensor_msgs/msg/Imu.msg'
    path.parent.mkdir(parents=True)
    path.write_text('float64 custom_field\n')
    assert MessageRegistry(str(tmp_path)).get_msg_file_path('sensor_msgs/msg/Imu') == path
    assert get_bundled_message_path('../../etc/passwd') is None
    assert get_bundled_message_path('unknown/msg/Missing') is None


def test_imu_cdr_roundtrip_preserves_quaternion_and_covariance():
    store = get_typestore(Stores.EMPTY)
    for name, text in get_bundled_message_definitions().items():
        store.register(get_types_from_msg(text, name))
    t = store.types
    vector = t['geometry_msgs/msg/Vector3']
    msg = t['sensor_msgs/msg/Imu'](
        t['std_msgs/msg/Header'](t['builtin_interfaces/msg/Time'](12, 34), 'pelvis'),
        t['geometry_msgs/msg/Quaternion'](0., 0., .6, .8), np.arange(9, dtype=np.float64),
        vector(1., 2., 3.), np.zeros(9), vector(0., 0., 9.81), np.zeros(9))
    result = store.deserialize_cdr(store.serialize_cdr(msg, 'sensor_msgs/msg/Imu'), 'sensor_msgs/msg/Imu')
    assert result.orientation.z == .6 and result.orientation.w == .8
    assert result.header.frame_id == 'pelvis'
    assert np.array_equal(result.orientation_covariance, np.arange(9))
