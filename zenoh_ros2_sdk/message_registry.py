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

        request_definition_reg = self._expand_type_refs(request_definition, namespace_part)
        response_definition_reg = self._expand_type_refs(response_definition, namespace_part)

        # Extract dependencies for request and response
        request_deps = self._extract_dependencies(request_definition, request_type)
        response_deps = self._extract_dependencies(response_definition, response_type)

        # Load dependencies first
        for dep_type in request_deps + response_deps:
            if dep_type not in self._loaded_types and dep_type not in visited:
                try:
                    self._load_dependencies(dep_type, visited.copy())
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load dependency {dep_type} for service {srv_type}: {e}"
                    ) from e

        # Register request and response types
        try:
            if request_type not in self.session._registered_types:
                self.session.register_message_type(request_definition_reg, request_type)
            if response_type not in self.session._registered_types:
                self.session.register_message_type(response_definition_reg, response_type)
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

    def get_action_file_path(self, action_type: str) -> Optional[Path]:
        """
        Get the path to a .action file for a given action type.
        First checks local messages directory, then tries to download from git.

        Args:
            action_type: ROS2 action type (e.g., "example_interfaces/action/Fibonacci")

        Returns:
            Path to .action file or None if not found
        """
        parts = action_type.split("/")
        if len(parts) != 3 or parts[1] != "action":
            return None

        namespace, _, action_name = parts

        # First, check local messages directory
        action_file = self.messages_dir / namespace / "action" / f"{action_name}.action"
        if action_file.exists():
            return action_file

        # If not found locally, try to download from git repository
        try:
            repo_name = get_repository_for_package(namespace)
            if repo_name:
                try:
                    repo_path = clone_to_cache(repo_name)
                    repository = MESSAGE_REPOSITORIES[repo_name]

                    # Reuse construct_message_path with "action" as the type/extension
                    action_file_path = construct_message_path(
                        repo_path, repository, namespace, "action", action_name
                    )

                    if os.path.exists(action_file_path):
                        return Path(action_file_path)
                except Exception as e:
                    logger.warning(
                        f"Failed to get action file from cache for {action_type}: {e}. "
                        f"Trying to clone repository..."
                    )
        except ImportError as e:
            logger.warning(
                f"GitPython not available. Cannot auto-download action file for {action_type}. "
                f"Install GitPython with 'pip install GitPython' to enable auto-download. "
                f"Error: {e}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to auto-download action file for {action_type} from git repository: {e}. "
                f"You may need to add the action file manually."
            )

        return None

    def _expand_type_refs(self, definition: str, package: str) -> str:
        """Expand short/two-part type names to fully qualified 3-part names.

        When rosbags registers a type under a non-msg namespace (e.g. action),
        it resolves unqualified field type names relative to that namespace.
        Expanding them here ensures rosbags finds the already-loaded msg types.

        'Foo'         -> '{package}/msg/Foo'
        'pkg/Foo'     -> 'pkg/msg/Foo'
        'pkg/msg/Foo' -> unchanged
        Primitives    -> unchanged
        """
        primitives = {
            'bool', 'int8', 'uint8', 'int16', 'uint16',
            'int32', 'uint32', 'int64', 'uint64',
            'float32', 'float64', 'string', 'time', 'duration',
            'byte', 'char', 'wchar', 'wstring', 'octet',
        }
        result_lines = []
        for line in definition.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('---'):
                result_lines.append(line)
                continue
            # Split off inline comment
            code_part = line
            comment_part = ''
            if '#' in line:
                idx = line.index('#')
                code_part = line[:idx]
                comment_part = line[idx:]
            words = code_part.split()
            if len(words) >= 2:
                type_token = words[0]
                base_type = type_token
                array_suffix = ''
                if '[' in type_token:
                    bracket_idx = type_token.index('[')
                    base_type = type_token[:bracket_idx]
                    array_suffix = type_token[bracket_idx:]
                if base_type not in primitives:
                    parts = base_type.split('/')
                    if len(parts) == 1:
                        expanded = f"{package}/msg/{base_type}"
                    elif len(parts) == 2:
                        expanded = f"{parts[0]}/msg/{parts[1]}"
                    else:
                        expanded = base_type
                    new_token = expanded + array_suffix
                    result_lines.append(code_part.replace(type_token, new_token, 1) + comment_part)
                    continue
            result_lines.append(line)
        return '\n'.join(result_lines)

    def _load_action_types(self, action_type: str, visited: Optional[Set[str]] = None):
        """
        Load all action sub-types synthesized from a .action file.

        A .action file has three sections separated by '---':
          1. Goal fields
          2. Result fields
          3. Feedback fields

        This method synthesizes and registers the following types:
          - {Name}_Goal, {Name}_Result, {Name}_Feedback  (raw sections)
          - {Name}_SendGoal_Request/Response
          - {Name}_GetResult_Request/Response
          - {Name}_FeedbackMessage
        It also loads the standard action_msgs types (CancelGoal, GoalStatusArray).

        Args:
            action_type: ROS2 action type (e.g., "fibonacci/action/Fibonacci")
            visited: Set of already visited types to prevent cycles
        """
        if visited is None:
            visited = set()

        parts = action_type.split("/")
        if len(parts) != 3 or parts[1] != "action":
            raise ValueError(
                f"Invalid action type format: {action_type}. Expected: pkg/action/Name"
            )

        pkg, _, name = parts

        # All synthesized type names
        goal_type = f"{action_type}_Goal"
        result_type = f"{action_type}_Result"
        feedback_type = f"{action_type}_Feedback"
        send_goal_req_type = f"{action_type}_SendGoal_Request"
        send_goal_resp_type = f"{action_type}_SendGoal_Response"
        get_result_req_type = f"{action_type}_GetResult_Request"
        get_result_resp_type = f"{action_type}_GetResult_Response"
        feedback_msg_type = f"{action_type}_FeedbackMessage"

        all_synthesized = [
            goal_type, result_type, feedback_type,
            send_goal_req_type, send_goal_resp_type,
            get_result_req_type, get_result_resp_type,
            feedback_msg_type,
        ]

        # Guard: skip if all sub-types are already loaded
        if all(t in self._loaded_types for t in all_synthesized):
            return

        # Find and read the .action file
        action_file = self.get_action_file_path(action_type)
        if not action_file:
            raise FileNotFoundError(
                f"Action file not found for type: {action_type}. "
                "Please ensure the action type is available in the message registry "
                "or provide the action definition manually."
            )

        try:
            with open(action_file, 'r') as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"Failed to read action file {action_file}: {e}") from e

        sections = content.split('---')
        if len(sections) != 3:
            raise ValueError(
                f"Invalid action file format for {action_type}: "
                f"expected 3 sections separated by '---', got {len(sections)}"
            )

        goal_def = sections[0].strip()
        result_def = sections[1].strip()
        feedback_def = sections[2].strip()

        # Expand short/two-part type names to fully qualified names so that
        # rosbags resolves them correctly regardless of the action sub-namespace.
        goal_def_reg = self._expand_type_refs(goal_def, pkg)
        result_def_reg = self._expand_type_refs(result_def, pkg)
        feedback_def_reg = self._expand_type_refs(feedback_def, pkg)

        # Standard types used in synthesized definitions
        uuid_type = "unique_identifier_msgs/msg/UUID"
        time_type = "builtin_interfaces/msg/Time"

        # --- Load standard infrastructure dependencies first ---
        for dep in [uuid_type, time_type]:
            if dep not in self._loaded_types and dep not in visited:
                try:
                    self._load_dependencies(dep, visited.copy())
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load standard dependency {dep} for action {action_type}: {e}"
                    ) from e

        # --- Load goal/result/feedback field dependencies ---
        for raw_def, raw_type in [
            (goal_def, goal_type),
            (result_def, result_type),
            (feedback_def, feedback_type),
        ]:
            for dep in self._extract_dependencies(raw_def, raw_type):
                if dep not in self._loaded_types and dep not in visited:
                    try:
                        self._load_dependencies(dep, visited.copy())
                    except Exception as e:
                        raise RuntimeError(
                            f"Failed to load dependency {dep} for action {action_type}: {e}"
                        ) from e

        # --- Register Goal, Result, Feedback from raw action file sections ---
        for reg_def, raw_type in [
            (goal_def_reg, goal_type),
            (result_def_reg, result_type),
            (feedback_def_reg, feedback_type),
        ]:
            if raw_type not in self.session._registered_types:
                self.session.register_message_type(reg_def, raw_type)
            self._loaded_types.add(raw_type)

        # --- Synthesize and register composite types ---
        # SendGoal: request = UUID goal_id + Goal goal, response = bool accepted + Time stamp
        send_goal_req_def = (
            f"{uuid_type} goal_id\n"
            f"{goal_type} goal"
        )
        send_goal_resp_def = (
            f"bool accepted\n"
            f"{time_type} stamp"
        )
        # GetResult: request = UUID goal_id, response = int8 status + Result result
        get_result_req_def = f"{uuid_type} goal_id"
        get_result_resp_def = (
            f"int8 status\n"
            f"{result_type} result"
        )
        # FeedbackMessage: UUID goal_id + Feedback feedback
        feedback_msg_def = (
            f"{uuid_type} goal_id\n"
            f"{feedback_type} feedback"
        )

        for syn_def, syn_type in [
            (send_goal_req_def, send_goal_req_type),
            (send_goal_resp_def, send_goal_resp_type),
            (get_result_req_def, get_result_req_type),
            (get_result_resp_def, get_result_resp_type),
            (feedback_msg_def, feedback_msg_type),
        ]:
            if syn_type not in self.session._registered_types:
                self.session.register_message_type(syn_def, syn_type)
            self._loaded_types.add(syn_type)

        # --- Load standard cancel_goal and status types ---
        cancel_srv = "action_msgs/srv/CancelGoal"
        cancel_req_type = "action_msgs/srv/CancelGoal_Request"
        if cancel_req_type not in self._loaded_types:
            try:
                self._load_service_types(cancel_srv, visited.copy())
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load cancel_goal service type for {action_type}: {e}"
                ) from e

        status_msg = "action_msgs/msg/GoalStatusArray"
        if status_msg not in self._loaded_types:
            try:
                self._load_dependencies(status_msg, visited.copy())
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load GoalStatusArray for {action_type}: {e}"
                ) from e

        self._loaded_types.add(action_type)

    def load_action_type(self, action_type: str) -> bool:
        """
        Load an action type and all its synthesized sub-types.

        Args:
            action_type: ROS2 action type (e.g., "fibonacci/action/Fibonacci")

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self._load_action_types(action_type)
            return True
        except Exception as e:
            logger.warning(f"Failed to load action type {action_type}: {e}", exc_info=True)
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
                            'float32', 'float64', 'string', 'time', 'duration',
                            'byte', 'char', 'wchar', 'wstring', 'octet']

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


def load_action_type(action_type: str, messages_dir: Optional[str] = None) -> bool:
    """
    Convenience function to load an action type and all its synthesized sub-types.

    Args:
        action_type: ROS2 action type (e.g., "fibonacci/action/Fibonacci")
        messages_dir: Optional custom messages directory

    Returns:
        True if loaded successfully
    """
    registry = get_registry(messages_dir)
    return registry.load_action_type(action_type)
