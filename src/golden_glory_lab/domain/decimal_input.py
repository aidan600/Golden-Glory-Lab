"""One bounded exact-decimal parser shared by U, M, and T."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import NoReturn

DECIMAL_DIGIT_LIMIT = 128
_DECIMAL_RE = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")


class DecimalInputError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise DecimalInputError(code, message)


@dataclass(frozen=True, slots=True)
class ParsedDecimal:
    lexeme: str
    value: Decimal

    @property
    def integral(self) -> bool:
        return self.value == self.value.to_integral_value()


def parse_decimal_text(value: str) -> ParsedDecimal:
    r"""Parse the exact grammar ``^-?[0-9]+(?:\.[0-9]+)?$``.

    The digit bound is enforced before constructing :class:`Decimal`, and the
    accepted lexeme is returned without canonicalization.
    """

    if not isinstance(value, str):
        _fail("DECIMAL_TEXT_TYPE", "Manual decimal input must be text")
    if not _DECIMAL_RE.fullmatch(value):
        _fail(
            "DECIMAL_TEXT_GRAMMAR",
            "Manual decimal input does not match the exact ASCII decimal grammar",
        )
    digit_count = sum(character in "0123456789" for character in value)
    if digit_count > DECIMAL_DIGIT_LIMIT:
        _fail(
            "DECIMAL_TEXT_DIGIT_LIMIT",
            f"Manual decimal input exceeds the {DECIMAL_DIGIT_LIMIT}-digit limit",
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:  # pragma: no cover - guarded exact grammar
        _fail("DECIMAL_TEXT_INVALID", f"Manual decimal input is invalid: {error}")
    if not parsed.is_finite():  # pragma: no cover - guarded exact grammar
        _fail("DECIMAL_TEXT_NONFINITE", "Manual decimal input must be finite")
    return ParsedDecimal(value, parsed)
