/* Review-collection pure core for visual-explain.
   This file is the source of truth; assets/skeleton.html embeds it verbatim
   between the FIXED DECISION ENGINE CORE markers (byte-equality is enforced
   by test_skeleton_audit.py). No DOM, no timers, no I/O here. */
(function (global) {
  "use strict";

  const CHIPS = ["わからない", "図にしてほしい", "もっと詳しく", "短くする", "削る", "言い換える", "事実を確認", "ここは良い"];
  const QUOTE_LIMIT = 40;
  const CLOSING_LINE = "上の回答を反映して作業を続けてください。お任せの項目は推奨案で確定してください。";

  function storageKey(contract) {
    // Digest and block count make a rebuilt document with changed asks or
    // blocks start clean instead of restoring drafts onto the wrong targets.
    return "ve-review:" + contract.documentId + ":" + contract.schemaVersion + ":" +
      contract.digest + ":" + contract.blockCount;
  }

  function emptyMap() {
    // Object.create(null) keeps ask ids like "__proto__" as ordinary own
    // properties instead of tripping the Object.prototype accessor.
    return Object.create(null);
  }

  function emptyState() {
    return { selections: emptyMap(), memos: emptyMap(), globalMemo: "", annotations: [] };
  }

  function findAsk(contract, askId) {
    for (const ask of contract.asks) if (ask.id === askId) return ask;
    return null;
  }

  function findOption(ask, optionId) {
    for (const option of ask.options) if (option.id === optionId) return option;
    return null;
  }

  function activeOption(ask, optionId) {
    const option = typeof optionId === "string" ? findOption(ask, optionId) : null;
    return option && !option.withdrawn ? option : null;
  }

  function findPanelRow(rows, askId) {
    // Match by dataset equality so arbitrary ids never build a CSS selector.
    for (const row of rows) if (row.dataset.vePanelAsk === askId) return row;
    return null;
  }

  function cloneWith(state, patch) {
    return {
      selections: Object.assign(emptyMap(), state.selections, patch.selections || emptyMap()),
      memos: Object.assign(emptyMap(), state.memos, patch.memos || emptyMap()),
      globalMemo: patch.globalMemo !== undefined ? patch.globalMemo : state.globalMemo,
      annotations: patch.annotations !== undefined ? patch.annotations : state.annotations.slice(),
    };
  }

  function selectOption(state, askId, optionId, contract) {
    // Radio-like choice; choosing the selected option again returns to the
    // recommendation ("お任せ"). Withdrawn and unknown options are ignored.
    const ask = findAsk(contract, askId);
    if (!ask || !activeOption(ask, optionId)) return state;
    const next = cloneWith(state, {});
    if (next.selections[askId] === optionId) delete next.selections[askId];
    else next.selections[askId] = optionId;
    return next;
  }

  function setMemo(state, askId, text) {
    const next = cloneWith(state, {});
    next.memos[askId] = String(text);
    return next;
  }

  function setGlobalMemo(state, text) {
    return cloneWith(state, { globalMemo: String(text) });
  }

  function flatten(text) {
    return String(text == null ? "" : text).replace(/\s+/g, " ").trim();
  }

  function normalizeQuote(text) {
    // Count code points so a surrogate pair is never split.
    return Array.from(flatten(text)).slice(0, QUOTE_LIMIT).join("");
  }

  function addAnnotation(state, blk, chip, quote, note, contract) {
    if (!Number.isInteger(blk) || blk < 1 || blk > contract.blockCount) return state;
    if (CHIPS.indexOf(chip) < 0) return state;
    const annotations = state.annotations.slice();
    annotations.push({ blk: blk, chip: chip, quote: normalizeQuote(quote), note: flatten(note) });
    return cloneWith(state, { annotations: annotations });
  }

  function removeAnnotation(state, index) {
    if (!Number.isInteger(index) || index < 0 || index >= state.annotations.length) return state;
    const annotations = state.annotations.slice();
    annotations.splice(index, 1);
    return cloneWith(state, { annotations: annotations });
  }

  function annotationsFor(state, blk) {
    const found = [];
    state.annotations.forEach(function (item, index) {
      if (item.blk === blk) found.push({ index: index, chip: item.chip, quote: item.quote, note: item.note });
    });
    return found;
  }

  function restoreState(raw, contract) {
    // Stale or foreign entries never survive: unknown asks, unknown or
    // withdrawn options, out-of-range blocks, and unknown chips are dropped.
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (error) {
      return emptyState();
    }
    if (!parsed || typeof parsed !== "object") return emptyState();
    let state = emptyState();
    for (const ask of contract.asks) {
      const selected = parsed.selections ? parsed.selections[ask.id] : undefined;
      if (activeOption(ask, selected)) state.selections[ask.id] = selected;
      const memo = parsed.memos ? parsed.memos[ask.id] : undefined;
      if (typeof memo === "string") state.memos[ask.id] = memo;
    }
    if (typeof parsed.globalMemo === "string") state.globalMemo = parsed.globalMemo;
    if (Array.isArray(parsed.annotations)) {
      for (const item of parsed.annotations) {
        if (!item || typeof item !== "object") continue;
        const quote = typeof item.quote === "string" ? item.quote : "";
        const note = typeof item.note === "string" ? item.note : "";
        state = addAnnotation(state, item.blk, item.chip, quote, note, contract);
      }
    }
    return state;
  }

  function serializeState(state) {
    return JSON.stringify(state);
  }

  function defaultLabel(ask) {
    const option = ask.defaultId ? findOption(ask, ask.defaultId) : null;
    return option ? option.label : "";
  }

  function cardStatus(ask, state) {
    const option = activeOption(ask, state.selections[ask.id]);
    return option ? "選択: " + option.label : "お任せ（推奨: " + defaultLabel(ask) + "）";
  }

  function nextChipIndex(current, key, total) {
    if (total <= 0) return -1;
    if (key === "ArrowRight" || key === "ArrowDown") return current < 0 ? 0 : (current + 1) % total;
    if (key === "ArrowLeft" || key === "ArrowUp") return current <= 0 ? total - 1 : current - 1;
    if (key === "Home") return 0;
    if (key === "End") return total - 1;
    return -1;
  }

  function askLine(ask, index, state) {
    const option = activeOption(ask, state.selections[ask.id]);
    let line = "Q" + (index + 1) + ". " + ask.question + ": " + (option ? option.label : "(未選択 = お任せ)");
    const memo = typeof state.memos[ask.id] === "string" ? state.memos[ask.id].trim() : "";
    if (memo) line += " / 補足: " + memo;
    return line;
  }

  function annotationLine(item) {
    let line = "#" + item.blk + " [" + item.chip + "]";
    if (item.quote) line += " 「" + item.quote + "」";
    if (item.note) line += " " + item.note;
    return line;
  }

  function formatCopyText(contract, state) {
    const lines = [
      "[visual-explain 回答]",
      "資料: " + contract.title,
      "(" + contract.documentPath + " / id: " + contract.documentId +
        " / schema: " + contract.schemaVersion + " / asks: " + contract.digest + ")",
    ];
    contract.asks.forEach(function (ask, index) { lines.push(askLine(ask, index, state)); });
    const globalMemo = typeof state.globalMemo === "string" ? state.globalMemo.trim() : "";
    if (globalMemo) lines.push("全体メモ: " + globalMemo);
    const ordered = state.annotations
      .map(function (item, order) { return { item: item, order: order }; })
      .sort(function (a, b) { return a.item.blk - b.item.blk || a.order - b.order; });
    if (ordered.length) {
      lines.push("## 指摘");
      ordered.forEach(function (entry) { lines.push(annotationLine(entry.item)); });
    }
    lines.push("---");
    lines.push(CLOSING_LINE);
    return lines.join("\n");
  }

  const engine = {
    CHIPS, QUOTE_LIMIT, storageKey, emptyState, selectOption, setMemo, setGlobalMemo,
    normalizeQuote, addAnnotation, removeAnnotation, annotationsFor, restoreState,
    serializeState, cardStatus, nextChipIndex, formatCopyText, findPanelRow,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
  else global.veDecisionEngine = engine;
})(globalThis);
