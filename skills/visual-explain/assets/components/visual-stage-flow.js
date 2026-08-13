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
    const box = scope.getBoundingClientRect();
    const relative = (node) => {
      const bounds = node.getBoundingClientRect();
      return {
        left: bounds.left - box.left,
        right: bounds.right - box.left,
        top: bounds.top - box.top,
        bottom: bounds.bottom - box.top,
        width: bounds.width,
        height: bounds.height
      };
    };
    return [relative(from), relative(to), box];
  };

  /* TESTABLE_GEOMETRY:BEGIN */
  const segmentClear = (start, end, boxes) => boxes.every((box) => {
    if (start.y === end.y) {
      const overlapsX = Math.max(Math.min(start.x, end.x), box.left)
        < Math.min(Math.max(start.x, end.x), box.right);
      return !(start.y > box.top && start.y < box.bottom && overlapsX);
    }
    if (start.x === end.x) {
      const overlapsY = Math.max(Math.min(start.y, end.y), box.top)
        < Math.min(Math.max(start.y, end.y), box.bottom);
      return !(start.x > box.left && start.x < box.right && overlapsY);
    }
    return false;
  });
  const routeClear = (points, boxes) => points.slice(1)
    .every((point, index) => segmentClear(points[index], point, boxes));
  const pathData = (points) => points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${Number(point.x.toFixed(3))} ${Number(point.y.toFixed(3))}`)
    .join(' ');
  const directRoute = (from, to, boxes, gap) => {
    const rowTop = Math.max(from.top, to.top);
    const rowBottom = Math.min(from.bottom, to.bottom);
    const columnLeft = Math.max(from.left, to.left);
    const columnRight = Math.min(from.right, to.right);
    let start;
    let end;
    let dx = 0;
    let dy = 0;
    if (rowBottom > rowTop && (from.right <= to.left || to.right <= from.left)) {
      const y = (rowTop + rowBottom) / 2;
      dx = from.right <= to.left ? 1 : -1;
      start = {x: dx > 0 ? from.right : from.left, y};
      end = {x: dx > 0 ? to.left : to.right, y};
    } else if (columnRight > columnLeft && (from.bottom <= to.top || to.bottom <= from.top)) {
      const x = (columnLeft + columnRight) / 2;
      dy = from.bottom <= to.top ? 1 : -1;
      start = {x, y: dy > 0 ? from.bottom : from.top};
      end = {x, y: dy > 0 ? to.top : to.bottom};
    } else {
      return null;
    }
    const points = [
      start,
      {x: start.x + dx * gap, y: start.y + dy * gap},
      {x: end.x - dx * gap, y: end.y - dy * gap},
      end
    ];
    return routeClear(points, boxes) ? points : null;
  };
  const gate = (box, direction, gap) => {
    const x = (box.left + box.right) / 2;
    const y = (box.top + box.bottom) / 2;
    if (direction === 'right') return {anchor: {x: box.right, y}, stub: {x: box.right + gap, y}};
    if (direction === 'bottom') return {anchor: {x, y: box.bottom}, stub: {x, y: box.bottom + gap}};
    if (direction === 'left') return {anchor: {x: box.left, y}, stub: {x: box.left - gap, y}};
    return {anchor: {x, y: box.top}, stub: {x, y: box.top - gap}};
  };
  const outerRoute = (from, to, boxes, gap, declarationIndex) => {
    const baseDirections = ['right', 'bottom', 'left', 'top'];
    const offset = declarationIndex % baseDirections.length;
    const directions = baseDirections.slice(offset).concat(baseDirections.slice(0, offset));
    const otherBoxes = boxes.filter((box) => box !== from && box !== to);
    const sourceGates = directions.map((direction) => gate(from, direction, gap))
      .filter((item) => routeClear([item.anchor, item.stub], otherBoxes));
    const targetGates = directions.map((direction) => gate(to, direction, gap))
      .filter((item) => routeClear([item.stub, item.anchor], otherBoxes));
    const laneXs = boxes.flatMap((box) => [box.left - gap, box.right + gap]);
    const laneYs = boxes.flatMap((box) => [box.top - gap, box.bottom + gap]);
    let best = null;
    let bestScore = Infinity;
    sourceGates.forEach((source) => targetGates.forEach((target) => {
      const start = source.stub;
      const end = target.stub;
      const candidates = [
        [start, end],
        [start, {x: end.x, y: start.y}, end],
        [start, {x: start.x, y: end.y}, end]
      ];
      laneXs.forEach((x) => candidates.push(
        [start, {x, y: start.y}, {x, y: end.y}, end]
      ));
      laneYs.forEach((y) => candidates.push(
        [start, {x: start.x, y}, {x: end.x, y}, end]
      ));
      laneXs.forEach((x) => laneYs.forEach((y) => candidates.push(
        [start, {x, y: start.y}, {x, y}, {x: end.x, y}, end],
        [start, {x: start.x, y}, {x, y}, {x, y: end.y}, end]
      )));
      candidates.forEach((candidate) => {
        if (!routeClear(candidate, boxes)) return;
        const points = [source.anchor, ...candidate, target.anchor];
        const length = points.slice(1).reduce((total, point, index) => (
          total + Math.abs(point.x - points[index].x) + Math.abs(point.y - points[index].y)
        ), 0);
        const score = length + candidate.length * gap;
        if (score < bestScore) {
          best = points;
          bestScore = score;
        }
      });
    }));
    return best;
  };
  /* TESTABLE_GEOMETRY:END */

  const pathFor = (from, to, scope, declarationIndex) => {
    const [fromBox, toBox, scopeBox] = pointPair(from, to, scope);
    const stations = Array.from(scope.querySelectorAll('.ve-flow-path-canvas > .ve-flow-station[id]'));
    const boxes = stations.map((station) => {
      const bounds = station.getBoundingClientRect();
      return {
        left: bounds.left - scopeBox.left,
        right: bounds.right - scopeBox.left,
        top: bounds.top - scopeBox.top,
        bottom: bounds.bottom - scopeBox.top,
        width: bounds.width,
        height: bounds.height
      };
    });
    const fromIndex = stations.indexOf(from);
    const toIndex = stations.indexOf(to);
    if (fromIndex >= 0) Object.assign(boxes[fromIndex], fromBox);
    if (toIndex >= 0) Object.assign(boxes[toIndex], toBox);
    const source = fromIndex >= 0 ? boxes[fromIndex] : fromBox;
    const target = toIndex >= 0 ? boxes[toIndex] : toBox;
    const minimumSize = Math.min(...boxes.flatMap((box) => [box.width, box.height]));
    const gap = Math.max(6, Math.min(12, minimumSize * .12));
    const obstacles = boxes.filter((box) => box !== source && box !== target);
    const points = directRoute(source, target, obstacles, gap)
      || outerRoute(source, target, boxes, gap, declarationIndex);
    return pathData(points || [{x: source.right, y: source.top}, {x: target.left, y: target.top}]);
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
