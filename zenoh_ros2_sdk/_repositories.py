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
        flat_layout: If True, single-package repos use <repo>/msg/ (e.g. example_interfaces).
            If False, use <repo>/<package>/msg/ even for one package (e.g. geometry2).
    """
    url: str
    commit: str
    cache_path: str
    msg_path: str
    packages: List[str]
    flat_layout: bool = False  # True only for example_interfaces (msg/ at root)


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
        commit="jazzy",  # Use specific commit/tag for reproducibility
        cache_path="example_interfaces",
        msg_path="",  # Files are directly at repo root: msg/ and srv/ (not in a package subdirectory)
        packages=[
            "example_interfaces",  # Contains AddTwoInts service and other examples
        ],
        flat_layout=True,  # <repo>/msg/<file>.msg, not <repo>/example_interfaces/msg/
    ),
    # Geometry2 (contains tf2_msgs and other TF2-related packages)
    # This repository contains TF2 transform message definitions
    # Reference: https://github.com/ros2/geometry2
    "geometry2": MessageRepository(
        url="https://github.com/ros2/geometry2.git",
        commit="jazzy",  # Use specific commit/tag for reproducibility
        cache_path="geometry2",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "tf2_msgs",  # Contains TFMessage, TF2Error messages
        ],
    ),
    # control_msgs (ROS 2 control message definitions)
    # Reference: https://github.com/ros-controls/control_msgs
    "control_msgs": MessageRepository(
        url="https://github.com/ros-controls/control_msgs.git",
        commit="jazzy",  # Use jazzy branch/tag for reproducibility
        cache_path="control_msgs",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "control_msgs",
        ],
    ),
    # ros2_control (contains controller_manager_msgs and related interfaces)
    # Reference: https://github.com/ros-controls/ros2_control
    "ros2_control": MessageRepository(
        url="https://github.com/ros-controls/ros2_control.git",
        commit="jazzy",  # Use jazzy branch/tag for reproducibility
        cache_path="ros2_control",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "controller_manager_msgs",
        ],
    ),
    # pal_statistics (PAL Robotics statistics messages)
    # Reference: https://github.com/pal-robotics/pal_statistics
    "pal_statistics": MessageRepository(
        url="https://github.com/pal-robotics/pal_statistics.git",
        commit="humble-devel",  # Use jazzy branch/tag for reproducibility
        cache_path="pal_statistics",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "pal_statistics_msgs",
        ],
    ),
    # dynamixel_interfaces (ROBOTIS Dynamixel message interfaces)
    # Reference: https://github.com/ROBOTIS-GIT/dynamixel_interfaces
    "dynamixel_interfaces": MessageRepository(
        url="https://github.com/ROBOTIS-GIT/dynamixel_interfaces.git",
        commit="jazzy",  # Use jazzy branch/tag for reproducibility
        cache_path="dynamixel_interfaces",
        msg_path="",  # Messages are at <package>/msg/<message>.msg
        packages=[
            "dynamixel_interfaces",
        ],
    ),
    # physical_ai_interfaces (ROBOTIS Physical AI message/service interfaces)
    # Reference: https://github.com/ROBOTIS-GIT/physical_ai_tools/tree/main/physical_ai_interfaces
    "physical_ai_tools": MessageRepository(
        url="https://github.com/ROBOTIS-GIT/physical_ai_tools.git",
        commit="feature-temp-merge",
        cache_path="physical_ai_tools",
        msg_path="",
        packages=[
            "physical_ai_interfaces",
        ],
    ),
    # interfaces (Cyclo Intelligence message/service interfaces)
    # Reference: https://github.com/ROBOTIS-GIT/cyclo_intelligence/tree/main/interfaces
    "cyclo_intelligence": MessageRepository(
        url="https://github.com/ROBOTIS-GIT/cyclo_intelligence.git",
        commit="feature-code-optimization",
        cache_path="cyclo_intelligence",
        msg_path="",
        packages=[
            "interfaces",
        ],
    ),
}

# Mapping from message package namespace to repository name
PACKAGE_TO_REPOSITORY: Dict[str, str] = {}
for repo_name, repo in MESSAGE_REPOSITORIES.items():
    for package in repo.packages:
        PACKAGE_TO_REPOSITORY[package] = repo_name
