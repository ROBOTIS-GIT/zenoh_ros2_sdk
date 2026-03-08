# `session`

The SDK uses a **default Zenoh session config** aligned with **rmw_zenoh** (copied from `ros2/rmw_zenoh` `DEFAULT_RMW_ZENOH_SESSION_CONFIG.json5`), so session behavior (scouting, transport, timings, etc.) matches ROS 2 nodes using rmw_zenoh. The `router_ip` / `router_port` passed to `ZenohSession.get_instance()` override the config’s `connect/endpoints`.

- **Custom config file**: set `ZENOH_SESSION_CONFIG_URI` to the path of a JSON5 config file to use instead of the bundled default.
- **Overrides**: set `ZENOH_CONFIG_OVERRIDE` to apply extra config (e.g. `connect/endpoints=["tcp/192.168.1.1:7447"]`) on top of the loaded config.

::: zenoh_ros2_sdk.session
