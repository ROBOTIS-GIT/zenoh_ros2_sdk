# AGENTS.md

This file is the canonical guide for AI coding agents working in this repository.
Tool-specific files such as `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/*`, and
`.github/copilot-instructions.md` should point back here instead of drifting into
separate guidance.

## Project Snapshot

- Package: `zenoh-ros2-sdk`
- Purpose: Python SDK for ROS 2-style topic, service, discovery, and message
  handling over Zenoh without requiring a local ROS 2 installation.
- Python support: 3.9 through 3.12.
- Main package: `zenoh_ros2_sdk/`
- Examples: `examples/`
- Tests: `tests/`
- Docs: `docs/`, published with MkDocs.

## First Commands

Run commands from the repository root.

```bash
python3 -m pip install -e ".[dev,docs]"
python3 -m pytest
```

Useful focused checks:

```bash
python3 -m pytest tests/test_utils.py
python3 -m pytest tests/test_cache.py
python3 setup.py --version
python3 -m mkdocs build
```

## Architecture Map

- `zenoh_ros2_sdk/session.py` manages shared Zenoh session behavior.
- `zenoh_ros2_sdk/publisher.py` and `zenoh_ros2_sdk/subscriber.py` implement
  topic APIs.
- `zenoh_ros2_sdk/service_client.py` and `zenoh_ros2_sdk/service_server.py`
  implement service APIs.
- `zenoh_ros2_sdk/message_registry.py`, `_repositories.py`, and `_cache.py`
  handle automatic ROS 2 message/service definition loading from Git
  repositories.
- `zenoh_ros2_sdk/utils.py` contains serialization, parsing, and type-hash
  helpers.
- `zenoh_ros2_sdk/topic_cli.py`, `service_cli.py`, and `daemon/` back the
  `zenoh-ros2` command.

## Coding Rules

- Prefer small, focused changes that match the existing style.
- Keep public APIs stable unless the user explicitly asks for a breaking change.
- Preserve ROS 2 wire-compatibility details: CDR serialization, type hashes,
  key expressions, liveliness tokens, and QoS behavior are user-facing.
- Use typed, explicit Python where it improves readability, but do not refactor
  unrelated modules just to add annotations.
- Do not vendor cloned ROS 2 message repositories into this repo. They belong in
  the runtime cache, normally `~/.cache/zenoh_ros2_sdk/` or
  `$ZENOH_ROS2_SDK_CACHE`.
- Do not commit local caches, `__pycache__`, `.pytest_cache`, build output, or
  machine-specific editor files.

## Tests And Validation

- Run the narrowest relevant `pytest` target while iterating.
- Run the full `python3 -m pytest` suite before finishing changes that touch
  serialization, discovery, services, cache behavior, or public APIs.
- For docs-only changes, run `python3 -m mkdocs build`.
- For version bumps, verify `python3 setup.py --version`.
- If a test requires a running Zenoh router or ROS 2 environment and cannot be
  run locally, say so explicitly in the final response.

## Common Tasks

### Bump Version

Update all three version locations together:

- `pyproject.toml` `[project].version`
- `setup.py` `version=...`
- `zenoh_ros2_sdk/__init__.py` `__version__`

Then run:

```bash
python3 setup.py --version
```

### Add A Message Repository

Edit `zenoh_ros2_sdk/_repositories.py`.

- Prefer stable ROS 2 distribution branches or tags such as `jazzy` unless a
  specific commit is required.
- Keep `packages` accurate so `PACKAGE_TO_REPOSITORY` maps message namespaces to
  the right repository.
- Add or update tests when cache, repository, or type-loading behavior changes.

### Add Examples

Examples use numbered filenames in `examples/`.

- Odd numbers are publishers.
- Even numbers are subscribers.
- Update `examples/README.md` with usage instructions.
- Use `get_message_class()` for nested message construction.
- Use NumPy arrays where CDR serialization expects array fields.

## AI Tooling Files

- `AGENTS.md`: canonical project instructions for agents.
- `CLAUDE.md`: Claude Code entrypoint; keep it short and linked to this file.
- `.claude/skills/`: Claude Code skills for recurring repo tasks.
- `.agents/skills/`: Codex/Agent Skills copy of the recurring repo tasks.
- `GEMINI.md`: Gemini CLI and Antigravity entrypoint.
- `.cursor/rules/`: Cursor project rules.
- `.github/copilot-instructions.md`: GitHub Copilot repository instructions.

When changing workflow guidance, update this file first, then update only the
thin tool-specific adapters that need to mention the change.
