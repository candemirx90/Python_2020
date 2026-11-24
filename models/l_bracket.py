"""L-bracket, laser cut and bent from 3 mm aluminium sheet (5052-H32).

Outside dimensions 40 x 40 mm, 30 mm wide along the bend, two M5 clearance holes per flange.

Check: cad model dfm "$ID" --process sheet --material aluminum --thickness 3 --bend-radius 3
"""

import build123d as bd
from cad import model
from cad.build123d import unfold

T = 3.0            # sheet thickness
R = 3.0            # inside bend radius (1 x t, the minimum for a brake bend)
LEG_A = 40.0       # base flange, outside length along X
LEG_B = 40.0       # upright flange, outside height along Z
WIDTH = 30.0       # along the bend (Y)
HOLE_D = 5.5       # M5 clearance, ISO 273 medium
HOLE_FROM_CORNER = 23.0   # hole centres from the outside corner: centred on each flange's flat
HOLE_PITCH = 16.0  # hole centres apart, across the width
K_FACTOR = 0.33    # Hubs air-bending chart, soft aluminium, r <= t (what `cad model dfm` assumes); use the shop's bend table


def l_bracket_body(t, r, leg_a, leg_b, width, hole_d, hole_from_corner, hole_pitch):
    align = (bd.Align.MIN, bd.Align.CENTER, bd.Align.MIN)
    base = bd.Box(leg_a, width, t, align=align)
    upright = bd.Box(t, width, leg_b, align=align)
    body = base + upright

    along = body.edges().filter_by(bd.Axis.Y)
    inside = [e for e in along if abs(e.center().X - t) < 1e-6 and abs(e.center().Z - t) < 1e-6]
    outside = [e for e in along if abs(e.center().X) < 1e-6 and abs(e.center().Z) < 1e-6]
    body = body.fillet(r, inside).fillet(r + t, outside)

    for y in (-hole_pitch / 2, hole_pitch / 2):
        # cutters centred on each flange's mid-plane, longer than t so they cut clean through
        body -= bd.Pos(hole_from_corner, y, t / 2) * bd.Cylinder(hole_d / 2, 2 * t)
        body -= bd.Pos(t / 2, y, hole_from_corner) * bd.Rot(0, 90, 0) * bd.Cylinder(hole_d / 2, 2 * t)

    body.label = "l_bracket"
    body.material = "alu_g5052_h32"
    body.color = "#a9b3bd"
    return body


@model
def l_bracket():
    body = l_bracket_body(T, R, LEG_A, LEG_B, WIDTH, HOLE_D, HOLE_FROM_CORNER, HOLE_PITCH)

    bb = body.bounding_box()
    assert abs(bb.size.X - LEG_A) < 1e-6, bb.size
    assert abs(bb.size.Y - WIDTH) < 1e-6, bb.size
    assert abs(bb.size.Z - LEG_B) < 1e-6, bb.size
    assert len(body.solids()) == 1
    holes = [f for f in body.faces() if f.geom_type == bd.GeomType.CYLINDER
             and abs(f.radius - HOLE_D / 2) < 1e-6]
    assert len(holes) == 4, len(holes)
    return body


@model
def l_bracket_flat():
    """Flat pattern for the laser: CUT outline at finished size (no kerf offset), BEND centre line."""
    return unfold(l_bracket().shape, k_factor=K_FACTOR, bend_lines=True)


if __name__ == "__main__":
    l_bracket()
    l_bracket_flat()
