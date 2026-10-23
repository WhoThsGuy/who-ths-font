from pixelfont.bdf import Glyph
from pixelfont.trace import signed_area, trace


def px(art: str) -> set[tuple[int, int]]:
    return Glyph.from_ascii(0, art).pixels()


def test_single_pixel_is_one_clockwise_square():
    (c,) = trace({(0, 0)})
    assert set(c) == {(0, 0), (0, 1), (1, 1), (1, 0)}
    assert len(c) == 4
    assert signed_area(c) < 0  # clockwise


def test_horizontal_run_merges_into_one_rectangle():
    (c,) = trace({(0, 0), (1, 0), (2, 0)})
    assert set(c) == {(0, 0), (0, 1), (3, 1), (3, 0)}


def test_letter_with_hole_has_ccw_inner_contour():
    contours = trace(px("""
###
#.#
###
"""))
    assert len(contours) == 2
    outer = max(contours, key=lambda c: abs(signed_area(c)))
    inner = min(contours, key=lambda c: abs(signed_area(c)))
    assert signed_area(outer) < 0  # clockwise
    assert signed_area(inner) > 0  # counter-clockwise hole
    assert set(inner) == {(1, 1), (1, 2), (2, 2), (2, 1)}


def test_diagonal_touch_stays_two_contours():
    contours = trace({(0, 0), (1, 1)})
    assert len(contours) == 2
    assert all(len(c) == 4 and signed_area(c) < 0 for c in contours)


def test_pinched_hole_keeps_contours_separate():
    # Ring whose hole touches the outside only at corners: still exactly one
    # clockwise outer contour and one counter-clockwise hole, no figure-eights.
    contours = trace(px("""
.###.
##.##
#...#
##.##
.###.
"""))
    assert sum(1 for c in contours if signed_area(c) < 0) == 1
    assert sum(1 for c in contours if signed_area(c) > 0) == 1


def test_empty_glyph_has_no_contours():
    assert trace(set()) == []
