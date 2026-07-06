"""
Unit tests for ROS2Publisher
"""
import pytest
import time
from types import SimpleNamespace
from zenoh_ros2_sdk import ROS2Publisher
from zenoh_ros2_sdk.qos import QosDurability, QosProfile, QosReliability
from zenoh_ros2_sdk.session import ZenohSession


class TestROS2Publisher:
    """Tests for ROS2Publisher class"""

    def test_publisher_creation(self):
        """Test creating a publisher"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0
        )

        assert pub.topic == "/test_topic"
        assert pub.msg_type == "std_msgs/msg/String"
        assert pub.domain_id == 0
        assert pub.node_name is not None

        pub.close()

    def test_publisher_custom_node_name(self):
        """Test publisher with custom node name"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            node_name="my_custom_node",
            domain_id=0
        )

        assert pub.node_name == "my_custom_node"

        pub.close()

    def test_publisher_namespace(self):
        """Test publisher with custom namespace"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            namespace="/my_namespace",
            domain_id=0
        )

        assert pub.namespace == "/my_namespace"

        pub.close()

    def test_publisher_domain_id(self):
        """Test publisher with custom domain ID"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub = ROS2Publisher(
            topic="/test_topic",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=30
        )

        assert pub.domain_id == 30

        pub.close()

    def test_publisher_shared_session(self):
        """Test that multiple publishers share the same session"""
        # Reset singleton for clean test
        ZenohSession._instance = None

        pub1 = ROS2Publisher(
            topic="/topic1",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0
        )

        pub2 = ROS2Publisher(
            topic="/topic2",
            msg_type="std_msgs/msg/String",
            msg_definition="string data\n",
            domain_id=0
        )

        # Both should use the same session instance
        assert pub1.session_mgr is pub2.session_mgr

        pub1.close()
        pub2.close()

    def test_resolve_congestion_control_top_level_enum(self):
        """Zenoh 1.x exposes CongestionControl at module top level."""
        cc_enum = SimpleNamespace(BLOCK="block", DROP="drop")
        zenoh_module = SimpleNamespace(CongestionControl=cc_enum)

        assert ROS2Publisher._resolve_congestion_control(
            zenoh_module,
            reliability=QosReliability.RELIABLE,
            strict=True,
        ) == "block"
        assert ROS2Publisher._resolve_congestion_control(
            zenoh_module,
            reliability=QosReliability.BEST_EFFORT,
            strict=True,
        ) == "drop"

    def test_resolve_congestion_control_nested_enum(self):
        """Older Zenoh APIs may expose CongestionControl under zenoh.qos."""
        cc_enum = SimpleNamespace(Block="block", Drop="drop")
        zenoh_module = SimpleNamespace(qos=SimpleNamespace(CongestionControl=cc_enum))

        assert ROS2Publisher._resolve_congestion_control(
            zenoh_module,
            reliability=QosReliability.RELIABLE,
            strict=True,
        ) == "block"
        assert ROS2Publisher._resolve_congestion_control(
            zenoh_module,
            reliability=QosReliability.BEST_EFFORT,
            strict=True,
        ) == "drop"

    def test_resolve_congestion_control_strict_missing_enum_raises(self):
        """Strict mode fails instead of silently losing reliability mapping."""
        zenoh_module = SimpleNamespace()

        with pytest.raises(RuntimeError, match="does not expose CongestionControl"):
            ROS2Publisher._resolve_congestion_control(
                zenoh_module,
                reliability=QosReliability.RELIABLE,
                strict=True,
            )

        assert ROS2Publisher._resolve_congestion_control(
            zenoh_module,
            reliability=QosReliability.RELIABLE,
            strict=False,
        ) is None

    def test_declare_zenoh_publisher_strict_raises_when_options_unsupported(self, monkeypatch):
        """Strict mode fails if the Zenoh API rejects QoS declaration kwargs."""
        monkeypatch.setattr(
            ROS2Publisher,
            "_resolve_congestion_control",
            staticmethod(lambda *args, **kwargs: "block"),
        )

        class Session:
            def __init__(self):
                self.calls = []

            def declare_publisher(self, keyexpr, **kwargs):
                self.calls.append((keyexpr, kwargs))
                raise TypeError("unsupported kwargs")

        session = Session()
        pub = object.__new__(ROS2Publisher)
        pub.session_mgr = SimpleNamespace(session=session)
        pub.qos_profile = QosProfile()
        pub.strict_zenoh_qos = True
        pub._put_extra_kwargs = {}

        with pytest.raises(RuntimeError, match="does not support setting publisher QoS options"):
            pub._declare_zenoh_publisher("demo/key")

        assert session.calls == [
            (
                "demo/key",
                {"congestion_control": "block", "express": False},
            )
        ]

    def test_declare_zenoh_publisher_compatibility_mode_falls_back(self, monkeypatch):
        """Compatibility mode declares a plain publisher and stores put-time QoS kwargs."""
        monkeypatch.setattr(
            ROS2Publisher,
            "_resolve_congestion_control",
            staticmethod(lambda *args, **kwargs: "drop"),
        )
        sentinel = object()

        class Session:
            def __init__(self):
                self.calls = []

            def declare_publisher(self, keyexpr, **kwargs):
                self.calls.append((keyexpr, kwargs))
                if kwargs:
                    raise TypeError("unsupported kwargs")
                return sentinel

        session = Session()
        pub = object.__new__(ROS2Publisher)
        pub.session_mgr = SimpleNamespace(session=session)
        pub.qos_profile = QosProfile(
            reliability=QosReliability.BEST_EFFORT,
            durability=QosDurability.TRANSIENT_LOCAL,
        )
        pub.strict_zenoh_qos = False
        pub._put_extra_kwargs = {}

        assert pub._declare_zenoh_publisher("demo/key") is sentinel
        assert session.calls == [
            (
                "demo/key",
                {"congestion_control": "drop", "express": True},
            ),
            ("demo/key", {}),
        ]
        assert pub._put_extra_kwargs == {
            "congestion_control": "drop",
            "express": True,
        }

    def test_publish_compatibility_mode_retries_without_extra_kwargs(self):
        """Compatibility mode retries put() without QoS kwargs when put-time kwargs are unsupported."""
        class Pub:
            def __init__(self):
                self.calls = []

            def put(self, payload, **kwargs):
                self.calls.append((payload, kwargs))
                if "express" in kwargs:
                    raise TypeError("unsupported kwargs")

        class Store:
            def serialize_cdr(self, msg, msg_type):
                assert msg == {"data": "hello"}
                assert msg_type == "std_msgs/msg/String"
                return b"cdr"

        pub = object.__new__(ROS2Publisher)
        pub.msg_class = lambda **kwargs: kwargs
        pub.session_mgr = SimpleNamespace(store=Store())
        pub.msg_type = "std_msgs/msg/String"
        pub.publisher_gid = b"publisher-gid"
        pub.sequence_number = 0
        pub.pub = Pub()
        pub._put_extra_kwargs = {"express": True}
        pub.strict_zenoh_qos = False

        pub.publish(data="hello")

        assert pub.sequence_number == 1
        assert len(pub.pub.calls) == 2
        assert pub.pub.calls[0][0] == b"cdr"
        assert pub.pub.calls[0][1]["express"] is True
        assert pub.pub.calls[1][1] == {
            "encoding": pub.pub.calls[0][1]["encoding"],
            "attachment": pub.pub.calls[0][1]["attachment"],
        }

    def test_publish_strict_mode_raises_when_put_time_kwargs_are_rejected(self):
        """Strict mode refuses to publish if compatibility QoS kwargs cannot be applied."""
        class Pub:
            def put(self, payload, **kwargs):
                raise TypeError("unsupported kwargs")

        class Store:
            def serialize_cdr(self, msg, msg_type):
                return b"cdr"

        pub = object.__new__(ROS2Publisher)
        pub.msg_class = lambda **kwargs: kwargs
        pub.session_mgr = SimpleNamespace(store=Store())
        pub.msg_type = "std_msgs/msg/String"
        pub.publisher_gid = b"publisher-gid"
        pub.sequence_number = 0
        pub.pub = Pub()
        pub._put_extra_kwargs = {"express": True}
        pub.strict_zenoh_qos = True

        with pytest.raises(RuntimeError, match="Unable to apply requested QoS"):
            pub.publish(data="hello")

    def teardown_method(self):
        """Clean up after each test"""
        if ZenohSession._instance:
            try:
                ZenohSession._instance.close()
            except:
                pass
            ZenohSession._instance = None
