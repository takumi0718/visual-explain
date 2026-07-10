"""Manifest-to-DOM traceability gate (completed in Task 7).

When ``build_document`` passes the ``CompositionResult`` as ``expected``, this
compares every canonical renderer manifest and compatibility record to the final
DOM data attributes without executing scripts. Task 4 wires the call; Task 7
fills in the comparisons.
"""
from __future__ import annotations

from .diagnostics import Diagnostic


def check_manifest_to_dom(text: str, slots: dict[str, str], expected) -> list[Diagnostic]:
    # Placeholder until Task 7. The safety layer in checker.py already runs.
    return []
