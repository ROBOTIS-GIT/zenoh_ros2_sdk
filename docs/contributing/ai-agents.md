# AI Agent Guide

This repository keeps AI-agent guidance in a small set of predictable files.
The goal is to make Claude Code, Codex, Cursor, Gemini CLI, Google Antigravity,
GitHub Copilot, and similar tools useful without forcing maintainers to edit a
different long rules file for each product.

## Source Of Truth

`AGENTS.md` is the canonical project guide. Put durable repo knowledge there:

- setup and validation commands
- architecture notes
- coding rules
- release/version workflow
- example and message-repository workflow

Tool-specific files should stay short and point back to `AGENTS.md`.

## Tool Entry Points

| Tool | File or directory |
| --- | --- |
| General agent ecosystem | `AGENTS.md` |
| OpenAI Codex | `AGENTS.md`, `.agents/skills/` |
| Claude Code | `CLAUDE.md`, `.claude/skills/` |
| Cursor | `AGENTS.md`, `.cursor/rules/project.mdc` |
| Gemini CLI | `GEMINI.md` |
| Google Antigravity | `AGENTS.md`, `GEMINI.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |

## Skills

The repo includes task skills for workflows that benefit from precise,
repeatable steps:

- `bump-version`
- `add-repository`
- `create-example`

Claude Code scans `.claude/skills/`. Codex scans `.agents/skills/`. Keep both
copies aligned when changing a shared skill.

## Maintenance Rules

- Update `AGENTS.md` first when project guidance changes.
- Keep adapters short. They should not become independent manuals.
- Avoid adding a new tool-specific rules file unless that tool actually reads it
  automatically or the team has agreed to use it.
- Prefer links back to canonical docs over duplicated prose.
- Keep instructions specific, command-oriented, and easy to verify.
