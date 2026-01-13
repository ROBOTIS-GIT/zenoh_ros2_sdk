# Tests

This directory contains the test suite for `zenoh-ros2-sdk`.

## Test Structure

- **`test_utils.py`**: Unit tests for utility functions (type conversion, name mangling, type hash computation, service type hash)
- **`test_session.py`**: Unit tests for `ZenohSession` singleton pattern
- **`test_publisher.py`**: Unit tests for `ROS2Publisher` class
- **`test_subscriber.py`**: Unit tests for `ROS2Subscriber` class
- **`test_service_client.py`**: Unit tests for `ROS2ServiceClient` class
- **`test_service_server.py`**: Unit tests for `ROS2ServiceServer` class
- **`test_integration.py`**: Integration tests requiring a running Zenoh router (publisher-subscriber and service client-server)
- **`conftest.py`**: Pytest configuration and fixtures

## Running Tests

### Unit Tests (No Zenoh Router Required)

Run all unit tests:
```bash
pytest tests/
```

Run specific test file:
```bash
pytest tests/test_utils.py
```

Run with verbose output:
```bash
pytest tests/ -v
```

### Integration Tests (Requires Zenoh Router)

Integration tests require a running `zenohd` router. They are disabled by default.

To enable integration tests:
```bash
ZENOH_TEST_INTEGRATION=1 pytest tests/test_integration.py
```

To specify a custom router IP:
```bash
ZENOH_TEST_INTEGRATION=1 ZENOH_ROUTER_IP=192.168.1.100 pytest tests/test_integration.py
```

### Test Coverage

Install coverage tools:
```bash
pip install pytest-cov
```

Run tests with coverage:
```bash
pytest tests/ --cov=zenoh_ros2_sdk --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Writing New Tests

1. **Unit Tests**: Test individual functions/classes in isolation
2. **Integration Tests**: Test full workflows with a real Zenoh router
3. **Use fixtures**: Leverage `conftest.py` fixtures for common setup/teardown
4. **Reset singleton**: Always reset `ZenohSession._instance` in tests to avoid state leakage

## Test Best Practices

- Keep tests isolated and independent
- Use descriptive test names
- Test both success and error cases
- Mock external dependencies when possible
- Clean up resources in `teardown_method` or fixtures
