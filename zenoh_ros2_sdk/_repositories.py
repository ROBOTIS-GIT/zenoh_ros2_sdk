"""
Git repository definitions for ROS2 message packages
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class MessageRepository:
    """Git repository containing ROS2 message definitions.

    Attributes:
        url: URL to the remote git repository
        commit: Commit ID or tag to checkout after cloning
        cache_path: Path to clone the repository to in the local cache
        msg_path: Relative path within the repo to message files (e.g., "msg/")
        packages: List of message package names this repository contains (e.g., ["std_msgs", "geometry_msgs"])
    """
    url: str
    commit: str
    cache_path: str
    msg_path: str
    packages: List[str]


# Repository definitions for common ROS2 message packages
MESSAGE_REPOSITORIES: Dict[str, MessageRepository] = {
    # RCL interfaces (contains builtin_interfaces and other core interfaces)
    # This repository contains messages and services used by ROS client libraries
    # Reference: https://github.com/ros2/rcl_interfaces
    "rcl_interfaces": MessageRepository(
        url="https://github.com/ros2/rcl_interfaces.git",
        commit="jazzy",  # Use specific commit/tag for reproducibility
        cache_path="rcl_interfaces",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "builtin_interfaces",  # Required for Time, Duration, etc.
            "action_msgs",
            "composition_interfaces",
            "lifecycle_msgs",
            "rcl_interfaces",
            "rosgraph_msgs",
            "service_msgs",
            "statistics_msgs",
            "test_msgs",
            "type_description_interfaces",
        ],
    ),
    # Common interfaces (contains many standard message packages)
    # This is the main repository for ROS2 common message interfaces
    "common_interfaces": MessageRepository(
        url="https://github.com/ros2/common_interfaces.git",
        commit="jazzy",  # Use specific commit/tag for reproducibility
        cache_path="common_interfaces",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "std_msgs",
            "geometry_msgs",
            "sensor_msgs",
            "nav_msgs",
            "diagnostic_msgs",
            "shape_msgs",
            "stereo_msgs",
            "trajectory_msgs",
            "visualization_msgs",
        ],
    ),
    # Example interfaces (single package repository, not a meta-package)
    # Structure: <repo_root>/msg/<message>.msg and <repo_root>/srv/<service>.srv
    # Reference: https://github.com/ros2/example_interfaces
    "example_interfaces": MessageRepository(
        url="https://github.com/ros2/example_interfaces.git",
        commit="rolling",  # Use rolling branch for latest examples
        cache_path="example_interfaces",
        msg_path="",  # Files are directly at repo root: msg/ and srv/ (not in a package subdirectory)
        packages=[
            "example_interfaces",  # Contains AddTwoInts service and other examples
        ],
    ),
}

# Mapping from message package namespace to repository name
PACKAGE_TO_REPOSITORY: Dict[str, str] = {}
for repo_name, repo in MESSAGE_REPOSITORIES.items():
    for package in repo.packages:
        PACKAGE_TO_REPOSITORY[package] = repo_name
