"""
Pytest configuration and fixtures
"""
import pytest
from zenoh_ros2_sdk.session import ZenohSession


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test"""
    # Reset before test
    ZenohSession._instance = None
    yield
    # Clean up after test
    if ZenohSession._instance:
        try:
            ZenohSession._instance.close()
        except:
            pass
        ZenohSession._instance = None
