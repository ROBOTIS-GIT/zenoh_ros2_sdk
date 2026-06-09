from types import SimpleNamespace

from zenoh_ros2_sdk import _cache


def test_mark_git_safe_directory_adds_missing_path(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "--get-all" in cmd:
            return SimpleNamespace(stdout="/other/path\n")
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(_cache.subprocess, "run", fake_run)

    _cache._mark_git_safe_directory("/cache/common_interfaces")

    assert calls[-1] == [
        "git",
        "config",
        "--global",
        "--add",
        "safe.directory",
        "/cache/common_interfaces",
    ]


def test_mark_git_safe_directory_skips_existing_path(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(stdout="/cache/common_interfaces\n")

    monkeypatch.setattr(_cache.subprocess, "run", fake_run)

    _cache._mark_git_safe_directory("/cache/common_interfaces")

    assert len(calls) == 1
