# Project Structure

```text
zenoh_ros2_sdk/
├── zenoh_ros2_sdk/          # Main package
│   ├── __init__.py          # Package exports (ROS2Publisher, ROS2Subscriber, ZenohSession)
│   ├── session.py           # ZenohSession (singleton)
│   ├── publisher.py         # ROS2Publisher class
│   ├── subscriber.py        # ROS2Subscriber class
│   └── utils.py             # Utility functions (type conversion, name mangling, type hash lookup)
├── examples/                # Example scripts
│   ├── __init__.py
│   ├── README.md            # Examples documentation
│   ├── simple_publisher.py  # Basic publisher example
│   ├── simple_subscriber.py # Basic subscriber example
│   ├── custom_message_type.py # Custom message type example
│   └── multiple_publishers.py # Multiple publishers example
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── README.md            # Test documentation
│   ├── conftest.py          # Pytest configuration and fixtures
│   ├── test_utils.py        # Unit tests for utility functions
│   ├── test_session.py      # Unit tests for ZenohSession
│   ├── test_publisher.py    # Unit tests for ROS2Publisher
│   ├── test_subscriber.py   # Unit tests for ROS2Subscriber
│   └── test_integration.py  # Integration tests (requires Zenoh router)
├── setup.py                 # Setuptools configuration (legacy)
├── pyproject.toml           # Modern Python packaging configuration
├── README.md                # Main documentation
├── STRUCTURE.md             # This file - project structure documentation
├── LICENSE                  # Apache 2.0 License
└── .gitignore               # Git ignore rules
```

## Module Responsibilities

- **session.py**: Manages shared Zenoh session (singleton), type registration, GID/node/entity ID generation, liveliness tokens
- **publisher.py**: ROS2 publisher with liveliness tokens, message serialization, and attachments (sequence, timestamp, GID)
- **subscriber.py**: ROS2 subscriber with message deserialization and callback handling
- **utils.py**: Helper functions for type conversion (ROS2 to DDS), name mangling, type hash lookup

## Package Exports

The main package (`zenoh_ros2_sdk`) exports:

- `ROS2Publisher`: Create and manage ROS2 publishers
- `ROS2Subscriber`: Create and manage ROS2 subscribers  
- `ZenohSession`: Access to the singleton session manager (typically not needed directly)
