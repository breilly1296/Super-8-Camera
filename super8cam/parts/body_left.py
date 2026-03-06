"""Body left half — left side of the camera shell (lens side)."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, CMOUNT, FASTENERS


def build() -> cq.Workplane:
    """Build the left body half-shell."""
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
        .translate((CAMERA.wall_thickness / 2, 0, 0))
    )
    shell = shell.cut(inner)

    # Lens opening on front face
    shell = (
        shell.faces("<Y").workplane()
        .center(CAMERA.lens_mount_offset_x + half_w / 2, 0)
        .hole(CMOUNT.thread_major_dia + 1.0)
    )

    # Assembly screw bosses along split line
    f = FASTENERS["M2_5x6_shcs"]
    boss_positions = [(0, -CAMERA.body_height / 2 + 8),
                      (0, 0),
                      (0, CAMERA.body_height / 2 - 8)]
    shell = (
        shell.faces(">X").workplane()
        .pushPoints(boss_positions)
        .hole(f.tap_hole)
    )

    return shell
