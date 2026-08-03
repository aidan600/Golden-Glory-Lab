"""Bounded, non-validating XML event loader used by the PoB importer.

The exact input string remains the byte-fidelity authority. This loader builds
an ordered structural view and exposes XML-normalized character data; it does
not claim byte-exact element spans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from xml.parsers import expat

from .limits import ImportLimits

MINIMUM_EXPAT_VERSION = (2, 7, 2)
MINIMUM_EXPAT_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_EXPAT_VERSION)
_EXPAT_VERSION_RE = re.compile(r"^(?:expat_)?([0-9]+)\.([0-9]+)\.([0-9]+)$")


@dataclass(slots=True)
class XmlLoadFailure(Exception):
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    byteIndex: int | None = None


@dataclass(slots=True)
class XmlLoadInstrumentation:
    """Test instrumentation for the character-data complexity boundary."""

    characterCallbacks: int = 0
    characterUtf8EncodeCalls: int = 0
    characterUtf8Bytes: int = 0
    retainedTextRescans: int = 0
    characterConsolidations: int = 0
    maxChunksPerConsolidation: int = 0


@dataclass(slots=True)
class _OpenElement:
    node: dict[str, Any]
    retainedTextUtf8Bytes: int = 0


def expat_runtime_metadata(version: object | None = None) -> dict[str, Any]:
    """Return non-throwing metadata for the linked Expat security boundary."""

    detected = getattr(expat, "EXPAT_VERSION", None) if version is None else version
    parsed: tuple[int, int, int] | None = None
    if isinstance(detected, str):
        match = _EXPAT_VERSION_RE.fullmatch(detected)
        if match:
            try:
                parsed = tuple(int(part) for part in match.groups())
            except (ValueError, OverflowError):
                parsed = None
    if parsed is None:
        status = "unparseable"
    elif parsed < MINIMUM_EXPAT_VERSION:
        status = "unsupported"
    else:
        status = "supported"
    return {
        "detectedExpatVersion": detected if isinstance(detected, str) else None,
        "parsedExpatVersion": list(parsed) if parsed is not None else None,
        "minimumExpatVersion": MINIMUM_EXPAT_VERSION_TEXT,
        "status": status,
    }


def _require_safe_expat_runtime() -> dict[str, Any]:
    metadata = expat_runtime_metadata()
    if metadata["status"] != "supported":
        detected = metadata["detectedExpatVersion"] or "unparseable"
        raise XmlLoadFailure(
            "XML_RUNTIME_UNSUPPORTED",
            f"Expat {detected} does not satisfy the reviewed minimum {MINIMUM_EXPAT_VERSION_TEXT}",
        )
    return metadata


def _attributes(pairs: list[str]) -> list[dict[str, str]]:
    return [
        {"name": pairs[index], "value": pairs[index + 1]}
        for index in range(0, len(pairs), 2)
    ]


def load_xml_tree(
    xml_bytes: bytes | bytearray,
    limits: ImportLimits,
    *,
    instrumentation: XmlLoadInstrumentation | None = None,
) -> dict[str, Any]:
    runtime_security = _require_safe_expat_runtime()
    parser = expat.ParserCreate(encoding="UTF-8")
    parser.ordered_attributes = True
    parser.specified_attributes = True
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    if hasattr(parser, "SetReparseDeferralEnabled"):
        parser.SetReparseDeferralEnabled(True)

    stack: list[_OpenElement] = []
    document_nodes: list[dict[str, Any]] = []
    in_cdata = False
    element_count = 0
    pending_target: list[dict[str, Any]] | None = None
    pending_kind: str | None = None
    pending_chunks: list[str] = []
    pending_exists = False

    def location() -> tuple[int, int, int]:
        return (
            parser.CurrentLineNumber,
            parser.CurrentColumnNumber,
            parser.CurrentByteIndex,
        )

    def fail(code: str, message: str) -> None:
        line, column, byte_index = location()
        raise XmlLoadFailure(code, message, line, column, byte_index)

    def current_target() -> list[dict[str, Any]]:
        return stack[-1].node["children"] if stack else document_nodes

    def flush_character_segment() -> None:
        nonlocal pending_target, pending_kind, pending_chunks, pending_exists
        if not pending_exists:
            return
        assert pending_target is not None
        assert pending_kind is not None
        pending_target.append({"kind": pending_kind, "value": "".join(pending_chunks)})
        if instrumentation is not None:
            instrumentation.characterConsolidations += 1
            instrumentation.maxChunksPerConsolidation = max(
                instrumentation.maxChunksPerConsolidation, len(pending_chunks)
            )
        pending_target = None
        pending_kind = None
        pending_chunks = []
        pending_exists = False

    def begin_character_segment(kind: str) -> None:
        nonlocal pending_target, pending_kind, pending_chunks, pending_exists
        target = current_target()
        if pending_exists and (pending_target is not target or pending_kind != kind):
            flush_character_segment()
        if not pending_exists:
            pending_target = target
            pending_kind = kind
            pending_chunks = []
            pending_exists = True

    def append_child(child: dict[str, Any]) -> None:
        current_target().append(child)

    def start_element(name: str, pairs: list[str]) -> None:
        nonlocal element_count
        flush_character_segment()
        element_count += 1
        if element_count > limits.maxXmlElements:
            fail("XML_ELEMENT_LIMIT", "XML element count exceeds the configured limit")
        if len(stack) + 1 > limits.maxXmlDepth:
            fail("XML_DEPTH_LIMIT", "XML nesting depth exceeds the configured limit")
        if len(pairs) // 2 > limits.maxAttributesPerElement:
            fail(
                "XML_ATTRIBUTE_LIMIT",
                "XML attribute count on one element exceeds the configured limit",
            )
        node = {
            "kind": "element",
            "name": name,
            "attributes": _attributes(pairs),
            "children": [],
        }
        append_child(node)
        stack.append(_OpenElement(node))

    def end_element(_name: str) -> None:
        flush_character_segment()
        stack.pop()

    def character_data(data: str) -> None:
        if not data:
            return
        if instrumentation is not None:
            instrumentation.characterCallbacks += 1
            instrumentation.characterUtf8EncodeCalls += 1
        encoded_size = len(data.encode("utf-8"))
        if instrumentation is not None:
            instrumentation.characterUtf8Bytes += encoded_size
        if stack:
            frame = stack[-1]
            retained = frame.retainedTextUtf8Bytes + encoded_size
            if retained > limits.maxTextBytesPerElement:
                fail(
                    "XML_TEXT_LIMIT",
                    "XML character data in one element exceeds the configured limit",
                )
            frame.retainedTextUtf8Bytes = retained
        begin_character_segment("cdata" if in_cdata else "text")
        pending_chunks.append(data)

    def start_cdata() -> None:
        nonlocal in_cdata
        flush_character_segment()
        in_cdata = True
        begin_character_segment("cdata")

    def end_cdata() -> None:
        nonlocal in_cdata
        flush_character_segment()
        in_cdata = False

    def comment(data: str) -> None:
        flush_character_segment()
        append_child({"kind": "comment", "value": data})

    def processing_instruction(target: str, data: str) -> None:
        flush_character_segment()
        append_child(
            {"kind": "processing-instruction", "target": target, "value": data}
        )

    def reject_doctype(*_args: Any) -> None:
        fail("XML_DTD_FORBIDDEN", "DTD declarations are forbidden")

    def reject_entity(*_args: Any) -> None:
        fail("XML_EXTERNAL_ENTITY_FORBIDDEN", "Entity declarations are forbidden")

    def reject_external_entity(*_args: Any) -> int:
        fail("XML_EXTERNAL_ENTITY_FORBIDDEN", "External entities are forbidden")
        return 0

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.CharacterDataHandler = character_data
    parser.StartCdataSectionHandler = start_cdata
    parser.EndCdataSectionHandler = end_cdata
    parser.CommentHandler = comment
    parser.ProcessingInstructionHandler = processing_instruction
    parser.StartDoctypeDeclHandler = reject_doctype
    parser.EntityDeclHandler = reject_entity
    parser.ExternalEntityRefHandler = reject_external_entity

    try:
        chunk_size = limits.decompressionChunkBytes
        for offset in range(0, len(xml_bytes), chunk_size):
            parser.Parse(xml_bytes[offset : offset + chunk_size], False)
        parser.Parse(b"", True)
        flush_character_segment()
    except XmlLoadFailure:
        raise
    except expat.ExpatError as error:
        raise XmlLoadFailure(
            "XML_SYNTAX_ERROR",
            str(error),
            getattr(error, "lineno", parser.ErrorLineNumber),
            getattr(error, "offset", parser.ErrorColumnNumber),
            parser.ErrorByteIndex,
        ) from error

    element_roots = [node for node in document_nodes if node["kind"] == "element"]
    if len(element_roots) != 1:
        raise XmlLoadFailure(
            "XML_ROOT_COUNT",
            "XML document must contain exactly one root element",
            parser.CurrentLineNumber,
            parser.CurrentColumnNumber,
            parser.CurrentByteIndex,
        )
    root = element_roots[0]
    document_events = [
        {"kind": "root-element", "name": node["name"]}
        if node["kind"] == "element"
        else node
        for node in document_nodes
    ]
    return {
        "root": root,
        "documentEvents": document_events,
        "runtimeSecurity": runtime_security,
    }


def character_value(element: dict[str, Any]) -> str:
    values: list[str] = []

    def visit(node: dict[str, Any]) -> None:
        if node["kind"] in {"text", "cdata"}:
            values.append(node["value"])
        elif node["kind"] == "element":
            for child in node["children"]:
                visit(child)

    visit(element)
    return "".join(values)


def element_children(
    element: dict[str, Any], name: str | None = None
) -> list[dict[str, Any]]:
    children = [child for child in element["children"] if child["kind"] == "element"]
    if name is None:
        return children
    return [child for child in children if child["name"] == name]


def attribute_state(element: dict[str, Any], name: str) -> dict[str, Any]:
    for attribute in element["attributes"]:
        if attribute["name"] == name:
            return {
                "state": "empty" if attribute["value"] == "" else "present",
                "value": attribute["value"],
            }
    return {"state": "missing", "value": None}


def attribute_value(element: dict[str, Any], name: str) -> str | None:
    state = attribute_state(element, name)
    return state["value"]
