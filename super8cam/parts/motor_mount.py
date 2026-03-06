"""Motor mount — bracket that secures the DC motor inside the body shell."""

import cadquery as cq
from super8cam.specs.master_specs import MOTOR, CAMERA, FASTENERS

BRACKET_THICK = 3.0  # mm
BRACKET_WIDTH = MOTOR.body_dia + 8.0  # mm — flanges on each side


def build() -> cq.Workplane:
    """Build the motor mount bracket (U-shaped cradle)."""
    cradle_h = MOTOR.body_dia / 2 + BRACKET_THICK

    bracket = (
        cq.Workplane("XY")
        .box(BRACKET_WIDTH, MOTOR.body_length + 4, BRACKET_THICK)
    )

    # Side walls
    for x_sign in [-1, 1]:
        wall = (
            cq.Workplane("XY")
            .box(BRACKET_THICK, MOTOR.body_length + 4, cradle_h)
            .translate((x_sign * (BRACKET_WIDTH / 2 - BRACKET_THICK / 2),
                        0, cradle_h / 2))
        )
        bracket = bracket.union(wall)

    # Motor bore (cylindrical cutout)
    motor_cyl = (
        cq.Workplane("XZ")
        .cylinder(MOTOR.body_length + 6, MOTOR.body_dia / 2 + 0.2)
        .translate((0, 0, MOTOR.body_dia / 2 + BRACKET_THICK))
    )
    bracket = bracket.cut(motor_cyl)

    # Mounting holes
    f = FASTENERS["M3x8_shcs"]
    half_spacing = MOTOR.mount_hole_spacing / 2
    bracket = (
        bracket.faces("<Z").workplane()
        .pushPoints([(-half_spacing, 0), (half_spacing, 0)])
        .hole(f.clearance_hole)
    )

    return bracket
