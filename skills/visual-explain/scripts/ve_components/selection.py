"""Deterministic explicit selection over the registry.

Selection is pure capability matching: narrow to the candidate set, then require
an explicit choice with exact matched-capability evidence. There is no ranking,
scoring, or auto-selection. This module re-exports the selection surface that is
implemented alongside the registry types in ``registry.py``.
"""
from __future__ import annotations

from .registry import (
    CandidateMatch,
    ResolvedComponent,
    narrow_candidates,
    resolve_component,
    validate_explicit_selection,
)

__all__ = [
    "CandidateMatch",
    "ResolvedComponent",
    "narrow_candidates",
    "resolve_component",
    "validate_explicit_selection",
]
