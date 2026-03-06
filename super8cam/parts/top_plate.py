"""Top plate — covers the top of the camera body, carries viewfinder."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS


def build() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .box(CAMERA.body_length - 2, CAMERA.body_depth - 2, CAMERA.wall_thickness)
        .edges("|Z").fillet(CAMERA.body_fillet - 1)
    )

    # Viewfinder bore
    plate = (
        plate.faces(">Z").workplane()
        .center(CAMERA.body_length / 4, 0)
        .hole(CAMERA.viewfinder_eye_dia + 1.0)
    )

    # Accessory shoe slot (cold shoe)
    shoe_l, shoe_w, shoe_d = 18.0, 12.0, 2.0
    plate = (
        plate.faces(">Z").workplane()
        .center(-CAMERA.body_length / 4, 0)
        .rect(shoe_l, shoe_w)
        .cutBlind(-shoe_d)
    )

    return plate
