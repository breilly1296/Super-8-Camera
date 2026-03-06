"""Registration pin — precision ground steel pin for film positioning."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["registration_pin"]]


def build() -> cq.Workplane:
    """Build the registration pin (cylindrical with chamfered tip)."""
    total_length = CAMERA.reg_pin_length + 2.0  # 2mm base embedded in gate
    pin = (
        cq.Workplane("XY")
        .cylinder(total_length, CAMERA.reg_pin_dia / 2)
    )

    # Chamfer the tip for easy film engagement
    pin = pin.faces(">Z").chamfer(0.1)

    return pin
