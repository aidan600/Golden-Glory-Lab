"""Deterministic serialization helpers for the neutral contract."""

from __future__ import annotations

import json
from typing import Any


def deterministic_json(result: dict[str, Any]) -> str:
    """Return the canonical human-reviewable JSON representation.

    Construction fixes object insertion order and this serializer fixes
    indentation, separators, Unicode handling, and the final newline. Arrays
    remain in source/report order; keys are intentionally not re-sorted.
    """

    return (
        json.dumps(
            result,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    )


def deterministic_json_bytes(result: dict[str, Any]) -> bytes:
    return deterministic_json(result).encode("utf-8")
