"""PCB bracket — standoffs and mounting plate for the control PCB."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, PCB, FASTENERS


def build() -> cq.Workplane:
    """Build 4 standoff posts on a thin base plate."""
    base_thick = 1.5
    base = (
        cq.Workplane("XY")
        .box(CAMERA.pcb_standoff_rect_w + 8,
             CAMERA.pcb_standoff_rect_h + 8,
             base_thick)
    )

    # Standoff posts
    posts = []
    for x_sign in [-1, 1]:
        for y_sign in [-1, 1]:
            px = x_sign * CAMERA.pcb_standoff_rect_w / 2
            py = y_sign * CAMERA.pcb_standoff_rect_h / 2
            post = (
                cq.Workplane("XY")
                .cylinder(CAMERA.pcb_standoff_height, CAMERA.pcb_standoff_dia / 2)
                .translate((px, py, base_thick / 2 + CAMERA.pcb_standoff_height / 2))
            )
            base = base.union(post)

    # M2 holes through standoffs
    f = FASTENERS["M2x8_shcs"]
    standoff_pts = [
        (x * CAMERA.pcb_standoff_rect_w / 2, y * CAMERA.pcb_standoff_rect_h / 2)
        for x in [-1, 1] for y in [-1, 1]
    ]
    base = (
        base.faces(">Z").workplane()
        .pushPoints(standoff_pts)
        .hole(f.tap_hole)
    )

    return base
