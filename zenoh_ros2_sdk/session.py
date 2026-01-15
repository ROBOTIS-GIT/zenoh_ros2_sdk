"""
ZenohSession - Manages shared Zenoh session and type store
"""
import os
import json
import json5
import zenoh
import uuid
import threading
from rosbags.typesys import get_types_from_msg, get_typestore, Stores
from .message_registry import get_registry, load_service_type
from .logger import get_logger

logger = get_logger("session")


def _parse_zenoh_config_override(override: str) -> list[tuple[str, str]]:
    """
    Parse `ZENOH_CONFIG_OVERRIDE`-style strings into (path, json5_value) pairs.

    Format:
      "path/to/key=value;other/key=[1,2,3];mode=\"client\""

    Notes:
    - Values are passed verbatim to `zenoh.Config.insert_json5`.
    - Splits on ';' (no escaping supported).
    """
    if override is None:
        return []
    override = override.strip()
    if not override:
        return []

    pairs: list[tuple[str, str]] = []
    for part in override.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(
                f"Invalid ZENOH_CONFIG_OVERRIDE segment {part!r}: expected 'path=value'"
            )
        path, value = part.split("=", 1)
        path = path.strip()
        value = value.strip()
        if not path:
            raise ValueError(
                f"Invalid ZENOH_CONFIG_OVERRIDE segment {part!r}: empty path"
            )
        if value == "":
            raise ValueError(
                f"Invalid ZENOH_CONFIG_OVERRIDE segment {part!r}: empty value"
            )
        pairs.append((path, value))
    return pairs


def _apply_zenoh_config_override(conf: "zenoh.Config", override: str) -> None:
    """
    Apply override pairs onto an existing config (later entries win).

    Values are parsed as JSON5 first (like ros-z), then serialized to JSON
    before being passed to `insert_json5`.
    """
    for path, json5_value in _parse_zenoh_config_override(override):
        try:
            parsed = json5.loads(json5_value)
        except Exception as e:
            raise ValueError(
                f"Failed to parse ZENOH_CONFIG_OVERRIDE value as JSON5 for key {path!r}: "
                f"{json5_value!r} ({e})"
            ) from e

        # Serialize to JSON; zenoh's insert_json5 accepts JSON too.
        value_str = json.dumps(parsed)
        conf.insert_json5(path, value_str)


class ZenohSession:
    """Manages a shared Zenoh session and type store"""
    _instance = None
    _lock = threading.Lock()

    def __init__(self, router_ip: str = "127.0.0.1", router_port: int = 7447):
        self.router_ip = router_ip
        self.router_port = router_port
        self.conf = zenoh.Config()
        # Defaults (can be overridden via ZENOH_CONFIG_OVERRIDE)
        self.conf.insert_json5(
            "connect/endpoints", f'["tcp/{router_ip}:{router_port}"]'
        )

        override = os.environ.get("ZENOH_CONFIG_OVERRIDE", "").strip()
        if override:
            _apply_zenoh_config_override(self.conf, override)

        self.session = zenoh.open(self.conf)
        self.store = get_typestore(Stores.EMPTY)
        self._registered_types = {}
        self._node_counter = 0
        self._entity_counter = 0
        self._lock = threading.Lock()

        # Get session ID
        session_info = self.session.info
        self.session_id = str(session_info.zid())
        self.liveliness = self.session.liveliness()

    @classmethod
    def get_instance(cls, router_ip: str = "127.0.0.1", router_port: int = 7447):
        """Get or create singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(router_ip, router_port)
        return cls._instance

    def register_message_type(self, msg_definition: str, ros2_type_name: str):
        """Register a ROS2 message type"""
        # Check if already registered and in store
        if ros2_type_name in self._registered_types:
            # Get the actual store key (may be converted name for service types)
            actual_key = self._registered_types[ros2_type_name]
            if isinstance(actual_key, str):
                # actual_key is the store key
                msg_class = self.store.types.get(actual_key)
                if msg_class is not None:
                    return msg_class
            else:
                # actual_key is the types dict (old format), try direct lookup
                msg_class = self.store.types.get(ros2_type_name)
                if msg_class is not None:
                    return msg_class
                # Try converted name for service types
                if '/srv/' in ros2_type_name:
                    converted_name = ros2_type_name.replace('/srv/', '/srv/msg/')
                    msg_class = self.store.types.get(converted_name)
                    if msg_class is not None:
                        # Update mapping to use converted name
                        self._registered_types[ros2_type_name] = converted_name
                        return msg_class

            # If in _registered_types but not in store, something went wrong - clear it
            logger.warning(f"Type {ros2_type_name} was marked as registered but not in store, re-registering")
            del self._registered_types[ros2_type_name]

        # If msg_definition is empty, try to load from message registry
        if not msg_definition.strip():
            registry = get_registry()

            # Check if this is a service request/response type
            # Service types are like "namespace/srv/ServiceName_Request" or "namespace/srv/ServiceName_Response"
            is_service_type = '/srv/' in ros2_type_name and ('_Request' in ros2_type_name or '_Response' in ros2_type_name)

            if is_service_type:
                # For service types, we need to load the service type first
                # Extract service type from request/response type
                # e.g., "example_interfaces/srv/AddTwoInts_Request" -> "example_interfaces/srv/AddTwoInts"
                if ros2_type_name.endswith('_Request'):
                    srv_type = ros2_type_name[:-8]  # Remove "_Request"
                elif ros2_type_name.endswith('_Response'):
                    srv_type = ros2_type_name[:-9]  # Remove "_Response"
                else:
                    srv_type = None

                if srv_type:
                    # Load the service type - this will register both request and response types
                    if load_service_type(srv_type):
                        # After loading, check if the type is now in _registered_types
                        # (load_service_type calls register_message_type which adds it)
                        if ros2_type_name in self._registered_types:
                            # Type was registered, get it from store using the actual key
                            actual_key = self._registered_types[ros2_type_name]
                            if isinstance(actual_key, str):
                                msg_class = self.store.types.get(actual_key)
                                if msg_class is not None:
                                    return msg_class

                        # If not found via _registered_types, try direct lookup (both original and converted names)
                        # Try converted name first (rosbags stores service types with /srv/msg/)
                        converted_name = ros2_type_name.replace('/srv/', '/srv/msg/')
                        msg_class = self.store.types.get(converted_name)
                        if msg_class is not None:
                            self._registered_types[ros2_type_name] = converted_name
                            return msg_class

                        # Try original name
                        msg_class = self.store.types.get(ros2_type_name)
                        if msg_class is not None:
                            self._registered_types[ros2_type_name] = ros2_type_name
                            return msg_class

            # For regular message types, use the existing logic
            if registry.is_loaded(ros2_type_name):
                # Already loaded, check if it's in the store (try both original and converted names)
                msg_class = self.store.types.get(ros2_type_name)
                if msg_class is None and '/srv/' in ros2_type_name:
                    # Try converted name for service types
                    converted_name = ros2_type_name.replace('/srv/', '/srv/msg/')
                    msg_class = self.store.types.get(converted_name)
                    if msg_class is not None:
                        self._registered_types[ros2_type_name] = converted_name
                        return msg_class
                if msg_class is not None:
                    # Store the mapping (use original name as key if found directly)
                    self._registered_types[ros2_type_name] = ros2_type_name
                    return msg_class
            elif registry.load_message_type(ros2_type_name):
                # Successfully loaded from registry, try both original and converted names
                msg_class = self.store.types.get(ros2_type_name)
                if msg_class is None and '/srv/' in ros2_type_name:
                    # Try converted name for service types
                    converted_name = ros2_type_name.replace('/srv/', '/srv/msg/')
                    msg_class = self.store.types.get(converted_name)
                    if msg_class is not None:
                        self._registered_types[ros2_type_name] = converted_name
                        return msg_class
                if msg_class is not None:
                    # Store the mapping (use original name as key if found directly)
                    self._registered_types[ros2_type_name] = ros2_type_name
                    return msg_class

            # If we get here, the type wasn't found or couldn't be loaded
            raise ValueError(
                f"Message type {ros2_type_name} not found in registry and no definition provided. "
                f"Please provide msg_definition or ensure the message type is loaded."
            )

        # Register the type from the provided definition
        try:
            types = get_types_from_msg(msg_definition, ros2_type_name)
            self.store.register(types)

            # get_types_from_msg may convert the type name (e.g., srv/TypeName -> srv/msg/TypeName)
            # Find the actual key that was registered in the store
            actual_type_key = None
            for key in types.keys():
                # Check if this key matches our type name
                if key == ros2_type_name:
                    actual_type_key = key
                    break
                # Handle conversion: srv/TypeName -> srv/msg/TypeName
                # Check if the key is a converted version of our type name
                if '/srv/' in ros2_type_name and '/srv/msg/' in key:
                    # Extract the base name (everything after srv/)
                    our_base = ros2_type_name.split('/srv/')[1]
                    store_base = key.split('/srv/msg/')[1]
                    if our_base == store_base:
                        actual_type_key = key
                        break

            # If no match found, use the first (and likely only) key from types
            if actual_type_key is None and types:
                actual_type_key = list(types.keys())[0]

            # Store mapping: our type name -> actual store key
            if actual_type_key:
                self._registered_types[ros2_type_name] = actual_type_key
                msg_class = self.store.types.get(actual_type_key)
                if msg_class is not None:
                    return msg_class
        except Exception as e:
            raise RuntimeError(
                f"Failed to register message type {ros2_type_name}: {e}"
            ) from e

        # Handle name conversion: rosbags converts srv/TypeName to srv/msg/TypeName
        # Try original name first, then converted name
        msg_class = self.store.types.get(ros2_type_name)
        if msg_class is None:
            # Try with /msg/ inserted (for service types: srv/ -> srv/msg/)
            if '/srv/' in ros2_type_name:
                converted_name = ros2_type_name.replace('/srv/', '/srv/msg/')
                msg_class = self.store.types.get(converted_name)
                if msg_class is not None:
                    # Cache the mapping for future lookups
                    self._registered_types[ros2_type_name] = converted_name
                    return msg_class

        if msg_class is None:
            # Provide helpful error message
            tried_names = [ros2_type_name]
            if '/srv/' in ros2_type_name:
                tried_names.append(ros2_type_name.replace('/srv/', '/srv/msg/'))
            available = [k for k in self.store.types.keys() if ros2_type_name.split('/')[-1] in k][:5]
            raise KeyError(
                f"Message type {ros2_type_name} was registered but not found in store. "
                f"Tried: {tried_names}. "
                f"Available matching types: {available}"
            )
        return msg_class

    def get_next_node_id(self):
        """Get next available node ID"""
        with self._lock:
            node_id = self._node_counter
            self._node_counter += 1
            return node_id

    def get_next_entity_id(self):
        """Get next available entity ID"""
        with self._lock:
            entity_id = self._entity_counter
            self._entity_counter += 1
            return entity_id

    def generate_gid(self) -> bytes:
        """Generate a unique GID (16 bytes)"""
        # Use UUID to generate unique GID
        uuid_bytes = uuid.uuid4().bytes
        return uuid_bytes

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
            self._instance = None
