"""External codecs use the same repository lookup as subscribers."""
from unittest.mock import patch
import pytest
from zenoh_ros2_sdk.message_registry import MessageRegistry
from zenoh_ros2_sdk._repositories import PACKAGE_TO_REPOSITORY
from zenoh_ros2_sdk.utils import get_type_hash


def test_repository_dependency_graph_without_session(tmp_path):
    # Files stand in for paths returned by the SDK's configured repository cache.
    definitions = {'sensor_msgs/msg/Imu': 'std_msgs/Header header\ngeometry_msgs/Quaternion orientation\n',
                   'std_msgs/msg/Header': 'builtin_interfaces/Time stamp\nstring frame_id\n',
                   'builtin_interfaces/msg/Time': 'int32 sec\nuint32 nanosec\n',
                   'geometry_msgs/msg/Quaternion': 'float64 x 0\nfloat64 y 0\nfloat64 z 0\nfloat64 w 1\n'}
    paths = {}
    for name, text in definitions.items():
        path = tmp_path / (name + '.msg')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        paths[name] = str(path)
    calls = []
    def cached(name, repository):
        calls.append((name, repository))
        return paths.get(name)
    registry = MessageRegistry(str(tmp_path / 'overrides'))
    with patch('zenoh_ros2_sdk.message_registry.get_message_file_path', side_effect=cached), \
         patch('zenoh_ros2_sdk.session.ZenohSession.get_instance', side_effect=AssertionError('session opened')):
        result = registry.get_message_definitions('sensor_msgs/msg/Imu')
    assert result == definitions
    assert list(result)[-1] == 'sensor_msgs/msg/Imu'
    assert ('sensor_msgs/msg/Imu', 'common_interfaces') in calls
    assert ('builtin_interfaces/msg/Time', 'rcl_interfaces') in calls
    assert PACKAGE_TO_REPOSITORY['sensor_msgs'] == 'common_interfaces'
    assert get_type_hash('geometry_msgs/msg/Quaternion', result['geometry_msgs/msg/Quaternion'], result) == \
        'RIHS01_8a765f66778c8ff7c8ab94afcc590a2ed5325a1d9a076ffff38fbce36f458684'


def test_local_overrides_precede_repository_lookup(tmp_path):
    path = tmp_path / 'sensor_msgs/msg/Imu.msg'
    path.parent.mkdir(parents=True)
    path.write_text('float64 custom_value\n')
    with patch('zenoh_ros2_sdk.message_registry.get_message_file_path', side_effect=AssertionError('Git lookup')):
        assert MessageRegistry(str(tmp_path)).get_message_definitions('sensor_msgs/msg/Imu') == {
            'sensor_msgs/msg/Imu': 'float64 custom_value\n'}


def test_missing_dependency_and_invalid_name_fail(tmp_path):
    path = tmp_path / 'test/msg/Parent.msg'
    path.parent.mkdir(parents=True)
    path.write_text('Missing child\n')
    registry = MessageRegistry(str(tmp_path))
    with pytest.raises(FileNotFoundError, match='test/msg/Missing'):
        registry.get_message_definitions('test/msg/Parent')
    with pytest.raises(ValueError, match='package/msg/Type'):
        registry.get_message_definitions('../msg/Invalid')
    path.write_text('Parent child\n')
    with pytest.raises(ValueError, match='Cyclic'):
        registry.get_message_definitions('test/msg/Parent')
