"""Bottom plate — camera base with tripod mount and battery door opening."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS


def build() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .box(CAMERA.body_length - 2, CAMERA.body_depth - 2, CAMERA.wall_thickness)
        .edges("|Z").fillet(CAMERA.body_fillet - 1)
    )

    # Tripod mount boss (raised pad for helicoil)
    boss = (
        cq.Workplane("XY")
        .cylinder(CAMERA.tripod_boss_depth, CAMERA.tripod_boss_dia / 2)
        .translate((0, 0, -(CAMERA.wall_thickness / 2 + CAMERA.tripod_boss_depth / 2)))
    )
    plate = plate.union(boss)

    # 1/4-20 threaded hole
    f = FASTENERS["quarter20x6"]
    plate = (
        plate.faces("<Z").workplane()
        .hole(f.tap_hole, f.length + 2)
    )

    # Battery door opening
    plate = (
        plate.faces("<Z").workplane()
        .center(CAMERA.body_length / 4, 0)
        .rect(CAMERA.batt_pocket_l + 2, CAMERA.batt_pocket_w + 2)
        .cutThruAll()
    )

    return plate
