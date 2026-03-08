"""Bottom plate — camera base with tripod mount, battery door cutout, strap lug.

Features:
  - 1/4"-20 tripod mount (helicoil insert, positioned under center of gravity)
  - Battery door cutout (rectangular opening for the battery compartment)
  - Strap lug on the left side
  - 4× M2.5 screw holes to attach to body halves
"""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS, SCULPT
from super8cam.parts.interfaces import make_snap_pocket

# =========================================================================
# PLATE DIMENSIONS
# =========================================================================
WALL = CAMERA.wall_thickness
BODY_L = CAMERA.body_length
BODY_D = CAMERA.body_depth
FILLET = CAMERA.body_fillet

PLATE_L = BODY_L - 2.0
PLATE_D = BODY_D - 2.0
PLATE_THICK = WALL                    # 2.5 mm

# =========================================================================
# TRIPOD MOUNT
# =========================================================================
# Positioned slightly right of center (under the approximate CG,
# accounting for the cartridge weight on the right side)
TRIPOD_X = 5.0                         # mm — slightly right of center
TRIPOD_Y = 0.0                         # centered front-to-back
TRIPOD_BOSS_DIA = CAMERA.tripod_boss_dia    # 14 mm
TRIPOD_BOSS_DEPTH = CAMERA.tripod_boss_depth  # 8 mm
QUARTER20 = FASTENERS["quarter20x6"]

# =========================================================================
# BATTERY DOOR CUTOUT
# =========================================================================
BATT_DOOR_L = CAMERA.batt_pocket_l + 4.0   # 62 mm — door slightly larger
BATT_DOOR_W = CAMERA.batt_pocket_w + 4.0   # 34 mm
BATT_X = 20.0                               # right of center (under cartridge area)
BATT_Y = 0.0

# =========================================================================
# MOUNTING
# =========================================================================
M25 = FASTENERS["M2_5x6_shcs"]
PLATE_MOUNT_POSITIONS = [
    (-PLATE_L / 2.0 + 8.0, -PLATE_D / 2.0 + 8.0),
    (-PLATE_L / 2.0 + 8.0,  PLATE_D / 2.0 - 8.0),
    ( PLATE_L / 2.0 - 8.0, -PLATE_D / 2.0 + 8.0),
    ( PLATE_L / 2.0 - 8.0,  PLATE_D / 2.0 - 8.0),
]

# Strap lug on left side
STRAP_LUG_X = -PLATE_L / 2.0 + 5.0
STRAP_HOLE_DIA = 3.0
STRAP_LUG_W = 8.0
STRAP_LUG_H = 6.0


def build() -> cq.Workplane:
    """Build the bottom plate.

    Lies in the XY plane at the bottom of the body (Z = -BODY_H/2).
    """
    # --- Base plate ---
    plate = (
        cq.Workplane("XY")
        .box(PLATE_L, PLATE_D, PLATE_THICK)
    )
    try:
        plate = plate.edges("|Z").fillet(FILLET - 1.0)
    except Exception:
        pass

    # --- Tripod mount boss (raised pad on bottom surface) ---
    boss = (
        cq.Workplane("XY")
        .cylinder(TRIPOD_BOSS_DEPTH, TRIPOD_BOSS_DIA / 2.0)
        .translate((TRIPOD_X, TRIPOD_Y,
                    -(PLATE_THICK / 2.0 + TRIPOD_BOSS_DEPTH / 2.0)))
    )
    plate = plate.union(boss)

    # 1/4"-20 threaded hole through boss and plate
    plate = (
        plate.faces("<Z").workplane()
        .center(TRIPOD_X, TRIPOD_Y)
        .hole(QUARTER20.tap_hole, TRIPOD_BOSS_DEPTH + PLATE_THICK)
    )

    # --- Battery door cutout ---
    batt_cut = (
        cq.Workplane("XY")
        .rect(BATT_DOOR_L, BATT_DOOR_W)
        .extrude(PLATE_THICK + 0.2)
        .translate((BATT_X, BATT_Y, -(PLATE_THICK + 0.2) / 2.0))
    )
    plate = plate.cut(batt_cut)

    # --- Light trap ledge around battery opening ---
    # Step for the battery door to overlap
    trap_depth = 1.0
    trap_overlap = 2.0
    outer_ledge = (
        cq.Workplane("XY")
        .rect(BATT_DOOR_L + 2 * trap_overlap, BATT_DOOR_W + 2 * trap_overlap)
        .extrude(trap_depth)
        .translate((BATT_X, BATT_Y, -PLATE_THICK / 2.0 + trap_depth / 2.0))
    )
    inner_ledge = (
        cq.Workplane("XY")
        .rect(BATT_DOOR_L, BATT_DOOR_W)
        .extrude(trap_depth + 0.1)
        .translate((BATT_X, BATT_Y, -PLATE_THICK / 2.0 + trap_depth / 2.0))
    )
    ledge = outer_ledge.cut(inner_ledge)
    plate = plate.cut(ledge)

    # --- 2× Snap pockets around battery door opening ---
    # Receive battery door snap latches at ±BATT_DOOR_L/4.0
    for sign in [-1, 1]:
        pocket = (
            make_snap_pocket()
            .translate((BATT_X + sign * BATT_DOOR_L / 4.0,
                        BATT_Y - BATT_DOOR_W / 2.0,
                        PLATE_THICK / 2.0))
        )
        plate = plate.cut(pocket)

    # --- Plate mounting holes (4× M2.5 clearance + counterbores) ---
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints(PLATE_MOUNT_POSITIONS)
        .hole(M25.clearance_hole, PLATE_THICK)
    )
    for px, py in PLATE_MOUNT_POSITIONS:
        cbore = (
            cq.Workplane("XY")
            .transformed(offset=(px, py, -PLATE_THICK / 2.0))
            .circle(M25.head_dia / 2.0 + 0.2)
            .extrude(M25.head_height + 0.3)
        )
        plate = plate.cut(cbore)

    # --- Pistol grip pass-through cutout ---
    # Rectangular opening where the grip (integral to body_right) passes through
    # the bottom plate. X range [grip_x_start, grip_x_start + grip_width].
    grip_cut_x_start = SCULPT.grip_x_start       # 45 mm
    grip_cut_x_end = min(grip_cut_x_start + SCULPT.grip_width, PLATE_L / 2.0)  # clamp to plate edge
    grip_cut_cx = (grip_cut_x_start + grip_cut_x_end) / 2.0
    grip_cut_len = grip_cut_x_end - grip_cut_x_start
    grip_cutout = (
        cq.Workplane("XY")
        .box(grip_cut_len, PLATE_D, PLATE_THICK + 2.0)
        .translate((grip_cut_cx, 0, 0))
    )
    plate = plate.cut(grip_cutout)

    # --- Strap lug on left side ---
    lug = (
        cq.Workplane("XY")
        .box(STRAP_LUG_W, 4.0, STRAP_LUG_H)
        .translate((STRAP_LUG_X, 0,
                    -(PLATE_THICK / 2.0 + STRAP_LUG_H / 2.0)))
    )
    plate = plate.union(lug)

    # Strap hole
    lug_hole = (
        cq.Workplane("XZ")
        .transformed(offset=(STRAP_LUG_X, 0,
                             -(PLATE_THICK / 2.0 + STRAP_LUG_H / 2.0)))
        .circle(STRAP_HOLE_DIA / 2.0)
        .extrude(6.0)
        .translate((0, -3.0, 0))
    )
    plate = plate.cut(lug_hole)

    return plate


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/bottom_plate.step")
    cq.exporters.export(solid, f"{output_dir}/bottom_plate.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Bottom plate exported to {output_dir}/")


if __name__ == "__main__":
    export()
