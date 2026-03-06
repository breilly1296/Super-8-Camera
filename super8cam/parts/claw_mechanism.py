"""Claw mechanism — the pulldown claw arm that advances film one frame per revolution.

The claw arm is a precision hardened-steel lever that engages a film perforation,
pulls the film down exactly one perforation pitch (4.234 mm), then retracts.
This cycle happens 18 or 24 times per second.

The arm is guided by two parallel pins allowing vertical-only travel.
Horizontal engage/retract motion comes from the secondary eccentric via
a connecting link (modelled in cam_follower.py).

Material: 440C stainless steel, HRC 58, for wear resistance at the tip.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, MATERIALS, MATERIAL_USAGE,
)
from super8cam.parts.cam_follower import (
    FOLLOWER_PIN_DIA, GUIDE_PIN_DIA, GUIDE_PIN_SPACING,
    LINK_BORE_CLAW, cam_profile_full,
)
from super8cam.parts.film_gate import (
    GATE_W, GATE_THICK, CHANNEL_W, PERF_SLOT_W,
    CLAW_SLOT_W, CLAW_SLOT_H, get_film_plane_origin,
)

# Claw arm material — 440C stainless, hardened
# Not in MATERIAL_USAGE so we define inline
CLAW_MATERIAL_NAME = "440C Stainless Steel, HRC 58"

# =========================================================================
# CLAW ARM DIMENSIONS
# =========================================================================
ARM_LENGTH = 15.0           # mm — pivot end to tip end
ARM_W = 3.0                 # mm — arm width
ARM_THICK = 1.0             # mm — arm thickness

# Claw tip (the tiny hook that engages the perforation)
TIP_W = 0.5                 # mm — width (must fit inside perf: 1.143 mm wide)
TIP_H = 0.3                 # mm — thickness (vertical dimension)
TIP_ENGAGE_DEPTH = CAMERA.claw_engage_depth  # 0.5 mm into perforation
TIP_RADIUS = 0.1            # mm — fillet on tip to avoid tearing film

# Pivot pin at the follower end
PIVOT_PIN_DIA = 1.5         # mm
PIVOT_PIN_LENGTH = 5.0      # mm — protrudes through arm + link

# Guide bushings in the arm (ride on the vertical guide pins)
GUIDE_BUSH_DIA = GUIDE_PIN_DIA + 0.05  # mm — 1.55 mm clearance bore
GUIDE_BUSH_LENGTH = ARM_THICK           # through arm thickness

# Follower pin hole (carries the pin that rides in the cam groove)
FOLLOWER_HOLE_DIA = FOLLOWER_PIN_DIA + 0.02  # mm — light press fit

# E-clip groove on pivot pin
ECLIP_GROOVE_DIA = PIVOT_PIN_DIA - 0.3  # mm
ECLIP_GROOVE_W = 0.4                     # mm


def build() -> cq.Workplane:
    """Build the complete claw arm with tip, guide holes, and follower mount.

    Coordinate system:
      X along arm length (+ toward tip)
      Y across arm width
      Z arm thickness direction

    Origin at arm center.  Tip extends in +X, pivot end in -X.
    """
    # --- Main arm body ---
    arm = (
        cq.Workplane("XY")
        .box(ARM_LENGTH, ARM_W, ARM_THICK)
        .edges("|Z").fillet(0.3)
    )

    # --- Claw tip ---
    # A small hook extending from the +X end of the arm.
    # The tip projects in +X (toward the film) and is narrower than the arm.
    tip_length = TIP_ENGAGE_DEPTH + 1.0  # 1mm base + engage depth
    tip = (
        cq.Workplane("XY")
        .box(tip_length, TIP_W, TIP_H)
        .edges("|Z").fillet(min(TIP_RADIUS, TIP_W / 2.0 - 0.01))
        .translate((
            ARM_LENGTH / 2.0 + tip_length / 2.0,
            0,
            -(ARM_THICK - TIP_H) / 2.0,  # tip at bottom of arm
        ))
    )
    arm = arm.union(tip)

    # --- Pivot pin hole (connects to cam follower/link) ---
    # At the -X end of the arm
    pivot_x = -ARM_LENGTH / 2.0 + 2.0  # 2mm from end
    arm = (
        arm.faces(">Z").workplane()
        .center(pivot_x, 0)
        .hole(PIVOT_PIN_DIA, ARM_THICK)
    )

    # --- Follower pin hole (for pin that rides in cam groove) ---
    # Positioned between pivot and center
    follower_x = -ARM_LENGTH / 2.0 + 5.0  # 5mm from pivot end
    arm = (
        arm.faces(">Z").workplane()
        .center(follower_x, 0)
        .hole(FOLLOWER_HOLE_DIA, ARM_THICK)
    )

    # --- Guide pin bushings (two holes for the vertical guide pins) ---
    # Spaced GUIDE_PIN_SPACING apart, centered on the arm
    for x_off in [-GUIDE_PIN_SPACING / 2.0, GUIDE_PIN_SPACING / 2.0]:
        # Only add guide holes that fit within the arm length
        if abs(x_off) < ARM_LENGTH / 2.0 - 1.0:
            arm = (
                arm.faces(">Z").workplane()
                .center(x_off, 0)
                .hole(GUIDE_BUSH_DIA, ARM_THICK)
            )

    return arm


def build_pivot_pin() -> cq.Workplane:
    """Build the pivot pin that connects the claw arm to the connecting link."""
    pin = (
        cq.Workplane("XY")
        .cylinder(PIVOT_PIN_LENGTH, PIVOT_PIN_DIA / 2.0)
    )

    # E-clip groove near each end
    for z_sign in [1, -1]:
        groove_z = z_sign * (PIVOT_PIN_LENGTH / 2.0 - 1.0)
        groove = (
            cq.Workplane("XY")
            .cylinder(ECLIP_GROOVE_W, PIVOT_PIN_DIA / 2.0)
            .cut(
                cq.Workplane("XY")
                .cylinder(ECLIP_GROOVE_W + 0.1, ECLIP_GROOVE_DIA / 2.0)
            )
            .translate((0, 0, groove_z))
        )
        pin = pin.cut(groove)

    return pin


def get_claw_tip_position(shaft_angle_deg: float) -> tuple:
    """Return the (x, y) position of the claw tip for a given shaft angle.

    Uses the cam profile from cam_follower module.

    Returns:
        (x_mm, y_mm) — claw tip position relative to its home (top, retracted).
    """
    profile = cam_profile_full(360)
    idx = int(shaft_angle_deg) % 360
    return (profile["x_mm"][idx], profile["y_mm"][idx])


def build_assembly(shaft_angle_deg: float = 0.0) -> dict:
    """Return claw mechanism parts positioned for a given shaft angle.

    Parts are positioned relative to the film gate's perforation slot.
    The claw tip aligns with the perforation clearance slot in the gate.

    Returns:
        Dict of {name: cq.Workplane}.
    """
    parts = {}

    # Get current claw position from cam profile
    tip_x, tip_y = get_claw_tip_position(shaft_angle_deg)

    # Film gate reference: perforation slot is at camera-left of channel
    film_plane = get_film_plane_origin()

    # Claw arm — translate so tip aligns with perf slot in gate
    arm = build()
    # The tip extends in +X from the arm.
    # Position the arm so the tip enters the gate's claw access slot.
    # Gate perf slot center X = -(CHANNEL_W/2 + PERF_SLOT_W/2)
    perf_slot_x = -(CHANNEL_W / 2.0 + PERF_SLOT_W / 2.0)

    arm = arm.translate((
        perf_slot_x - ARM_LENGTH / 2.0 - TIP_ENGAGE_DEPTH,  # arm body behind gate
        tip_y,                                                # vertical from cam
        film_plane[2] - ARM_THICK / 2.0 - FILM.thickness,   # behind film
    ))
    parts["claw_arm"] = arm

    # Pivot pin
    pivot = build_pivot_pin()
    pivot_x_local = -ARM_LENGTH / 2.0 + 2.0
    pivot = pivot.translate((
        perf_slot_x - ARM_LENGTH / 2.0 - TIP_ENGAGE_DEPTH + pivot_x_local,
        tip_y,
        film_plane[2] - ARM_THICK / 2.0 - FILM.thickness,
    ))
    parts["pivot_pin"] = pivot

    return parts


def export(output_dir: str = "export"):
    """Export claw mechanism parts as STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    exports = {
        "claw_arm": build,
        "pivot_pin": build_pivot_pin,
    }

    for name, builder in exports.items():
        solid = builder()
        cq.exporters.export(solid, f"{output_dir}/{name}.step")
        cq.exporters.export(solid, f"{output_dir}/{name}.stl",
                            tolerance=0.005, angularTolerance=0.05)
        print(f"  {name:25s} STEP + STL")


if __name__ == "__main__":
    export()
