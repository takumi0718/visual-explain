"""Shared minimal v2 assembly builders for first-screen, overview, and repetition tests."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

_HERE = Path(__file__).resolve().parent


def _matrix_canonical() -> dict:
    raw = json.loads((_HERE / "component-valid-matrix.json").read_text("utf-8"), parse_float=Decimal)
    section = next(s for s in raw["sections"] if s.get("kind") == "canonical")
    section = copy.deepcopy(section)
    section["ir"]["id"] = "sec-map"
    section["ir"]["caption"] = "見るところ: 右列の代償。"
    return section


CANONICAL = _matrix_canonical()
CLOSING = {"kind": "closing", "id": "sec-closing", "blocks": [
    {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
    {"heading": "不確かな点", "items": ["未確認の利用状況"]},
]}


def assembly(first: dict, *middle: dict) -> dict:
    return {
        "schemaVersion": 2,
        "document": {"id": "d", "title": "料金改定は限定対象で段階公開する", "summary": "要約文。",
                     "type": "proposal", "profile": "strict"},
        "sections": [{"kind": "first-screen", "id": "sec-first", **first}, *copy.deepcopy(list(middle)), CLOSING],
    }


def narr(sid: str, heading: str, body: str | None = None) -> dict:
    body = body if body is not None else f"<p>本文{sid}。</p>"
    return {"kind": "narrative", "id": sid,
            "markup": f'<section aria-labelledby="{sid}-h"><h2 id="{sid}-h">{heading}</h2>{body}</section>'}


def messages(raw: dict) -> list[str]:
    try:
        validate_assembly(raw)
    except ContractError as exc:
        return [d.message for d in exc.diagnostics]
    return []


DECISION_EVIDENCE = "scripts/build_explainer.py:1"


def decision_ask(sid: str = "sec-ask-decision", *, question: str = "限定対象で開始しますか？",
                 default: str = "limited", **extra) -> dict:
    """A valid question-card decision ask; tests mutate the returned dict."""
    section = {
        "kind": "ask", "id": sid, "askType": "decision", "question": question,
        "evidence": DECISION_EVIDENCE,
        "options": [
            {"id": "limited", "label": "限定対象で公開する", "benefit": "影響範囲を絞れる",
             "tradeoff": "運用が追加で必要"},
            {"id": "all", "label": "一斉公開する", "benefit": "切替が一度で済む",
             "tradeoff": "影響範囲が最初から広い"},
        ],
        "defaultId": default,
    }
    section.update(extra)
    return section
