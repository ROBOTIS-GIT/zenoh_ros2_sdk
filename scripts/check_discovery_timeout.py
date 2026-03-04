#!/usr/bin/env python3
"""
Check where time is spent when running topic discovery (zenoh-ros2 topic list).

Times:
  1. zenoh.open() (session connect to router)
  2. Liveliness get for MP (publishers)
  3. Liveliness get for MS (subscribers)

Usage:
  # With router running (default 127.0.0.1:7447):
  python3 scripts/check_discovery_timeout.py

  # Custom router:
  python3 scripts/check_discovery_timeout.py --router 192.168.1.10:7447

  # Unreachable router (to see connect timeout; often ~10s):
  python3 scripts/check_discovery_timeout.py --router 127.0.0.1:19999
"""
from __future__ import annotations

import argparse
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure discovery/timeout phases")
    parser.add_argument(
        "--router",
        default="127.0.0.1:7447",
        help="Zenoh router endpoint (default: 127.0.0.1:7447)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.5,
        help="Liveliness query timeout in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--domain-id",
        type=int,
        default=None,
        help="ROS domain ID (default: ROS_DOMAIN_ID or 0)",
    )
    args = parser.parse_args()

    if ":" in args.router:
        parts = args.router.rsplit(":", 1)
        router_ip = parts[0]
        router_port = int(parts[1])
    else:
        router_ip = "127.0.0.1"
        router_port = 7447

    print("Phases (seconds):")
    print("-" * 50)

    # 1) Session open
    t0 = time.perf_counter()
    try:
        import zenoh
        conf = zenoh.Config()
        conf.insert_json5("connect/endpoints", f'["tcp/{router_ip}:{router_port}"]')
        session = zenoh.open(conf)
        t1 = time.perf_counter()
        print(f"  1. zenoh.open()                    {t1 - t0:.3f}s")
    except Exception as e:
        print(f"  1. zenoh.open()                    FAILED: {e}")
        return 1

    # 2) Liveliness get MP
    from zenoh_ros2_sdk.utils import resolve_domain_id
    from zenoh_ros2_sdk.keyexpr import ADMIN_SPACE
    domain_id = resolve_domain_id(args.domain_id)

    t2_start = time.perf_counter()
    try:
        pattern_mp = f"{ADMIN_SPACE}/{domain_id}/*/*/*/MP/**"
        list(session.liveliness().get(pattern_mp, timeout=args.timeout))
    except Exception as e:
        print(f"  2. liveliness.get(MP)              FAILED: {e}")
    else:
        t2_end = time.perf_counter()
        print(f"  2. liveliness.get(MP)              {t2_end - t2_start:.3f}s")

    # 3) Liveliness get MS
    t3_start = time.perf_counter()
    try:
        pattern_ms = f"{ADMIN_SPACE}/{domain_id}/*/*/*/MS/**"
        list(session.liveliness().get(pattern_ms, timeout=args.timeout))
    except Exception as e:
        print(f"  3. liveliness.get(MS)              FAILED: {e}")
    else:
        t3_end = time.perf_counter()
        print(f"  3. liveliness.get(MS)              {t3_end - t3_start:.3f}s")

    t_before_close = time.perf_counter()
    try:
        session.close()
    except Exception:
        pass
    t_after_close = time.perf_counter()
    if t_after_close - t_before_close > 0.01:
        print(f"  4. session.close()                 {t_after_close - t_before_close:.3f}s")

    t_total = time.perf_counter() - t0
    print("-" * 50)
    print(f"  Total                               {t_total:.3f}s")
    print()
    print("If total is ~10s, the delay is from session.close() (or open if router unreachable).")
    print("Use ZENOH_CONFIG_OVERRIDE to set connect/timeout_ms for connect phase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
