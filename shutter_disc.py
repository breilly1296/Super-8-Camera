#!/usr/bin/env python3
"""Parametric Super 8 Rotary Shutter Disc — CadQuery Model

Generates a rotary shutter disc with:
  - Adjustable opening angle (default 180°)
  - Central shaft hole with keyway
  - Balance holes on the solid sector
  - Optical sensor flag notch on the outer edge

All dimensions are parameters at the top for easy tweaking.
Exports STEP and STL files.
"""

import math
import cadquery as cq

# ---------------------------------------------------------------------------
# Parameters — adjust these to modify the shutter disc
# ---------------------------------------------------------------------------

# Disc geometry
OUTER_DIAMETER = 30.0       # mm
DISC_THICKNESS = 0.8        # mm (aluminum sheet)
OPENING_ANGLE = 180.0       # degrees — open sector that exposes film

# Shaft hole
SHAFT_HOLE_DIA = 3.0        # mm

# Keyway (cut into shaft hole for alignment)
KEYWAY_WIDTH = 1.0          # mm
KEYWAY_DEPTH = 0.5          # mm (radial depth into bore wall)

# Balance holes on the solid sector
BALANCE_HOLE_DIA = 1.5      # mm
BALANCE_HOLE_COUNT = 2      # number of balance holes
BALANCE_HOLE_RADIUS = 10.0  # mm — radial distance from center

# Optical sensor flag — notch on outer edge
FLAG_WIDTH = 2.0            # mm (arc-length approximation at outer edge)
FLAG_DEPTH = 1.5            # mm (radial depth of notch from outer edge)


# ---------------------------------------------------------------------------
# Derived values
# ---------------------------------------------------------------------------

OUTER_RADIUS = OUTER_DIAMETER / 2.0
SHAFT_RADIUS = SHAFT_HOLE_DIA / 2.0


# ---------------------------------------------------------------------------
# Build the shutter disc
# ---------------------------------------------------------------------------

def build_shutter_disc():
    # --- Full disc ---
    disc = (
        cq.Workplane("XY")
        .cylinder(DISC_THICKNESS, OUTER_RADIUS, centered=(True, True, True))
    )

    # --- Shaft hole ---
    disc = (
        disc
        .faces(">Z")
        .workplane()
        .hole(SHAFT_HOLE_DIA)
    )

    # --- Keyway (flat cut into the shaft bore) ---
    # Position a rectangular cut at the top of the shaft hole, extending
    # KEYWAY_DEPTH into the bore wall.
    keyway_y = SHAFT_RADIUS - KEYWAY_DEPTH / 2.0
    disc = (
        disc
        .faces(">Z")
        .workplane()
        .center(0, keyway_y)
        .rect(KEYWAY_WIDTH, KEYWAY_DEPTH + 0.01)  # slight overcut for clean boolean
        .cutThruAll()
    )

    # --- Open sector cutout (the shutter opening) ---
    # The open sector is centered on the +X axis (0°).
    # We model a pie-slice polygon and cut it through the disc.
    half_angle = math.radians(OPENING_ANGLE / 2.0)
    # Build a fan polygon with enough arc segments for a smooth curve
    arc_steps = max(32, int(OPENING_ANGLE / 2))
    pts = [(0.0, 0.0)]  # center
    for i in range(arc_steps + 1):
        angle = -half_angle + i * (2 * half_angle) / arc_steps
        pts.append((
            (OUTER_RADIUS + 1.0) * math.cos(angle),
            (OUTER_RADIUS + 1.0) * math.sin(angle),
        ))
    pts.append((0.0, 0.0))  # close back to center

    sector_cut = (
        cq.Workplane("XY")
        .polyline(pts)
        .close()
        .extrude(DISC_THICKNESS + 1.0)
        .translate((0, 0, -(DISC_THICKNESS + 1.0) / 2.0))
    )
    disc = disc.cut(sector_cut)

    # --- Balance holes on the solid sector ---
    # The solid sector is centered on the −X axis (180°).
    # Distribute balance holes evenly within the solid sector.
    solid_center_angle = math.pi  # center of solid sector
    if BALANCE_HOLE_COUNT == 1:
        balance_angles = [solid_center_angle]
    else:
        # Spread across the middle portion of the solid sector
        solid_half = math.radians((360.0 - OPENING_ANGLE) / 2.0)
        spread = solid_half * 0.6  # use 60% of the half-angle for spread
        balance_angles = [
            solid_center_angle - spread + 2 * spread * i / (BALANCE_HOLE_COUNT - 1)
            for i in range(BALANCE_HOLE_COUNT)
        ]

    balance_pts = [
        (BALANCE_HOLE_RADIUS * math.cos(a), BALANCE_HOLE_RADIUS * math.sin(a))
        for a in balance_angles
    ]

    disc = (
        disc
        .faces(">Z")
        .workplane()
        .pushPoints(balance_pts)
        .hole(BALANCE_HOLE_DIA)
    )

    # --- Optical sensor flag notch ---
    # A small rectangular notch on the outer edge of the solid sector,
    # at the 180° position (−X side), for an optical interrupter sensor.
    flag_half_angle = math.atan2(FLAG_WIDTH / 2.0, OUTER_RADIUS)
    notch_center_r = OUTER_RADIUS - FLAG_DEPTH / 2.0

    notch = (
        cq.Workplane("XY")
        .rect(FLAG_DEPTH, FLAG_WIDTH)
        .extrude(DISC_THICKNESS + 1.0)
        .translate((-notch_center_r, 0, -(DISC_THICKNESS + 1.0) / 2.0))
    )
    disc = disc.cut(notch)

    return disc


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_disc(disc, step_path="shutter_disc.step", stl_path="shutter_disc.stl"):
    cq.exporters.export(disc, step_path)
    print(f"  Exported STEP: {step_path}")

    cq.exporters.export(disc, stl_path, tolerance=0.01, angularTolerance=0.1)
    print(f"  Exported STL:  {stl_path}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    sep = "=" * 60
    print(sep)
    print("  SUPER 8 ROTARY SHUTTER DISC — PARAMETRIC MODEL")
    print(sep)
    print()
    print(f"  Outer diameter:  {OUTER_DIAMETER} mm")
    print(f"  Thickness:       {DISC_THICKNESS} mm")
    print(f"  Opening angle:   {OPENING_ANGLE}°")
    print(f"  Shaft hole:      {SHAFT_HOLE_DIA} mm dia")
    print(f"  Keyway:          {KEYWAY_WIDTH} mm wide x "
          f"{KEYWAY_DEPTH} mm deep")
    print(f"  Balance holes:   {BALANCE_HOLE_COUNT} x {BALANCE_HOLE_DIA} mm "
          f"at r={BALANCE_HOLE_RADIUS} mm")
    print(f"  Sensor flag:     {FLAG_WIDTH} mm wide x "
          f"{FLAG_DEPTH} mm deep notch")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print_summary()
    disc = build_shutter_disc()
    export_disc(disc)
    print()
    print("  " + "=" * 60)


if __name__ == "__main__":
    main()
