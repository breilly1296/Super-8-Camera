"""Film gate — precision brass plate with aperture, channel, and reg pin hole."""

import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, TOL, FASTENERS, MATERIAL_USAGE, MATERIALS,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["film_gate"]]


def build() -> cq.Workplane:
    """Build the film gate plate."""
    gate = (
        cq.Workplane("XY")
        .box(CAMERA.gate_plate_w, CAMERA.gate_plate_h, CAMERA.gate_plate_thick)
        .edges("|Z").fillet(CAMERA.gate_fillet)
    )

    # Film channel
    gate = (
        gate.faces(">Z").workplane()
        .rect(CAMERA.gate_channel_w, CAMERA.gate_plate_h)
        .cutBlind(-CAMERA.gate_channel_depth)
    )

    # Pressure plate lip
    lip_outer_w = FILM.frame_w + 2 * CAMERA.gate_lip_w
    lip_outer_h = FILM.frame_h + 2 * CAMERA.gate_lip_w
    lip = (
        cq.Workplane("XY")
        .box(lip_outer_w, lip_outer_h, CAMERA.gate_lip_h)
        .translate((0, 0, CAMERA.gate_plate_thick / 2 - CAMERA.gate_channel_depth
                    + CAMERA.gate_lip_h / 2))
    )
    gate = gate.union(lip)

    # Aperture through-hole
    gate = (
        gate.faces(">Z").workplane()
        .rect(FILM.frame_w, FILM.frame_h)
        .cutThruAll()
    )

    # Aperture fillet
    gate = (
        gate.edges(cq.selectors.BoxSelector(
            (-FILM.frame_w / 2 - 0.1, -FILM.frame_h / 2 - 0.1, -CAMERA.gate_plate_thick),
            (FILM.frame_w / 2 + 0.1, FILM.frame_h / 2 + 0.1, CAMERA.gate_plate_thick)))
        .fillet(CAMERA.gate_aperture_fillet)
    )

    # Registration pin hole
    gate = (
        gate.faces(">Z").workplane()
        .center(0, -FILM.reg_pin_below_frame_center)
        .hole(CAMERA.reg_pin_dia)
    )

    # M2 mounting holes
    f = FASTENERS["M2x5_shcs"]
    hole_x = CAMERA.gate_plate_w / 2 - 3.0
    hole_y = CAMERA.gate_plate_h / 2 - 3.0
    gate = (
        gate.faces(">Z").workplane()
        .pushPoints([(-hole_x, hole_y), (hole_x, -hole_y)])
        .hole(f.clearance_hole)
    )

    return gate


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/film_gate.step")
    cq.exporters.export(solid, f"{output_dir}/film_gate.stl",
                        tolerance=0.01, angularTolerance=0.1)
