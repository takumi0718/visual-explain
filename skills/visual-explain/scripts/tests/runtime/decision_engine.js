/* Decision-collection pure core for visual-explain.
   This file is the source of truth; assets/skeleton.html embeds it verbatim
   between the FIXED DECISION ENGINE CORE markers (byte-equality is enforced
   by test_skeleton_audit.py). No DOM, no timers, no I/O here. */
(function (global) {
  "use strict";

  function storageKey(contract) {
    return "ve-decision:" + contract.documentId + ":" + contract.schemaVersion + ":" + contract.digest;
  }

  function emptyState() {
    return { selections: {}, memos: {}, globalMemo: "" };
  }

  function findAsk(contract, askId) {
    for (const ask of contract.asks) if (ask.id === askId) return ask;
    return null;
  }

  function findOption(ask, optionId) {
    for (const option of ask.options) if (option.id === optionId) return option;
    return null;
  }

  function cloneWith(state, patch) {
    return {
      selections: Object.assign({}, state.selections, patch.selections || {}),
      memos: Object.assign({}, state.memos, patch.memos || {}),
      globalMemo: patch.globalMemo !== undefined ? patch.globalMemo : state.globalMemo,
    };
  }

  function selectOption(state, askId, optionId, contract) {
    const ask = findAsk(contract, askId);
    if (!ask || !findOption(ask, optionId)) return state;
    const patch = { selections: {} };
    patch.selections[askId] = optionId;
    return cloneWith(state, patch);
  }

  function setMemo(state, askId, text) {
    const patch = { memos: {} };
    patch.memos[askId] = String(text);
    return cloneWith(state, patch);
  }

  function setGlobalMemo(state, text) {
    return cloneWith(state, { globalMemo: String(text) });
  }

  function restoreState(raw, contract) {
    // Stale or foreign entries never survive: unknown ask ids and option ids
    // are dropped so a regenerated document starts unselected (scenario 7).
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (error) {
      return emptyState();
    }
    if (!parsed || typeof parsed !== "object") return emptyState();
    const state = emptyState();
    for (const ask of contract.asks) {
      const selected = parsed.selections ? parsed.selections[ask.id] : undefined;
      if (typeof selected === "string" && findOption(ask, selected)) state.selections[ask.id] = selected;
      const memo = parsed.memos ? parsed.memos[ask.id] : undefined;
      if (typeof memo === "string") state.memos[ask.id] = memo;
    }
    if (typeof parsed.globalMemo === "string") state.globalMemo = parsed.globalMemo;
    return state;
  }

  function serializeState(state) {
    return JSON.stringify(state);
  }

  function defaultLabel(ask) {
    if (!ask.defaultId) return null;
    const option = findOption(ask, ask.defaultId);
    return option ? option.label : null;
  }

  function unselectedNote(ask) {
    const label = defaultLabel(ask);
    return ask.question + "（既定案: " + (label === null ? "なし" : label) + "）";
  }

  function selectionStatus(ask, optionId) {
    if (!ask.defaultId) return "既定案なし";
    return optionId === ask.defaultId ? "既定案どおり" : "既定案から変更";
  }

  function askLines(state, ask, unselected) {
    // r1 C3: every ask emits its 問い/選択/メモ block regardless of selection
    // state, so memos on unselected asks are never dropped from the copy text.
    const lines = ["問い: " + ask.question];
    const selectedId = state.selections[ask.id];
    const option = selectedId ? findOption(ask, selectedId) : null;
    if (option) {
      lines.push("→ 選択: " + option.label + "（" + selectionStatus(ask, option.id) + "）"
        + " — トレードオフ: " + option.tradeoff);
    } else {
      const label = defaultLabel(ask);
      lines.push("→ 選択: 未選択（既定案: " + (label === null ? "なし" : label) + "）");
      unselected.push(unselectedNote(ask));
    }
    const memo = state.memos[ask.id];
    if (typeof memo === "string" && memo.trim()) lines.push("→ メモ: " + memo);
    return lines;
  }

  function formatCopyText(contract, state) {
    const lines = [
      "[visual-explain 判断結果]",
      "資料: " + contract.title,
      "(" + contract.documentPath + " / id: " + contract.documentId +
        " / schema: " + contract.schemaVersion + " / asks: " + contract.digest + ")",
    ];
    const unselected = [];
    for (const ask of contract.asks) lines.push(...askLines(state, ask, unselected));
    if (unselected.length) lines.push("未選択: " + unselected.join(" / "));
    if (contract.riskHeadings.length) lines.push("リスク要約: " + contract.riskHeadings.join(" / "));
    if (state.globalMemo && state.globalMemo.trim()) lines.push("全体メモ: " + state.globalMemo);
    return lines.join("\n");
  }

  const engine = {
    storageKey, emptyState, selectOption, setMemo, setGlobalMemo,
    restoreState, serializeState, formatCopyText,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
  else global.veDecisionEngine = engine;
})(globalThis);
