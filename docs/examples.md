# Examples

The repo contains runnable scripts in `examples/` (numbered in recommended learning order).

Start a router in a ROS2 environment:

```bash
ros2 run rmw_zenoh_cpp rmw_zenohd
```

Run an example:

```bash
python3 examples/01_publish_string.py
python3 examples/02_subscribe_string.py
```

For the full list (including services, queue-mode services, and compressed image subscription), see `examples/README.md`.

