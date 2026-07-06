# GEMINI.md

Gemini CLI and Google Antigravity should use `AGENTS.md` as the canonical
repository guide.

Before editing, read `AGENTS.md` and follow its commands, validation guidance,
architecture map, and common-task checklists. In particular:

- Run commands from the repository root.
- Use `python3 -m pytest` for test validation.
- Use `python3 -m mkdocs build` for docs validation.
- Keep version strings synchronized across `pyproject.toml`, `setup.py`, and
  `zenoh_ros2_sdk/__init__.py`.
- Do not commit local caches, cloned message repositories, or generated Python
  cache files.
