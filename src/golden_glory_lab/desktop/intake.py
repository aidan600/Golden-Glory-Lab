"""Bounded desktop intake adapters over the adopted public PoB importer."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from golden_glory_lab.pob_import import (
    DEFAULT_IMPORT_LIMITS,
    importPobRawXml,
    importPobShareCode,
)


class DesktopIntakeError(ValueError):
    """A file/input boundary error distinct from an importer failure."""

    stage = "desktop-intake"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def as_attempt(self) -> dict[str, Any]:
        return {
            "kind": "desktop-intake-error",
            "code": self.code,
            "stage": self.stage,
            "message": self.message,
            "report": [],
        }


def import_raw_xml_file(
    path_value: str | os.PathLike[str],
    *,
    importer: Callable[[str], dict[str, Any]] = importPobRawXml,
) -> dict[str, Any]:
    """Stat first, then perform one bounded binary read and strict UTF-8 decode."""

    path = Path(path_value)
    try:
        observed_size = path.stat().st_size
    except OSError as error:
        raise DesktopIntakeError(
            "RAW_XML_FILE_ACCESS",
            f"Could not inspect the selected XML file: {error}",
        ) from error
    limit = DEFAULT_IMPORT_LIMITS.maxRawXmlBytes
    if observed_size > limit:
        raise DesktopIntakeError(
            "RAW_XML_FILE_SIZE",
            f"Selected XML file is {observed_size} bytes; the limit is {limit} bytes",
        )
    try:
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError as error:
        raise DesktopIntakeError(
            "RAW_XML_FILE_ACCESS",
            f"Could not read the selected XML file: {error}",
        ) from error
    if len(data) > limit:
        raise DesktopIntakeError(
            "RAW_XML_FILE_SIZE_CHANGED",
            "Selected XML file grew beyond the limit while it was being read",
        )
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise DesktopIntakeError(
            "RAW_XML_FILE_UTF8",
            f"Selected XML file is not strict UTF-8 at byte {error.start}",
        ) from error
    return importer(text)


def import_share_code_text(
    value: str,
    *,
    importer: Callable[[str], dict[str, Any]] = importPobShareCode,
) -> dict[str, Any]:
    """Reject oversized pasted input before invoking the public importer."""

    if not isinstance(value, str):
        raise DesktopIntakeError(
            "SHARE_CODE_TYPE", "Pasted share-code input must be text"
        )
    limit = DEFAULT_IMPORT_LIMITS.maxShareCodeCharacters
    if len(value) > limit:
        raise DesktopIntakeError(
            "SHARE_CODE_LENGTH",
            f"Pasted share code is {len(value)} characters; the limit is {limit}",
        )
    return importer(value)
