"""Body right half — cartridge door side of the camera shell."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS


def build() -> cq.Workplane:
    """Build the right body half-shell."""
    half_w = CAMERA.body_length / 2
    shell = (
        cq.Workplane("XY")
        .box(half_w, CAMERA.body_depth, CAMERA.body_height)
        .edges("|Z").fillet(CAMERA.body_fillet)
    )

    # Hollow interior
    inner = (
        cq.Workplane("XY")
        .box(half_w - CAMERA.wall_thickness,
             CAMERA.body_depth - 2 * CAMERA.wall_thickness,
             CAMERA.body_height - 2 * CAMERA.wall_thickness)
        .translate((-CAMERA.wall_thickness / 2, 0, 0))
    )
    shell = shell.cut(inner)

    # Cartridge door opening
    shell = (
        shell.faces(">X").workplane()
        .rect(CAMERA.cart_door_w, CAMERA.cart_door_h)
        .cutBlind(-CAMERA.wall_thickness - 1)
    )

    # Assembly screw clearance holes along split line
    f = FASTENERS["M2_5x6_shcs"]
    boss_positions = [(0, -CAMERA.body_height / 2 + 8),
                      (0, 0),
                      (0, CAMERA.body_height / 2 - 8)]
    shell = (
        shell.faces("<X").workplane()
        .pushPoints(boss_positions)
        .hole(f.clearance_hole)
    )

    return shell
