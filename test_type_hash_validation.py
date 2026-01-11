#!/usr/bin/env python3
"""
Validation script for type hash computation

Tests the type hash implementation against known ROS2 type hashes.
"""
from pathlib import Path
from zenoh_ros2_sdk.utils import compute_type_hash_from_msg


def test_string_hash():
    """Test std_msgs/msg/String type hash"""
    print("Testing std_msgs/msg/String...")
    
    expected_hash = "RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18"
    
    # Read String.msg
    string_msg_path = Path("/Users/woojin/Desktop/project/open_manipulator/docker/workspace/common_interfaces/std_msgs/msg/String.msg")
    if not string_msg_path.exists():
        print(f"  ERROR: String.msg not found")
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
    
    # Read Twist.msg and Vector3.msg
    geometry_msgs_dir = Path("/Users/woojin/Desktop/project/open_manipulator/docker/workspace/common_interfaces/geometry_msgs/msg")
    twist_msg_path = geometry_msgs_dir / "Twist.msg"
    vector3_msg_path = geometry_msgs_dir / "Vector3.msg"
    
    if not twist_msg_path.exists():
        print(f"  ERROR: Twist.msg not found")
        return False
    if not vector3_msg_path.exists():
        print(f"  ERROR: Vector3.msg not found")
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
