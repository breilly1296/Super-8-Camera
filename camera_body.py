#!/usr/bin/env python3
"""Parametric Super 8 Camera Body Shell — CadQuery Model

A simplified bounding-volume shell for layout purposes.
Features:
  - Hollow box with uniform wall thickness
  - C-mount lens opening on front face
  - Cartridge loading door cutout on right side
  - Battery compartment pocket on bottom
  - 1/4-20 tripod mount boss on bottom
  - M2 standoff posts inside for PCB mounting

All dimensions are parameters at the top for easy tweaking.
Exports STEP (and optionally STL).
"""

import cadquery as cq

# ---------------------------------------------------------------------------
# Parameters — adjust these to modify the camera body
# ---------------------------------------------------------------------------

# Outer shell
BODY_LENGTH = 150.0       # mm (X — left/right, lens faces −Y)
BODY_HEIGHT = 90.0        # mm (Z — vertical)
BODY_DEPTH = 55.0         # mm (Y — front/back)
WALL_THICKNESS = 3.0      # mm
SHELL_FILLET = 5.0        # mm — outer edge fillet for ergonomics

# C-mount lens opening (front face, −Y)
LENS_DIA = 25.4           # mm (1 inch, C-mount standard)
LENS_OFFSET_X = -25.0     # mm from center (negative = left when facing camera)
LENS_OFFSET_Z = 0.0       # mm from center (0 = vertically centered)
LENS_BOSS_DIA = 32.0      # mm — raised boss around lens opening
LENS_BOSS_HEIGHT = 4.0    # mm — protrusion from front face

# Cartridge loading door (right side, +X face)
DOOR_WIDTH = 60.0         # mm (along Y axis on the +X face)
DOOR_HEIGHT = 50.0        # mm (along Z axis)
DOOR_OFFSET_Y = 0.0       # mm from center of +X face
DOOR_OFFSET_Z = 5.0       # mm above center (shift up slightly)

# Battery compartment pocket (bottom face, −Z, external)
BATT_LENGTH = 60.0        # mm (X)
BATT_WIDTH = 30.0         # mm (Y)
BATT_DEPTH = 15.0         # mm (into bottom, downward pocket)
BATT_OFFSET_X = 20.0      # mm from center (toward right side)
BATT_WALL = 1.5           # mm — pocket wall thickness

# Tripod mount boss (bottom face, −Z)
TRIPOD_BOSS_DIA = 14.0    # mm — boss outer diameter
TRIPOD_BOSS_HEIGHT = 5.0  # mm — boss protrusion below bottom
TRIPOD_HOLE_DIA = 6.35    # mm — 1/4-20 UNC clearance (0.250")
TRIPOD_HOLE_DEPTH = 10.0  # mm — threaded insert depth
TRIPOD_OFFSET_X = 0.0     # mm from center
TRIPOD_OFFSET_Y = 0.0     # mm from center

# PCB standoff posts (inside, on bottom inner wall)
PCB_RECT_X = 50.0         # mm — post rectangle width
PCB_RECT_Y = 30.0         # mm — post rectangle depth
PCB_POST_DIA = 5.0        # mm — standoff outer diameter
PCB_POST_HOLE_DIA = 2.2   # mm — M2 clearance hole
PCB_POST_HEIGHT = 8.0     # mm — standoff height above inner floor
PCB_OFFSET_X = -20.0      # mm — shift post group left (near lens side)
PCB_OFFSET_Y = 0.0        # mm from center


# ---------------------------------------------------------------------------
# Build the camera body
# ---------------------------------------------------------------------------

def build_camera_body():
    half_x = BODY_LENGTH / 2.0
    half_y = BODY_DEPTH / 2.0
    half_z = BODY_HEIGHT / 2.0

    # --- Outer shell (centered at origin) ---
    outer = (
        cq.Workplane("XY")
        .box(BODY_LENGTH, BODY_DEPTH, BODY_HEIGHT)
        .edges()
        .fillet(SHELL_FILLET)
    )

    # --- Hollow out the interior ---
    inner = (
        cq.Workplane("XY")
        .box(
            BODY_LENGTH - 2 * WALL_THICKNESS,
            BODY_DEPTH - 2 * WALL_THICKNESS,
            BODY_HEIGHT - 2 * WALL_THICKNESS,
        )
    )
    body = outer.cut(inner)

    # --- C-mount lens opening (front face = −Y) ---
    # Raised boss + through-hole
    boss = (
        cq.Workplane("XY")
        .cylinder(LENS_BOSS_HEIGHT, LENS_BOSS_DIA / 2.0)
        # Rotate so cylinder axis points along Y
        .rotateAboutCenter((1, 0, 0), 90)
        .translate((
            LENS_OFFSET_X,
            -(half_y + LENS_BOSS_HEIGHT / 2.0),
            LENS_OFFSET_Z,
        ))
    )
    body = body.union(boss)

    # Lens bore through boss + front wall
    lens_bore = (
        cq.Workplane("XY")
        .cylinder(WALL_THICKNESS + LENS_BOSS_HEIGHT + 2.0, LENS_DIA / 2.0)
        .rotateAboutCenter((1, 0, 0), 90)
        .translate((
            LENS_OFFSET_X,
            -(half_y - WALL_THICKNESS / 2.0),
            LENS_OFFSET_Z,
        ))
    )
    body = body.cut(lens_bore)

    # --- Cartridge loading door cutout (right side = +X face) ---
    door_cut = (
        cq.Workplane("XY")
        .box(WALL_THICKNESS + 2.0, DOOR_WIDTH, DOOR_HEIGHT)
        .translate((
            half_x,
            DOOR_OFFSET_Y,
            DOOR_OFFSET_Z,
        ))
    )
    body = body.cut(door_cut)

    # --- Battery compartment pocket (bottom = −Z, external pocket) ---
    # Outer pocket box (extends downward)
    batt_outer = (
        cq.Workplane("XY")
        .box(BATT_LENGTH + 2 * BATT_WALL, BATT_WIDTH + 2 * BATT_WALL, BATT_DEPTH)
        .translate((
            BATT_OFFSET_X,
            0,
            -(half_z + BATT_DEPTH / 2.0),
        ))
    )
    body = body.union(batt_outer)

    # Hollow out the pocket interior
    batt_inner = (
        cq.Workplane("XY")
        .box(BATT_LENGTH, BATT_WIDTH, BATT_DEPTH + WALL_THICKNESS + 1.0)
        .translate((
            BATT_OFFSET_X,
            0,
            -(half_z + BATT_DEPTH / 2.0 - 0.5),
        ))
    )
    body = body.cut(batt_inner)

    # --- Tripod mount boss (bottom = −Z) ---
    tripod_boss = (
        cq.Workplane("XY")
        .cylinder(TRIPOD_BOSS_HEIGHT, TRIPOD_BOSS_DIA / 2.0)
        .translate((
            TRIPOD_OFFSET_X,
            TRIPOD_OFFSET_Y,
            -(half_z + TRIPOD_BOSS_HEIGHT / 2.0),
        ))
    )
    body = body.union(tripod_boss)

    # 1/4-20 threaded hole (modeled as a plain bore for the insert)
    tripod_hole = (
        cq.Workplane("XY")
        .cylinder(TRIPOD_HOLE_DEPTH, TRIPOD_HOLE_DIA / 2.0)
        .translate((
            TRIPOD_OFFSET_X,
            TRIPOD_OFFSET_Y,
            -(half_z + TRIPOD_BOSS_HEIGHT - TRIPOD_HOLE_DEPTH / 2.0),
        ))
    )
    body = body.cut(tripod_hole)

    # --- PCB standoff posts (inside, on bottom inner wall) ---
    inner_floor_z = -(half_z - WALL_THICKNESS)
    post_top_z = inner_floor_z + PCB_POST_HEIGHT / 2.0

    post_positions = [
        (PCB_OFFSET_X - PCB_RECT_X / 2.0, PCB_OFFSET_Y - PCB_RECT_Y / 2.0),
        (PCB_OFFSET_X + PCB_RECT_X / 2.0, PCB_OFFSET_Y - PCB_RECT_Y / 2.0),
        (PCB_OFFSET_X + PCB_RECT_X / 2.0, PCB_OFFSET_Y + PCB_RECT_Y / 2.0),
        (PCB_OFFSET_X - PCB_RECT_X / 2.0, PCB_OFFSET_Y + PCB_RECT_Y / 2.0),
    ]

    for px, py in post_positions:
        post = (
            cq.Workplane("XY")
            .cylinder(PCB_POST_HEIGHT, PCB_POST_DIA / 2.0)
            .translate((px, py, post_top_z))
        )
        body = body.union(post)

        hole = (
            cq.Workplane("XY")
            .cylinder(PCB_POST_HEIGHT + 2.0, PCB_POST_HOLE_DIA / 2.0)
            .translate((px, py, post_top_z))
        )
        body = body.cut(hole)

    return body


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_body(body, step_path="camera_body.step", stl_path="camera_body.stl"):
    cq.exporters.export(body, step_path)
    print(f"  Exported STEP: {step_path}")

    cq.exporters.export(body, stl_path, tolerance=0.02, angularTolerance=0.2)
    print(f"  Exported STL:  {stl_path}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    sep = "=" * 60
    print(sep)
    print("  SUPER 8 CAMERA BODY SHELL — PARAMETRIC MODEL")
    print(sep)
    print()
    print(f"  Outer dims:       {BODY_LENGTH} x {BODY_DEPTH} x "
          f"{BODY_HEIGHT} mm")
    print(f"  Wall thickness:   {WALL_THICKNESS} mm")
    print(f"  Shell fillet:     {SHELL_FILLET} mm")
    print()
    print(f"  Lens opening:     {LENS_DIA} mm (C-mount)")
    print(f"    Boss:           {LENS_BOSS_DIA} mm dia x "
          f"{LENS_BOSS_HEIGHT} mm protrusion")
    print(f"    Position:       X={LENS_OFFSET_X} Z={LENS_OFFSET_Z} "
          f"on front face")
    print()
    print(f"  Loading door:     {DOOR_WIDTH} x {DOOR_HEIGHT} mm "
          f"on right side")
    print()
    print(f"  Battery pocket:   {BATT_LENGTH} x {BATT_WIDTH} x "
          f"{BATT_DEPTH} mm (4xAA)")
    print(f"    Offset:         X={BATT_OFFSET_X} mm from center")
    print()
    print(f"  Tripod boss:      {TRIPOD_BOSS_DIA} mm dia, "
          f"1/4-20 bore ({TRIPOD_HOLE_DIA} mm)")
    print()
    print(f"  PCB standoffs:    4 posts, M2, "
          f"{PCB_RECT_X} x {PCB_RECT_Y} mm rect")
    print(f"    Post:           {PCB_POST_DIA} mm dia x "
          f"{PCB_POST_HEIGHT} mm tall")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print_summary()
    body = build_camera_body()
    export_body(body)
    print()
    print("  " + "=" * 60)


if __name__ == "__main__":
    main()
