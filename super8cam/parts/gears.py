"""Gears — 2-stage spur gear train (Delrin) from motor to main shaft."""

import math
import cadquery as cq
from super8cam.specs.master_specs import GEARBOX, MOTOR, CAMERA, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["gears"]]


def _spur_gear_profile(module: float, teeth: int, steps_per_tooth: int = 8):
    """Generate approximate spur gear 2D profile as a list of (x, y) points."""
    r_pitch = module * teeth / 2
    r_outer = r_pitch + module
    r_root = r_pitch - 1.25 * module
    points = []
    for i in range(teeth):
        base_angle = 2 * math.pi * i / teeth
        # Simplified trapezoidal tooth profile
        half_tooth = math.pi / teeth * 0.45
        angles = [
            base_angle - half_tooth * 1.2,  # root start
            base_angle - half_tooth,         # tip start
            base_angle + half_tooth,         # tip end
            base_angle + half_tooth * 1.2,  # root end
        ]
        radii = [r_root, r_outer, r_outer, r_root]
        for a, r in zip(angles, radii):
            points.append((r * math.cos(a), r * math.sin(a)))
    return points


def build_gear(module: float, teeth: int, bore: float,
               face_width: float = None) -> cq.Workplane:
    """Build a simplified spur gear."""
    fw = face_width or GEARBOX.gear_face_width
    r_outer = module * teeth / 2 + module

    # Simplified as a cylinder (exact involute profile not needed for layout)
    gear = (
        cq.Workplane("XY")
        .cylinder(fw, r_outer)
    )

    # Bore
    gear = gear.faces(">Z").workplane().hole(bore)

    return gear


def build_stage1_pinion() -> cq.Workplane:
    return build_gear(GEARBOX.stage1_module, GEARBOX.stage1_pinion_teeth,
                      bore=MOTOR.shaft_dia + 0.05)


def build_stage1_gear() -> cq.Workplane:
    return build_gear(GEARBOX.stage1_module, GEARBOX.stage1_gear_teeth,
                      bore=CAMERA.shaft_dia)


def build_stage2_pinion() -> cq.Workplane:
    return build_gear(GEARBOX.stage2_module, GEARBOX.stage2_pinion_teeth,
                      bore=CAMERA.shaft_dia)


def build_stage2_gear() -> cq.Workplane:
    return build_gear(GEARBOX.stage2_module, GEARBOX.stage2_gear_teeth,
                      bore=CAMERA.shaft_dia)
