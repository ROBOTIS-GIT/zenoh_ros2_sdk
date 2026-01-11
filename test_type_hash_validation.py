#!/usr/bin/env python3
"""
Validation script for type hash computation

Tests the type hash implementation against known ROS2 type hashes.

Environment Variables:
    COMMON_INTERFACES_PATH: Path to common_interfaces repository (optional)
                            If not set, will try to use message registry.
"""
import os
from pathlib import Path
from zenoh_ros2_sdk.utils import compute_type_hash_from_msg
from zenoh_ros2_sdk.message_registry import get_registry


def get_message_file_path(msg_type: str) -> Path:
    """
    Get message file path from environment variable or message registry.
    
    Args:
        msg_type: ROS2 message type (e.g., "std_msgs/msg/String")
        
    Returns:
        Path to message file or None if not found
    """
    # Try environment variable first
    common_interfaces_path = os.getenv("COMMON_INTERFACES_PATH")
    if common_interfaces_path:
        parts = msg_type.split("/")
        if len(parts) == 3:
            namespace, msg, message_name = parts
            msg_path = Path(common_interfaces_path) / namespace / msg / f"{message_name}.msg"
            if msg_path.exists():
                return msg_path
    
    # Try message registry as fallback
    try:
        registry = get_registry()
        msg_file = registry.get_msg_file_path(msg_type)
        if msg_file and Path(msg_file).exists():
            return Path(msg_file)
    except Exception:
        pass
    
    return None


def test_string_hash():
    """Test std_msgs/msg/String type hash"""
    print("Testing std_msgs/msg/String...")
    
    expected_hash = "RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18"
    
    # Get message file path
    string_msg_path = get_message_file_path("std_msgs/msg/String")
    if not string_msg_path or not string_msg_path.exists():
        print(f"  ERROR: String.msg not found")
        print(f"  Hint: Set COMMON_INTERFACES_PATH environment variable or ensure message registry is configured")
        return False
    
    with open(string_msg_path, 'r') as f:
        msg_def = f.read()
    
    computed_hash = compute_type_hash_from_msg("std_msgs/msg/String", msg_def)
    
    print(f"  Expected: {expected_hash}")
    print(f"  Computed: {computed_hash}")
    print(f"  Match: {computed_hash == expected_hash}")
    
    if computed_hash != expected_hash:
        print(f"  ERROR: Hash mismatch!")
        return False
    
    return True


def test_twist_hash():
    """Test geometry_msgs/msg/Twist type hash"""
    print("\nTesting geometry_msgs/msg/Twist...")
    
    expected_hash = "RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a"
    
    # Get message file paths
    twist_msg_path = get_message_file_path("geometry_msgs/msg/Twist")
    vector3_msg_path = get_message_file_path("geometry_msgs/msg/Vector3")
    
    if not twist_msg_path or not twist_msg_path.exists():
        print(f"  ERROR: Twist.msg not found")
        print(f"  Hint: Set COMMON_INTERFACES_PATH environment variable or ensure message registry is configured")
        return False
    if not vector3_msg_path or not vector3_msg_path.exists():
        print(f"  ERROR: Vector3.msg not found")
        print(f"  Hint: Set COMMON_INTERFACES_PATH environment variable or ensure message registry is configured")
        return False
    
    with open(twist_msg_path, 'r') as f:
        twist_def = f.read()
    with open(vector3_msg_path, 'r') as f:
        vector3_def = f.read()
    
    # Compute hash with Vector3 as dependency
    dependencies = {
        "geometry_msgs/msg/Vector3": vector3_def
    }
    
    computed_hash = compute_type_hash_from_msg(
        "geometry_msgs/msg/Twist",
        twist_def,
        dependencies=dependencies
    )
    
    print(f"  Expected: {expected_hash}")
    print(f"  Computed: {computed_hash}")
    print(f"  Match: {computed_hash == expected_hash}")
    
    if computed_hash != expected_hash:
        print(f"  ERROR: Hash mismatch!")
        return False
    
    return True


def main():
    print("=" * 60)
    print("Type Hash Validation Test")
    print("=" * 60)
    
    results = []
    
    # Test String hash
    results.append(("String", test_string_hash()))
    
    # Test Twist hash
    results.append(("Twist", test_twist_hash()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
