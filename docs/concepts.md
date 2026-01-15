# Concepts

This SDK follows the same conventions as `rmw_zenoh_cpp` / `ros-z` so ROS tools can discover entities and (when applicable) publishers can behave like ROS 2 “publish-on-subscribe”.

## Domain ID

ROS 2 uses a *domain ID* to isolate graphs. In this SDK you typically pass `domain_id` to publishers/subscribers/service endpoints. You must use the same `domain_id` as the ROS 2 side you want to communicate with.

## Types and type hashes

You specify types as ROS 2 strings like:

- `std_msgs/msg/String`
- `example_interfaces/srv/AddTwoInts`

The SDK can auto-load message/service definitions (via the message registry) and compute ROS 2 compatible type hashes.

## Discovery vs data transport

- **Discovery-plane**: liveliness tokens under `@ros2_lv/...` advertise nodes, publishers, subscribers, service servers, and service clients so they appear in the ROS graph.
- **Data-plane**: serialized CDR payloads are transported over Zenoh key expressions derived from the topic/service name, type, and type hash.

## QoS

For graph compatibility, QoS information is encoded into discovery tokens using the compact `rmw_zenoh` / `ros-z` format.

In most APIs you can pass either:

- a `QosProfile` object (from `zenoh_ros2_sdk.qos`), or
- a pre-encoded QoS string.

## Sessions

Publishers/subscribers/service endpoints share an underlying Zenoh session for efficiency (session pooling). Close resources when you’re done (`.close()`).

