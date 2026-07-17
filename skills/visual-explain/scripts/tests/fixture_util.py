"""Helpers for assembly fixtures that bookend with first-screen / closing."""
from __future__ import annotations


def canonical_section(raw: dict) -> dict:
    """Return the first canonical section dict in an assembly fixture."""
    for section in raw.get("sections") or []:
        if isinstance(section, dict) and section.get("kind") == "canonical":
            return section
    raise KeyError("canonical section not found")


def canonical_ir(raw: dict) -> dict:
    return canonical_section(raw)["ir"]


def compatibility_section(raw: dict) -> dict:
    for section in raw.get("sections") or []:
        if isinstance(section, dict) and section.get("kind") == "compatibility":
            return section
    raise KeyError("compatibility section not found")
