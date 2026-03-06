"""Shutter disc — half-circle rotary shutter with keyway and balance holes."""

import math
import cadquery as cq
from super8cam.specs.master_specs import CAMERA, ENCODER, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["shutter_disc"]]

BALANCE_HOLE_DIA = 1.5
BALANCE_HOLE_RADIUS = 10.0
BALANCE_HOLE_COUNT = 2
FLAG_DEPTH = 1.5


def build() -> cq.Workplane:
    outer_r = CAMERA.shutter_od / 2.0
    disc = cq.Workplane("XY").cylinder(CAMERA.shutter_thickness, outer_r,
                                        centered=(True, True, True))

    # Shaft hole
    disc = disc.faces(">Z").workplane().hole(CAMERA.shutter_shaft_hole)

    # Keyway
    ky = CAMERA.shutter_shaft_hole / 2 - CAMERA.shutter_keyway_depth / 2
    disc = (disc.faces(">Z").workplane()
            .center(0, ky)
            .rect(CAMERA.shutter_keyway_w, CAMERA.shutter_keyway_depth + 0.01)
            .cutThruAll())

    # Open sector cutout
    half_angle = math.radians(CAMERA.shutter_opening_angle / 2)
    arc_steps = max(32, int(CAMERA.shutter_opening_angle / 2))
    pts = [(0.0, 0.0)]
    for i in range(arc_steps + 1):
        a = -half_angle + i * (2 * half_angle) / arc_steps
        pts.append(((outer_r + 1) * math.cos(a), (outer_r + 1) * math.sin(a)))
    pts.append((0.0, 0.0))

    sector = (cq.Workplane("XY").polyline(pts).close()
              .extrude(CAMERA.shutter_thickness + 1)
              .translate((0, 0, -(CAMERA.shutter_thickness + 1) / 2)))
    disc = disc.cut(sector)

    # Balance holes
    solid_center = math.pi
    spread = math.radians((360 - CAMERA.shutter_opening_angle) / 2) * 0.6
    angles = [solid_center - spread + 2 * spread * i / (BALANCE_HOLE_COUNT - 1)
              for i in range(BALANCE_HOLE_COUNT)]
    bal_pts = [(BALANCE_HOLE_RADIUS * math.cos(a),
                BALANCE_HOLE_RADIUS * math.sin(a)) for a in angles]
    disc = disc.faces(">Z").workplane().pushPoints(bal_pts).hole(BALANCE_HOLE_DIA)

    # Sensor flag notch
    notch_r = outer_r - FLAG_DEPTH / 2
    notch = (cq.Workplane("XY")
             .rect(FLAG_DEPTH, ENCODER.flag_width)
             .extrude(CAMERA.shutter_thickness + 1)
             .translate((-notch_r, 0, -(CAMERA.shutter_thickness + 1) / 2)))
    disc = disc.cut(notch)

    return disc
