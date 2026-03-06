"""Pressure plate — spring steel leaf that holds film flat against gate."""

import cadquery as cq
from super8cam.specs.master_specs import FILM, CAMERA, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["pressure_plate"]]


def build() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .box(CAMERA.pressure_plate_w, CAMERA.pressure_plate_h,
             CAMERA.pressure_plate_thick)
    )

    # Aperture window (slightly larger than film frame for clearance)
    clearance = 0.5
    plate = (
        plate.faces(">Z").workplane()
        .rect(FILM.frame_w + clearance, FILM.frame_h + clearance)
        .cutThruAll()
    )

    # Spring tabs on top and bottom
    tab_w = 4.0
    tab_h = 3.0
    for y_sign in [1, -1]:
        tab = (
            cq.Workplane("XY")
            .box(tab_w, tab_h, CAMERA.pressure_plate_thick)
            .translate((0, y_sign * (CAMERA.pressure_plate_h / 2 + tab_h / 2), 0))
        )
        plate = plate.union(tab)

    return plate
