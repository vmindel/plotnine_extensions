"""
Force-directed placement of rectangular labels

All quantities are in display units (pixels). The solver knows nothing
about matplotlib; it moves axis-aligned boxes so they stop overlapping
each other and a set of circular points, while springs pull each box
back towards its anchor.

This is an independent implementation of the general idea behind R's
ggrepel; no ggrepel code was used.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

# Boxes closer than this (px) still repel, so that springs settle the
# labels just outside each other instead of just inside.
_MARGIN = 1.0

# Fraction of the penetration depth applied perpendicular to the push
_SLIDE = 0.25

# Overlap-resolution passes per iteration
_PROJECTION_PASSES = 3

# Over-relaxation of the projection. Moving boxes slightly further than
# their overlap lets crowds expand instead of jamming; springs pull them
# back afterwards.
_RELAX = 1.5

# Largest per-iteration movement (px) of a layout considered settled
_SETTLED = 0.5

# Iterations to keep tightening after the first overlap-free layout
_PATIENCE = 300

@dataclass
class RepelResult:
    centres: np.ndarray
    """(n, 2) final box centres"""

    iterations: int
    converged: bool
    """True if no box overlaps another box or a point"""


def _overlap(d, sx, sy):
    """
    Penetration of box pairs along x and y; positive on both = overlap
    """
    return sx - np.abs(d[:, 0]), sy - np.abs(d[:, 1])


def _push(d, sx, sy, tie, move, room_lo, room_hi):
    """
    Smallest translation that separates each overlapping pair

    Of the four ways out of an overlap (left, right, down, up) the
    shortest one that stays within ``room_lo``/``room_hi`` (allowed
    displacement, per pair) is taken. A box against the panel edge thus
    escapes sideways instead of being pushed into the edge. A small
    perpendicular slide lets a box squeezed between two obstacles whose
    pushes cancel work its way around one of them.

    ``sx`` and ``sy`` are the combined half sizes (with margin); ``d`` is
    the centre offset of the moving box from the obstacle.
    """
    k = len(d)
    amount = np.column_stack(
        [sx - d[:, 0], -(sx + d[:, 0]), sy - d[:, 1], -(sy + d[:, 1])]
    )
    axis = np.array([0, 0, 1, 1])
    cost = np.abs(amount)
    # Prefer the side the tie direction points to when costs are equal
    cost = cost - 1e-6 * np.column_stack(
        [tie[:, 0], -tie[:, 0], tie[:, 1], -tie[:, 1]]
    )
    feasible = (amount >= room_lo[:, axis] - 1e-9) & (
        amount <= room_hi[:, axis] + 1e-9
    )
    feasible &= (move[axis] != 0)[None, :]
    cost_f = np.where(feasible, cost, np.inf)
    best = np.argmin(cost_f, axis=1)
    # Nowhere to go within bounds: take the shortest permitted way out
    trapped = ~np.isfinite(cost_f[np.arange(k), best])
    if trapped.any():
        cost_m = np.where((move[axis] != 0)[None, :], cost, np.inf)
        best[trapped] = np.argmin(cost_m[trapped], axis=1)

    chosen = amount[np.arange(k), best]
    along_x = axis[best] == 0
    depth = np.minimum(np.abs(chosen), np.minimum(sx, sy))
    p = np.zeros_like(d)
    p[along_x, 0] = chosen[along_x]
    p[~along_x, 1] = chosen[~along_x]
    sgn = np.sign(d)
    sgn[sgn == 0] = np.sign(tie[sgn == 0])
    p[along_x, 1] = (sgn[:, 1] * depth * _SLIDE)[along_x]
    p[~along_x, 0] = (sgn[:, 0] * depth * _SLIDE)[~along_x]
    return p


def count_overlaps(
    centres: np.ndarray,
    half: np.ndarray,
    points: np.ndarray,
    radius: np.ndarray,
    own_point: np.ndarray,
    max_overlaps: float,
) -> np.ndarray:
    """
    Greedily keep labels, in order, that overlap at most max_overlaps things

    A label's own point does not count. Labels already dropped do not
    count against later ones.

    Returns
    -------
    :
        Boolean mask of labels to keep.
    """
    n = len(centres)
    keep = np.ones(n, dtype=bool)
    if not np.isfinite(max_overlaps) or n == 0:
        return keep

    n_point = np.zeros(n, dtype=int)
    if len(points):
        half_diag = np.hypot(half[:, 0], half[:, 1])
        li, pj = _label_point_pairs(
            centres, half_diag, float(radius.max()), cKDTree(points), 0.0
        )
        d = np.abs(centres[li] - points[pj])
        hit = (d[:, 0] < half[li, 0] + radius[pj]) & (
            d[:, 1] < half[li, 1] + radius[pj]
        )
        hit &= pj != own_point[li]
        n_point = np.bincount(li[hit], minlength=n)

    neighbours: list[list[int]] = [[] for _ in range(n)]
    if n > 1:
        pairs = cKDTree(centres).query_pairs(
            r=2 * float(np.hypot(half[:, 0], half[:, 1]).max()),
            output_type="ndarray",
        )
        if len(pairs):
            i, j = pairs[:, 0], pairs[:, 1]
            d = np.abs(centres[i] - centres[j])
            hit = (d[:, 0] < half[i, 0] + half[j, 0]) & (
                d[:, 1] < half[i, 1] + half[j, 1]
            )
            for a, b in zip(i[hit], j[hit]):
                lo_, hi_ = (a, b) if a < b else (b, a)
                neighbours[hi_].append(lo_)

    for i in range(n):
        earlier = sum(keep[k] for k in neighbours[i])
        if n_point[i] + earlier > max_overlaps:
            keep[i] = False
    return keep


def repel(
    anchors: np.ndarray,
    sizes: np.ndarray,
    points: np.ndarray,
    radius: np.ndarray,
    bounds: tuple[float, float, float, float],
    *,
    start: np.ndarray | None = None,
    force: float = 1.0,
    force_pull: float = 1.0,
    direction: str = "both",
    max_iter: int = 10_000,
    max_time: float = 0.5,
    seed: int | None = 1,
) -> RepelResult:
    """
    Move boxes off each other and off points

    Parameters
    ----------
    anchors :
        (n, 2) positions each box is pulled towards.
    sizes :
        (n, 2) box widths and heights.
    points :
        (m, 2) positions of obstacles.
    radius :
        (m,) obstacle radii. Obstacles are treated as squares of this
        half-width, which is conservative for round markers.
    bounds :
        (xmin, xmax, ymin, ymax) that boxes must stay within.
    start :
        (n, 2) initial centres; defaults to the anchors.
    force :
        Strength of repulsion.
    force_pull :
        Strength of the spring to the anchor.
    direction :
        One of "both", "x", "y".
    max_iter, max_time :
        Stop after this many iterations or seconds.
    seed :
        Seed for the jitter that breaks symmetric ties.
    """
    if direction not in ("both", "x", "y"):
        raise ValueError(f"direction must be 'both', 'x' or 'y', got {direction!r}")

    anchors = np.asarray(anchors, float).reshape(-1, 2)
    n = len(anchors)
    half = np.asarray(sizes, float).reshape(-1, 2) / 2
    points = np.asarray(points, float).reshape(-1, 2)
    radius = np.broadcast_to(np.asarray(radius, float), (len(points),))
    c = (anchors if start is None else np.asarray(start, float)).copy()

    if n == 0:
        return RepelResult(c, 0, True)

    rng = np.random.default_rng(seed)
    # Labels leave their points outwards from the middle of the panel,
    # which keeps neighbouring segments roughly parallel.
    xmin, xmax, ymin, ymax = bounds
    outward = anchors - [(xmin + xmax) / 2, (ymin + ymax) / 2]
    angle = np.arctan2(outward[:, 1], outward[:, 0])
    flat = np.hypot(outward[:, 0], outward[:, 1]) < 1e-9
    angle[flat] = rng.uniform(0, 2 * np.pi, flat.sum())
    angle += rng.normal(scale=0.3, size=n)
    tie_dir = np.column_stack([np.cos(angle), np.sin(angle)])

    move = np.array(
        {"both": [1.0, 1.0], "x": [1.0, 0.0], "y": [0.0, 1.0]}[direction]
    )
    if direction != "both":
        # A label that may only move along one axis cannot escape its own
        # point sideways; give ties the allowed direction.
        tie_dir = tie_dir * move
        tie_dir[np.all(tie_dir == 0, axis=1)] = move
        tie_dir /= np.hypot(tie_dir[:, 0], tie_dir[:, 1])[:, None]
    c += 0.5 * tie_dir

    xmin, xmax, ymin, ymax = bounds
    lo = np.column_stack([xmin + half[:, 0], ymin + half[:, 1]])
    hi = np.column_stack([xmax - half[:, 0], ymax - half[:, 1]])
    too_big = lo > hi
    mid = (lo + hi) / 2
    lo[too_big] = mid[too_big]
    hi[too_big] = mid[too_big]

    max_step = max(1.0, 0.5 * float(np.median(half[:, 1])))
    half_diag = np.hypot(half[:, 0], half[:, 1])
    rmax = float(radius.max()) if len(radius) else 0.0
    point_tree = cKDTree(points) if len(points) else None
    pair_r = 2 * float(half_diag.max()) + _MARGIN

    spring = 0.02 * force_pull
    damping = 0.6
    v = np.zeros_like(c)
    t0 = time.perf_counter()
    best = None
    first_clean = None
    jammed = np.zeros(n, dtype=bool)
    it = 0

    for it in range(1, max_iter + 1):
        # Position-based dynamics: springs move the boxes, then overlaps
        # are projected out and the velocity is whatever movement
        # survived. Projection, unlike a repulsive force, leaves no
        # residual overlap balanced against the springs.
        # Springs are released on boxes jammed against other boxes, so a
        # crowd can spread out instead of being squeezed back together.
        # Boxes that only touch points keep their springs; otherwise a
        # label inside a dense point cloud drifts away indefinitely.
        pull = spring * (anchors - c) * move
        pull[jammed] = 0
        v = damping * v + pull
        speed = np.hypot(v[:, 0], v[:, 1])
        fast = speed > max_step
        if fast.any():
            v[fast] *= (max_step / speed[fast])[:, None]
        prev = c
        c = np.clip(c + v, lo, hi)

        for k in range(_PROJECTION_PASSES):
            disp, stuck, jammed = _separation(
                c, half, half_diag, points, radius, rmax, point_tree,
                pair_r, tie_dir, force, move, lo, hi,
            )
            if k == 0 and stuck.any():
                # Jitter boxes that still overlap something to break
                # deadlocks the deterministic pushes cannot resolve.
                disp[stuck] += rng.normal(
                    scale=0.25 * max_step, size=(stuck.sum(), 2)
                )
            c = np.clip(c + disp * move, lo, hi)
            if not stuck.any():
                break

        v = c - prev
        # The last projection pass was measured before it moved the boxes;
        # confirm the layout it produced is clean before accepting it.
        clean = not stuck.any() and not _has_overlap(c, half, points, radius)
        if clean:
            # Springs keep nudging boxes into contact, so an overlap-free
            # layout need not be a still one. Keep the latest clean layout
            # and stop once it has settled.
            best = c
            if first_clean is None:
                first_clean = it
            if (
                np.abs(v).max() < _SETTLED
                or it - first_clean > _PATIENCE
            ):
                break
        if time.perf_counter() - t0 > max_time:
            break

    # Swapping two labels moves them along both axes
    untangle = direction == "both"
    if best is not None:
        if untangle:
            best = _untangle(best, anchors, half, points, radius, lo, hi)
        return RepelResult(best, it, True)

    if untangle:
        c = _untangle(c, anchors, half, points, radius, lo, hi)
    return RepelResult(c, it, not _has_overlap(c, half, points, radius))


def _bincount2(idx, values, n):
    return np.column_stack(
        [
            np.bincount(idx, values[:, 0], minlength=n),
            np.bincount(idx, values[:, 1], minlength=n),
        ]
    )


def _label_point_pairs(c, half_diag, rmax, point_tree, pad):
    hits = point_tree.query_ball_point(
        c, r=half_diag + rmax + pad, return_sorted=False
    )
    lens = np.fromiter((len(h) for h in hits), int, len(c))
    if not lens.sum():
        e = np.empty(0, int)
        return e, e
    li = np.repeat(np.arange(len(c)), lens)
    pj = np.concatenate([np.asarray(h, int) for h in hits if len(h)])
    return li, pj


def _separation(
    c, half, half_diag, points, radius, rmax, point_tree, pair_r, tie_dir,
    force, move, lo, hi,
):
    """
    Displacement that moves every overlapping box out of what it overlaps
    """
    n = len(c)
    disp = np.zeros_like(c)
    stuck = np.zeros(n, dtype=bool)
    jammed = np.zeros(n, dtype=bool)

    if n > 1:
        ll = cKDTree(c).query_pairs(r=pair_r, output_type="ndarray")
        if len(ll):
            i, j = ll[:, 0], ll[:, 1]
            d = c[i] - c[j]
            sx = half[i, 0] + half[j, 0]
            sy = half[i, 1] + half[j, 1]
            ox, oy = _overlap(d, sx + _MARGIN, sy + _MARGIN)
            hit = (ox > 0) & (oy > 0)
            if hit.any():
                i, j = i[hit], j[hit]
                ox, oy = ox[hit], oy[hit]
                real = (ox > _MARGIN) & (oy > _MARGIN)
                stuck[i[real]] = True
                stuck[j[real]] = True
                jammed[i[real]] = True
                jammed[j[real]] = True
                room_lo = np.maximum(2 * (lo[i] - c[i]), -2 * (hi[j] - c[j]))
                room_hi = np.minimum(2 * (hi[i] - c[i]), -2 * (lo[j] - c[j]))
                p = _push(
                    d[hit], sx[hit] + _MARGIN, sy[hit] + _MARGIN, tie_dir[i],
                    move, room_lo, room_hi,
                )
                p *= 0.5 * force * _RELAX
                disp += _bincount2(i, p, n) - _bincount2(j, p, n)

    if point_tree is not None:
        li, pj = _label_point_pairs(c, half_diag, rmax, point_tree, _MARGIN)
        if len(li):
            d = c[li] - points[pj]
            sx = half[li, 0] + radius[pj]
            sy = half[li, 1] + radius[pj]
            ox, oy = _overlap(d, sx + _MARGIN, sy + _MARGIN)
            hit = (ox > 0) & (oy > 0)
            if hit.any():
                li = li[hit]
                ox, oy = ox[hit], oy[hit]
                stuck[li[(ox > _MARGIN) & (oy > _MARGIN)]] = True
                p = _push(
                    d[hit], sx[hit] + _MARGIN, sy[hit] + _MARGIN, tie_dir[li],
                    move, lo[li] - c[li], hi[li] - c[li],
                )
                disp += _bincount2(li, p * (force * _RELAX), n)

    return disp, stuck, jammed


def _has_overlap(c, half, points, radius) -> bool:
    n = len(c)
    half_diag = np.hypot(half[:, 0], half[:, 1])
    if n > 1:
        pairs = cKDTree(c).query_pairs(
            r=2 * half_diag.max(), output_type="ndarray"
        )
        if len(pairs):
            i, j = pairs[:, 0], pairs[:, 1]
            ox, oy = _overlap(
                c[i] - c[j], half[i, 0] + half[j, 0], half[i, 1] + half[j, 1]
            )
            if ((ox > 0) & (oy > 0)).any():
                return True
    if len(points):
        li, pj = _label_point_pairs(
            c, half_diag, float(radius.max()), cKDTree(points), 0.0
        )
        if len(li):
            ox, oy = _overlap(
                c[li] - points[pj],
                half[li, 0] + radius[pj],
                half[li, 1] + radius[pj],
            )
            if ((ox > 0) & (oy > 0)).any():
                return True
    return False


def _crossings(a: np.ndarray, c: np.ndarray) -> np.ndarray:
    """
    Pairs (i, j), i < j, whose anchor-to-centre segments cross
    """
    n = len(a)
    if n < 2:
        return np.empty((0, 2), int)
    i, j = np.triu_indices(n, 1)
    p, r = a[i], c[i] - a[i]
    q, s = a[j], c[j] - a[j]
    rxs = r[:, 0] * s[:, 1] - r[:, 1] * s[:, 0]
    qp = q - p
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / rxs
        u = (qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]) / rxs
    hit = (np.abs(rxs) > 1e-9) & (t > 0) & (t < 1) & (u > 0) & (u < 1)
    return np.column_stack([i[hit], j[hit]])


def _overlaps_of(k, c, half, points, radius, point_tree) -> int:
    """
    Number of boxes and points that box k overlaps
    """
    d = np.abs(c - c[k])
    n_box = int(
        ((d[:, 0] < half[:, 0] + half[k, 0]) & (d[:, 1] < half[:, 1] + half[k, 1])).sum()
    ) - 1
    if point_tree is None:
        return n_box
    near = point_tree.query_ball_point(
        c[k], r=float(np.hypot(*half[k])) + float(radius.max())
    )
    if not near:
        return n_box
    near = np.asarray(near, int)
    dp = np.abs(points[near] - c[k])
    n_pt = int(
        (
            (dp[:, 0] < half[k, 0] + radius[near])
            & (dp[:, 1] < half[k, 1] + radius[near])
        ).sum()
    )
    return n_box + n_pt


def _untangle(c, anchors, half, points, radius, lo, hi, passes=3):
    """
    Swap pairs of labels whose leader lines cross

    A swap is kept only if it shortens the two segments and does not add
    overlaps. Quadratic in the number of labels, so skipped for large n.
    """
    n = len(c)
    if n < 2 or n > 2000:
        return c
    point_tree = cKDTree(points) if len(points) else None
    c = c.copy()
    for _ in range(passes):
        swapped = False
        for i, j in _crossings(anchors, c):
            old = np.hypot(*(c[i] - anchors[i])) + np.hypot(*(c[j] - anchors[j]))
            ci = np.clip(c[j], lo[i], hi[i])
            cj = np.clip(c[i], lo[j], hi[j])
            new = np.hypot(*(ci - anchors[i])) + np.hypot(*(cj - anchors[j]))
            if new >= old:
                continue
            before = _overlaps_of(i, c, half, points, radius, point_tree) + _overlaps_of(
                j, c, half, points, radius, point_tree
            )
            trial = c.copy()
            trial[i], trial[j] = ci, cj
            after = _overlaps_of(i, trial, half, points, radius, point_tree) + _overlaps_of(
                j, trial, half, points, radius, point_tree
            )
            if after <= before:
                c = trial
                swapped = True
        if not swapped:
            break
    return c
