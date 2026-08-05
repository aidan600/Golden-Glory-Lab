"""Bounded copied-item recognition and derived common item review."""

from .adapters import derive_item_reviews, review_source_locators
from .copied_text import (
    COPIED_ITEM_LIMITS,
    STATE_AGGREGATION_TABLE,
    CopiedItemRecognitionError,
    recognize_copied_item,
)
from .model import (
    AssignmentBinding,
    ItemReview,
    ParsedIdentity,
    RecognitionReport,
    RecognitionResult,
    ReviewSourceLocator,
)

__all__ = [
    "COPIED_ITEM_LIMITS",
    "STATE_AGGREGATION_TABLE",
    "AssignmentBinding",
    "CopiedItemRecognitionError",
    "ItemReview",
    "ParsedIdentity",
    "RecognitionReport",
    "RecognitionResult",
    "ReviewSourceLocator",
    "derive_item_reviews",
    "recognize_copied_item",
    "review_source_locators",
]
