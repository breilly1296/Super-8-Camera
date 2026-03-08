"""Body right half — right side of the camera shell (cartridge/trigger side).

Mates with the left half along the X=0 plane with 0.1mm clearance.

Key internal features on the right side:
  - Cartridge receiver pocket (the dominant internal feature)
  - Film channel and guide roller mount points
  - Cartridge loading door opening (right face, ~60×50mm)
  - Trigger button hole and mechanism mount
  - Right half of lens mount boss
  - Right portion of battery compartment

Material: 6061-T6 aluminum, black anodize Type II.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    CAMERA, CMOUNT, CARTRIDGE, FASTENERS, BEARINGS,
)
from super8cam.parts.interfaces import (
    make_dovetail_rail, make_snap_pocket,
    DOVETAIL_DEPTH, M3_TAP_DIA,
)

# =========================================================================
# BODY ENVELOPE (mirrors body_left.py)
# =========================================================================
WALL = CAMERA.wall_thickness          # 2.5 mm
BODY_L = CAMERA.body_length           # 148 mm
BODY_H = CAMERA.body_height           # 88 mm
BODY_D = CAMERA.body_depth            # 52 mm
FILLET = CAMERA.body_fillet            # 4 mm

HALF_L = BODY_L / 2.0                 # 74 mm
SPLIT_CLEARANCE = 0.1                  # mm

# =========================================================================
# INTERNAL POSITIONS
# =========================================================================
# Main shaft bearing housing (right side bearing)
SHAFT_Z = 8.0
BRG = BEARINGS["main_shaft"]
BRG_BORE_DIA = BRG.od + 0.05

# Cartridge pocket: dominates the right interior
# Pocket is positioned so cartridge film exit aligns with film gate
CART_X = 25.0                          # mm right of center
CART_Y = 5.0                           # slightly behind optical axis
CART_Z = 5.0                           # slightly above center

# Cartridge door opening on the right face (+X)
CART_DOOR_W = CAMERA.cart_door_w       # 60 mm
CART_DOOR_H = CAMERA.cart_door_h       # 50 mm

# Trigger position: right side, upper area, where index finger falls
TRIGGER_X = HALF_L - WALL - 5.0       # near right edge
TRIGGER_Z = BODY_H / 2.0 - 20.0       # 20mm below top
TRIGGER_Y = -BODY_D / 4.0             # front quarter

# Trigger button hole diameter
TRIGGER_HOLE_DIA = 8.0                 # mm — finger pad clearance

# Film channel roller mount points
ROLLER_MOUNT_X = 0.0                   # at split line
ROLLER_MOUNT_Z_ENTRY = 18.5           # above gate (entry roller)
ROLLER_MOUNT_Z_EXIT = -18.5           # below gate (exit roller)

# Assembly screws (clearance holes matching left side tapped holes)
M25 = FASTENERS["M2_5x6_shcs"]
SPLIT_SCREW_POSITIONS = [
    (0, -BODY_H / 2.0 + 10.0),
    (0, 0.0),
    (0, BODY_H / 2.0 - 10.0),
    (-BODY_D / 4.0, -BODY_H / 2.0 + 10.0),
    (-BODY_D / 4.0, BODY_H / 2.0 - 10.0),
]

# Lens mount (right portion, only if it extends past centerline)
LENS_X = CAMERA.lens_mount_offset_x   # -18mm (on left side, so minimal right contribution)


def build() -> cq.Workplane:
    """Build the right body half-shell.

    Shell extends from X=0 (split line) to X=+HALF_L (right edge).
    """
    # --- Outer shell (right half) ---
    shell = (
        cq.Workplane("XY")
        .box(HALF_L - SPLIT_CLEARANCE / 2.0, BODY_D, BODY_H)
        .translate(((HALF_L - SPLIT_CLEARANCE / 2.0) / 2.0, 0, 0))
    )

    try:
        shell = shell.edges("|X").fillet(FILLET)
    except Exception:
        pass

    # --- Hollow interior ---
    inner_l = HALF_L - WALL - SPLIT_CLEARANCE / 2.0
    inner = (
        cq.Workplane("XY")
        .box(inner_l,
             BODY_D - 2 * WALL,
             BODY_H - 2 * WALL)
        .translate(((inner_l / 2.0 + WALL / 2.0), 0, 0))
    )
    shell = shell.cut(inner)

    # --- Cartridge loading door opening (right face) ---
    door_opening = (
        cq.Workplane("YZ")
        .rect(CART_DOOR_H, CART_DOOR_W)
        .extrude(WALL + 1.0)
        .translate((HALF_L - WALL, 0, CART_Z))
    )
    shell = shell.cut(door_opening)

    # --- Light trap ledge around door opening ---
    # A 2mm step around the opening for the door to overlap
    trap_depth = 1.5  # mm step depth
    trap_width = 2.0  # mm overlap
    outer_trap = (
        cq.Workplane("YZ")
        .rect(CART_DOOR_H + 2 * trap_width, CART_DOOR_W + 2 * trap_width)
        .extrude(trap_depth)
        .translate((HALF_L - WALL - trap_depth, 0, CART_Z))
    )
    inner_trap = (
        cq.Workplane("YZ")
        .rect(CART_DOOR_H, CART_DOOR_W)
        .extrude(trap_depth + 0.1)
        .translate((HALF_L - WALL - trap_depth - 0.05, 0, CART_Z))
    )
    trap = outer_trap.cut(inner_trap)
    shell = shell.cut(trap)

    # --- Cartridge receiver pocket ---
    # Large pocket for the Kodak Super 8 cartridge (68×63×21.5mm)
    pocket_l = CARTRIDGE.length + 5.0   # 72mm (+2mm each side)
    pocket_w = CARTRIDGE.width + 5.0    # 67mm (+2mm each side)
    pocket_d = CARTRIDGE.depth + 4.5    # 25.5mm (+2mm each side)
    cart_pocket = (
        cq.Workplane("XY")
        .box(pocket_l, pocket_d, pocket_w)
        .translate((CART_X, CART_Y, CART_Z))
    )
    shell = shell.cut(cart_pocket)

    # --- Film exit/entry slots through interior wall toward gate ---
    film_slot = (
        cq.Workplane("XY")
        .box(CART_X - 5.0, CARTRIDGE.exit_slot_h + 1.0,
             CARTRIDGE.exit_slot_w + 2.0)
        .translate((CART_X / 2.0, CART_Y, 0))
    )
    shell = shell.cut(film_slot)

    # --- Main shaft bearing housing (right side) ---
    brg_boss = (
        cq.Workplane("YZ")
        .transformed(offset=(0, SHAFT_Z, 0))
        .circle(BRG_BORE_DIA / 2.0 + 2.0)
        .extrude(8.0)
        .translate((WALL, 0, 0))
    )
    shell = shell.union(brg_boss)

    brg_hole = (
        cq.Workplane("YZ")
        .transformed(offset=(0, SHAFT_Z, 0))
        .circle(BRG_BORE_DIA / 2.0)
        .extrude(BRG.width + 1.0)
        .translate((WALL, 0, 0))
    )
    shell = shell.cut(brg_hole)

    # --- Trigger button hole ---
    trigger_hole = (
        cq.Workplane("YZ")
        .transformed(offset=(0, TRIGGER_Z, TRIGGER_Y))
        .circle(TRIGGER_HOLE_DIA / 2.0)
        .extrude(WALL + 1.0)
        .translate((HALF_L - WALL, 0, 0))
    )
    shell = shell.cut(trigger_hole)

    # --- Trigger mechanism mount boss (internal) ---
    trigger_boss = (
        cq.Workplane("XY")
        .box(8.0, 8.0, 6.0)
        .translate((TRIGGER_X - 8.0, TRIGGER_Y, TRIGGER_Z))
    )
    shell = shell.union(trigger_boss)

    # M2 tapped hole for trigger pivot pin
    m2 = FASTENERS["M2x5_shcs"]
    trigger_pivot = (
        cq.Workplane("XY")
        .transformed(offset=(TRIGGER_X - 8.0, TRIGGER_Y, TRIGGER_Z))
        .circle(m2.tap_hole / 2.0)
        .extrude(8.0)
        .translate((0, 0, -4.0))
    )
    shell = shell.cut(trigger_pivot)

    # --- Guide roller mount points (M2 bosses) ---
    m2 = FASTENERS["M2x5_shcs"]
    for rz in [ROLLER_MOUNT_Z_ENTRY, ROLLER_MOUNT_Z_EXIT]:
        roller_boss = (
            cq.Workplane("XY")
            .cylinder(4.0, 3.0)
            .translate((5.0, -BODY_D / 2.0 + WALL + 3.0, rz))
        )
        shell = shell.union(roller_boss)
        r_hole = (
            cq.Workplane("XY")
            .transformed(offset=(5.0, -BODY_D / 2.0 + WALL + 3.0, rz))
            .circle(m2.tap_hole / 2.0)
            .extrude(4.0)
            .translate((0, 0, -2.0))
        )
        shell = shell.cut(r_hole)

    # --- Split line screw clearance holes ---
    for sy, sz in SPLIT_SCREW_POSITIONS:
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, sz, sy))
            .circle(M25.clearance_hole / 2.0)
            .extrude(8.0)
            .translate((0, 0, 0))
        )
        shell = shell.cut(hole)

        # Counterbore for screw head
        cbore = (
            cq.Workplane("YZ")
            .transformed(offset=(0, sz, sy))
            .circle(M25.head_dia / 2.0 + 0.3)
            .extrude(M25.head_height + 0.5)
            .translate((M25.length - M25.head_height, 0, 0))
        )
        shell = shell.cut(cbore)

    # --- Strap lug on right side (near top) ---
    lug = (
        cq.Workplane("XY")
        .box(8.0, 4.0, 10.0)
        .translate((HALF_L, 0, BODY_H / 2.0 - 15.0))
    )
    shell = shell.union(lug)
    # Strap hole through lug
    lug_hole = (
        cq.Workplane("XZ")
        .transformed(offset=(HALF_L, 0, BODY_H / 2.0 - 15.0))
        .circle(1.5)
        .extrude(4.0)
        .translate((0, -2.0, 0))
    )
    shell = shell.cut(lug_hole)

    # --- Dovetail rail on interior right wall (mirrors left side) ---
    # Rail runs along Y (front-to-back), 30mm long, at film plane height (Z=0).
    # Positioned on right interior wall, profile faces inward (-X direction).
    RAIL_LENGTH = 30.0
    rail_x = HALF_L - WALL - 4.0  # 4mm inset from interior wall surface
    rail = (
        make_dovetail_rail(RAIL_LENGTH)
        .rotate((0, 0, 0), (0, 1, 0), -90)  # rotate profile to face -X
        .translate((rail_x, 0, 0))
    )
    shell = shell.union(rail)

    # 2× M3 tapped holes for thumbscrew retention alongside dovetail rail
    for ty in [-10.0, 10.0]:
        m3_hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, 0, ty))
            .circle(M3_TAP_DIA / 2.0)
            .extrude(8.0)
            .translate((rail_x + DOVETAIL_DEPTH, 0, 0))
        )
        shell = shell.cut(m3_hole)

    # --- 2× Snap pockets near top edge for top plate latches (right side) ---
    PLATE_L_APPROX = BODY_L - 2.0
    PLATE_D_APPROX = BODY_D - 2.0
    snap_top_positions = [
        (PLATE_L_APPROX / 2.0 - 8.0, -PLATE_D_APPROX / 2.0 + 8.0),  # front-right
        (PLATE_L_APPROX / 2.0 - 8.0,  PLATE_D_APPROX / 2.0 - 8.0),  # rear-right
    ]
    for sx, sy in snap_top_positions:
        if sx > 0:  # only right-side positions
            pocket = (
                make_snap_pocket()
                .rotate((0, 0, 0), (1, 0, 0), 180)  # flip to receive downward latches
                .translate((sx, sy, BODY_H / 2.0 - WALL))
            )
            shell = shell.cut(pocket)

    # --- 2× Snap pockets near cartridge door opening for door latches ---
    for dz in [-CART_DOOR_H / 4.0, CART_DOOR_H / 4.0]:
        door_pocket = (
            make_snap_pocket()
            .rotate((0, 0, 0), (0, 0, 1), -90)  # orient for door engagement
            .translate((HALF_L - WALL, -CART_DOOR_W / 2.0, CART_Z + dz))
        )
        shell = shell.cut(door_pocket)

    return shell


def get_internal_layout() -> dict:
    """Return key positions for assembly verification."""
    return {
        "cartridge_center": (CART_X, CART_Y, CART_Z),
        "trigger_center": (TRIGGER_X, TRIGGER_Y, TRIGGER_Z),
        "door_opening": (HALF_L, 0, CART_Z),
        "door_size": (CART_DOOR_W, CART_DOOR_H),
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/body_right.step")
    cq.exporters.export(solid, f"{output_dir}/body_right.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Body right half exported to {output_dir}/")


if __name__ == "__main__":
    export()
