"""
WIKIFUNCTIONS API MOCK
----------------------

Minimal helpers to simulate Wikifunctions Z-Objects for local testing.

Why this file exists
~~~~~~~~~~~~~~~~~~~~
On Wikifunctions, implementations do not always receive plain Python
values like strings or integers. Instead, they receive *Z-Objects*,
which are JSON structures describing typed values such as:

- Z6 (String)
- Z9 (Reference / ZID)

For local development, it is convenient to be able to:

- Construct such objects (Z6, Z9).
- Unwrap them back into plain Python types.
- Handle both wrapped and raw inputs transparently.

This module provides tiny helpers to do exactly that, without pulling in
the full official Z-Object machinery.
"""

from __future__ import annotations

from typing import Any, Dict


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------


def Z6(text: str) -> Dict[str, Any]:
    """
    Wrap a Python string in a Z6 (String) object.

    Example:
        Z6("Hello") →
            {
                "Z1K1": "Z6",
                "Z6K1": "Hello"
            }
    """
    return {
        "Z1K1": "Z6",
        "Z6K1": text,
    }


def Z9(zid: str) -> Dict[str, Any]:
    """
    Wrap a ZID (e.g. 'Z12345') in a Z9 (Reference) object.

    Example:
        Z9("Z12345") →
            {
                "Z1K1": "Z9",
                "Z9K1": "Z12345"
            }
    """
    return {
        "Z1K1": "Z9",
        "Z9K1": zid,
    }


# ---------------------------------------------------------------------------
# Unwrapping helpers
# ---------------------------------------------------------------------------


def unwrap(z_object: Any) -> Any:
    """
    Unwrap a *single* Z-Object to a native Python type, non-recursively.

    This is intentionally minimal: it only handles Z6 (String) and Z9
    (Reference) objects, which are the most common wrappers you are likely
    to encounter in simple implementations.

    Behavior:
        - If z_object is already a plain string, return it unchanged.
        - If z_object is a dict with {"Z1K1": "Z6"}, return its "Z6K1" field.
        - If z_object is a dict with {"Z1K1": "Z9"}, return its "Z9K1" field.
        - Otherwise, return z_object unchanged.

    Note:
        This function does NOT recurse into nested dicts/lists.
        For that, use `unwrap_recursive`.
    """
    # Already a plain string
    if isinstance(z_object, str):
        return z_object

    # Z-Object dictionary
    if isinstance(z_object, dict):
        z_type = z_object.get("Z1K1")

        # Z6 String
        if z_type == "Z6":
            return z_object.get("Z6K1", "")

        # Z9 Reference (we return the ZID as a plain string)
        if z_type == "Z9":
            return z_object.get("Z9K1", "")

    # Anything else: leave untouched
    return z_object


def unwrap_recursive(value: Any) -> Any:
    """
    Recursively unwrap Z-Objects inside nested structures.

    This is useful if your Wikifunctions implementation receives
    composite arguments such as lists or dictionaries of Z-Objects.

    Behavior:
        - If value is a list, recursively unwrap each element.
        - If value is a dict and looks like a Z-Object, unwrap it with
          `unwrap`, then (if still a dict) recurse into its children.
        - For anything else, fall back to `unwrap`.

    Example:
        unwrap_recursive([Z6("A"), Z6("B")]) → ["A", "B"]
    """
    # Lists: unwrap each element
    if isinstance(value, list):
        return [unwrap_recursive(v) for v in value]

    # Dict: first try to unwrap as a single Z-Object
    if isinstance(value, dict):
        unwrapped = unwrap(value)
        # If unwrap() returned something else (e.g. string or non-dict), return it
        if not isinstance(unwrapped, dict):
            return unwrapped

        # Otherwise, recurse into its fields (plain dict)
        return {k: unwrap_recursive(v) for k, v in unwrapped.items()}

    # For primitives, just use simple unwrap (handles Z6/Z9 directly)
    return unwrap(value)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def ensure_z6(value: Any) -> Dict[str, Any]:
    """
    Ensure a value is represented as a Z6 object.

    - If `value` is already a Z6, return it.
    - If `value` is a plain string, wrap it as Z6.
    - Otherwise, convert to str and wrap.

    This is handy when simulating outputs that should be Z6 on
    Wikifunctions.
    """
    if isinstance(value, dict) and value.get("Z1K1") == "Z6":
        return value
    if isinstance(value, str):
        return Z6(value)
    return Z6(str(value))


__all__ = [
    "Z6",
    "Z9",
    "unwrap",
    "unwrap_recursive",
    "ensure_z6",
]


# ---------------------------------------------------------------------------
# Example usage for ad-hoc testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    raw_input = "Hello"
    z_input = Z6("Hello")
    nested = {"greeting": Z6("Hi"), "ref": Z9("Z42"), "list": [Z6("A"), "B"]}

    print("=== Simple unwrap ===")
    print(f"Raw input unwrapped: {unwrap(raw_input)!r}")
    print(f"Z6 input unwrapped:  {unwrap(z_input)!r}")

    print("\n=== Recursive unwrap ===")
    print(f"Nested before: {nested}")
    print(f"Nested after:  {unwrap_recursive(nested)}")

    print("\n=== ensure_z6 ===")
    print(ensure_z6("ok"))
    print(ensure_z6(Z6("already")))
