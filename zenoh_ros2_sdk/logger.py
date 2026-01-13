"""
Logging configuration for zenoh-ros2-sdk
"""
import logging

# Configure default logger for the SDK
_logger = logging.getLogger("zenoh_ros2_sdk")
_logger.setLevel(logging.WARNING)  # Default to WARNING level
_logger.propagate = True  # Allow propagation to root logger for user configuration

# Create a default handler if none exists
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.WARNING)  # Set handler level to match logger
    _handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    _logger.addHandler(_handler)


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger for the zenoh-ros2-sdk package.

    Args:
        name: Optional logger name (defaults to 'zenoh_ros2_sdk')

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger()
        >>> logger.setLevel(logging.DEBUG)
        >>> logger.info("SDK initialized")
    """
    if name is None:
        return _logger
    return logging.getLogger(f"zenoh_ros2_sdk.{name}")
