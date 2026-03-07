"""Trigger — ergonomic lever that actuates a microswitch to start/stop the motor.

Design:
  - Pivot lever on a 2mm pin (smooth rotation)
  - Finger pad: 12mm x 8mm, slightly concave (comfortable press)
  - Internal arm actuates a microswitch
  - Return spring: compression spring 3mm OD, 5mm free length
  - Travel: 2mm to actuate
  - Position: right side of camera, upper area, where index finger
    naturally falls when gripping with right hand

The trigger assembly includes the lever, pivot pin, spring post,
and a placeholder for the microswitch.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS, TRIGGER_SPEC

# =========================================================================
# LEVER DIMENSIONS
# =========================================================================
LEVER_LENGTH = TRIGGER_SPEC.lever_length
LEVER_WIDTH = TRIGGER_SPEC.lever_width
LEVER_THICK = TRIGGER_SPEC.lever_thick

# Finger pad
PAD_L = TRIGGER_SPEC.pad_l
PAD_W = TRIGGER_SPEC.pad_w
PAD_DEPTH = TRIGGER_SPEC.pad_depth
PAD_OFFSET = LEVER_LENGTH / 2.0 - PAD_L / 2.0 + 2.0  # keep computed

# Pivot
PIVOT_PIN_DIA = TRIGGER_SPEC.pivot_pin_dia
PIVOT_BUSHING_OD = TRIGGER_SPEC.pivot_bushing_od
PIVOT_BOSS_H = LEVER_WIDTH
PIVOT_X = -LEVER_LENGTH / 2.0 + 3.0  # keep computed

# Internal actuator arm
ARM_LENGTH = TRIGGER_SPEC.arm_length
ARM_THICK = TRIGGER_SPEC.arm_thick
ARM_X = PIVOT_X - ARM_LENGTH / 2.0 - 1.0  # keep computed

# =========================================================================
# MICROSWITCH
# =========================================================================
SWITCH_L = TRIGGER_SPEC.switch_l
SWITCH_W = TRIGGER_SPEC.switch_w
SWITCH_H = TRIGGER_SPEC.switch_h
SWITCH_BUTTON_DIA = TRIGGER_SPEC.switch_button_dia
SWITCH_BUTTON_H = TRIGGER_SPEC.switch_button_h

# =========================================================================
# RETURN SPRING
# =========================================================================
SPRING_OD = TRIGGER_SPEC.spring_od
SPRING_FREE_LENGTH = TRIGGER_SPEC.spring_free_length
SPRING_WIRE_DIA = TRIGGER_SPEC.spring_wire_dia
SPRING_POST_DIA = TRIGGER_SPEC.spring_post_dia

# Total trigger travel
TRIGGER_TRAVEL = TRIGGER_SPEC.travel

# =========================================================================
# MOUNTING
# =========================================================================
M2 = FASTENERS["M2x5_shcs"]


def build() -> cq.Workplane:
    """Build the trigger lever.

    X = along lever length (+ toward finger end)
    Y = across lever width
    Z = perpendicular to lever face (+ = outward/exterior)
    """
    # --- Main lever body ---
    lever = (
        cq.Workplane("XY")
        .box(LEVER_LENGTH, LEVER_WIDTH, LEVER_THICK)
    )

    # Round the finger end
    try:
        lever = lever.edges(">X").fillet(2.0)
    except Exception:
        pass

    # --- Concave finger pad ---
    # Cut a shallow rectangular pocket with rounded floor
    pad_center_x = PAD_OFFSET
    pad_cut = (
        cq.Workplane("XY")
        .box(PAD_L, PAD_W, PAD_DEPTH)
        .translate((pad_center_x, 0, LEVER_THICK / 2.0 - PAD_DEPTH / 2.0))
    )
    lever = lever.cut(pad_cut)

    # --- Finger pad texture (crosshatch grooves) ---
    groove_spacing = 2.0
    groove_depth = 0.15
    groove_w = 0.3
    for i in range(-3, 4):
        gx = pad_center_x + i * groove_spacing
        groove = (
            cq.Workplane("XY")
            .box(groove_w, PAD_W - 1.0, groove_depth)
            .translate((gx, 0, LEVER_THICK / 2.0 - PAD_DEPTH - groove_depth / 2.0))
        )
        lever = lever.cut(groove)

    # --- Pivot boss ---
    pivot_boss = (
        cq.Workplane("XZ")
        .transformed(offset=(0, PIVOT_X, 0))
        .circle(PIVOT_BUSHING_OD / 2.0)
        .extrude(PIVOT_BOSS_H)
        .translate((0, -PIVOT_BOSS_H / 2.0, 0))
    )
    lever = lever.union(pivot_boss)

    # Pivot pin hole through boss
    pivot_hole = (
        cq.Workplane("XZ")
        .transformed(offset=(0, PIVOT_X, 0))
        .circle(PIVOT_PIN_DIA / 2.0)
        .extrude(PIVOT_BOSS_H + 2.0)
        .translate((0, -(PIVOT_BOSS_H / 2.0 + 1.0), 0))
    )
    lever = lever.cut(pivot_hole)

    # --- Internal actuator arm ---
    arm = (
        cq.Workplane("XY")
        .box(ARM_LENGTH, LEVER_WIDTH - 2.0, ARM_THICK)
        .translate((ARM_X, 0, -LEVER_THICK / 2.0 + ARM_THICK / 2.0))
    )
    lever = lever.union(arm)

    # --- Spring post hole ---
    spring_x = PIVOT_X + 3.0
    spring_hole = (
        cq.Workplane("XY")
        .transformed(offset=(spring_x, 0, 0))
        .circle(SPRING_POST_DIA / 2.0)
        .extrude(LEVER_THICK)
        .translate((0, 0, -LEVER_THICK / 2.0))
    )
    lever = lever.cut(spring_hole)

    return lever


def build_pivot_pin() -> cq.Workplane:
    """Build the pivot pin (2mm stainless steel)."""
    pin = (
        cq.Workplane("XY")
        .cylinder(LEVER_WIDTH + 4.0, PIVOT_PIN_DIA / 2.0)
    )
    return pin


def build_microswitch() -> cq.Workplane:
    """Build a placeholder microswitch (6x3x4mm body + 1mm button)."""
    body = (
        cq.Workplane("XY")
        .box(SWITCH_L, SWITCH_W, SWITCH_H)
    )
    button = (
        cq.Workplane("XY")
        .cylinder(SWITCH_BUTTON_H, SWITCH_BUTTON_DIA / 2.0)
        .translate((SWITCH_L / 4.0, 0, SWITCH_H / 2.0 + SWITCH_BUTTON_H / 2.0))
    )
    body = body.union(button)
    return body


def build_return_spring() -> cq.Workplane:
    """Build a placeholder compression spring (simplified hollow cylinder)."""
    spring = (
        cq.Workplane("XY")
        .cylinder(SPRING_FREE_LENGTH, SPRING_OD / 2.0)
    )
    inner = (
        cq.Workplane("XY")
        .cylinder(SPRING_FREE_LENGTH + 0.1,
                  SPRING_OD / 2.0 - SPRING_WIRE_DIA)
    )
    spring = spring.cut(inner)
    return spring


def build_assembly() -> cq.Assembly:
    """Build the complete trigger assembly."""
    assy = cq.Assembly(name="trigger_assembly")

    assy.add(build(), name="trigger_lever",
             loc=cq.Location((0, 0, 0)))

    assy.add(build_pivot_pin(), name="pivot_pin",
             loc=cq.Location((PIVOT_X, 0, 0)))

    assy.add(build_microswitch(), name="microswitch",
             loc=cq.Location((ARM_X - 2.0, 0,
                               -LEVER_THICK / 2.0 - SWITCH_H / 2.0 - 1.0)))

    spring_x = PIVOT_X + 3.0
    assy.add(build_return_spring(), name="return_spring",
             loc=cq.Location((spring_x, 0,
                               -LEVER_THICK / 2.0 - SPRING_FREE_LENGTH / 2.0)))

    return assy


def get_trigger_geometry() -> dict:
    """Return key geometry for assembly positioning."""
    return {
        "lever_length": LEVER_LENGTH,
        "lever_width": LEVER_WIDTH,
        "lever_thick": LEVER_THICK,
        "pivot_x": PIVOT_X,
        "pivot_pin_dia": PIVOT_PIN_DIA,
        "travel_mm": TRIGGER_TRAVEL,
        "pad_size": (PAD_L, PAD_W),
        "switch_size": (SWITCH_L, SWITCH_W, SWITCH_H),
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    solid = build()
    cq.exporters.export(solid, f"{output_dir}/trigger_lever.step")
    cq.exporters.export(solid, f"{output_dir}/trigger_lever.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Trigger lever exported to {output_dir}/")

    sw = build_microswitch()
    cq.exporters.export(sw, f"{output_dir}/trigger_microswitch.step")

    assy = build_assembly()
    cq.exporters.export(assy.toCompound(), f"{output_dir}/trigger_assembly.step")
    print(f"  Trigger assembly exported to {output_dir}/")


if __name__ == "__main__":
    export()
