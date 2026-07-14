"""Manifest-to-DOM traceability gate.

When ``build_document`` passes the ``CompositionResult`` as ``expected``, this
compares every canonical renderer manifest and compatibility record to the final
DOM data attributes without executing scripts. Every manifest claim is checked:
component id/version, instance, fallback, consumed semantic IDs, generated
relationship and landmark IDs, asset IDs/digests, and declared dependencies.
"""
from __future__ import annotations

import re

from .diagnostics import MANIFEST_DOM_MISMATCH, MISSING_PROVENANCE, Diagnostic


def _present(content: str, sid: str) -> bool:
    return (f'data-ve-semantic-id="{sid}"' in content
            or f'data-ve-instance="{sid}"' in content)


def _wrapper_attrs(content: str, instance_id: str) -> str | None:
    for match in re.finditer(r"<section\b([^>]*)>", content):
        attrs = match.group(1)
        if f'data-ve-instance="{instance_id}"' in attrs:
            return attrs
    return None


def check_manifest_to_dom(content: str, slots: dict[str, str], expected) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    asset_text = slots.get("styles", "") + slots.get("scripts", "")
    for manifest in expected.manifests:
        attrs = _wrapper_attrs(content, manifest.instance_id)
        if attrs is None:
            diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH,
                                          f"canonical instance '{manifest.instance_id}' が最終DOMにありません"))
            continue
        if (f'data-ve-component="{manifest.component_id}"' not in attrs
                or f'data-ve-contract-version="{manifest.component_version}"' not in attrs):
            diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH,
                                          f"instance '{manifest.instance_id}' の component/version が manifest と不一致です"))
        if f'data-ve-fallback="{manifest.fallback_mode}"' not in attrs:
            diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH,
                                          f"instance '{manifest.instance_id}' の fallback が manifest と不一致です"))
        for sid in manifest.consumed_semantic_ids:
            if not _present(content, sid):
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH, f"意味ID '{sid}' が最終DOMに現れていません"))
        for rid in manifest.generated_relationship_ids:
            if f'data-ve-semantic-id="{rid}"' not in content:
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH, f"関係ID '{rid}' が最終DOMにありません"))
        for lid in manifest.generated_landmark_ids:
            if f'id="{lid}"' not in content:
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH, f"ランドマーク '{lid}' が最終DOMにありません"))
        for aid, adig in zip(manifest.asset_ids, manifest.asset_digests):
            if f'data-ve-asset="{aid}"' not in asset_text or f'data-ve-digest="{adig}"' not in asset_text:
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH, f"アセット '{aid}' が最終DOMに宣言どおり現れていません"))
        for dep in manifest.declared_dependencies:
            if f'data-ve-asset="{dep}"' not in asset_text:
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH, f"依存アセット '{dep}' が最終DOMにありません"))
    for record in expected.compatibility:
        if (f'data-ve-instance="{record.instance_id}"' not in content
                or f'data-ve-compat-source="{record.source}"' not in content
                or f'data-ve-compat-reason="{record.reason}"' not in content):
            diagnostics.append(Diagnostic(MISSING_PROVENANCE,
                                          f"compatibility '{record.instance_id}' の provenance が最終DOMにありません"))
    for record in expected.narrative:
        if f'data-ve-instance="{record.instance_id}"' not in content:
            diagnostics.append(Diagnostic(MISSING_PROVENANCE,
                                          f"narrative '{record.instance_id}' が最終DOMにありません"))
    return diagnostics
