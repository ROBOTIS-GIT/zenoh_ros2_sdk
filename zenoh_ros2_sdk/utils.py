"""
Utility functions for type conversion and message handling
"""


def ros2_to_dds_type(ros2_type: str) -> str:
    """Convert ROS2 type name to DDS type name"""
    # Format: namespace::msg::dds_::MessageName_
    parts = ros2_type.split("/")
    if len(parts) == 3:
        namespace, msg, message_name = parts
        # Capitalize first letter of message name
        message_name = message_name[0].upper() + message_name[1:] if message_name else ""
        return f"{namespace}::msg::dds_::{message_name}_"
    return ros2_type.replace("/", "::")


def get_type_hash(msg_type: str) -> str:
    """Get type hash for common message types"""
    # Common type hashes - in production, this should be computed or looked up
    common_hashes = {
        "std_msgs/msg/String": "RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18",
        "std_msgs/msg/Int32": "RIHS01_0000000000000000000000000000000000000000000000000000000000000000",  # Placeholder
    }
    return common_hashes.get(msg_type, "RIHS01_0000000000000000000000000000000000000000000000000000000000000000")


def mangle_name(name: str) -> str:
    """Mangle a name by replacing / with %"""
    if not name or name == "/":
        return "%"
    return name.replace("/", "%")
