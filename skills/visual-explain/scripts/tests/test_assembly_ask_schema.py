"""assembly.schema.json askType discriminated union contract."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
REFERENCES = SKILL / "references"
EXAMPLES = SKILL / "examples"
ASSEMBLY_SCHEMA = json.loads((REFERENCES / "assembly.schema.json").read_text("utf-8"))


def _resolve_ref(node: dict) -> dict:
    ref = node.get("$ref")
    if not ref:
        return node
    if not ref.startswith("#/$defs/"):
        raise AssertionError(f"unsupported $ref: {ref}")
    name = ref[len("#/$defs/"):]
    return ASSEMBLY_SCHEMA["$defs"][name]


def _ask_branches() -> list[dict]:
    ask = ASSEMBLY_SCHEMA["$defs"]["askSection"]
    if "oneOf" not in ask:
        return []
    return [_resolve_ref(branch) for branch in ask["oneOf"]]


def _branch_ask_type(branch: dict) -> str | None:
    props = branch.get("properties") or {}
    ask_type = props.get("askType") or {}
    if "const" in ask_type:
        return ask_type["const"]
    if "enum" in ask_type and len(ask_type["enum"]) == 1:
        return ask_type["enum"][0]
    return None


def _instance_matches_branch(instance: dict, branch: dict) -> bool:
    """Minimal draft-07 subset: required, additionalProperties:false, askType const."""
    branch = _resolve_ref(branch)
    required = set(branch.get("required") or [])
    if not required <= set(instance.keys()):
        return False
    props = branch.get("properties") or {}
    if branch.get("additionalProperties") is False:
        if set(instance.keys()) - set(props.keys()):
            return False
    for key, schema in props.items():
        if key not in instance:
            continue
        schema = _resolve_ref(schema) if isinstance(schema, dict) and "$ref" in schema else schema
        if not isinstance(schema, dict):
            continue
        if "const" in schema and instance[key] != schema["const"]:
            return False
        if "enum" in schema and instance[key] not in schema["enum"]:
            return False
    if "oneOf" in branch:
        return any(_instance_matches_branch(instance, sub) for sub in branch["oneOf"])
    if "not" in branch:
        forbidden = branch["not"]
        if "required" in forbidden and set(forbidden["required"]) <= set(instance.keys()):
            return False
    return True


def schema_accepts_ask(instance: dict) -> bool:
    branches = _ask_branches()
    if not branches:
        # Flat askSection (pre-fix): only kind/id/askType required → too permissive.
        ask = ASSEMBLY_SCHEMA["$defs"]["askSection"]
        required = set(ask.get("required") or [])
        return required <= set(instance.keys())
    return any(_instance_matches_branch(instance, branch) for branch in branches)


class AskSchemaDiscriminatedUnionTest(unittest.TestCase):
    def test_ask_section_is_oneof_by_ask_type(self) -> None:
        branches = _ask_branches()
        self.assertGreaterEqual(len(branches), 3, "askSection must use oneOf variants")
        by_type: dict[str, list[dict]] = {}
        for branch in branches:
            ask_type = _branch_ask_type(branch)
            self.assertIsNotNone(ask_type, f"branch missing askType const: {branch}")
            by_type.setdefault(ask_type, []).append(branch)
        self.assertEqual(set(by_type), {"decision", "request", "hypothesis"})

    def test_decision_requires_question_options_and_exactly_one_default_field(self) -> None:
        decision_branches = [b for b in _ask_branches() if _branch_ask_type(b) == "decision"]
        self.assertTrue(decision_branches)
        bare = {"kind": "ask", "id": "x", "askType": "decision"}
        self.assertFalse(schema_accepts_ask(bare))
        with_steps = {
            "kind": "ask", "id": "x", "askType": "decision",
            "steps": [{"role": "user", "roleLabel": "あなた", "text": "確認する"}],
        }
        self.assertFalse(schema_accepts_ask(with_steps))
        both_defaults = {
            "kind": "ask", "id": "x", "askType": "decision",
            "question": "進めますか？",
            "options": [
                {"id": "a", "label": "A", "tradeoff": "t1"},
                {"id": "b", "label": "B", "tradeoff": "t2"},
            ],
            "defaultId": "a",
            "noDefaultReason": "拮抗しているため",
        }
        self.assertFalse(schema_accepts_ask(both_defaults))
        with_default = {
            "kind": "ask", "id": "x", "askType": "decision",
            "question": "進めますか？",
            "options": [
                {"id": "a", "label": "A", "tradeoff": "t1"},
                {"id": "b", "label": "B", "tradeoff": "t2"},
            ],
            "defaultId": "a",
        }
        self.assertTrue(schema_accepts_ask(with_default))
        with_reason = {
            "kind": "ask", "id": "x", "askType": "decision",
            "question": "進めますか？",
            "options": [
                {"id": "a", "label": "A", "tradeoff": "t1"},
                {"id": "b", "label": "B", "tradeoff": "t2"},
            ],
            "noDefaultReason": "拮抗しているため",
        }
        self.assertTrue(schema_accepts_ask(with_reason))

    def test_request_requires_steps_rejects_decision_fields(self) -> None:
        bare = {"kind": "ask", "id": "x", "askType": "request"}
        self.assertFalse(schema_accepts_ask(bare))
        with_question = {
            "kind": "ask", "id": "x", "askType": "request",
            "question": "進めますか？",
            "steps": [{"role": "user", "roleLabel": "あなた", "text": "確認する"}],
        }
        self.assertFalse(schema_accepts_ask(with_question))
        valid = {
            "kind": "ask", "id": "x", "askType": "request",
            "steps": [{"role": "user", "roleLabel": "あなた", "text": "確認する"}],
        }
        self.assertTrue(schema_accepts_ask(valid))

    def test_hypothesis_requires_claim_and_verify(self) -> None:
        bare = {"kind": "ask", "id": "x", "askType": "hypothesis"}
        self.assertFalse(schema_accepts_ask(bare))
        missing_verify = {
            "kind": "ask", "id": "x", "askType": "hypothesis",
            "claim": {"text": "見出しだけで判断できる", "certainty": "inferred"},
        }
        self.assertFalse(schema_accepts_ask(missing_verify))
        valid = {
            "kind": "ask", "id": "x", "askType": "hypothesis",
            "claim": {"text": "見出しだけで判断できる", "certainty": "inferred"},
            "verify": "検証方法: 見出し列のみで確認する",
        }
        self.assertTrue(schema_accepts_ask(valid))


class AskSchemaRegressionTest(unittest.TestCase):
    def test_example_proposal_asks_match_schema_and_validate(self) -> None:
        raw = json.loads((EXAMPLES / "example-proposal.assembly.json").read_text("utf-8"))
        asks = [s for s in raw["sections"] if s.get("kind") == "ask"]
        self.assertEqual(len(asks), 2)
        for section in asks:
            self.assertTrue(schema_accepts_ask(section), section)
        validate_assembly(raw)

    def test_patterns_template_asks_match_schema(self) -> None:
        # Minimal decision from patterns.md template (embedded shape).
        decision = {
            "kind": "ask",
            "id": "sec-ask-decision",
            "askType": "decision",
            "question": "限定対象で開始しますか？",
            "options": [
                {"id": "limited", "label": "限定対象で公開する", "tradeoff": "運用が追加で必要"},
                {"id": "all", "label": "一斉公開する", "tradeoff": "影響範囲が最初から広い"},
            ],
            "defaultId": "limited",
        }
        self.assertTrue(schema_accepts_ask(decision))


if __name__ == "__main__":
    unittest.main()
