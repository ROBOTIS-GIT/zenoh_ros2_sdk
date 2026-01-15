# Documentation (MkDocs)

These instructions are for building/serving the documentation site locally.

## Install docs dependencies

From the repo root:

```bash
pip install -e ".[docs]"
```

## Serve locally

```bash
mkdocs serve
```

## Container note (Jetson/NVIDIA pip indexes)

Some container images set `PIP_INDEX_URL` to Jetson/NVIDIA indexes which may not contain build dependencies like `setuptools`.
To force PyPI, set:

```bash
export PIP_INDEX_URL=https://pypi.org/simple
unset PIP_EXTRA_INDEX_URL
```

