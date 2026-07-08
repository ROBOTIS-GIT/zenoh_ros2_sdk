FROM ros:jazzy

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    netcat-openbsd \
    python3-dev \
    python3-pip \
    python3-venv \
    ripgrep \
    ros-jazzy-action-tutorials-interfaces \
    ros-jazzy-action-tutorials-py \
    ros-jazzy-example-interfaces \
    ros-jazzy-rmw-zenoh-cpp \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages /opt/zenoh_ros2_sdk_venv
ENV PATH="/opt/zenoh_ros2_sdk_venv/bin:${PATH}"

RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /workspace

CMD ["bash", "docker/ros_jazzy_rmw_zenoh/run_tests.sh"]
