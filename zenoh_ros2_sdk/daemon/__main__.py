"""Allow running the daemon as python -m zenoh_ros2_sdk.daemon."""

import sys

from . import main

sys.exit(main())
