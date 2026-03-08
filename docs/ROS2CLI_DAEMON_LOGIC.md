# ros2cli daemon — exact logic

This document describes how the ROS 2 CLI daemon works, by pointing to the code in the upstream **ros2cli** repository. Use it as a reference when implementing a daemon for `zenoh-ros2`.

---

## 1. Protocol: XML-RPC over HTTP (TCP)

- **Not** raw HTTP REST; the CLI talks to the daemon via **XML-RPC**.
- **Client:** stdlib `xmlrpc.client.ServerProxy` (re-exported in `ros2cli/xmlrpc/client.py`).
- **Server:** `ros2cli/xmlrpc/local_server.py` — `LocalXMLRPCServer` extends `xmlrpc.server.SimpleXMLRPCServer`, binds to `127.0.0.1`, and only accepts requests from local IPs (`verify_request` checks `get_local_ipaddrs()` via psutil).
- **URL:** `http://127.0.0.1:<port>/ros2cli/` — port is `11511 + ROS_DOMAIN_ID` (see `ros2cli/daemon/__init__.py` `get_port()`, `get_xmlrpc_server_url()`).

---

## 2. Node strategy: daemon vs direct

`ros2cli/node/strategy.py`:

- **`NodeStrategy.__init__(args)`**
  1. If `use_daemon` (default True, unless `--no-daemon`) and **`is_daemon_running(args)`** → use **`DaemonNode(args)`**. If `DaemonNode.connected` is False, fall back to **`DirectNode(args)`**.
  2. Else (daemon not running): if `use_daemon`, call **`spawn_daemon(args)`**, then create **`DirectNode(args)`** (so this invocation still runs direct; next invocation will see the daemon).
- **`__getattr__(name)`:** If we have a daemon node and `name` is in `daemon_node.methods`, forward to the daemon (XML-RPC); otherwise forward to `direct_node`.

So: **first run** spawns the daemon but uses DirectNode for that run. **Subsequent runs** use the daemon (no node created in CLI process).

---

## 3. DaemonNode — CLI side

`ros2cli/node/daemon.py`:

- **`DaemonNode(args)`**  
  Builds **`ServerProxy(daemon.get_xmlrpc_server_url(), allow_none=True)`** (stdlib XML-RPC client).
- **`connected`**  
  Tries `self._proxy.system.listMethods()`; on success caches method names (excluding `system.*`), returns True; on `ConnectionRefusedError` / `ConnectionResetError` / `TimeoutError` returns False.
- **`methods`**  
  List of RPC method names (e.g. `get_topic_names_and_types`, `count_publishers`, …).
- **`__getattr__(name)`**  
  Forwards to `self._proxy`, so e.g. `node.get_topic_names_and_types(...)` becomes an XML-RPC call.

---

## 4. Spawning the daemon (socket handoff)

`ros2cli/node/daemon.py` `spawn_daemon(args, timeout=None, debug=False)`:

1. **Create XML-RPC server in this process**  
   `server = daemon.make_xmlrpc_server()` → binds to `127.0.0.1:11511+ROS_DOMAIN_ID`. If **`EADDRINUSE`**, assume daemon already running and return False.
2. **`server.socket.set_inheritable(True)`**  
   So the socket can be passed to the child.
3. **(Unix only)** Mark all FDs except 0,1,2 and the server socket as non-inheritable so daemonize doesn’t hang (see comment and issue #851).
4. **Start daemon process with socket handoff**  
   `daemonize(functools.partial(daemon.serve_and_close, server), tags={...}, timeout=timeout, debug=debug)`.
5. **`daemonize`** ([daemon/daemonize.py](deps/ros2cli/ros2cli/ros2cli/daemon/daemonize.py)):  
   - Spawns subprocess: `python -c 'from ros2cli.daemon.daemonize import main; main()'` with `--name ros2-daemon`, `--ros-domain-id`, `--rmw-implementation`.  
   - Child’s stdin is a pipe. Parent **pickles** the callable `serve_and_close(server)` with **`PicklerForProcess`**, which can serialize the **socket** (by fileno on Unix, or `socket.share()` on Windows) and sends it over stdin.  
   - Child **unpickles** the callable (which now holds the same server/socket), closes stdin, then runs `callable_()` → **`serve_and_close(server)`** in the daemon process.  
   - So the **listening socket is created in the parent**, then **transferred to the child**; only one process ever binds it (avoids TOCTOU).
6. Parent calls `server.server_close()` in `finally` (server object in parent is no longer listening).
7. If `timeout` is set, parent waits for daemon to close its stdin (child closes stdin after unpickling) via `wait_for(daemon_ready, timeout)`.

---

## 5. Daemon process — server side

`ros2cli/daemon/__init__.py`:

- **`serve_and_close(server, timeout=2*60*60)`**  
  Calls **`serve(server, timeout=timeout)`**, then `server.server_close()` in `finally`.
- **`serve(server, timeout=...)`**
  1. Creates **one long-lived node**: `with NetworkAwareNode(node_args) as node:` — this is a **DirectNode** (rclpy node) that may be recreated if network interfaces change ([node/network_aware.py](deps/ros2cli/ros2cli/ros2cli/node/network_aware.py)).
  2. **Registers RPC methods** with the XML-RPC server: each method is a **bound method** of that node, e.g.  
     `node.get_topic_names_and_types`,  
     `node.get_service_names_and_types`,  
     `node.count_publishers`,  
     `node.count_subscribers`,  
     … (see the `functions` list in `serve()`).  
     So when the CLI calls `proxy.get_topic_names_and_types(...)`, the daemon runs `node.get_topic_names_and_types(...)` and returns the result (serialized via XML-RPC; rclpy types are marshalled, see [xmlrpc/marshal/](deps/ros2cli/ros2cli/ros2cli/xmlrpc/marshal/)).
  3. Registers **`system.shutdown`** to set a shutdown flag.
  4. **Loop:** `while rclpy.ok() and not shutdown: server.handle_request()` with **`server.timeout = 0.2`** so the daemon can react to signals and an inactivity timeout. If no RPC for `timeout` seconds, the daemon exits.

So the daemon holds **one** rclpy node (via NetworkAwareNode) and serves all discovery/getters over XML-RPC.

---

## 6. Summary flow

```text
CLI (e.g. ros2 topic list)
  → NodeStrategy: is_daemon_running? (ServerProxy to http://127.0.0.1:11511+domain/ros2cli/)
  → If yes: DaemonNode → proxy.get_topic_names_and_types(...) → XML-RPC → daemon runs node.get_topic_names_and_types() → response → CLI prints and exits (no node in CLI).
  → If no:  spawn_daemon() [creates server, binds socket, daemonize(serve_and_close(server)); daemon process receives socket, runs serve() with one DirectNode, registers RPC methods, handle_request() loop];
             then DirectNode(args) for this run (so this run still creates a node in CLI).
```

- **Port:** `11511 + ROS_DOMAIN_ID`, path `/ros2cli/`.
- **Transport:** XML-RPC over TCP (HTTP with XML payloads).
- **Socket handoff:** Parent creates and binds the server socket, passes it to child via pickle over stdin; only the child serves.
- **Daemon API:** Methods of the long-lived node (get_topic_names_and_types, count_publishers, etc.) plus `system.listMethods` and `system.shutdown`.
