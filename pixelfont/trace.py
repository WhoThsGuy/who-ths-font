"""Turn a set of filled pixels into clean, non-overlapping TrueType contours.

Each pixel (x, y) is the unit square [x, x+1] x [y, y+1] with y pointing up.
Every pixel contributes its four edges walked clockwise; an edge shared by two
neighbouring pixels appears once in each direction and cancels out. What is left
is the outline. Chaining the remaining edges yields outer contours running
clockwise and holes running counter-clockwise, which is exactly what TrueType's
non-zero winding rule expects.
"""

from __future__ import annotations

from collections import defaultdict

Point = tuple[int, int]
Contour = list[Point]


def _pixel_edges(x: int, y: int) -> list[tuple[Point, Point]]:
    bl, tl, tr, br = (x, y), (x, y + 1), (x + 1, y + 1), (x + 1, y)
    return [(bl, tl), (tl, tr), (tr, br), (br, bl)]  # clockwise with y up


def _turn(incoming: Point, outgoing: Point) -> int:
    """Cross product of two direction vectors: <0 right turn, >0 left turn."""
    return incoming[0] * outgoing[1] - incoming[1] * outgoing[0]


def trace(pixels: set[Point]) -> list[Contour]:
    edges: set[tuple[Point, Point]] = set()
    for x, y in pixels:
        for a, b in _pixel_edges(x, y):
            if (b, a) in edges:
                edges.discard((b, a))
            else:
                edges.add((a, b))

    outgoing: dict[Point, list[Point]] = defaultdict(list)
    for a, b in edges:
        outgoing[a].append(b)

    contours: list[Contour] = []
    remaining = set(edges)
    while remaining:
        start, nxt = min(remaining)
        contour: Contour = [start]
        prev, cur = start, nxt
        remaining.discard((start, nxt))
        while cur != start:
            contour.append(cur)
            candidates = [b for b in outgoing[cur] if (cur, b) in remaining]
            if len(candidates) == 1:
                b = candidates[0]
            else:
                # Two pixels touching only at a corner: four edges meet here.
                # Turn right so we keep hugging the pixel we came along and the
                # two squares stay separate contours.
                d_in = (cur[0] - prev[0], cur[1] - prev[1])
                b = min(candidates, key=lambda c: _turn(d_in, (c[0] - cur[0], c[1] - cur[1])))
            remaining.discard((cur, b))
            prev, cur = cur, b
        contours.append(_drop_collinear(contour))
    return contours


def _drop_collinear(contour: Contour) -> Contour:
    n = len(contour)
    out: Contour = []
    for i, p in enumerate(contour):
        a, c = contour[i - 1], contour[(i + 1) % n]
        if _turn((p[0] - a[0], p[1] - a[1]), (c[0] - p[0], c[1] - p[1])) != 0:
            out.append(p)
    return out


def signed_area(contour: Contour) -> int:
    """Twice the signed area; negative means clockwise (y up)."""
    return sum(contour[i - 1][0] * p[1] - p[0] * contour[i - 1][1] for i, p in enumerate(contour))
