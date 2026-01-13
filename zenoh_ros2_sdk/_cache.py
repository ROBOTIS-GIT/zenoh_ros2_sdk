"""
Git utility functions to clone message repositories

This module is adapted from robot_descriptions.py (Apache-2.0 licensed).
Original work: Copyright 2022 Stéphane Caron, Copyright 2023 Inria
Source: https://github.com/robot-descriptions/robot_descriptions.py
"""
import os
import shutil
from typing import Optional, Union

from git import GitCommandError, InvalidGitRepositoryError, RemoteProgress, Repo
import tqdm

from ._repositories import MESSAGE_REPOSITORIES, MessageRepository, PACKAGE_TO_REPOSITORY
from .logger import get_logger

logger = get_logger("cache")


def construct_message_path(
    repo_path: str,
    repository: MessageRepository,
    namespace: str,
    msg_type: str,  # "msg" or "srv"
    file_name: str
) -> str:
    """
    Construct path to message/service file based on repository structure.

    Handles three repository structures:
    1. Single-package repos: <repo_root>/msg/<file>.msg or <repo_root>/srv/<file>.srv
    2. Repos with msg_path: <repo_root>/<msg_path>/<package>/msg/<file>.msg
    3. Meta-package repos: <repo_root>/<package>/msg/<file>.msg

    Args:
        repo_path: Path to the cloned repository root
        repository: MessageRepository configuration
        namespace: Package namespace (e.g., "std_msgs", "example_interfaces")
        msg_type: Type of file - "msg" or "srv"
        file_name: Name of the message/service file (without extension)

    Returns:
        Full path to the message/service file
    """
    # Check if this is a single-package repository
    # (repository contains only one package and it matches the namespace)
    is_single_package = len(repository.packages) == 1 and repository.packages[0] == namespace

    if is_single_package:
        # Single-package repository: files are directly at repo root (msg/, srv/)
        # Example: example_interfaces -> <repo>/msg/UInt32.msg
        return os.path.join(repo_path, msg_type, f"{file_name}.{msg_type}")
    elif repository.msg_path:
        # Repository has a custom msg_path prefix (for future use)
        # Example: if msg_path="ros2_msgs/" -> <repo>/ros2_msgs/std_msgs/msg/String.msg
        return os.path.join(
            repo_path,
            repository.msg_path,
            namespace,
            msg_type,
            f"{file_name}.{msg_type}"
        )
    else:
        # Meta-package repository: files in package subdirectory
        # Example: common_interfaces -> <repo>/std_msgs/msg/String.msg
        return os.path.join(repo_path, namespace, msg_type, f"{file_name}.{msg_type}")


class CloneProgressBar(RemoteProgress):
    """Progress bar when cloning."""

    def __init__(self):
        """Initialize progress bar."""
        super().__init__()
        self.progress = tqdm.tqdm()

    def update(
        self,
        op_code: int,
        cur_count: Union[str, float],
        max_count: Union[str, float, None] = None,
        message: str = "",
    ) -> None:
        """Update progress bar.

        Args:
            op_code: Integer that can be compared against Operation IDs and stage IDs.
            cur_count: Current item count.
            max_count: Maximum item count, or None if there is none.
            message: Unused here.
        """
        if max_count:
            self.progress.total = max_count
        self.progress.n = cur_count
        self.progress.refresh()


def get_repository_for_package(package_name: str) -> Optional[str]:
    """
    Get the repository name for a given message package.

    Args:
        package_name: Message package name (e.g., "geometry_msgs")

    Returns:
        Repository name or None if not found
    """
    return PACKAGE_TO_REPOSITORY.get(package_name)


def clone_to_cache(repo_name: str, commit: Optional[str] = None) -> str:
    """
    Clone a message repository to the local cache.

    Args:
        repo_name: Name of the repository (key in MESSAGE_REPOSITORIES)
        commit: Optional commit to checkout (overrides default)

    Returns:
        Path to the cloned repository directory

    Raises:
        KeyError: If repository name is not found
    """
    try:
        repository = MESSAGE_REPOSITORIES[repo_name]
    except KeyError as exn:
        raise KeyError(f"Unknown message repository: {repo_name}") from exn

    # Get cache directory
    cache_dir = os.path.expanduser(
        os.environ.get(
            "ZENOH_ROS2_SDK_CACHE",
            "~/.cache/zenoh_ros2_sdk",
        )
    )

    target_dir = os.path.join(cache_dir, repository.cache_path)

    # Clone or update repository
    clone = None
    if os.path.exists(target_dir):
        try:
            clone = Repo(target_dir)
        except InvalidGitRepositoryError:
            logger.warning(f"Repository at {target_dir} is invalid, recreating it...")
            shutil.rmtree(target_dir)
            clone = None

    if clone is None:
        logger.info(f"Cloning {repository.url}...")
        os.makedirs(target_dir, exist_ok=True)
        progress_bar = CloneProgressBar()
        clone = Repo.clone_from(
            repository.url,
            target_dir,
            progress=progress_bar.update,
        )

    # Checkout specific commit if needed
    checkout_commit = commit if commit is not None else repository.commit
    if checkout_commit and checkout_commit != clone.head.object.hexsha:
        try:
            clone.git.checkout(checkout_commit)
        except GitCommandError:
            logger.debug(f"Commit {checkout_commit} not found, fetching origin...")
            clone.git.fetch("origin")
            clone.git.checkout(checkout_commit)

    return str(clone.working_dir)


def get_message_file_path(
    msg_type: str,
    repo_name: Optional[str] = None
) -> Optional[str]:
    """
    Get the path to a message file, downloading the repository if needed.

    Args:
        msg_type: ROS2 message type (e.g., "geometry_msgs/msg/Twist")
        repo_name: Repository name (required - use get_repository_for_package to find it)

    Returns:
        Path to the .msg file or None if not found
    """
    parts = msg_type.split("/")
    if len(parts) != 3:
        return None

    namespace, msg, message_name = parts

    # Repository name must be provided
    if repo_name is None:
        return None

    if repo_name not in MESSAGE_REPOSITORIES:
        return None

    try:
        repo_path = clone_to_cache(repo_name)
        repository = MESSAGE_REPOSITORIES[repo_name]

        # Construct path to message file using shared helper function
        msg_file_path = construct_message_path(
            repo_path, repository, namespace, msg, message_name
        )

        if os.path.exists(msg_file_path):
            return msg_file_path

    except Exception as e:
        logger.warning(f"Failed to get message file for {msg_type}: {e}")
        return None

    return None


def clear_cache() -> None:
    """Clear the local cache where message repositories are stored."""
    cache_dir = os.path.expanduser(
        os.environ.get(
            "ZENOH_ROS2_SDK_CACHE",
            "~/.cache/zenoh_ros2_sdk",
        )
    )
    shutil.rmtree(cache_dir, ignore_errors=True)
