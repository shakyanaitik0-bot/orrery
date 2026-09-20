"""Turning the knowledge graph into coordinates.

The 3D interface is not a decorative shell over a list — it draws this graph.
Position carries meaning, so it is computed on the server from the same edges
that gate progression:

* **Height (y)** is prerequisite depth. A concept sits above everything it
  requires, so "up" is genuinely "further in".
* **Ring position (x, z)** spreads the concepts within a depth band, ordered so
  that concepts sharing a prerequisite end up near each other.
* **Mastery** is returned per node and drives size and glow in the client.

A concept whose prerequisites are unmet is returned as `locked`, which is the
same gate OpenTutor and SkillCoco both applied — expressed here as geometry.
"""

import math
from collections import defaultdict

from models import EdgeType
from services.learning.mastery import MASTERY_THRESHOLD

RING_RADIUS = 7.4
LAYER_HEIGHT = 3.0


def _depths(node_ids: list[str], prereq_edges: list[tuple[str, str]]) -> dict[str, int]:
    """Longest-path depth for each node over prerequisite edges.

    Longest path rather than shortest: a concept is only as reachable as its
    deepest requirement. Cycles are broken by visiting each node once, so a
    malformed graph degrades to a flat layer instead of hanging.
    """
    incoming: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for src, dst in prereq_edges:
        outgoing[src].append(dst)
        incoming[dst].append(src)

    depth = {n: 0 for n in node_ids}
    # Kahn's algorithm; anything left over is in a cycle and keeps depth 0.
    indeg = {n: len(incoming[n]) for n in node_ids}
    queue = [n for n in node_ids if indeg[n] == 0]
    seen = 0
    while queue:
        node = queue.pop(0)
        seen += 1
        for nxt in outgoing[node]:
            depth[nxt] = max(depth[nxt], depth[node] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return depth


def build_scene(
    concepts: list[dict],
    edges: list[dict],
    mastery: dict[str, float],
) -> dict:
    """Produce the payload the 3D client renders.

    `concepts` are dicts with id/title/summary/subject; `edges` have
    source/target/relation; `mastery` maps concept id to probability.
    """
    ids = [c["id"] for c in concepts]
    prereqs = [
        (e["source"], e["target"])
        for e in edges
        if e["relation"] == EdgeType.prerequisite.value
    ]
    depth = _depths(ids, prereqs)

    by_depth: dict[int, list[str]] = defaultdict(list)
    for cid in ids:
        by_depth[depth[cid]].append(cid)

    # A concept unlocks when every prerequisite is mastered.
    required: dict[str, list[str]] = defaultdict(list)
    for src, dst in prereqs:
        required[dst].append(src)

    positions: dict[str, tuple[float, float, float]] = {}
    layer_radius: dict[int, float] = {}
    for layer, members in by_depth.items():
        count = len(members)
        # Widen the ring as layers grow so nodes never collide.
        radius = RING_RADIUS * (1 + 0.18 * max(0, count - 3))
        layer_radius[layer] = radius
        for i, cid in enumerate(members):
            angle = (2 * math.pi * i / count) + (layer * 0.4)  # offset per layer
            # A layer holding one concept still sits off-axis, so a long
            # single-file chain reads as a path rather than a straight pole.
            r = radius if count > 1 else radius * 0.26
            x = math.cos(angle) * r
            z = math.sin(angle) * r
            positions[cid] = (x, layer * LAYER_HEIGHT, z)

    nodes = []
    for c in concepts:
        cid = c["id"]
        p = mastery.get(cid, 0.0)
        unmet = [r for r in required[cid] if mastery.get(r, 0.0) < MASTERY_THRESHOLD]
        x, y, z = positions[cid]
        nodes.append(
            {
                **c,
                "position": {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
                "depth": depth[cid],
                "mastery": round(p, 4),
                "mastered": p >= MASTERY_THRESHOLD,
                "locked": len(unmet) > 0,
                "blockedBy": unmet,
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "layers": max(depth.values()) + 1 if depth else 0,
        "layerHeight": LAYER_HEIGHT,
        # Per-layer ring radius, so the client draws guides that match the
        # actual node spread instead of a fixed circle.
        "layerRadius": [
            round(layer_radius.get(i, RING_RADIUS), 3)
            for i in range(max(depth.values()) + 1 if depth else 0)
        ],
        "masteryThreshold": MASTERY_THRESHOLD,
    }
