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
