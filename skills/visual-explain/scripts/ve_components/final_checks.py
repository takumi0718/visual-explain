"""Manifest-to-DOM traceability gate.

When ``build_document`` passes the ``CompositionResult`` as ``expected``, this
compares every canonical renderer manifest and compatibility record to the final
DOM data attributes without executing scripts: each consumed semantic ID and
each instance/provenance value must survive IR → manifest → final DOM.
"""
from __future__ import annotations

from .diagnostics import MANIFEST_DOM_MISMATCH, MISSING_PROVENANCE, Diagnostic


def _present(content: str, sid: str) -> bool:
    return (f'data-ve-semantic-id="{sid}"' in content
            or f'data-ve-instance="{sid}"' in content)


def check_manifest_to_dom(content: str, slots: dict[str, str], expected) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for manifest in expected.manifests:
        if f'data-ve-instance="{manifest.instance_id}"' not in content:
            diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH,
                                          f"canonical instance '{manifest.instance_id}' が最終DOMにありません"))
            continue
        for sid in manifest.consumed_semantic_ids:
            if not _present(content, sid):
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH,
                                              f"意味ID '{sid}' が最終DOMに現れていません"))
        for rid in manifest.generated_relationship_ids:
            if f'data-ve-semantic-id="{rid}"' not in content:
                diagnostics.append(Diagnostic(MANIFEST_DOM_MISMATCH,
                                              f"関係ID '{rid}' が最終DOMにありません"))
    for record in expected.compatibility:
        if (f'data-ve-instance="{record.instance_id}"' not in content
                or f'data-ve-compat-source="{record.source}"' not in content
                or f'data-ve-compat-reason="{record.reason}"' not in content):
            diagnostics.append(Diagnostic(MISSING_PROVENANCE,
                                          f"compatibility '{record.instance_id}' の provenance が最終DOMにありません"))
    return diagnostics
