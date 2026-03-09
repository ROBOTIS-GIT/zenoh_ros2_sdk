# Why `zenoh-ros2 topic list` can take ~10 seconds to return

## Observed behaviour

When you run `zenoh-ros2 topic list` (or `zenoh-ros2 topic info …`), the command can take about **10 seconds** before the shell prompt returns, even though discovery itself (liveliness queries) finishes in under a second.

## Root cause (exact code)

The delay comes from **Zenoh’s session close**, not from discovery. This was checked using `scripts/check_discovery_timeout.py`, which times each phase:

1. **zenoh.open()** – ~0.5 s  
2. **liveliness.get(MP)** / **liveliness.get(MS)** – ~0 s  
3. **session.close()** – **~9.5 s**  
4. Total ≈ 10 s

So the process blocks in **session.close()** (or in the equivalent cleanup when the process exits and the session is dropped).

### Where the 10 s is defined in Zenoh (eclipse-zenoh/zenoh)

In the upstream `eclipse-zenoh/zenoh` repository:

**1. Close timeout (10 s default)**

- **File:** `zenoh/src/api/builders/close.rs`
- **Line 47:** `timeout: Duration::from_secs(10),`
- **Lines 119–124:** The close future runs as  
  `tokio::time::timeout(self.timeout, self.closee.close_inner(self.close_args))`  
  so the close is **capped at 10 seconds**. If `close_inner` takes longer, the call hits this timeout.

So the **maximum** wait for a single close is **10 s**, and that matches what we see.

**2. What actually runs during close**

- **File:** `zenoh/src/api/session.rs`
- **Lines 3489–3528:** `impl Closee for WeakSession` → `close_inner`:
  - Takes primitives from state
  - `task_controller.terminate_all_async().await`
  - `primitives.send_close()` (or runtime’s `close_inner` when using static runtime)
  - Drops session state (queryables, subscribers, etc.)

- **File:** `zenoh/src/net/runtime/mod.rs`
- **Lines 983–1003:** `impl Closee for Arc<RuntimeState>` → `close_inner`:
  - `task_controller.terminate_all_async().await`
  - **`self.manager.close().await`** ← transport/link shutdown
  - Cleans transport handlers, router tables, etc.

So the 10 s we see is the **close timeout** in `close.rs` while the runtime’s `close_inner` (and thus `manager.close()`) runs. The timeout is **hardcoded** in Zenoh; the Python API does not expose a way to change it (the `timeout()` builder method is `#[doc(hidden)]` and behind the `unstable` and `internal` features).

## Summary

| What                         | Where (zenoh repo)                    | Role |
|-----------------------------|----------------------------------------|------|
| 10 s close timeout          | `zenoh/src/api/builders/close.rs:47`  | `Duration::from_secs(10)` for `CloseBuilder` |
| Close future                | `zenoh/src/api/builders/close.rs:119–124` | `tokio::time::timeout(self.timeout, close_inner(...))` |
| Session close logic         | `zenoh/src/api/session.rs:3493`       | `close_inner`: terminate tasks, send_close, drop state |
| Runtime/transport close     | `zenoh/src/net/runtime/mod.rs:986`    | `close_inner`: terminate_all_async, **manager.close()** |

So the delay is **by design** in Zenoh (fixed 10 s close timeout) and is not a bug in this SDK. Avoiding it in a “proper” way would require either:

- **Upstream:** Making the close timeout configurable (e.g. in Zenoh config or on `CloseBuilder`) and exposing it in the Python API, or
- **In this SDK:** Using a dedicated short-lived session for discovery (e.g. with a shorter transport/link lease) so that transport teardown finishes sooner and close returns before the 10 s cap—if Zenoh’s behaviour allows that.

Until then, the **check script** (`scripts/check_discovery_timeout.py`) is the way to **debug and confirm** where time is spent (open vs liveliness vs close).

## Solution: background daemon

The SDK provides a **background daemon** (like ros2's daemon). When the daemon is running, `zenoh-ros2 topic list` and `zenoh-ros2 topic info` delegate discovery to it over HTTP and **return quickly** (no session close in the CLI process).

- **Start the daemon:** `zenoh-ros2 daemon start`  
  (Or let the CLI auto-spawn it on first use; that run also uses the daemon and returns quickly.)
- **Check status:** `zenoh-ros2 daemon status`
- **Stop:** `zenoh-ros2 daemon stop`

With the daemon running, topic list/info avoid the 10 s delay. See README or getting-started for details.
