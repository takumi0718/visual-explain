"""Task 2 tests: registry validation and deterministic explicit selection.

Selection is pure capability matching with no ranking, heuristics, or
auto-selection. Registry resolution fails closed for unknown version, renderer,
asset hash, dependency, or checker rule.
"""
from __future__ import annotations

import copy
import unittest

from ve_components.diagnostics import ContractError
from ve_components.model import ExplicitSelection, RelationshipDeclaration
from ve_components.registry import (
    AssetDefinition,
    ComponentDefinition,
    Registry,
    load_registry,
    narrow_candidates,
    resolve_component,
    validate_explicit_selection,
)

FAKE_DIGEST = "a" * 64


def make_component(component_id: str, capabilities: list[str], *, kind: str = "two-axis",
                   version: int = 1, renderer: str | None = None,
                   checker_rules=("static-content", "semantic-ids"),
                   dependencies=(), assets=None) -> ComponentDefinition:
    return ComponentDefinition(
        id=component_id,
        version=version,
        relationship_kind=kind,
        capabilities=tuple(capabilities),
        semantic_responsibility=f"{component_id} responsibility",
        required_inputs=("rows", "columns", "cells"),
        optional_inputs=(),
        behavior="static",
        slots=("caption", "certainty", "source", "accessibility"),
        accessibility="labelled figure",
        responsive=True,
        dependencies=tuple(dependencies),
        fallback="static-content",
        checker_rules=tuple(checker_rules),
        renderer=renderer or f"{component_id}@{version}",
        assets=tuple(assets or (AssetDefinition(id=f"{component_id}.css", slot="styles", path=f"{component_id}.css", digest=FAKE_DIGEST),)),
    )


def registry_dict(**overrides) -> dict:
    entry = {
        "id": "matrix",
        "version": 2,
        "relationshipKind": "two-axis",
        "capabilities": ["two-axis-classification", "intersection-comparison"],
        "semanticResponsibility": "two-axis classification and intersection comparison",
        "requiredInputs": ["rows", "columns", "cells"],
        "optionalInputs": [],
        "behavior": "static table",
        "slots": ["caption", "certainty", "source", "accessibility"],
        "accessibility": "labelled figure with table",
        "responsive": True,
        "dependencies": [],
        "fallback": "static-content",
        "checkerRules": ["static-content", "semantic-ids"],
        "renderer": "matrix@2",
        "assets": [{"id": "matrix.css", "slot": "styles", "path": "matrix.css", "digest": FAKE_DIGEST}],
    }
    entry.update(overrides)
    return {"registryVersion": 1, "components": [entry]}


class RegistryValidationTest(unittest.TestCase):
    def test_valid_entry_loads(self) -> None:
        registry = load_registry(registry_dict())
        self.assertEqual(registry.components[0].id, "matrix")
        self.assertEqual(registry.components[0].capabilities, ("two-axis-classification", "intersection-comparison"))

    def test_empty_production_registry_loads(self) -> None:
        registry = load_registry({"registryVersion": 1, "components": []})
        self.assertEqual(registry.components, ())

    def test_unknown_component_id_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(id="sankey"))
        self.assertIn("invalid_registry_entry", ctx.exception.codes)

    def test_unknown_capability_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(capabilities=["mind-reading"]))
        self.assertIn("invalid_registry_entry", ctx.exception.codes)

    def test_wrong_relationship_kind_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(relationshipKind="directed-graph"))
        self.assertIn("invalid_registry_entry", ctx.exception.codes)

    def test_ranking_metadata_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(ranking=5))
        self.assertIn("invalid_registry_entry", ctx.exception.codes)

    def test_theme_metadata_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(theme="dark"))
        self.assertIn("invalid_registry_entry", ctx.exception.codes)

    def test_bad_asset_digest_rejected(self) -> None:
        entry = registry_dict()
        entry["components"][0]["assets"][0]["digest"] = "not-a-hash"
        with self.assertRaises(ContractError) as ctx:
            load_registry(entry)
        self.assertIn("invalid_asset_definition", ctx.exception.codes)

    def test_unknown_checker_rule_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(checkerRules=["telepathy"]))
        self.assertIn("unknown_checker_rule", ctx.exception.codes)

    def test_unknown_dependency_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            load_registry(registry_dict(dependencies=["ghost.css"]))
        self.assertIn("unknown_dependency", ctx.exception.codes)


class SelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = make_component("matrix", ["two-axis-classification", "intersection-comparison"], version=2)
        self.matrix_alt = make_component("matrix-alt", ["two-axis-classification", "intersection-comparison"], renderer="matrix-alt@1")
        self.flow = make_component("flow", ["ordered-transition", "directed-transition", "branching"], kind="directed-graph", version=2, renderer="flow@2")

    def registry(self, *components) -> Registry:
        return Registry(registry_version=1, components=tuple(components))

    def declaration(self, kind: str, caps: list[str]) -> RelationshipDeclaration:
        return RelationshipDeclaration(kind=kind, capabilities=tuple(caps))

    def test_one_match_returns_one_candidate(self) -> None:
        reg = self.registry(self.matrix, self.flow)
        decl = self.declaration("two-axis", ["two-axis-classification"])
        candidates = narrow_candidates(decl, reg)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].component.id, "matrix")
        self.assertEqual(candidates[0].matched_capabilities, ("two-axis-classification",))

    def test_two_components_same_capability_return_two_candidates(self) -> None:
        reg = self.registry(self.matrix, self.matrix_alt)
        decl = self.declaration("two-axis", ["two-axis-classification"])
        candidates = narrow_candidates(decl, reg)
        self.assertEqual({c.component.id for c in candidates}, {"matrix", "matrix-alt"})

    def test_explicit_selection_of_either_candidate_succeeds(self) -> None:
        reg = self.registry(self.matrix, self.matrix_alt)
        decl = self.declaration("two-axis", ["two-axis-classification"])
        candidates = narrow_candidates(decl, reg)
        for cid in ("matrix", "matrix-alt"):
            version = 2 if cid == "matrix" else 1
            selection = ExplicitSelection(component=cid, version=version, matched_capabilities=("two-axis-classification",))
            match = validate_explicit_selection(decl, selection, candidates)
            self.assertEqual(match.component.id, cid)

    def test_combined_declaration_zero_candidates_raises_no_match(self) -> None:
        reg = self.registry(self.matrix, self.flow)
        decl = self.declaration("two-axis", ["two-axis-classification", "ordered-transition"])
        candidates = narrow_candidates(decl, reg)
        self.assertEqual(candidates, [])
        selection = ExplicitSelection(component="matrix", version=2, matched_capabilities=("two-axis-classification",))
        with self.assertRaises(ContractError) as ctx:
            validate_explicit_selection(decl, selection, candidates)
        self.assertIn("no_matching_component", ctx.exception.codes)

    def test_under_specified_declaration_raises_before_matching(self) -> None:
        reg = self.registry(self.matrix)
        decl = RelationshipDeclaration(kind="two-axis", capabilities=())
        with self.assertRaises(ContractError) as ctx:
            narrow_candidates(decl, reg)
        self.assertIn("invalid_relationship_declaration", ctx.exception.codes)

    def test_selection_outside_candidate_set(self) -> None:
        reg = self.registry(self.matrix, self.flow)
        decl = self.declaration("two-axis", ["two-axis-classification"])
        candidates = narrow_candidates(decl, reg)
        selection = ExplicitSelection(component="flow", version=2, matched_capabilities=("two-axis-classification",))
        with self.assertRaises(ContractError) as ctx:
            validate_explicit_selection(decl, selection, candidates)
        self.assertIn("selection_outside_candidate_set", ctx.exception.codes)

    def test_selection_reason_mismatch(self) -> None:
        reg = self.registry(self.matrix)
        decl = self.declaration("two-axis", ["two-axis-classification"])
        candidates = narrow_candidates(decl, reg)
        # matched capability not present in the declaration
        selection = ExplicitSelection(component="matrix", version=2, matched_capabilities=("intersection-comparison",))
        with self.assertRaises(ContractError) as ctx:
            validate_explicit_selection(decl, selection, candidates)
        self.assertIn("selection_reason_mismatch", ctx.exception.codes)


class ResolveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = make_component("matrix", ["two-axis-classification", "intersection-comparison"], version=2)
        self.registry = Registry(registry_version=1, components=(self.matrix,))

    def test_resolve_unknown_component_fails_closed(self) -> None:
        selection = ExplicitSelection(component="flow", version=1, matched_capabilities=("ordered-transition",))
        with self.assertRaises(ContractError) as ctx:
            resolve_component(selection, self.registry, renderers={"matrix@2": lambda *a: None})
        self.assertIn("unknown_component", ctx.exception.codes)

    def test_resolve_unknown_version_fails_closed(self) -> None:
        selection = ExplicitSelection(component="matrix", version=99, matched_capabilities=("two-axis-classification",))
        with self.assertRaises(ContractError) as ctx:
            resolve_component(selection, self.registry, renderers={"matrix@2": lambda *a: None})
        self.assertIn("unknown_component", ctx.exception.codes)

    def test_resolve_unknown_renderer_fails_closed(self) -> None:
        selection = ExplicitSelection(component="matrix", version=2, matched_capabilities=("two-axis-classification",))
        with self.assertRaises(ContractError) as ctx:
            resolve_component(selection, self.registry, renderers={})
        self.assertIn("unknown_renderer", ctx.exception.codes)

    def test_resolve_succeeds_with_registered_renderer(self) -> None:
        selection = ExplicitSelection(component="matrix", version=2, matched_capabilities=("two-axis-classification",))
        sentinel = lambda *a: None
        resolved = resolve_component(selection, self.registry, renderers={"matrix@2": sentinel})
        self.assertIs(resolved.renderer, sentinel)
        self.assertEqual(resolved.component.id, "matrix")


if __name__ == "__main__":
    unittest.main()
