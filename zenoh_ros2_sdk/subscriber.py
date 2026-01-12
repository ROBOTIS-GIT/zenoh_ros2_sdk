"""
ROS2Subscriber - ROS2 Subscriber using Zenoh
"""
import uuid
from typing import Optional, Callable, Dict, Set

from .session import ZenohSession
from .utils import ros2_to_dds_type, get_type_hash
from .logger import get_logger

logger = get_logger("subscriber")


class ROS2Subscriber:
    """ROS2 Subscriber using Zenoh"""

    def __init__(
        self,
        topic: str,
        msg_type: str,
        callback: Callable,
        msg_definition: str = "",
        node_name: Optional[str] = None,
        namespace: str = "/",
        domain_id: int = 0,
        router_ip: str = "127.0.0.1",
        router_port: int = 7447,
        type_hash: Optional[str] = None
    ):
        """
        Create a ROS2 subscriber

        Args:
            topic: ROS2 topic name
            msg_type: ROS2 message type
            callback: Callback function(msg) called when message is received
            msg_definition: Message definition text (empty string to auto-load from registry)
            node_name: Node name (auto-generated if None)
            namespace: Node namespace
            domain_id: ROS domain ID
            router_ip: Zenoh router IP
            router_port: Zenoh router port
            type_hash: Message type hash (auto-detected if None)
        """
        self.topic = topic
        self.msg_type = msg_type
        self.callback = callback
        self.domain_id = domain_id
        self.namespace = namespace
        self.node_name = node_name or f"zenoh_subscriber_{uuid.uuid4().hex[:8]}"

        # Get or create shared session
        self.session_mgr = ZenohSession.get_instance(router_ip, router_port)

        # Register message type
        self.session_mgr.register_message_type(msg_definition, msg_type)

        # Get DDS type name
        self.dds_type_name = ros2_to_dds_type(msg_type)

        # Get type hash if not provided
        if type_hash is None:
            # Get message definition for hash computation
            hash_msg_definition = msg_definition
            if not hash_msg_definition:
                # Try to get from message registry
                try:
                    from .message_registry import get_registry
                    registry = get_registry()
                    msg_file = registry.get_msg_file_path(msg_type)
                    if msg_file and msg_file.exists():
                        with open(msg_file, 'r') as f:
                            hash_msg_definition = f.read()
                except Exception as e:
                    # Registry not available or file not found - will raise ValueError below
                    logger.debug(f"Could not load message definition from registry for {msg_type}: {e}")
                    pass

            if not hash_msg_definition:
                raise ValueError(
                    f"Cannot compute type hash for {msg_type}: message definition not provided. "
                    "Please provide msg_definition or ensure the message type is loaded in the registry."
                )

            # Get dependencies from message registry if available (recursively)
            dependencies = None
            try:
                from .message_registry import get_registry
                registry = get_registry()

                def load_dependencies_recursive(msg_type: str, msg_def: str, visited: Optional[Set[str]] = None) -> Dict[str, str]:
                    """Recursively load all dependencies including transitive ones."""
                    if visited is None:
                        visited = set()

                    if msg_type in visited:
                        return {}

                    visited.add(msg_type)
                    all_dependencies = {}

                    # Extract direct dependencies (pass full type name, not just namespace)
                    dep_types = registry._extract_dependencies(msg_def, msg_type)

                    for dep_type in dep_types:
                        if dep_type not in visited:
                            dep_file = registry.get_msg_file_path(dep_type)
                            if dep_file and dep_file.exists():
                                with open(dep_file, 'r') as f:
                                    dep_def = f.read()
                                all_dependencies[dep_type] = dep_def

                                # Recursively load dependencies of this dependency
                                nested_deps = load_dependencies_recursive(dep_type, dep_def, visited)
                                all_dependencies.update(nested_deps)

                    return all_dependencies

                # Load all dependencies recursively
                dependencies = load_dependencies_recursive(msg_type, hash_msg_definition)
            except Exception as e:
                # If dependency loading fails, continue without dependencies
                # Type hash computation will still work, just without nested type info
                logger.debug(f"Could not load dependencies for {msg_type}: {e}")
                pass

            type_hash = get_type_hash(msg_type, msg_definition=hash_msg_definition, dependencies=dependencies)
        self.type_hash = type_hash

        # Build keyexpr
        fully_qualified_name = topic.lstrip("/")
        self.keyexpr = f"{domain_id}/{fully_qualified_name}/{self.dds_type_name}/{type_hash}"

        # Create subscriber
        self.sub = self.session_mgr.session.declare_subscriber(self.keyexpr, self._listener)
        self._closed = False

    def _listener(self, sample):
        """Internal message listener"""
        try:
            cdr_bytes = bytes(sample.payload)
            msg = self.session_mgr.store.deserialize_cdr(cdr_bytes, self.msg_type)
            self.callback(msg)
        except Exception as e:
            logger.error(f"Error deserializing message on topic {self.topic}: {e}", exc_info=True)

    def close(self):
        """
        Close the subscriber and cleanup resources.

        This method is idempotent - it's safe to call multiple times.
        """
        # Check if already closed
        if hasattr(self, '_closed') and self._closed:
            return

        try:
            if hasattr(self, 'sub') and self.sub is not None:
                # Zenoh subscribers have an undeclare() method to explicitly remove them
                # This is the proper way to clean up a subscriber
                if hasattr(self.sub, 'undeclare'):
                    self.sub.undeclare()
                # Mark as closed
                self.sub = None
            self._closed = True
        except (AttributeError, RuntimeError) as e:
            # AttributeError: subscriber doesn't exist or undeclare method not available
            # RuntimeError: Zenoh runtime errors
            logger.debug(f"Error during subscriber cleanup for topic {self.topic}: {e}")
            # Mark as closed even if undeclare failed to prevent retry loops
            self._closed = True
        except Exception as e:
            # Catch any other unexpected exceptions during cleanup
            # Log at warning level since this is unexpected
            logger.warning(f"Unexpected error during subscriber cleanup for topic {self.topic}: {e}")
            self._closed = True
