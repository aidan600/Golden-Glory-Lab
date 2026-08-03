"""Centralized resource limits for the PoB neutral importer.

These values are proof defaults. They are deliberately explicit and included
in every import result; a later release may revise them through review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ImportLimits:
    maxShareCodeCharacters: int = 4_000_000
    maxDecodedCompressedBytes: int = 3_000_000
    maxDecompressedXmlBytes: int = 8_000_000
    maxRawXmlBytes: int = 8_000_000
    maxXmlDepth: int = 64
    maxXmlElements: int = 50_000
    maxAttributesPerElement: int = 64
    maxTextBytesPerElement: int = 1_000_000
    maxReportEntries: int = 256
    decompressionChunkBytes: int = 16_384

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    def with_overrides(self, overrides: Mapping[str, Any] | None) -> "ImportLimits":
        if not overrides:
            return self
        allowed = {field.name for field in fields(self)}
        unknown = sorted(set(overrides) - allowed)
        if unknown:
            raise ValueError(f"unknown import limit(s): {', '.join(unknown)}")
        normalized: dict[str, int] = {}
        for name, value in overrides.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"import limit {name} must be a positive integer")
            normalized[name] = value
        return replace(self, **normalized)


DEFAULT_IMPORT_LIMITS = ImportLimits()

