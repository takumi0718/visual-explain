"""Task 4 registry contract for the shared visual-stage asset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ve_components.registry import load_registry


REPO_ROOT = Path(__file__).resolve().parents[4]
COMPONENTS = REPO_ROOT / "skills" / "visual-explain" / "assets" / "components"
REGISTRY_PATH = COMPONENTS / "registry.json"
VISUAL_STAGE_DIGEST = "c58e56d47dbbd0ccc737ed06cff0074677d49f66db6e498510cac57547b2bb5e"

EXISTING_ASSETS = {
    "matrix": ("matrix.css", "fe9fd5f86063dcb93790a9549a7630a162d674082446e2dd5f86c540bd6b692c"),
    "flow": ("flow.css", "778c861a2bf3acd4f197f92fac9385a0b4acec7accc4c97a1d25a871b701770e"),
    "enumeration": ("enumeration.css", "70c182dfb356bb58117fac1cce740dde5e5b1201a5eeb309d0555a9e84ab7e34"),
    "chevron": ("chevron.css", "afdb6d3b748a45e67714851bdb8033993fadd7bc27a9a5295f46fef77c6720f8"),
    "pyramid": ("pyramid.css", "5ae27d2763f9f6d1871a99b662a91804a892798707a444dc14d3138fd33ecf7c"),
    "stairs": ("stairs.css", "c490a27d4fda79c63cfbb0a1595ece6589715d65947a788737482c464adfacc6"),
    "logic-tree": ("logic-tree.css", "2a701472b525d268eb2946c5f3f5bec2d79f9335b66286c06cd67f00e8292e30"),
    "waterfall": ("waterfall.css", "b6662c0fa0d983c0c6ae5bdb742aaf4818dc341122c381380e2779e8847504a8"),
    "slope": ("slope.css", "a0059b8aa25254449fabe0aa3ba4899974b524b6d0b9d08c08524af0ca61dae6"),
    "evidence-map": ("evidence-map.css", "b70f35e5c997affac8204c4f21b98b7827e36963361db823ee1d9b0246c8637b"),
    "bars": ("bars.css", "dc4053c7f159dc7a52ad80571bf261882a48a4d10aa7c97e5790643b9f0288c9"),
    "kpi": ("kpi.css", "5953282c293f6788a73d77faa0cab1453330e46e86eddc62c897b4766c8c2b78"),
}


def test_every_component_declares_the_identical_verified_visual_stage_asset() -> None:
    raw = json.loads(REGISTRY_PATH.read_text("utf-8"))
    registry = load_registry(raw)
    actual_digest = hashlib.sha256((COMPONENTS / "visual-stage.css").read_bytes()).hexdigest()

    assert raw["registryVersion"] == 1
    assert actual_digest == VISUAL_STAGE_DIGEST
    assert len(registry.components) == 12
    for component in registry.components:
        shared = component.asset_by_id("visual-stage")
        assert shared is not None
        assert (shared.slot, shared.path, shared.digest) == (
            "styles", "visual-stage.css", VISUAL_STAGE_DIGEST,
        )


def test_only_sequence_capable_components_gain_typed_sequence_and_existing_assets_stay_exact() -> None:
    registry = load_registry(REGISTRY_PATH)
    sequence_components = {"flow", "matrix", "stairs", "waterfall", "bars"}

    for component in registry.components:
        assert component.version == 2
        assert ("typed-sequence" in component.capabilities) == (component.id in sequence_components)
        incumbent = component.assets[0]
        assert (incumbent.id, incumbent.path, incumbent.digest) == (
            EXISTING_ASSETS[component.id][0],
            EXISTING_ASSETS[component.id][0],
            EXISTING_ASSETS[component.id][1],
        )
