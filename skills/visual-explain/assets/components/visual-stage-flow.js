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
  const segmentClear = (start, end, boxes, metrics) => {
    for (const box of boxes) {
      if (metrics) metrics.boxChecks += 1;
      if (start.y === end.y) {
        const overlapsX = Math.max(Math.min(start.x, end.x), box.left)
          < Math.min(Math.max(start.x, end.x), box.right);
        if (start.y > box.top && start.y < box.bottom && overlapsX) return false;
      } else if (start.x === end.x) {
        const overlapsY = Math.max(Math.min(start.y, end.y), box.top)
          < Math.min(Math.max(start.y, end.y), box.bottom);
        if (start.x > box.left && start.x < box.right && overlapsY) return false;
      } else {
        return false;
      }
    }
    return true;
  };
  const routeClear = (points, boxes, metrics) => points.slice(1)
    .every((point, index) => segmentClear(points[index], point, boxes, metrics));
  const pathData = (points) => points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${Number(point.x.toFixed(3))} ${Number(point.y.toFixed(3))}`)
    .join(' ');
  const directRoute = (from, to, boxes, gap, metrics) => {
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
    return routeClear(points, boxes, metrics) ? points : null;
  };
  const gate = (box, direction, gap) => {
    const x = (box.left + box.right) / 2;
    const y = (box.top + box.bottom) / 2;
    if (direction === 'right') return {anchor: {x: box.right, y}, stub: {x: box.right + gap, y}};
    if (direction === 'bottom') return {anchor: {x, y: box.bottom}, stub: {x, y: box.bottom + gap}};
    if (direction === 'left') return {anchor: {x: box.left, y}, stub: {x: box.left - gap, y}};
    return {anchor: {x, y: box.top}, stub: {x, y: box.top - gap}};
  };
  const outerRoute = (from, to, boxes, gap, declarationIndex, metrics) => {
    const baseDirections = ['right', 'bottom', 'left', 'top'];
    const offset = declarationIndex % baseDirections.length;
    const directions = baseDirections.slice(offset).concat(baseDirections.slice(0, offset));
    const otherBoxes = boxes.filter((box) => box !== from && box !== to);
    const sourceGates = directions.map((direction) => gate(from, direction, gap))
      .filter((item) => routeClear([item.anchor, item.stub], otherBoxes, metrics));
    const targetGates = directions.map((direction) => gate(to, direction, gap))
      .filter((item) => routeClear([item.stub, item.anchor], otherBoxes, metrics));
    const centerX = (from.left + from.right + to.left + to.right) / 4;
    const centerY = (from.top + from.bottom + to.top + to.bottom) / 4;
    const preferPositive = declarationIndex % 2 === 1;
    const corridorOrder = (center) => (a, b) => {
      const aPreferred = preferPositive ? a >= center : a <= center;
      const bPreferred = preferPositive ? b >= center : b <= center;
      if (aPreferred !== bPreferred) return aPreferred ? -1 : 1;
      const distance = Math.abs(a - center) - Math.abs(b - center);
      return distance || a - b;
    };
    const laneXs = Array.from(new Set(
      boxes.flatMap((box) => [box.left - gap, box.right + gap])
    )).sort(corridorOrder(centerX));
    const laneYs = Array.from(new Set(
      boxes.flatMap((box) => [box.top - gap, box.bottom + gap])
    )).sort(corridorOrder(centerY));
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
      candidates.forEach((candidate) => {
        if (metrics) metrics.candidateEvaluations += 1;
        if (!routeClear(candidate, boxes, metrics)) return;
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
  const lowerBound = (values, target) => {
    let low = 0;
    let high = values.length;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (values[middle] < target) low = middle + 1;
      else high = middle;
    }
    return low;
  };
  const upperBound = (values, target) => {
    let low = 0;
    let high = values.length;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (values[middle] <= target) low = middle + 1;
      else high = middle;
    }
    return low;
  };
  const compressRoute = (points) => points.filter((point, index) => {
    if (index === 0 || index === points.length - 1) return true;
    const before = points[index - 1];
    const after = points[index + 1];
    return !((before.x === point.x && point.x === after.x)
      || (before.y === point.y && point.y === after.y));
  });
  const gridRoute = (from, to, boxes, gap, declarationIndex, metrics) => {
    const baseDirections = ['right', 'bottom', 'left', 'top'];
    const offset = declarationIndex % baseDirections.length;
    const directions = baseDirections.slice(offset).concat(baseDirections.slice(0, offset));
    const otherBoxes = boxes.filter((box) => box !== from && box !== to);
    const sourceGates = directions.map((direction) => gate(from, direction, gap))
      .filter((item) => routeClear([item.anchor, item.stub], otherBoxes, metrics));
    const targetGates = directions.map((direction) => gate(to, direction, gap))
      .filter((item) => routeClear([item.stub, item.anchor], otherBoxes, metrics));
    if (!sourceGates.length || !targetGates.length) return null;

    const xs = Array.from(new Set([
      ...boxes.flatMap((box) => [box.left - gap, box.right + gap]),
      ...sourceGates.map((item) => item.stub.x),
      ...targetGates.map((item) => item.stub.x)
    ])).sort((a, b) => a - b);
    const ys = Array.from(new Set([
      ...boxes.flatMap((box) => [box.top - gap, box.bottom + gap]),
      ...sourceGates.map((item) => item.stub.y),
      ...targetGates.map((item) => item.stub.y)
    ])).sort((a, b) => a - b);
    const horizontalDiff = ys.map(() => new Int16Array(xs.length));
    const verticalDiff = xs.map(() => new Int16Array(ys.length));

    boxes.forEach((box) => {
      const firstXEdge = Math.max(0, upperBound(xs, box.left) - 1);
      const afterXEdge = Math.min(xs.length - 1, lowerBound(xs, box.right));
      ys.forEach((y, yIndex) => {
        if (metrics) metrics.graphOccupancyChecks = (metrics.graphOccupancyChecks || 0) + 1;
        if (y <= box.top || y >= box.bottom || firstXEdge >= afterXEdge) return;
        horizontalDiff[yIndex][firstXEdge] += 1;
        horizontalDiff[yIndex][afterXEdge] -= 1;
      });
      const firstYEdge = Math.max(0, upperBound(ys, box.top) - 1);
      const afterYEdge = Math.min(ys.length - 1, lowerBound(ys, box.bottom));
      xs.forEach((x, xIndex) => {
        if (metrics) metrics.graphOccupancyChecks = (metrics.graphOccupancyChecks || 0) + 1;
        if (x <= box.left || x >= box.right || firstYEdge >= afterYEdge) return;
        verticalDiff[xIndex][firstYEdge] += 1;
        verticalDiff[xIndex][afterYEdge] -= 1;
      });
    });
    const horizontalBlocked = horizontalDiff.map((differences) => {
      let active = 0;
      return Array.from(differences.slice(0, -1), (difference) => {
        active += difference;
        return active > 0;
      });
    });
    const verticalBlocked = verticalDiff.map((differences) => {
      let active = 0;
      return Array.from(differences.slice(0, -1), (difference) => {
        active += difference;
        return active > 0;
      });
    });
    const xIndex = new Map(xs.map((value, index) => [value, index]));
    const yIndex = new Map(ys.map((value, index) => [value, index]));
    const width = xs.length;
    const directionSteps = [
      [1, 0], [0, 1], [-1, 0], [0, -1]
    ];
    const orderedSteps = directionSteps.slice(offset).concat(directionSteps.slice(0, offset));
    const edgeClear = (x, y, nextX, nextY) => {
      if (x === nextX) return !verticalBlocked[x][Math.min(y, nextY)];
      return !horizontalBlocked[y][Math.min(x, nextX)];
    };

    for (const source of sourceGates) {
      for (const target of targetGates) {
        const startX = xIndex.get(source.stub.x);
        const startY = yIndex.get(source.stub.y);
        const endX = xIndex.get(target.stub.x);
        const endY = yIndex.get(target.stub.y);
        const startId = startY * width + startX;
        const endId = endY * width + endX;
        const parents = new Int32Array(width * ys.length).fill(-2);
        const queue = new Int32Array(width * ys.length);
        let head = 0;
        let tail = 0;
        parents[startId] = -1;
        queue[tail++] = startId;
        while (head < tail && parents[endId] === -2) {
          const id = queue[head++];
          if (metrics) metrics.graphNodeVisits = (metrics.graphNodeVisits || 0) + 1;
          const x = id % width;
          const y = Math.floor(id / width);
          orderedSteps.forEach(([dx, dy]) => {
            const nextX = x + dx;
            const nextY = y + dy;
            if (nextX < 0 || nextX >= width || nextY < 0 || nextY >= ys.length) return;
            if (metrics) metrics.graphEdgeChecks = (metrics.graphEdgeChecks || 0) + 1;
            const nextId = nextY * width + nextX;
            if (parents[nextId] !== -2 || !edgeClear(x, y, nextX, nextY)) return;
            parents[nextId] = id;
            queue[tail++] = nextId;
          });
        }
        if (parents[endId] === -2) continue;
        const route = [];
        for (let id = endId; id >= 0; id = parents[id]) {
          route.push({x: xs[id % width], y: ys[Math.floor(id / width)]});
        }
        route.reverse();
        return compressRoute([source.anchor, ...route, target.anchor]);
      }
    }
    return null;
  };
  /* TESTABLE_GEOMETRY:END */

  const pathFor = (from, to, scope, declarationIndex, metrics = null) => {
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
    const points = directRoute(source, target, obstacles, gap, metrics)
      || outerRoute(source, target, boxes, gap, declarationIndex, metrics)
      || gridRoute(source, target, boxes, gap, declarationIndex, metrics);
    return points ? pathData(points) : null;
  };

  const warning = (scope, message) => {
    const badge = document.createElement('p');
    badge.className = 'connector-warning';
    badge.setAttribute('role', 'status');
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

          const route = pathFor(from, to, scope, declarationIndex);
          if (!route) {
            console.error('visual-explain: no clear path connector route', item);
            warning(scope, `「${item}」の接続経路が見つかりません。`);
            const text = document.createElement('li');
            text.textContent = `${from.textContent.trim()} から ${to.textContent.trim()} への接続経路が見つかりません`;
            list.append(text);
            return;
          }
          const path = document.createElementNS(SVG_NS, 'path');
          path.setAttribute('d', route);
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
