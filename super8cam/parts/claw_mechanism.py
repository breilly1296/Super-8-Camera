"""Claw mechanism — the pulldown claw arm that advances film one frame."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["claw"]]


def build() -> cq.Workplane:
    """Build the claw arm with tip."""
    # Main arm
    arm = (
        cq.Workplane("XY")
        .box(CAMERA.claw_arm_length, CAMERA.claw_arm_w, CAMERA.claw_arm_thick)
    )

    # Tip (narrower, at one end)
    tip = (
        cq.Workplane("XY")
        .box(CAMERA.claw_engage_depth + 1.0, CAMERA.claw_tip_w, CAMERA.claw_tip_h)
        .translate((CAMERA.claw_arm_length / 2 + CAMERA.claw_engage_depth / 2, 0, 0))
    )
    arm = arm.union(tip)

    # Pivot hole at the other end
    pivot_hole_dia = 1.5  # mm — pivot pin
    arm = (
        arm.faces(">Z").workplane()
        .center(-CAMERA.claw_arm_length / 2 + 2.0, 0)
        .hole(pivot_hole_dia)
    )

    return arm
