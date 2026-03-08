# Zenoh session close: 10s delay and Rust panic

When a process that only uses discovery (e.g. `get_topic_names_and_types`, `get_topic_info`) or any script that never explicitly closes the Zenoh session exits, you may see:

1. **~10 second delay** after the script has finished printing, then  
2. **A Rust panic**:  
   `thread '<unnamed>' panicked at src/session.rs:299:49: called Result::unwrap() on an Err value: PyErr { type: <class 'zenoh.ZError'>, value: ZError('close operation timed out! at ... close.rs:122.') }`

---

## What you should do (zenoh_ros2_sdk)

| Your case | What to do |
|-----------|------------|
| **Discovery only** (topic list, topic info, service list/type, type-hash checks, one-off scripts) | Run discovery via the **daemon**: `zenoh-ros2 daemon start`. Then `zenoh-ros2 topic list` / `topic info` / `service list` / `service type` and scripts that use the daemon don’t own a Zenoh session → no panic, no 10s delay. See [DISCOVERY_CLOSE_DELAY.md](DISCOVERY_CLOSE_DELAY.md). |
| **Discovery from your own Python script** | Use **NodeStrategy** (daemon path), not the raw `get_topic_names_and_types` / `get_topic_info` / `get_service_names_and_types` / `get_service_info`. With the daemon running (or auto-spawned), the strategy talks to the daemon over HTTP and your process does **not** open a Zenoh session → no 10s delay, no panic. Example: `NodeStrategy().get_topic_names_and_types()` or `NodeStrategy().get_service_names_and_types()` (default router; start daemon first or leave `spawn_if_missing=True`). |
| **Pub/sub** (subscriber, publisher examples) | Nothing special. They exit without an extra delay. No atexit close is registered. |
| **You want to close the session yourself** | Call `ZenohSession.get_instance(router_ip, router_port).close()` and catch `zenoh.ZError`. It may block up to 10s. |

**Summary:** Use the daemon (or NodeStrategy in code) for discovery so your process doesn’t own a session; keep pub/sub as-is; optionally close manually if you accept the possible 10s wait.

**Programmatic discovery without 10s delay (use daemon path):**

```python
from zenoh_ros2_sdk.node.strategy import NodeStrategy

# With daemon running (or spawn_if_missing=True), this uses HTTP to the daemon;
# your process does not open a Zenoh session → fast exit, no panic.
strategy = NodeStrategy()  # default 127.0.0.1:7447; will use daemon if running or spawn it
topics = strategy.get_topic_names_and_types()
info = strategy.get_topic_info("/some/topic", verbose=True)
```

Avoid using the raw `get_topic_names_and_types()` / `get_topic_info()` from `zenoh_ros2_sdk` for discovery-only scripts if you want fast exit; those open a session in your process.

---

This document points to the **exact locations in the upstream Zenoh and zenoh-python source** where the delay and panic happen.

---

## 1. Where the 10s comes from (eclipse-zenoh/zenoh)

**Repository:** https://github.com/eclipse-zenoh/zenoh  

**File:** `zenoh/src/api/builders/close.rs`

- **Line 47** – Close timeout is fixed at 10 seconds:
  ```rust
  timeout: Duration::from_secs(10),
  ```

- **Lines 118–122** – The close future runs under `tokio::time::timeout`. If `close_inner()` does not complete within 10s, the call returns an error:
  ```rust
  if tokio::time::timeout(self.timeout, self.closee.close_inner())
      .await
      .is_err()
  {
      bail!("close operation timed out!")
  }
  ```

So the “close operation timed out!” message is produced here when the 10s cap is hit. What runs during close (and can take that long) is transport/link shutdown in the runtime (`zenoh/src/net/runtime/mod.rs`, `close_inner` → `manager.close().await`). See also `docs/DISCOVERY_CLOSE_DELAY.md` in this repo.

---

## 2. Where the panic comes from (eclipse-zenoh/zenoh-python)

**Repository:** https://github.com/eclipse-zenoh/zenoh-python  

**File:** `src/session.rs`

- **Lines 278–282** – `Drop` implementation for the Python `Session` wrapper:
  ```rust
  impl Drop for Session {
      fn drop(&mut self) {
          Python::with_gil(|gil| self.close(gil)).unwrap()
      }
  }
  ```

When the Python process exits (or the last reference to the zenoh session is dropped), this `Drop` runs. It:

1. Calls `self.close(gil)`, which calls `wait(py, self.0.close())` (zenoh’s session close).
2. If close times out, zenoh returns `Err` with the “close operation timed out!” message; `wait` turns that into a `PyErr` (ZError).
3. **`.unwrap()`** on that `Result` causes the panic you see: “called `Result::unwrap()` on an `Err` value: PyErr { ... ZError('close operation timed out! ...') }”.

So the **exact problem** is: in zenoh-python, the session’s `Drop` always calls close and then **unwraps** the result. When close times out (after 10s), that unwrap panics instead of surfacing the error to Python or ignoring it during shutdown.

---

## Summary

| What | Where (upstream) |
|------|-------------------|
| 10s close timeout | `zenoh` → `zenoh/src/api/builders/close.rs` line 47 |
| “close operation timed out!” | `zenoh` → `zenoh/src/api/builders/close.rs` lines 118–122 |
| Panic (unwrap on close error) | **zenoh-python** → `src/session.rs` lines 278–282 (`Drop for Session`) |

The core zenoh crate does **not** panic on close timeout; it returns `Err`. The panic is in **zenoh-python**’s `Session` drop, which uses `.unwrap()` on that error.

---

## Workarounds in this SDK

- **Use the daemon** for discovery: `zenoh-ros2 daemon start`. Then `zenoh-ros2 topic list` / `topic info` use the daemon over HTTP and the CLI process does not own a Zenoh session, so no session is dropped and no close/panic there. See `docs/DISCOVERY_CLOSE_DELAY.md`. This is the recommended way to avoid both the panic and a 10s delay for discovery-only tools (e.g. `check_type_hashes.py`).

- **No atexit close:** The SDK does not register an atexit handler to close the session. Doing so would avoid the panic but would introduce a ~10s delay on exit for all processes that create a session (including subscriber examples). So we leave exit as-is: subscriber and similar examples exit without delay; discovery-only scripts that run in-process may show the panic when the session is dropped. Use the daemon for discovery to avoid that.
- **Manual close:** You can call `ZenohSession._instance.close()` (and catch `zenoh.ZError`) in your own script if you want to close explicitly and accept the possible 10s wait.

---

## Is the 10s delay after exit intended?

If you had added an **atexit** handler that closes the session (as we tried earlier), then yes: that close can block for up to 10s, so the delay would be expected. The SDK no longer does that, because it made *every* process that creates a session (including subscriber examples) wait ~10s on exit. So now: no atexit close, subscriber and similar examples exit without that delay; discovery-only in-process scripts may still hit the panic (and/or delay) when the session is dropped. Use the daemon for discovery to avoid the panic and delay.

---

## Why don't I see the 10s delay in the subscriber example?

The SDK does not close the session at exit (no atexit handler), so the session is only dropped during interpreter teardown. Depending on GC/teardown order, that may not block the main thread for the full 10s before the process exits, so the subscriber example can appear to exit without a delay. Discovery-only scripts (e.g. `check_type_hashes.py`) that create a session in-process may still show the delay and/or panic when the session is dropped. Use the daemon for discovery to avoid both.

---

## Does rmw_zenoh have the same problem?

**Same underlying Zenoh close:** rmw_zenoh (ROS 2 RMW using Zenoh) uses the same Zenoh runtime. Session close in Zenoh has the same 10s timeout and transport teardown, so in principle the same delay could occur when the session is closed.

**Different handling on exit:** rmw_zenoh had a similar panic-on-termination issue (see [ros2/rmw_zenoh#324](https://github.com/ros2/rmw_zenoh/issues/324)). Their fix (PR [#339](https://github.com/ros2/rmw_zenoh/pull/339)) is to **not close** the Zenoh session when the process is exiting:

- They register an `atexit` handler that sets a flag (`is_exiting`).
- When `rmw_shutdown()` runs (e.g. during context teardown), they check that flag; if it is set, they **skip** closing the Zenoh session.
- So on normal process exit they never call Zenoh session close, and the process exits without the 10s delay and without triggering the problematic close path.

So **rmw_zenoh does not** show the 10s delay on normal exit, because they avoid closing the session at exit. If you explicitly call `rcl_shutdown()` / `rmw_shutdown()` before exit (e.g. in a cleanup path), then they do close the session and you could see the delay. The SDK cannot do the same “skip close at exit” trick in Python without leaving the session to be dropped (which triggers zenoh-python’s `Drop` and the panic), so for discovery-only we recommend using the daemon.
