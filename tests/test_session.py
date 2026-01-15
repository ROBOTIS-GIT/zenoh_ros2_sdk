"""
Unit tests for ZenohSession singleton
"""
import pytest
import threading
from zenoh_ros2_sdk.session import ZenohSession


class TestZenohSessionSingleton:
    """Tests for singleton pattern"""

    def test_singleton_instance(self):
        """Test that get_instance returns the same instance"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        instance1 = ZenohSession.get_instance()
        instance2 = ZenohSession.get_instance()

        assert instance1 is instance2
        assert id(instance1) == id(instance2)

    def test_thread_safety(self):
        """Test that singleton is thread-safe"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        instances = []

        def get_instance():
            instances.append(ZenohSession.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert all(inst is instances[0] for inst in instances)

    def test_node_id_generation(self):
        """Test node ID counter"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        session = ZenohSession.get_instance()
        id1 = session.get_next_node_id()
        id2 = session.get_next_node_id()
        id3 = session.get_next_node_id()

        assert id1 == 0
        assert id2 == 1
        assert id3 == 2

    def test_entity_id_generation(self):
        """Test entity ID counter"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        session = ZenohSession.get_instance()
        id1 = session.get_next_entity_id()
        id2 = session.get_next_entity_id()
        id3 = session.get_next_entity_id()

        assert id1 == 0
        assert id2 == 1
        assert id3 == 2

    def test_gid_generation(self):
        """Test GID generation"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        session = ZenohSession.get_instance()
        gid1 = session.generate_gid()
        gid2 = session.generate_gid()

        # GIDs should be 16 bytes
        assert len(gid1) == 16
        assert len(gid2) == 16

        # GIDs should be unique
        assert gid1 != gid2

    def test_message_type_registration(self):
        """Test message type registration"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        session = ZenohSession.get_instance()

        # Register a type
        msg_class = session.register_message_type(
            "string data\n",
            "std_msgs/msg/String"
        )

        # Should return a class
        assert msg_class is not None

        # Registering again should return same class
        msg_class2 = session.register_message_type(
            "string data\n",
            "std_msgs/msg/String"
        )

        assert msg_class is msg_class2

    def teardown_method(self):
        """Clean up after each test"""
        if ZenohSession._instance:
            try:
                ZenohSession._instance.close()
            except:
                pass
            ZenohSession._instance = None


def test_parse_zenoh_config_override():
    from zenoh_ros2_sdk.session import _parse_zenoh_config_override

    override = (
        'transport/shared_memory/enabled=true;'
        'mode="client";'
        'connect/endpoints=["tcp/192.168.6.2:7447"]'
    )
    assert _parse_zenoh_config_override(override) == [
        ("transport/shared_memory/enabled", "true"),
        ("mode", '"client"'),
        ("connect/endpoints", '["tcp/192.168.6.2:7447"]'),
    ]


def test_apply_zenoh_config_override_parses_json5(monkeypatch):
    # Avoid needing a live zenoh runtime: just capture insert_json5 calls.
    from zenoh_ros2_sdk.session import _apply_zenoh_config_override

    class DummyConf:
        def __init__(self):
            self.calls = []

        def insert_json5(self, path, value):
            self.calls.append((path, value))

    conf = DummyConf()

    override = 'mode="client";connect/endpoints=["tcp/127.0.0.1:7447"];transport/shared_memory/enabled=true'
    _apply_zenoh_config_override(conf, override)

    # Values should be serialized JSON (not raw JSON5)
    assert conf.calls == [
        ("mode", '"client"'),
        ("connect/endpoints", '["tcp/127.0.0.1:7447"]'),
        ("transport/shared_memory/enabled", "true"),
    ]


def test_apply_zenoh_config_override_rejects_invalid_json5():
    from zenoh_ros2_sdk.session import _apply_zenoh_config_override

    class DummyConf:
        def insert_json5(self, path, value):
            pass

    conf = DummyConf()

    # mode without quotes is invalid JSON5 (bare identifier)
    with pytest.raises(ValueError):
        _apply_zenoh_config_override(conf, "mode=client")
