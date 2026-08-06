"""One bounded exact-decimal parser shared by U, M, and T."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP
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


def _significand_digits(value: Decimal) -> int:
    if not isinstance(value, Decimal):
        value = Decimal(value)
    if not value.is_finite():
        return DECIMAL_DIGIT_LIMIT
    digits = value.as_tuple().digits
    return max(len(digits), 1)


def numeric_context_for(*values: Decimal) -> Context:
    """Return a Decimal Context exact for arithmetic over accepted operands.

    Operands are bounded by :data:`DECIMAL_DIGIT_LIMIT` significant digits.
    Precision accounts for additive growth across summed terms and product
    growth across multiplied factors (life component, effect multiplier, and
    flat damage), plus scale adjustments for ``/100`` and ``*0.05``.
    """

    counts = [_significand_digits(value) for value in values] if values else [1]
    term_count = max(len(counts), 1)
    max_digits = max(counts)
    sum_digits = sum(counts)
    # Additive slack: max significand plus carries across terms.
    additive = max_digits + term_count + 8
    # Product slack: significands of all factors plus intermediate scales.
    product = sum_digits + term_count + 16
    # Floor covering two max-bound factors times a third scaled operand.
    bound_floor = DECIMAL_DIGIT_LIMIT * 3 + 32
    precision = max(28, additive, product, bound_floor)
    return Context(
        prec=precision,
        rounding=ROUND_HALF_UP,
        Emax=999999999,
        Emin=-999999999,
        capitals=1,
        clamp=0,
    )


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
