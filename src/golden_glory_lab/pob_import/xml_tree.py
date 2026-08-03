"""Bounded, non-validating XML event loader used by the PoB importer.

The exact input string remains the byte-fidelity authority. This loader builds
an ordered structural view and exposes XML-normalized character data; it does
not claim byte-exact element spans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from xml.parsers import expat

from .limits import ImportLimits


@dataclass(slots=True)
class XmlLoadFailure(Exception):
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    byteIndex: int | None = None


def _attributes(pairs: list[str]) -> list[dict[str, str]]:
    return [
        {"name": pairs[index], "value": pairs[index + 1]}
        for index in range(0, len(pairs), 2)
    ]


def load_xml_tree(xml_bytes: bytes, limits: ImportLimits) -> dict[str, Any]:
    parser = expat.ParserCreate(encoding="UTF-8")
    parser.ordered_attributes = True
    parser.specified_attributes = True
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)

    stack: list[dict[str, Any]] = []
    roots: list[dict[str, Any]] = []
    in_cdata = False
    element_count = 0

    def location() -> tuple[int, int, int]:
        return (
            parser.CurrentLineNumber,
            parser.CurrentColumnNumber,
            parser.CurrentByteIndex,
        )

    def fail(code: str, message: str) -> None:
        line, column, byte_index = location()
        raise XmlLoadFailure(code, message, line, column, byte_index)

    def append_child(child: dict[str, Any]) -> None:
        if stack:
            stack[-1]["children"].append(child)
        else:
            roots.append(child)

    def start_element(name: str, pairs: list[str]) -> None:
        nonlocal element_count
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
        stack.append(node)

    def end_element(_name: str) -> None:
        stack.pop()

    def character_data(data: str) -> None:
        if not data:
            return
        kind = "cdata" if in_cdata else "text"
        target = stack[-1]["children"] if stack else roots
        if target and target[-1]["kind"] == kind:
            target[-1]["value"] += data
        else:
            target.append({"kind": kind, "value": data})
        if stack:
            total = _character_bytes(stack[-1])
            if total > limits.maxTextBytesPerElement:
                fail(
                    "XML_TEXT_LIMIT",
                    "XML character data in one element exceeds the configured limit",
                )

    def start_cdata() -> None:
        nonlocal in_cdata
        in_cdata = True

    def end_cdata() -> None:
        nonlocal in_cdata
        in_cdata = False

    def comment(data: str) -> None:
        append_child({"kind": "comment", "value": data})

    def processing_instruction(target: str, data: str) -> None:
        append_child({"kind": "processing-instruction", "target": target, "value": data})

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

    element_roots = [node for node in roots if node["kind"] == "element"]
    if len(element_roots) != 1:
        raise XmlLoadFailure(
            "XML_ROOT_COUNT",
            "XML document must contain exactly one root element",
            parser.CurrentLineNumber,
            parser.CurrentColumnNumber,
            parser.CurrentByteIndex,
        )
    return element_roots[0]


def _character_bytes(element: dict[str, Any]) -> int:
    total = 0
    for child in element["children"]:
        if child["kind"] in {"text", "cdata"}:
            total += len(child["value"].encode("utf-8"))
    return total


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


def element_children(element: dict[str, Any], name: str | None = None) -> list[dict[str, Any]]:
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
