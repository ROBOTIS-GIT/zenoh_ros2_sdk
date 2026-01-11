# Message Definitions

This directory is **optional** and can be used to store custom message definition files (`.msg`) that are not available in public repositories, or to override default message definitions.

## Automatic Download (Recommended)

The SDK automatically downloads message definitions from Git repositories when needed. You typically **don't need to add anything here** - the SDK handles it automatically:

```python
from zenoh_ros2_sdk import load_message_type

# Automatically downloads from git if not found locally
load_message_type("geometry_msgs/msg/Twist")
```

Message repositories are cached in `~/.cache/zenoh_ros2_sdk/` (or `$ZENOH_ROS2_SDK_CACHE` if set), so they only need to be downloaded once.

## When to Use This Directory

Use this directory if you need to:

1. **Add custom messages** that aren't in public repositories
2. **Override message definitions** for testing or compatibility
3. **Work offline** without Git access (after manually adding required messages)

## Structure

Message files are organized by package and type:
```
messages/
├── my_package/
│   └── msg/
│       └── MyCustomMessage.msg
└── std_msgs/
    └── msg/
        └── String.msg  # Optional override
```

## Adding Custom Messages

1. Create the appropriate directory structure: `messages/<package>/msg/`
2. Add the `.msg` file with the message definition
3. The SDK will automatically load it when you call `load_message_type()`

### Example: Adding a custom message

```python
# 1. Create messages/my_package/msg/MyMessage.msg
# 2. Use it in your code:
from zenoh_ros2_sdk import load_message_type, get_message_class

load_message_type("my_package/msg/MyMessage")
MyMessage = get_message_class("my_package/msg/MyMessage")
```

## Dependencies

The message registry automatically handles dependencies. For example:
- `Twist.msg` depends on `Vector3.msg`
- When you load `Twist`, `Vector3` is automatically loaded first (from git or this directory)

## Priority

The SDK checks in this order:
1. Local `messages/` directory (this folder)
2. Git repositories (auto-downloaded and cached)

This means messages in this directory take precedence over downloaded ones.
