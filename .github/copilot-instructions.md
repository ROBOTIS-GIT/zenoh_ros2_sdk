# GitHub Copilot Instructions

Use `AGENTS.md` as the canonical repository guide for `zenoh-ros2-sdk`.

Follow these defaults:

- Keep Python changes small and consistent with the existing module style.
- Preserve ROS 2 compatibility behavior for serialization, type hashes,
  discovery, liveliness, QoS, and services.
- Run `python3 -m pytest` for code changes when possible.
- Run `python3 -m mkdocs build` for docs changes when possible.
- Keep version bumps synchronized across `pyproject.toml`, `setup.py`, and
  `zenoh_ros2_sdk/__init__.py`.
- Do not add local caches, cloned message repositories, `__pycache__`,
  `.pytest_cache`, or build output.
