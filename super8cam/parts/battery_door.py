"""Battery door — hinged cover for the battery compartment on the bottom."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA


def build() -> cq.Workplane:
    door = (
        cq.Workplane("XY")
        .box(CAMERA.batt_pocket_l + 4, CAMERA.batt_pocket_w + 4,
             CAMERA.batt_door_thick)
        .edges("|Z").fillet(1.5)
    )

    # Latch notch
    door = (
        door.faces(">Y").workplane()
        .center(0, 0)
        .rect(6.0, CAMERA.batt_door_thick - 0.5)
        .cutBlind(-1.5)
    )

    # Hinge pin holes
    pin_dia = 1.5
    door = (
        door.faces("<Y").workplane()
        .pushPoints([(-CAMERA.batt_pocket_l / 2, 0),
                     (CAMERA.batt_pocket_l / 2, 0)])
        .hole(pin_dia)
    )

    return door
