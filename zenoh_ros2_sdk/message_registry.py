"""
Message Registry - Loads and manages ROS2 message definitions from .msg files
"""
import os
from pathlib import Path
from typing import Any, Optional, Set, Type

from ._cache import (
    get_repository_for_package,
    clone_to_cache,
    MESSAGE_REPOSITORIES,
    construct_message_path,
    get_message_file_path,
)
from .logger import get_logger

logger = get_logger("message_registry")


class MessageRegistry:
    """Registry for loading and managing ROS2 message definitions"""

    def __init__(self, messages_dir: Optional[str] = None):
        """
        Initialize message registry

        Args:
            messages_dir: Directory containing message files (default: SDK messages directory)
        """
        if messages_dir is None:
            # Default to SDK's messages directory
            sdk_dir = Path(__file__).parent.parent
            messages_dir = str(sdk_dir / "messages")

        self.messages_dir = Path(messages_dir)
        # Import at module level (no lazy loading)
        # We use a property to get the session dynamically to ensure we always use the current session
        # (important when singleton is reset in tests)
        from .session import ZenohSession
        self._ZenohSession = ZenohSession  # Store class reference
        self._loaded_types: Set[str] = set()

    @property
    def session(self):
        """Get the current ZenohSession instance (always fresh)"""
        return self._ZenohSession.get_instance()

    def get_msg_file_path(self, msg_type: str) -> Optional[Path]:
        """
        Get the path to a .msg file for a given message type.
        First checks local messages directory, then tries to download from git.

        Args:
            msg_type: ROS2 message type (e.g., "geometry_msgs/msg/Vector3")

        Returns:
            Path to .msg file or None if not found
        """
        parts = msg_type.split("/")
        if len(parts) != 3:
            return None

        namespace, msg, message_name = parts

        # First, check local messages directory
        msg_file = self.messages_dir / namespace / msg / f"{message_name}.msg"
        if msg_file.exists():
            return msg_file

        # If not found locally, try to download from git repository
        try:
            # Find which repository contains this package
            repo_name = get_repository_for_package(namespace)
            if repo_name:
                git_path = get_message_file_path(msg_type, repo_name)
                if git_path and os.path.exists(git_path):
                    return Path(git_path)
        except ImportError as e:
            # GitPython not available - log warning but don't fail
            logger.warning(
                f"GitPython not available. Cannot auto-download message file for {msg_type}. "
                f"Install GitPython with 'pip install GitPython' to enable auto-download. "
                f"Error: {e}"
            )
        except Exception as e:
            # Log the error but don't fail - user can add message manually
            logger.warning(
                f"Failed to auto-download message file for {msg_type} from git repository: {e}. "
                f"You may need to add the message file manually."
            )

        return None

    def get_srv_file_path(self, srv_type: str, is_request: bool = True) -> Optional[Path]:
        """
        Get the path to a .srv file for a given service type.
        First checks local messages directory, then tries to download from git.

        Args:
            srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")
            is_request: If True, return path for request part; if False, for response part

        Returns:
            Path to .srv file or None if not found
        """
        parts = srv_type.split("/")
        if len(parts) != 3:
            return None

        namespace, srv, service_name = parts

        # First, check local messages directory
        srv_file = self.messages_dir / namespace / srv / f"{service_name}.srv"
        if srv_file.exists():
            return srv_file

        # If not found locally, try to download from git repository
        try:
            # Find which repository contains this package
            repo_name = get_repository_for_package(namespace)
            if repo_name:
                try:
                    repo_path = clone_to_cache(repo_name)
                    repository = MESSAGE_REPOSITORIES[repo_name]

                    # Construct path to service file using shared helper function
                    srv_file_path = construct_message_path(
                        repo_path, repository, namespace, srv, service_name
                    )

                    if os.path.exists(srv_file_path):
                        return Path(srv_file_path)
                except Exception as e:
                    logger.warning(
                        f"Failed to get service file from cache for {srv_type}: {e}. "
                        f"Trying to clone repository..."
                    )
        except ImportError as e:
            # GitPython not available - log warning but don't fail
            logger.warning(
                f"GitPython not available. Cannot auto-download service file for {srv_type}. "
                f"Install GitPython with 'pip install GitPython' to enable auto-download. "
                f"Error: {e}"
            )
        except Exception as e:
            # Log the error but don't fail - user can add message manually
            logger.warning(
                f"Failed to auto-download service file for {srv_type} from git repository: {e}. "
                f"You may need to add the service file manually."
            )

        return None

    def _load_service_types(self, srv_type: str, visited: Optional[Set[str]] = None):
        """
        Load service request and response types from a .srv file

        Args:
            srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")
            visited: Set of already visited types to prevent cycles
        """
        if visited is None:
            visited = set()

        # Parse service type to get request and response types
        parts = srv_type.split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid service type format: {srv_type}")

        namespace_part, srv, service_name_part = parts
        request_type = f"{namespace_part}/srv/{service_name_part}_Request"
        response_type = f"{namespace_part}/srv/{service_name_part}_Response"

        if request_type in visited or response_type in visited:
            return

        visited.add(request_type)
        visited.add(response_type)

        # Load the service file
        srv_file = self.get_srv_file_path(srv_type)
        if not srv_file:
            raise FileNotFoundError(
                f"Service file not found for type: {srv_type}. "
                f"Please ensure the service type is available in the message registry or provide the service definition manually."
            )

        # Read service definition
        try:
            with open(srv_file, 'r') as f:
                srv_definition = f.read()
        except Exception as e:
            raise IOError(f"Failed to read service file {srv_file}: {e}") from e

        # Split into request and response parts
        parts = srv_definition.split('---')
        if len(parts) != 2:
            raise ValueError(
                f"Invalid service file format for {srv_type}: expected '---' separator. "
                f"Found {len(parts)} parts instead of 2."
            )

        request_definition = parts[0].strip()
        response_definition = parts[1].strip()

        if not request_definition:
            raise ValueError(f"Empty request definition in service file for {srv_type}")
        if not response_definition:
            raise ValueError(f"Empty response definition in service file for {srv_type}")

        # Extract dependencies for request and response
        request_deps = self._extract_dependencies(request_definition, request_type)
        response_deps = self._extract_dependencies(response_definition, response_type)

        # Load dependencies first
        for dep_type in request_deps + response_deps:
            if dep_type not in self._loaded_types and dep_type not in visited:
                try:
                    self._load_dependencies(dep_type, visited.copy())
                except Exception as e:
                    logger.error(
                        f"Failed to load dependency {dep_type} for service {srv_type}: {e}. "
                        f"This may cause service type registration to fail."
                    )
                    # Continue loading other dependencies, but log the error
                    # The registration will fail later if the dependency is truly required

        # Register request and response types
        try:
            if request_type not in self.session._registered_types:
                self.session.register_message_type(request_definition, request_type)
            if response_type not in self.session._registered_types:
                self.session.register_message_type(response_definition, response_type)
        except Exception as e:
            raise RuntimeError(
                f"Failed to register service types for {srv_type}: {e}. "
                f"Request type: {request_type}, Response type: {response_type}"
            ) from e

        self._loaded_types.add(request_type)
        self._loaded_types.add(response_type)

    def load_service_type(self, srv_type: str) -> bool:
        """
        Load a service type (request and response) and their dependencies

        Args:
            srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self._load_service_types(srv_type)
            return True
        except Exception as e:
            logger.warning(f"Failed to load service type {srv_type}: {e}", exc_info=True)
            return False

    def _load_dependencies(self, msg_type: str, visited: Optional[Set[str]] = None):
        """
        Recursively load message type and its dependencies

        Args:
            msg_type: ROS2 message type to load
            visited: Set of already visited types to prevent cycles
        """
        if visited is None:
            visited = set()

        if msg_type in visited or msg_type in self._loaded_types:
            return

        visited.add(msg_type)

        # Load the message file (checks local first, then downloads from git if needed)
        msg_file = self.get_msg_file_path(msg_type)
        if not msg_file:
            # Try one more time after potential download
            msg_file = self.get_msg_file_path(msg_type)
            if not msg_file:
                # Message file not found - raise exception so it can be caught and logged
                raise FileNotFoundError(f"Message file not found for type: {msg_type}")

        # Read message definition
        with open(msg_file, 'r') as f:
            msg_definition = f.read()

        # Parse dependencies from the message definition
        dependencies = self._extract_dependencies(msg_definition, msg_type)

        # Load dependencies first (recursively)
        for dep_type in dependencies:
            if dep_type not in self._loaded_types:
                self._load_dependencies(dep_type, visited.copy())

        # Register this message type (only if not already registered)
        if msg_type not in self.session._registered_types:
            self.session.register_message_type(msg_definition, msg_type)
        self._loaded_types.add(msg_type)

    def _extract_dependencies(self, msg_definition: str, current_type: str) -> list:
        """
        Extract message type dependencies from a message definition

        Args:
            msg_definition: Message definition text
            current_type: Current message type (for namespace resolution)

        Returns:
            List of dependency message types
        """
        dependencies = []
        parts = current_type.split("/")
        if len(parts) != 3:
            return dependencies

        namespace, _, _ = parts

        # Parse lines to find type references
        for line in msg_definition.split('\n'):
            # Remove comments first
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            # Skip empty lines
            if not line:
                continue

            # Skip separator lines
            if line.startswith('---'):
                continue

            # Check for type references (format: TypeName field_name)
            words = line.split()
            if len(words) >= 2:
                type_name = words[0]

                # Strip array notation: string[] -> string, geometry_msgs/msg/Vector3[10] -> geometry_msgs/msg/Vector3
                base_type = type_name
                if '[' in type_name:
                    base_type = type_name.split('[')[0]

                # Check if it's a custom type (not a primitive)
                primitives = ['bool', 'int8', 'uint8', 'int16', 'uint16',
                            'int32', 'uint32', 'int64', 'uint64',
                            'float32', 'float64', 'string', 'time', 'duration']

                if base_type not in primitives and not base_type.startswith('['):
                    # Resolve namespace
                    if '/' in base_type:
                        # Could be: builtin_interfaces/Time or geometry_msgs/msg/Vector3
                        parts = base_type.split('/')
                        if len(parts) == 2:
                            # Format: namespace/TypeName -> convert to namespace/msg/TypeName
                            dep_type = f"{parts[0]}/msg/{parts[1]}"
                        else:
                            # Already full path: namespace/msg/TypeName
                            dep_type = base_type
                    else:
                        # Short name: assume same namespace
                        dep_type = f"{namespace}/msg/{base_type}"

                    if dep_type not in dependencies:
                        dependencies.append(dep_type)

        return dependencies

    def load_message_type(self, msg_type: str) -> bool:
        """
        Load a message type and its dependencies

        Args:
            msg_type: ROS2 message type (e.g., "geometry_msgs/msg/Twist")

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self._load_dependencies(msg_type)
            return True
        except Exception as e:
            logger.warning(f"Failed to load message type {msg_type}: {e}")
            return False

    def get_message_class(self, msg_type: str) -> Optional[Type[Any]]:
        """
        Get a message class for a given type (loads if not already loaded)

        Args:
            msg_type: ROS2 message type

        Returns:
            Optional[Type[Any]]: Message class or None if not found
        """
        if msg_type not in self._loaded_types:
            # Service request/response types cannot be loaded from a single .msg file path.
            # They must be loaded from the parent .srv file.
            is_service_req_resp = (
                "/srv/" in msg_type and (msg_type.endswith("_Request") or msg_type.endswith("_Response"))
            )
            if is_service_req_resp:
                # example_interfaces/srv/AddTwoInts_Request -> example_interfaces/srv/AddTwoInts
                if msg_type.endswith("_Request"):
                    base_srv = msg_type[:-8]
                else:
                    base_srv = msg_type[:-9]
                if not self.load_service_type(base_srv):
                    return None
            else:
                if not self.load_message_type(msg_type):
                    return None

        # Check if we have a mapping to the actual store key (for service types)
        actual_key = self.session._registered_types.get(msg_type)
        if actual_key and isinstance(actual_key, str):
            # actual_key is the store key (may be converted name)
            return self.session.store.types.get(actual_key)

        # Try direct lookup
        msg_class = self.session.store.types.get(msg_type)
        if msg_class is not None:
            return msg_class

        # Try with /msg/ inserted (for service types: srv/ -> srv/msg/)
        if '/srv/' in msg_type:
            converted_name = msg_type.replace('/srv/', '/srv/msg/')
            return self.session.store.types.get(converted_name)

        return None

    def is_loaded(self, msg_type: str) -> bool:
        """Check if a message type is already loaded"""
        return msg_type in self._loaded_types


# Global registry instance
_registry = None


def get_registry(messages_dir: Optional[str] = None) -> MessageRegistry:
    """Get or create the global message registry"""
    global _registry
    if _registry is None:
        _registry = MessageRegistry(messages_dir)
    return _registry


def load_message_type(msg_type: str, messages_dir: Optional[str] = None) -> bool:
    """
    Convenience function to load a message type

    Args:
        msg_type: ROS2 message type (e.g., "geometry_msgs/msg/Twist")
        messages_dir: Optional custom messages directory

    Returns:
        True if loaded successfully
    """
    registry = get_registry(messages_dir)
    return registry.load_message_type(msg_type)


def get_message_class(msg_type: str, messages_dir: Optional[str] = None) -> Optional[Type[Any]]:
    """
    Convenience function to get a message class

    Args:
        msg_type: ROS2 message type
        messages_dir: Optional custom messages directory

    Returns:
        Optional[Type[Any]]: Message class or None
    """
    registry = get_registry(messages_dir)
    return registry.get_message_class(msg_type)


def load_service_type(srv_type: str, messages_dir: Optional[str] = None) -> bool:
    """
    Convenience function to load a service type

    Args:
        srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")
        messages_dir: Optional custom messages directory

    Returns:
        True if loaded successfully
    """
    registry = get_registry(messages_dir)
    return registry.load_service_type(srv_type)
