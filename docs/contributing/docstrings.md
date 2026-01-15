# Docstring Guidelines (Google style)

This project generates web API docs from docstrings using **MkDocs + mkdocstrings**.

## Goals

- Keep docstrings **accurate** (never describe behavior that isn’t implemented).
- Make sharp edges **explicit** (required env vars, Zenoh API constraints, expected payload shapes).
- Provide **copy/paste examples** for the most used APIs.

## Style (Google)

Use:

- One-line summary
- Blank line
- Optional longer description
- `Args:` / `Returns:` / `Raises:`
- `Examples:` when it helps adoption

Example:

```python
def foo(x: int) -> int:
    """Double an integer.

    Args:
        x: Input integer.

    Returns:
        The doubled value.

    Raises:
        ValueError: If `x` is negative.
    """
    if x < 0:
        raise ValueError("x must be non-negative")
    return 2 * x
```

## What must be documented (public APIs)

For each public class/function:

- **Args**: types + meaning; mention accepted unions (e.g., `qos` accepts `QosProfile | str | None`).
- **Returns**: include “None on timeout/error” if that’s the contract.
- **Raises**: list concrete exceptions users should expect.
- **Semantics**:
  - Data-plane keyexpr format
  - Liveliness token behavior (`@ros2_lv/...`)
  - Service attachment requirement and correlation key behavior
- **Examples**: minimal working examples (publish/subscribe, service callback, service queue mode).

