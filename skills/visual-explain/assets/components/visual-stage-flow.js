/* Opt-in path-spotlight connector runtime. The fixed runtime remains unchanged. */
(() => {
  const SVG_NS = 'http:' + '//www.w3.org/2000/svg';
  const INITIAL_SCOPE_SELECTOR = '[data-stepper][data-ve-sequence-mode="path-spotlight"] [data-connect-scope]';
  const SCOPE_SELECTOR = '[data-stepper][data-ve-sequence-mode="path-spotlight"] [data-ve-flow-connect-scope]';
  let resizeObserver;
  let scheduled = false;

  const scopes = () => Array.from(document.querySelectorAll(SCOPE_SELECTOR));
  const suspendScope = (scope) => {
    scope.setAttribute('data-ve-flow-connect-scope', '');
    scope.removeAttribute('data-connect-scope');
    scope.querySelectorAll('[data-connect]').forEach((declaration) => {
      const value = declaration.getAttribute('data-connect');
      declaration.setAttribute('data-ve-flow-connect', value);
      declaration.removeAttribute('data-connect');
    });
  };
  const restoreScope = (scope) => {
    scope.setAttribute('data-connect-scope', '');
    scope.removeAttribute('data-ve-flow-connect-scope');
    scope.querySelectorAll('[data-ve-flow-connect]').forEach((declaration) => {
      declaration.setAttribute('data-connect', declaration.getAttribute('data-ve-flow-connect'));
      declaration.removeAttribute('data-ve-flow-connect');
    });
  };
  const suspendScopes = () => document.querySelectorAll(INITIAL_SCOPE_SELECTOR)
    .forEach(suspendScope);
  const directChild = (parent, className) => Array.from(parent.children)
    .find((node) => node.classList && node.classList.contains(className));
  const nodeMap = (scope) => new Map(
    Array.from(scope.querySelectorAll('[id]')).map((node) => [node.id, node])
  );

  const pointPair = (from, to, scope) => {
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    const box = scope.getBoundingClientRect();
    const ax = a.left + a.width / 2;
    const ay = a.top + a.height / 2;
    const bx = b.left + b.width / 2;
    const by = b.top + b.height / 2;
    if (Math.abs(bx - ax) >= Math.abs(by - ay)) {
      return [bx >= ax ? a.right : a.left, ay, bx >= ax ? b.left : b.right, by, box];
    }
    return [ax, by >= ay ? a.bottom : a.top, bx, by >= ay ? b.top : b.bottom, box];
  };

  /* TESTABLE_GEOMETRY:BEGIN */
  const outerPath = (start, end, boxes, declarationIndex) => {
    const top = Math.min(...boxes.map((box) => box.top));
    const bottom = Math.max(...boxes.map((box) => box.bottom));
    const minimumHeight = Math.min(...boxes.map((box) => box.bottom - box.top));
    const laneGap = Math.max(8, minimumHeight * .25);
    const laneDepth = Math.floor(declarationIndex / 2) + 1;
    const laneY = declarationIndex % 2 === 0
      ? top - laneGap * laneDepth
      : bottom + laneGap * laneDepth;
    const midpoint = (start.x + end.x) / 2;
    return `M ${start.x} ${start.y} C ${start.x} ${laneY}, ${start.x} ${laneY}, ${midpoint} ${laneY} C ${end.x} ${laneY}, ${end.x} ${laneY}, ${end.x} ${end.y}`;
  };
  /* TESTABLE_GEOMETRY:END */

  const pathFor = (from, to, scope, declarationIndex) => {
    const [sx, sy, ex, ey, box] = pointPair(from, to, scope);
    const x1 = sx - box.left;
    const y1 = sy - box.top;
    const x2 = ex - box.left;
    const y2 = ey - box.top;
    const stations = Array.from(scope.querySelectorAll('.ve-flow-path-canvas > .ve-flow-station[id]'));
    const fromIndex = stations.indexOf(from);
    const toIndex = stations.indexOf(to);
    if (fromIndex >= 0 && toIndex >= 0 && Math.abs(toIndex - fromIndex) > 1) {
      const first = Math.min(fromIndex, toIndex);
      const last = Math.max(fromIndex, toIndex);
      const boxes = stations.slice(first, last + 1).map((station) => {
        const bounds = station.getBoundingClientRect();
        return {top: bounds.top - box.top, bottom: bounds.bottom - box.top};
      });
      return outerPath({x: x1, y: y1}, {x: x2, y: y2}, boxes, declarationIndex);
    }
    const horizontal = Math.abs(x2 - x1) >= Math.abs(y2 - y1);
    const c1x = horizontal ? x1 + (x2 - x1) * .45 : x1;
    const c1y = horizontal ? y1 : y1 + (y2 - y1) * .45;
    const c2x = horizontal ? x2 - (x2 - x1) * .45 : x2;
    const c2y = horizontal ? y2 : y2 - (y2 - y1) * .45;
    return `M ${x1} ${y1} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${x2} ${y2}`;
  };

  const warning = (scope, message) => {
    const badge = document.createElement('p');
    badge.className = 'connector-warning';
    badge.textContent = `接続を描画できません: ${message}`;
    scope.append(badge);
  };

  const marker = (markerId) => {
    const defs = document.createElementNS(SVG_NS, 'defs');
    const arrow = document.createElementNS(SVG_NS, 'marker');
    arrow.setAttribute('id', markerId);
    arrow.setAttribute('markerWidth', '8');
    arrow.setAttribute('markerHeight', '8');
    arrow.setAttribute('refX', '7');
    arrow.setAttribute('refY', '4');
    arrow.setAttribute('orient', 'auto');
    const shape = document.createElementNS(SVG_NS, 'path');
    shape.setAttribute('d', 'M0,0 L8,4 L0,8 Z');
    shape.setAttribute('fill', 'context-stroke');
    arrow.append(shape);
    defs.append(arrow);
    return defs;
  };

  const render = (scope, scopeIndex) => {
    scope.querySelectorAll('.connector-layer, .connector-warning').forEach((node) => node.remove());
    const list = directChild(scope, 'connection-text') || document.createElement('ul');
    list.className = 'connection-text visually-hidden';
    list.setAttribute('aria-label', '接続関係');
    list.replaceChildren();
    if (!list.parentElement) scope.append(list);
    if (scope.closest('[data-step][hidden]')) return;

    const markerId = `ve-flow-connector-arrow-${scopeIndex + 1}`;
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'connector-layer ve-flow-connector-layer');
    svg.setAttribute('aria-hidden', 'true');
    svg.append(marker(markerId));
    const nodes = nodeMap(scope);
    let hasLine = false;

    scope.querySelectorAll('[data-connect]').forEach((declaration, declarationIndex) => {
      declaration.dataset.connect.split(',').map((item) => item.trim()).filter(Boolean)
        .forEach((item) => {
          const [fromId, toId] = item.split('->').map((id) => id && id.trim());
          const from = nodes.get(fromId);
          const to = nodes.get(toId);
          if (!from || !to) {
            console.error('visual-explain: unknown path connector reference', item);
            warning(scope, `「${item}」の ID が見つかりません。`);
            return;
          }

          const path = document.createElementNS(SVG_NS, 'path');
          path.setAttribute('d', pathFor(from, to, scope, declarationIndex));
          path.setAttribute('fill', 'none');
          path.setAttribute('stroke', 'currentColor');
          path.setAttribute('stroke-width', '2');
          path.setAttribute('marker-end', `url(#${markerId})`);
          const semanticId = declaration.dataset.veSemanticId || '';
          path.setAttribute('data-ve-semantic-id', semanticId);
          const stateClass = declaration.classList.contains('ve-seq-spot')
            ? 've-seq-spot'
            : declaration.classList.contains('ve-seq-dim') ? 've-seq-dim' : '';
          if (stateClass) path.classList.add(stateClass);
          svg.append(path);

          const text = document.createElement('li');
          text.textContent = `${from.textContent.trim()} から ${to.textContent.trim()} へ接続`;
          list.append(text);
          hasLine = true;
        });
    });
    if (hasLine) scope.append(svg);
  };

  const renderAll = () => scopes().forEach((scope, scopeIndex) => {
    restoreScope(scope);
    try {
      render(scope, scopeIndex);
    } finally {
      suspendScope(scope);
    }
  });
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    // Component scripts execute before the fixed connector runtime. Deferring
    // lets that runtime finish first, then replaces only opted-in flow scopes.
    requestAnimationFrame(() => {
      scheduled = false;
      renderAll();
    });
  };
  const suspendAndSchedule = () => {
    suspendScopes();
    schedule();
  };

  suspendScopes();
  schedule();
  window.addEventListener('load', suspendAndSchedule);
  window.addEventListener('load', () => {
    resizeObserver = new ResizeObserver(suspendAndSchedule);
    scopes().forEach((scope) => resizeObserver.observe(scope));
  });
  document.addEventListener('visual-explain:stepchange', suspendAndSchedule);
  document.addEventListener('toggle', (event) => {
    if (event.target.matches('details')) suspendAndSchedule();
  }, true);
})();
