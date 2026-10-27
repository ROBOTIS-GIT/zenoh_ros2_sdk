# Bundled telemetry definitions

Imu and JointState and their payload dependencies (Quaternion, Vector3, Header,
Time) are shipped in the SDK wheel for offline use. MessageRegistry checks an
explicit/local message directory first, these bundled definitions second, and
its existing default Git repositories last. Other types retain their existing
on-demand behavior. No new sensor_msgs repository mapping is necessary.

Definitions and package/license metadata were copied from the installed ROS
Jazzy packages on k1-snpr50a1018.local on 2026-10-27. Source comments are preserved.
Upstream: https://github.com/ros2/common_interfaces/tree/jazzy and
https://github.com/ros2/rcl_interfaces/tree/jazzy .
Tests compare SDK-computed hashes with the installed ROS-generated type hashes.

Consumers such as Cyclo Gateway can use `get_bundled_message_definitions()` to
register these types in their own codec before constructing an SDK subscriber.
The API does not create a session or fetch data from the network.
