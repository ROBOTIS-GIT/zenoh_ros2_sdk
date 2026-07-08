# Concepts

This SDK follows the same conventions as `rmw_zenoh_cpp` so ROS tools can discover entities and (when applicable) publishers can behave like ROS 2 "publish-on-subscribe".

## Domain ID

ROS 2 uses a *domain ID* to isolate graphs. In this SDK you typically pass `domain_id` to publishers, subscribers, service endpoints, and action clients. You must use the same `domain_id` as the ROS 2 side you want to communicate with. If you do not pass `domain_id` to the constructor, the SDK uses `ROS_DOMAIN_ID` from the environment (falling back to 0 when it is not set). An explicit `domain_id` argument always overrides the environment value.

## Types and type hashes

You specify types as ROS 2 strings like:

- `std_msgs/msg/String`
- `example_interfaces/srv/AddTwoInts`
- `example_interfaces/action/Fibonacci`

The SDK can auto-load message, service, and action definitions (via the message registry) and compute ROS 2 compatible type hashes.

## Discovery vs data transport

- **Discovery-plane**: liveliness tokens under `@ros2_lv/...` advertise nodes, publishers, subscribers, service servers, service clients, and action-client endpoints so they appear in the ROS graph.
- **Data-plane**: serialized CDR payloads are transported over Zenoh key expressions derived from the topic, service, or action endpoint name, type, and type hash.

## QoS

For graph compatibility, QoS information is encoded into discovery tokens using the compact `rmw_zenoh` format.

In most APIs you can pass either:

- a `QosProfile` object (from `zenoh_ros2_sdk.qos`), or
- a pre-encoded QoS string.

## Sessions

Publishers, subscribers, service endpoints, and action clients share an underlying Zenoh session for efficiency (session pooling). Close resources when you’re done (`.close()`).
