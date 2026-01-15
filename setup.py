#!/usr/bin/env python3
"""Setup script for zenoh-ros2-sdk"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zenoh-ros2-sdk",
    version="0.1.0",
    author="Woojin Wie",
    author_email="wwj@robotis.com",
    description="Python SDK for ROS2 communication via Zenoh - No ROS2 installation required",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/robotis-git/zenoh_ros2_sdk",
    packages=find_packages(exclude=["tests", "examples"]),
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "eclipse-zenoh>=0.10.0",
        "rosbags>=0.11.0",
        "GitPython>=3.1.18",
        "tqdm>=4.64.0",
        "json5>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
    },
)
