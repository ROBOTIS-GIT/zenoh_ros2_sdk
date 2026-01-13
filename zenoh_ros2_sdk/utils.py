"""
Utility functions for type conversion and message handling
"""
import hashlib
import json
import re
from copy import deepcopy
from typing import Dict, List, Optional, Set

# RIHS constants
RIHS01_PREFIX = 'RIHS01_'
RIHS01_HASH_VALUE_SIZE = 32

# Field type mappings (from type_description_interfaces/msgs/FieldType.msg)
# Copied directly from rosidl_generator_type_description to ensure exact match
FIELD_TYPE_NAME_TO_ID = {
    'FIELD_TYPE_NOT_SET': 0,

    # Nested type defined in other .msg/.idl files.
    'FIELD_TYPE_NESTED_TYPE': 1,

    # Basic Types
    # Integer Types
    'FIELD_TYPE_INT8': 2,
    'FIELD_TYPE_UINT8': 3,
    'FIELD_TYPE_INT16': 4,
    'FIELD_TYPE_UINT16': 5,
    'FIELD_TYPE_INT32': 6,
    'FIELD_TYPE_UINT32': 7,
    'FIELD_TYPE_INT64': 8,
    'FIELD_TYPE_UINT64': 9,

    # Floating-Point Types
    'FIELD_TYPE_FLOAT': 10,
    'FIELD_TYPE_DOUBLE': 11,
    'FIELD_TYPE_LONG_DOUBLE': 12,

    # Char and WChar Types
    'FIELD_TYPE_CHAR': 13,
    'FIELD_TYPE_WCHAR': 14,

    # Boolean Type
    'FIELD_TYPE_BOOLEAN': 15,

    # Byte/Octet Type
    'FIELD_TYPE_BYTE': 16,

    # String Types
    'FIELD_TYPE_STRING': 17,
    'FIELD_TYPE_WSTRING': 18,

    # Fixed String Types
    'FIELD_TYPE_FIXED_STRING': 19,
    'FIELD_TYPE_FIXED_WSTRING': 20,

    # Bounded String Types
    'FIELD_TYPE_BOUNDED_STRING': 21,
    'FIELD_TYPE_BOUNDED_WSTRING': 22,

    # Fixed Sized Array Types
    'FIELD_TYPE_NESTED_TYPE_ARRAY': 49,
    'FIELD_TYPE_INT8_ARRAY': 50,
    'FIELD_TYPE_UINT8_ARRAY': 51,
    'FIELD_TYPE_INT16_ARRAY': 52,
    'FIELD_TYPE_UINT16_ARRAY': 53,
    'FIELD_TYPE_INT32_ARRAY': 54,
    'FIELD_TYPE_UINT32_ARRAY': 55,
    'FIELD_TYPE_INT64_ARRAY': 56,
    'FIELD_TYPE_UINT64_ARRAY': 57,
    'FIELD_TYPE_FLOAT_ARRAY': 58,
    'FIELD_TYPE_DOUBLE_ARRAY': 59,
    'FIELD_TYPE_LONG_DOUBLE_ARRAY': 60,
    'FIELD_TYPE_CHAR_ARRAY': 61,
    'FIELD_TYPE_WCHAR_ARRAY': 62,
    'FIELD_TYPE_BOOLEAN_ARRAY': 63,
    'FIELD_TYPE_BYTE_ARRAY': 64,
    'FIELD_TYPE_STRING_ARRAY': 65,
    'FIELD_TYPE_WSTRING_ARRAY': 66,
    'FIELD_TYPE_FIXED_STRING_ARRAY': 67,
    'FIELD_TYPE_FIXED_WSTRING_ARRAY': 68,
    'FIELD_TYPE_BOUNDED_STRING_ARRAY': 69,
    'FIELD_TYPE_BOUNDED_WSTRING_ARRAY': 70,

    # Bounded Sequence Types
    'FIELD_TYPE_NESTED_TYPE_BOUNDED_SEQUENCE': 97,
    'FIELD_TYPE_INT8_BOUNDED_SEQUENCE': 98,
    'FIELD_TYPE_UINT8_BOUNDED_SEQUENCE': 99,
    'FIELD_TYPE_INT16_BOUNDED_SEQUENCE': 100,
    'FIELD_TYPE_UINT16_BOUNDED_SEQUENCE': 101,
    'FIELD_TYPE_INT32_BOUNDED_SEQUENCE': 102,
    'FIELD_TYPE_UINT32_BOUNDED_SEQUENCE': 103,
    'FIELD_TYPE_INT64_BOUNDED_SEQUENCE': 104,
    'FIELD_TYPE_UINT64_BOUNDED_SEQUENCE': 105,
    'FIELD_TYPE_FLOAT_BOUNDED_SEQUENCE': 106,
    'FIELD_TYPE_DOUBLE_BOUNDED_SEQUENCE': 107,
    'FIELD_TYPE_LONG_DOUBLE_BOUNDED_SEQUENCE': 108,
    'FIELD_TYPE_CHAR_BOUNDED_SEQUENCE': 109,
    'FIELD_TYPE_WCHAR_BOUNDED_SEQUENCE': 110,
    'FIELD_TYPE_BOOLEAN_BOUNDED_SEQUENCE': 111,
    'FIELD_TYPE_BYTE_BOUNDED_SEQUENCE': 112,
    'FIELD_TYPE_STRING_BOUNDED_SEQUENCE': 113,
    'FIELD_TYPE_WSTRING_BOUNDED_SEQUENCE': 114,
    'FIELD_TYPE_FIXED_STRING_BOUNDED_SEQUENCE': 115,
    'FIELD_TYPE_FIXED_WSTRING_BOUNDED_SEQUENCE': 116,
    'FIELD_TYPE_BOUNDED_STRING_BOUNDED_SEQUENCE': 117,
    'FIELD_TYPE_BOUNDED_WSTRING_BOUNDED_SEQUENCE': 118,

    # Unbounded Sequence Types
    'FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE': 145,
    'FIELD_TYPE_INT8_UNBOUNDED_SEQUENCE': 146,
    'FIELD_TYPE_UINT8_UNBOUNDED_SEQUENCE': 147,
    'FIELD_TYPE_INT16_UNBOUNDED_SEQUENCE': 148,
    'FIELD_TYPE_UINT16_UNBOUNDED_SEQUENCE': 149,
    'FIELD_TYPE_INT32_UNBOUNDED_SEQUENCE': 150,
    'FIELD_TYPE_UINT32_UNBOUNDED_SEQUENCE': 151,
    'FIELD_TYPE_INT64_UNBOUNDED_SEQUENCE': 152,
    'FIELD_TYPE_UINT64_UNBOUNDED_SEQUENCE': 153,
    'FIELD_TYPE_FLOAT_UNBOUNDED_SEQUENCE': 154,
    'FIELD_TYPE_DOUBLE_UNBOUNDED_SEQUENCE': 155,
    'FIELD_TYPE_LONG_DOUBLE_UNBOUNDED_SEQUENCE': 156,
    'FIELD_TYPE_CHAR_UNBOUNDED_SEQUENCE': 157,
    'FIELD_TYPE_WCHAR_UNBOUNDED_SEQUENCE': 158,
    'FIELD_TYPE_BOOLEAN_UNBOUNDED_SEQUENCE': 159,
    'FIELD_TYPE_BYTE_UNBOUNDED_SEQUENCE': 160,
    'FIELD_TYPE_STRING_UNBOUNDED_SEQUENCE': 161,
    'FIELD_TYPE_WSTRING_UNBOUNDED_SEQUENCE': 162,
    'FIELD_TYPE_FIXED_STRING_UNBOUNDED_SEQUENCE': 163,
    'FIELD_TYPE_FIXED_WSTRING_UNBOUNDED_SEQUENCE': 164,
    'FIELD_TYPE_BOUNDED_STRING_UNBOUNDED_SEQUENCE': 165,
    'FIELD_TYPE_BOUNDED_WSTRING_UNBOUNDED_SEQUENCE': 166,
}

# Mapping from ROS2 primitive types to field type names
PRIMITIVE_TO_FIELD_TYPE = {
    'bool': 'FIELD_TYPE_BOOLEAN',
    'int8': 'FIELD_TYPE_INT8',
    'uint8': 'FIELD_TYPE_UINT8',
    'int16': 'FIELD_TYPE_INT16',
    'uint16': 'FIELD_TYPE_UINT16',
    'int32': 'FIELD_TYPE_INT32',
    'uint32': 'FIELD_TYPE_UINT32',
    'int64': 'FIELD_TYPE_INT64',
    'uint64': 'FIELD_TYPE_UINT64',
    'float32': 'FIELD_TYPE_FLOAT',
    'float': 'FIELD_TYPE_FLOAT',
    'float64': 'FIELD_TYPE_DOUBLE',
    'double': 'FIELD_TYPE_DOUBLE',
    'string': 'FIELD_TYPE_STRING',
    'wstring': 'FIELD_TYPE_WSTRING',
    'char': 'FIELD_TYPE_CHAR',
    'wchar': 'FIELD_TYPE_WCHAR',
    'byte': 'FIELD_TYPE_BYTE',
    'octet': 'FIELD_TYPE_BYTE',
}


def ros2_to_dds_type(ros2_type: str) -> str:
    """Convert ROS2 type name to DDS type name"""
    # Format: namespace::msg::dds_::MessageName_ or namespace::srv::dds_::ServiceName_
    parts = ros2_type.split("/")
    if len(parts) == 3:
        namespace, msg_or_srv, message_name = parts
        # Capitalize first letter of message/service name
        message_name = message_name[0].upper() + message_name[1:] if message_name else ""
        # Preserve msg/ or srv/ in the DDS type name
        return f"{namespace}::{msg_or_srv}::dds_::{message_name}_"
    return ros2_type.replace("/", "::")


def _parse_msg_definition(msg_def: str) -> List[Dict]:
    """Parse a .msg file definition into field structures."""
    fields = []
    for line in msg_def.split('\n'):
        # Remove comments
        if '#' in line:
            line = line[:line.index('#')]
        line = line.strip()
        if not line:
            continue

        # Parse field: type name [array_size]
        # Handle both formats: "string[] name" (unbounded sequence) and "string name[10]" (fixed array)
        parts = line.split()
        if len(parts) < 2:
            continue

        field_type = parts[0]
        field_name = parts[1]

        # Check for array/sequence notation
        is_array = False
        is_bounded = False
        array_size = 0
        if field_type.endswith('[]'):
            # Unbounded sequence: string[] -> UNBOUNDED_SEQUENCE
            is_array = True
            is_bounded = False
            field_type = field_type[:-2]  # Remove [] from type name
        elif len(parts) > 2:
            # Check for array notation after field name (e.g., "string name[10]")
            array_part = ' '.join(parts[2:])
            if '[' in array_part and ']' in array_part:
                is_array = True
                # Check if it's a fixed-size array [10] or bounded sequence [<=10]
                match = re.search(r'\[(\d+)\]', array_part)
                if match:
                    # Fixed-size array
                    array_size = int(match.group(1))
                    is_bounded = False
                else:
                    # Bounded sequence [<=10] - not common in .msg files but possible
                    match = re.search(r'\[<=\s*(\d+)\]', array_part)
                    if match:
                        array_size = int(match.group(1))
                        is_bounded = True

        fields.append({
            'name': field_name,
            'type': field_type,
            'is_array': is_array,
            'is_bounded': is_bounded,
            'array_size': array_size,
        })

    return fields


def _field_type_to_type_id(field_type: str, is_array: bool = False, is_bounded: bool = False) -> int:
    """
    Convert ROS2 field type to field type ID.

    In ROS2 .msg files:
    - Fixed-size arrays like `string[10]` are ARRAY types
    - Unbounded sequences like `string[]` are UNBOUNDED_SEQUENCE types
    - Bounded sequences like `string[<=10]` are BOUNDED_SEQUENCE types

    For .msg files, `[]` syntax represents unbounded sequences, not arrays.
    """
    if field_type in PRIMITIVE_TO_FIELD_TYPE:
        type_name = PRIMITIVE_TO_FIELD_TYPE[field_type]
    else:
        type_name = 'FIELD_TYPE_NESTED_TYPE'

    if is_array:
        if is_bounded:
            type_name += '_BOUNDED_SEQUENCE'
        else:
            # Unbounded sequence ([] syntax in .msg files)
            type_name += '_UNBOUNDED_SEQUENCE'
    # Note: Fixed-size arrays would use _ARRAY suffix, but .msg files use [] for sequences

    return FIELD_TYPE_NAME_TO_ID.get(type_name, 0)


def _serialize_field(field: Dict, msg_type: str) -> Dict:
    """Serialize a field to type description format"""
    field_type = field['type']
    is_nested = field_type not in PRIMITIVE_TO_FIELD_TYPE

    type_dict = {
        'type_id': _field_type_to_type_id(field_type, field['is_array'], field.get('is_bounded', False)),
        'capacity': field['array_size'] if field['is_array'] else 0,
        'string_capacity': 0,
        'nested_type_name': '',
    }

    if is_nested:
        # Normalize nested type name to full format: namespace/msg/TypeName
        if '/' in field_type:
            # Already has namespace, check if it has /msg/
            parts = field_type.split('/')
            if len(parts) == 2:
                # Format: namespace/TypeName -> convert to namespace/msg/TypeName
                type_dict['nested_type_name'] = f"{parts[0]}/msg/{parts[1]}"
            elif len(parts) == 3:
                # Already full format: namespace/msg/TypeName
                type_dict['nested_type_name'] = field_type
            else:
                type_dict['nested_type_name'] = field_type
        else:
            # No namespace, assume same namespace as parent message
            namespace = msg_type.split('/')[0]
            type_dict['nested_type_name'] = f"{namespace}/msg/{field_type}"

    return {
        'name': field['name'],
        'type': type_dict,
        'default_value': '',
    }


def _serialize_type_description(msg_type: str, fields: List[Dict]) -> Dict:
    """Serialize a message type to type description format"""
    return {
        'type_name': msg_type,
        'fields': [_serialize_field(f, msg_type) for f in fields],
    }


def _extract_full_type_description(
    msg_type: str,
    type_map: Dict[str, Dict],
    visited: Optional[Set[str]] = None
) -> Dict:
    """
    Extract full type description including all referenced types.

    This matches the rosidl implementation exactly:
    https://github.com/ros2/rosidl/blob/master/rosidl_generator_type_description/rosidl_generator_type_description/__init__.py
    """
    if msg_type not in type_map:
        raise ValueError(f"Type {msg_type} not found in type map")

    output_type = type_map[msg_type]
    output_references = set()
    process_queue = [
        field['type']['nested_type_name']
        for field in output_type['fields']
        if field['type']['nested_type_name']
    ]

    while process_queue:
        process_type = process_queue.pop()
        if process_type and process_type not in output_references and process_type in type_map:
            output_references.add(process_type)
            # Extend queue with nested types from this referenced type
            process_queue.extend([
                field['type']['nested_type_name']
                for field in type_map[process_type]['fields']
                if field['type']['nested_type_name']
            ])

    return {
        'type_description': output_type,
        'referenced_type_descriptions': [
            type_map[type_name] for type_name in sorted(output_references)
        ],
    }


def _calculate_type_hash(serialized_type_description: Dict) -> str:
    """Calculate type hash from serialized type description (ROS2 algorithm)."""
    hashable_dict = deepcopy(serialized_type_description)
    for field in hashable_dict['type_description']['fields']:
        if 'default_value' in field:
            del field['default_value']
    for referenced_td in hashable_dict.get('referenced_type_descriptions', []):
        for field in referenced_td['fields']:
            if 'default_value' in field:
                del field['default_value']

    hashable_repr = json.dumps(
        hashable_dict,
        skipkeys=False,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=False,
        indent=None,
        separators=(', ', ': '),  # Critical: must match ROS2's format
        sort_keys=False
    )

    sha = hashlib.sha256()
    sha.update(hashable_repr.encode('utf-8'))
    return RIHS01_PREFIX + sha.hexdigest()


def compute_type_hash_from_msg(
    msg_type: str,
    msg_definition: str,
    dependencies: Optional[Dict[str, str]] = None
) -> str:
    """
    Compute ROS2 type hash from message definition.

    Args:
        msg_type: Full message type name (e.g., "std_msgs/msg/String")
        msg_definition: Raw .msg file content
        dependencies: Optional dict of {type_name: msg_definition} for nested types

    Returns:
        Type hash string in format RIHS01_<hash>
    """
    fields = _parse_msg_definition(msg_definition)
    type_map = {}
    type_map[msg_type] = _serialize_type_description(msg_type, fields)

    if dependencies:
        for dep_type, dep_def in dependencies.items():
            dep_fields = _parse_msg_definition(dep_def)
            type_map[dep_type] = _serialize_type_description(dep_type, dep_fields)

    full_type_description = _extract_full_type_description(msg_type, type_map)
    return _calculate_type_hash(full_type_description)


def get_type_hash(msg_type: str, msg_definition: Optional[str] = None, dependencies: Optional[Dict[str, str]] = None) -> str:
    """
    Get type hash for a message type.

    Computes the hash from the message definition. If msg_definition is not provided,
    raises ValueError as the hash cannot be computed.

    Args:
        msg_type: ROS2 message type (e.g., "std_msgs/msg/String")
        msg_definition: Message definition text (required)
        dependencies: Optional dict of {type_name: msg_definition} for nested types

    Returns:
        Type hash string in format RIHS01_<hash>

    Raises:
        ValueError: If msg_definition is not provided
    """
    if not msg_definition:
        raise ValueError(
            f"Message definition is required to compute type hash for {msg_type}. "
            "Please provide msg_definition or use the message registry to load the type."
        )

    return compute_type_hash_from_msg(msg_type, msg_definition, dependencies)


def compute_service_type_hash(
    srv_type: str,
    request_definition: str,
    response_definition: str,
    dependencies: Optional[Dict[str, str]] = None
) -> str:
    """
    Compute ROS2 type hash for a service type.

    Services in ROS2 are represented as a type with 3 nested fields:
    - request_message (nested type pointing to request message)
    - response_message (nested type pointing to response message)
    - event_message (nested type pointing to event message)

    The service type hash is computed from this service type structure,
    not from just the request type.

    Args:
        srv_type: ROS2 service type (e.g., "example_interfaces/srv/AddTwoInts")
        request_definition: Request message definition text
        response_definition: Response message definition text
        dependencies: Optional dict of {type_name: msg_definition} for nested types

    Returns:
        Type hash string in format RIHS01_<hash>
    """
    # Parse service type to get request and response types
    parts = srv_type.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid service type format: {srv_type}")
    
    # Validate that definitions are provided
    if not request_definition or not request_definition.strip():
        raise ValueError(f"Service definition is required for request. Service type: {srv_type}")
    if not response_definition or not response_definition.strip():
        raise ValueError(f"Service definition is required for response. Service type: {srv_type}")

    namespace, srv, service_name = parts
    request_type = f"{namespace}/srv/{service_name}_Request"
    response_type = f"{namespace}/srv/{service_name}_Response"
    # Event message type (for services, this is typically empty or a special type)
    # For most services, event_message is not used, but we need to include it
    # The event message is typically the same structure as the service itself
    # For simplicity, we'll use an empty message type or the service type itself
    event_type = f"{namespace}/srv/{service_name}_Event"

    # Parse request and response definitions
    request_fields = _parse_msg_definition(request_definition)
    response_fields = _parse_msg_definition(response_definition)

    # Build type map with request, response, and event message types
    type_map = {}
    type_map[request_type] = _serialize_type_description(request_type, request_fields)
    type_map[response_type] = _serialize_type_description(response_type, response_fields)

    # Event message has 3 fields:
    # 1. info: service_msgs/msg/ServiceEventInfo
    # 2. request: BoundedSequence of request type (max 1)
    # 3. response: BoundedSequence of response type (max 1)
    event_info_type = 'service_msgs/msg/ServiceEventInfo'
    event_fields = [
        {
            'name': 'info',
            'type': {
                'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE'],
                'capacity': 0,
                'string_capacity': 0,
                'nested_type_name': event_info_type,
            },
            'default_value': '',
        },
        {
            'name': 'request',
            'type': {
                'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE_BOUNDED_SEQUENCE'],
                'capacity': 1,  # BoundedSequence with max size 1
                'string_capacity': 0,
                'nested_type_name': request_type,
            },
            'default_value': '',
        },
        {
            'name': 'response',
            'type': {
                'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE_BOUNDED_SEQUENCE'],
                'capacity': 1,  # BoundedSequence with max size 1
                'string_capacity': 0,
                'nested_type_name': response_type,
            },
            'default_value': '',
        },
    ]
    type_map[event_type] = {
        'type_name': event_type,
        'fields': event_fields,
    }

    # ServiceEventInfo is a standard ROS2 message - we need to include it
    # For now, we'll create a minimal ServiceEventInfo type
    # ServiceEventInfo has: event_type (uint8), stamp (builtin_interfaces/Time), client_gid (uint8[16]), sequence_number (int64)
    service_event_info_fields = [
        {
            'name': 'event_type',
            'type': {'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_UINT8'], 'capacity': 0, 'string_capacity': 0, 'nested_type_name': ''},
            'default_value': '',
        },
        {
            'name': 'stamp',
            'type': {'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE'], 'capacity': 0, 'string_capacity': 0, 'nested_type_name': 'builtin_interfaces/msg/Time'},
            'default_value': '',
        },
        {
            'name': 'client_gid',
            'type': {'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_UINT8_ARRAY'], 'capacity': 16, 'string_capacity': 0, 'nested_type_name': ''},
            'default_value': '',
        },
        {
            'name': 'sequence_number',
            'type': {'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_INT64'], 'capacity': 0, 'string_capacity': 0, 'nested_type_name': ''},
            'default_value': '',
        },
    ]
    type_map[event_info_type] = {
        'type_name': event_info_type,
        'fields': service_event_info_fields,
    }

    # builtin_interfaces/msg/Time is also needed
    time_type = 'builtin_interfaces/msg/Time'
    time_fields = [
        {
            'name': 'sec',
            'type': {'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_INT32'], 'capacity': 0, 'string_capacity': 0, 'nested_type_name': ''},
            'default_value': '',
        },
        {
            'name': 'nanosec',
            'type': {'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_UINT32'], 'capacity': 0, 'string_capacity': 0, 'nested_type_name': ''},
            'default_value': '',
        },
    ]
    type_map[time_type] = {
        'type_name': time_type,
        'fields': time_fields,
    }

    # Add dependencies
    if dependencies:
        for dep_type, dep_def in dependencies.items():
            if dep_type not in type_map:
                dep_fields = _parse_msg_definition(dep_def)
                type_map[dep_type] = _serialize_type_description(dep_type, dep_fields)

    # Create service type description with 3 nested fields
    service_fields = [
        {
            'name': 'request_message',
            'type': {
                'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE'],
                'capacity': 0,
                'string_capacity': 0,
                'nested_type_name': request_type,
            },
            'default_value': '',
        },
        {
            'name': 'response_message',
            'type': {
                'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE'],
                'capacity': 0,
                'string_capacity': 0,
                'nested_type_name': response_type,
            },
            'default_value': '',
        },
        {
            'name': 'event_message',
            'type': {
                'type_id': FIELD_TYPE_NAME_TO_ID['FIELD_TYPE_NESTED_TYPE'],
                'capacity': 0,
                'string_capacity': 0,
                'nested_type_name': event_type,
            },
            'default_value': '',
        },
    ]

    type_map[srv_type] = {
        'type_name': srv_type,
        'fields': service_fields,
    }

    # Extract full type description and compute hash
    full_type_description = _extract_full_type_description(srv_type, type_map)
    return _calculate_type_hash(full_type_description)


def mangle_name(name: str) -> str:
    """Mangle a name by replacing / with %"""
    if not name or name == "/":
        return "%"
    return name.replace("/", "%")


def load_dependencies_recursive(
    msg_type: str,
    msg_def: str,
    registry,
    visited: Optional[Set[str]] = None
) -> Dict[str, str]:
    """
    Recursively load all message dependencies including transitive ones.

    This function is shared across Publisher, Subscriber, ServiceClient, and ServiceServer
    to avoid code duplication.

    Args:
        msg_type: Message type name (e.g., "geometry_msgs/msg/Twist")
        msg_def: Message definition text
        registry: MessageRegistry instance
        visited: Set of already visited types to prevent cycles

    Returns:
        Dictionary mapping dependency type names to their definitions
    """
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
                nested_deps = load_dependencies_recursive(dep_type, dep_def, registry, visited)
                all_dependencies.update(nested_deps)

    return all_dependencies
