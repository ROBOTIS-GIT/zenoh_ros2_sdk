"""
Message Registry - Loads and manages ROS2 message definitions from .msg files
"""
import os
from pathlib import Path
from typing import Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import ZenohSession


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
        # Import here to avoid circular import
        from .session import ZenohSession
        self.session = ZenohSession.get_instance()
        self._loaded_types: Set[str] = set()
    
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
            from ._cache import get_message_file_path, get_repository_for_package
            
            # Find which repository contains this package
            repo_name = get_repository_for_package(namespace)
            if repo_name:
                git_path = get_message_file_path(msg_type, repo_name)
                if git_path and os.path.exists(git_path):
                    return Path(git_path)
        except ImportError:
            # GitPython not available, skip auto-download
            pass
        except Exception as e:
            # Silently fail - user can add message manually
            pass
        
        return None
    
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
                return
        
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
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Skip separator lines
            if line.startswith('---'):
                continue
            
            # Check for type references (format: TypeName field_name)
            words = line.split()
            if len(words) >= 2:
                type_name = words[0]
                # Check if it's a custom type (not a primitive)
                primitives = ['bool', 'int8', 'uint8', 'int16', 'uint16', 
                            'int32', 'uint32', 'int64', 'uint64', 
                            'float32', 'float64', 'string', 'time', 'duration']
                
                if type_name not in primitives and not type_name.startswith('['):
                    # Resolve namespace
                    if '/' in type_name:
                        # Full path: geometry_msgs/msg/Vector3
                        dep_type = type_name
                    else:
                        # Short name: assume same namespace
                        dep_type = f"{namespace}/msg/{type_name}"
                    
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
            print(f"Warning: Failed to load message type {msg_type}: {e}")
            return False
    
    def get_message_class(self, msg_type: str):
        """
        Get a message class for a given type (loads if not already loaded)
        
        Args:
            msg_type: ROS2 message type
            
        Returns:
            Message class or None if not found
        """
        if msg_type not in self._loaded_types:
            if not self.load_message_type(msg_type):
                return None
        
        return self.session.store.types.get(msg_type)
    
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


def get_message_class(msg_type: str, messages_dir: Optional[str] = None):
    """
    Convenience function to get a message class
    
    Args:
        msg_type: ROS2 message type
        messages_dir: Optional custom messages directory
        
    Returns:
        Message class or None
    """
    registry = get_registry(messages_dir)
    return registry.get_message_class(msg_type)
