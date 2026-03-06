"""Main shaft — hardened steel shaft carrying shutter, cam, and output gear."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["main_shaft"]]


def build() -> cq.Workplane:
    shaft = (
        cq.Workplane("XY")
        .cylinder(CAMERA.shaft_length, CAMERA.shaft_dia / 2)
    )

    # Keyway flat for shutter disc
    flat_depth = CAMERA.shutter_keyway_depth
    flat_length = 8.0  # mm — keyway section
    flat = (
        cq.Workplane("XY")
        .box(CAMERA.shaft_dia, flat_depth, flat_length)
        .translate((0, CAMERA.shaft_dia / 2 - flat_depth / 2, 0))
    )
    shaft = shaft.cut(flat)

    return shaft
