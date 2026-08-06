"""Bounded deterministic recognition for Flame Link player-chain lines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .decimal_input import parse_decimal_text

_LIGHT_RADIUS_RE = re.compile(
    r"(?P<value>-?[0-9]+(?:\.[0-9]+)?)\s*%\s+"
    r"(?P<direction>increased|reduced)\s+Light\s+Radius\b",
    re.IGNORECASE,
)
_LINK_BUFF_EFFECT_PATTERNS = (
    re.compile(
        r"(?P<value>-?[0-9]+(?:\.[0-9]+)?)\s*%\s+"
        r"(?P<direction>increased|reduced)\s+Effect\s+of\s+your\s+Link\s+Skills\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<value>-?[0-9]+(?:\.[0-9]+)?)\s*%\s+"
        r"(?P<direction>increased|reduced)\s+Buff\s+Effect\s+of\s+Link\s+Skills\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<value>-?[0-9]+(?:\.[0-9]+)?)\s*%\s+"
        r"(?P<direction>increased|reduced)\s+Effect\s+of\s+Link\s+Skills\b",
        re.IGNORECASE,
    ),
)
# Identity evidence only — never treat Powerful Bond or generic level text as Empowered.
_EMPOWERED_BOND_IDENTITY_RE = re.compile(r"\bEmpowered\s+Bond\b", re.IGNORECASE)
_GENERIC_LINK_GEM_LEVEL_RE = re.compile(
    r"(?P<sign>[+-])?(?P<value>[0-9]+)\s+to\s+Level\s+of\s+all\s+Link\s+Skill\s+Gems?\b|"
    r"(?P<sign2>[+-])?(?P<value2>[0-9]+)\s+(?:additional\s+)?levels?\s+to\s+"
    r"(?:your\s+)?Link\s+(?:Skill\s+)?Gems?\b|"
    r"Link\s+(?:Skill\s+)?Gems?\s+(?:have|gain)\s+(?P<sign3>[+-])?(?P<value3>[0-9]+)\s+"
    r"(?:to\s+)?levels?\b",
    re.IGNORECASE,
)
_POWERFUL_BOND_RE = re.compile(r"\bPowerful\s+Bond\b", re.IGNORECASE)
_INSPIRING_BOND_RE = re.compile(r"\bInspiring\s+Bond\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RecognizedPlayerChainLine:
    kind: str
    signedValueLexeme: str | None
    rawSourceText: str
    sourceLine: str
    notes: tuple[str, ...]
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "signedValueLexeme": self.signedValueLexeme,
            "label": self.label,
            "rawSourceText": self.rawSourceText,
            "sourceLine": self.sourceLine,
            "notes": list(self.notes),
        }


def _signed_lexeme(value_text: str, direction: str) -> str | None:
    try:
        parsed = parse_decimal_text(value_text)
    except Exception:
        return None
    magnitude = parsed.value.copy_abs()
    if direction.lower() == "reduced":
        signed = -magnitude
    else:
        signed = magnitude
    text = format(signed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"


def _generic_level_lexeme(match: re.Match[str]) -> str | None:
    for value_key, sign_key in (
        ("value", "sign"),
        ("value2", "sign2"),
        ("value3", "sign3"),
    ):
        value = match.group(value_key)
        if value is None:
            continue
        sign = match.group(sign_key) or "+"
        if sign == "-":
            return f"-{value}" if not value.startswith("-") else value
        return value
    return None


def _iter_lines(raw_text: str) -> Iterable[str]:
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def recognize_player_chain_text(raw_text: str) -> tuple[RecognizedPlayerChainLine, ...]:
    """Recognize advisory player-chain candidate lines from reviewed item text.

    Ownership, equipped state, and Mercenary targeting are never inferred.
    Recognition does not mutate build state; reviewed manual totals remain
    authoritative when the user applies them.
    """

    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")
    found: list[RecognizedPlayerChainLine] = []
    for line in _iter_lines(raw_text):
        light = _LIGHT_RADIUS_RE.search(line)
        if light is not None:
            lexeme = _signed_lexeme(light.group("value"), light.group("direction"))
            if lexeme is not None:
                found.append(
                    RecognizedPlayerChainLine(
                        kind="light-radius",
                        signedValueLexeme=lexeme,
                        label="Light Radius",
                        rawSourceText=raw_text,
                        sourceLine=line,
                        notes=("advisory-only", "does-not-infer-ownership-or-target"),
                    )
                )
        for pattern in _LINK_BUFF_EFFECT_PATTERNS:
            match = pattern.search(line)
            if match is None:
                continue
            lexeme = _signed_lexeme(match.group("value"), match.group("direction"))
            if lexeme is None:
                continue
            found.append(
                RecognizedPlayerChainLine(
                    kind="direct-link-buff-effect",
                    signedValueLexeme=lexeme,
                    label="Direct Link Skill Buff Effect",
                    rawSourceText=raw_text,
                    sourceLine=line,
                    notes=("advisory-only", "does-not-infer-ownership-or-target"),
                )
            )
            break
        if _EMPOWERED_BOND_IDENTITY_RE.search(line):
            found.append(
                RecognizedPlayerChainLine(
                    kind="empowered-bond-level",
                    signedValueLexeme="2",
                    label="Empowered Bond",
                    rawSourceText=raw_text,
                    sourceLine=line,
                    notes=("advisory-only", "empowered-bond-level-candidate"),
                )
            )
        else:
            generic = _GENERIC_LINK_GEM_LEVEL_RE.search(line)
            if generic is not None and not _POWERFUL_BOND_RE.search(line):
                lexeme = _generic_level_lexeme(generic)
                if lexeme is not None:
                    found.append(
                        RecognizedPlayerChainLine(
                            kind="generic-link-gem-level",
                            signedValueLexeme=lexeme,
                            label="Additional Link Skill Gem levels",
                            rawSourceText=raw_text,
                            sourceLine=line,
                            notes=(
                                "advisory-only",
                                "generic-link-gem-level-candidate",
                                "does-not-infer-empowered-bond",
                            ),
                        )
                    )
        if _POWERFUL_BOND_RE.search(line):
            found.append(
                RecognizedPlayerChainLine(
                    kind="powerful-bond-conditional",
                    signedValueLexeme="20",
                    label="Powerful Bond",
                    rawSourceText=raw_text,
                    sourceLine=line,
                    notes=(
                        "advisory-only",
                        "conditional-buff-effect-not-additional-gem-levels",
                        "does-not-auto-activate",
                    ),
                )
            )
        if _INSPIRING_BOND_RE.search(line):
            found.append(
                RecognizedPlayerChainLine(
                    kind="inspiring-bond-conditional",
                    signedValueLexeme="20",
                    label="Inspiring Bond",
                    rawSourceText=raw_text,
                    sourceLine=line,
                    notes=(
                        "advisory-only",
                        "conditional-buff-effect-not-additional-gem-levels",
                        "does-not-auto-activate",
                    ),
                )
            )
    return tuple(found)


def recognize_player_chain_sources(
    texts: Iterable[str],
) -> tuple[RecognizedPlayerChainLine, ...]:
    results: list[RecognizedPlayerChainLine] = []
    for text in texts:
        results.extend(recognize_player_chain_text(text))
    return tuple(results)
