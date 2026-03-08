"""Body right half — right side of the camera shell (cartridge/trigger side).

Mates with the left half along the X=0 plane with 0.1mm clearance.

Sculpted exterior: multi-section lofted shell creating organic, Canon 514XL-
style proportions. Integrated pistol grip extending below the body, and a
finger recess near the cartridge door. All internal features remain at their
exact coordinates.

Key internal features on the right side:
  - Cartridge receiver pocket (the dominant internal feature)
  - Film channel and guide roller mount points
  - Cartridge loading door opening (right face, ~55x50mm)
  - Trigger button hole and mechanism mount
  - Right half of lens mount boss
  - Right portion of battery compartment

Material: 6061-T6 aluminum, black anodize Type II.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    CAMERA, CMOUNT, CARTRIDGE, FASTENERS, BEARINGS, SCULPT,
)
from super8cam.parts.interfaces import (
    make_dovetail_rail, make_snap_pocket,
    DOVETAIL_DEPTH, M3_TAP_DIA,
)

# =========================================================================
# BODY ENVELOPE (mirrors body_left.py)
# =========================================================================
WALL = CAMERA.wall_thickness          # 2.5 mm
BODY_L = CAMERA.body_length           # 135 mm
BODY_H = CAMERA.body_height           # 80 mm
BODY_D = CAMERA.body_depth            # 48 mm
FILLET = CAMERA.body_fillet            # 4 mm
TAPER = SCULPT.front_taper            # 4.0 mm total Y reduction at front

HALF_L = BODY_L / 2.0                 # 67.5 mm
SPLIT_CLEARANCE = 0.1                  # mm

# =========================================================================
# INTERNAL POSITIONS
# =========================================================================
# Main shaft bearing housing (right side bearing)
SHAFT_Z = 8.0
BRG = BEARINGS["main_shaft"]
BRG_BORE_DIA = BRG.od + 0.05

# Cartridge pocket: dominates the right interior
CART_X = 31.0                          # shifted left to fit compact body
CART_Y = 0.0
CART_Z = 3.0

# Cartridge door opening on the right face (+X)
CART_DOOR_W = CAMERA.cart_door_w       # 55 mm
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
LENS_X = CAMERA.lens_mount_offset_x   # -18mm (on left side, minimal right contribution)


# =========================================================================
# LOFT PROFILE STATIONS (Right half: X from 0 to +HALF_L)
# =========================================================================
_LOFT_STATIONS = [
    (0.0,      BODY_D, BODY_H),   # Split face: full size
    (+35.0,    46.0, 78.0),       # Cartridge area: housing cartridge
    (+55.0,    42.0, 74.0),       # Grip zone: narrower
    (+HALF_L,  38.0, 70.0),       # Right edge: tapered, door area
]


# =========================================================================
# SCULPTED OUTER SHELL — MULTI-SECTION LOFT
# =========================================================================

def _make_outer_shell() -> cq.Workplane:
    """Create the lofted outer shell (right half).

    Uses multi-section loft through YZ cross-section profiles to create
    organic proportions. Split face is full-size; right edge is tapered.
    """
    half_len = HALF_L - SPLIT_CLEARANCE / 2.0

    try:
        return _loft_outer_shell(half_len)
    except Exception:
        try:
            return _loft_outer_shell(half_len, ruled=False)
        except Exception:
            return _box_outer_shell(half_len)


def _loft_outer_shell(half_len: float, ruled: bool = True) -> cq.Workplane:
    """Build lofted outer shell through YZ profile stations."""
    stations = _LOFT_STATIONS

    wp = cq.Workplane("YZ")
    x0, y0, z0 = stations[0]
    wp = wp.transformed(offset=(x0, 0, 0)).rect(y0, z0)

    prev_x = x0
    for x, y, z in stations[1:]:
        dx = x - prev_x
        wp = wp.workplane(offset=dx).rect(y, z)
        prev_x = x

    shell = wp.loft(ruled=ruled)

    # Clip to exact half-length
    if half_len < HALF_L:
        clip = (
            cq.Workplane("XY")
            .box(half_len + 0.01, BODY_D + 2, BODY_H + 2)
            .translate((half_len / 2.0 + 0.005, 0, 0))
        )
        shell = shell.intersect(clip)

    try:
        shell = shell.edges("|X").fillet(SCULPT.exterior_fillet)
    except Exception:
        try:
            shell = shell.edges("|X").fillet(FILLET)
        except Exception:
            pass

    return shell


def _box_outer_shell(half_len: float) -> cq.Workplane:
    """Fallback: box + wedge taper approach."""
    taper_per_side = TAPER / 2.0

    shell = (
        cq.Workplane("XY")
        .box(half_len, BODY_D, BODY_H)
        .translate((half_len / 2.0, 0, 0))
    )

    for y_sign in [-1, 1]:
        wedge = (
            cq.Workplane("XZ")
            .rect(half_len, BODY_H)
            .workplane(offset=taper_per_side)
            .rect(0.001, BODY_H)
            .loft()
        )
        y_pos = y_sign * BODY_D / 2.0
        if y_sign < 0:
            wedge = (
                wedge
                .rotate((0, 0, 0), (0, 0, 1), 180)
                .translate((half_len / 2.0, y_pos, 0))
            )
        else:
            wedge = wedge.translate((half_len / 2.0, y_pos, 0))
        shell = shell.cut(wedge)

    try:
        shell = shell.edges("|X").fillet(SCULPT.exterior_fillet)
    except Exception:
        try:
            shell = shell.edges("|X").fillet(FILLET)
        except Exception:
            pass

    return shell


def _hollow_interior(shell: cq.Workplane) -> cq.Workplane:
    """Hollow out the shell with matching lofted interior cavity."""
    half_len = HALF_L - SPLIT_CLEARANCE / 2.0

    try:
        return _loft_hollow(shell, half_len)
    except Exception:
        return _box_hollow(shell, half_len)


def _loft_hollow(shell: cq.Workplane, half_len: float) -> cq.Workplane:
    """Lofted inner cavity matching the outer shell profile."""
    w2 = 2 * WALL

    inner_stations = [
        (x, max(y - w2, 4.0), max(z - w2, 4.0))
        for x, y, z in _LOFT_STATIONS
    ]
    # Open at split face
    inner_stations[0] = (0.0, inner_stations[0][1], inner_stations[0][2])
    # Shift right edge inward by WALL
    inner_stations[-1] = (inner_stations[-1][0] - WALL, inner_stations[-1][1], inner_stations[-1][2])

    wp = cq.Workplane("YZ")
    x0, y0, z0 = inner_stations[0]
    wp = wp.transformed(offset=(x0, 0, 0)).rect(y0, z0)

    prev_x = x0
    for x, y, z in inner_stations[1:]:
        dx = x - prev_x
        wp = wp.workplane(offset=dx).rect(y, z)
        prev_x = x

    inner = wp.loft(ruled=True)
    shell = shell.cut(inner)
    return shell


def _box_hollow(shell: cq.Workplane, half_len: float) -> cq.Workplane:
    """Fallback box-based interior hollowing."""
    inner_l = half_len - WALL
    taper_per_side = TAPER / 2.0

    inner = (
        cq.Workplane("XY")
        .box(inner_l,
             BODY_D - 2 * WALL,
             BODY_H - 2 * WALL)
        .translate(((inner_l / 2.0 + WALL / 2.0), 0, 0))
    )

    for y_sign in [-1, 1]:
        inner_wedge = (
            cq.Workplane("XZ")
            .rect(inner_l, BODY_H - 2 * WALL)
            .workplane(offset=taper_per_side)
            .rect(0.001, BODY_H - 2 * WALL)
            .loft()
        )
        y_pos = y_sign * (BODY_D / 2.0 - WALL)
        if y_sign < 0:
            inner_wedge = (
                inner_wedge
                .rotate((0, 0, 0), (0, 0, 1), 180)
                .translate(((inner_l / 2.0 + WALL / 2.0), y_pos, 0))
            )
        else:
            inner_wedge = inner_wedge.translate(
                ((inner_l / 2.0 + WALL / 2.0), y_pos, 0))
        inner = inner.cut(inner_wedge)

    shell = shell.cut(inner)
    return shell


def _add_pistol_grip(shell: cq.Workplane) -> cq.Workplane:
    """Add integrated pistol grip extending below the body.

    The grip is a lofted hollow shape:
      - Top profile (body bottom, Z = -BODY_H/2): full body depth at grip X
      - Bottom profile (Z = -BODY_H/2 - grip_height): narrower, tilted toward rear
    """
    grip_w = SCULPT.grip_width          # 22mm (X)
    grip_d_bottom = SCULPT.grip_depth   # 22mm (Y at bottom)
    grip_h = SCULPT.grip_height         # 50mm (Z extent)
    grip_angle = SCULPT.grip_angle      # 15 degrees
    grip_wall = SCULPT.grip_wall        # 2.5mm
    grip_x_start = SCULPT.grip_x_start  # 45mm

    grip_cx = grip_x_start + grip_w / 2.0  # center X of grip
    body_bottom_z = -BODY_H / 2.0
    grip_bottom_z = body_bottom_z - grip_h

    # Y offset at bottom due to ergonomic tilt toward rear (+Y)
    y_tilt = grip_h * math.tan(math.radians(grip_angle))

    # Top profile: match body depth at that X position
    # Interpolate body depth from loft stations
    taper_fraction = grip_cx / HALF_L
    grip_d_top = BODY_D - TAPER * (1.0 - taper_fraction)

    # Outer grip: loft between top rect and bottom rect
    top_wp = (
        cq.Workplane("XY")
        .transformed(offset=(grip_cx, 0, body_bottom_z))
        .rect(grip_w, grip_d_top)
    )
    bottom_wp = (
        top_wp.workplane(offset=-grip_h)
        .transformed(offset=(0, y_tilt, 0))
        .rect(grip_w - 4.0, grip_d_bottom)
    )

    try:
        grip_outer = top_wp.loft(combine=False, ruled=True)
    except Exception:
        # Fallback: simple tapered box
        grip_outer = (
            cq.Workplane("XY")
            .box(grip_w, grip_d_bottom, grip_h)
            .translate((grip_cx, y_tilt / 2.0,
                        body_bottom_z - grip_h / 2.0))
        )

    # Hollow interior
    inner_w = grip_w - 2 * grip_wall
    inner_d_top = grip_d_top - 2 * grip_wall
    inner_d_bottom = grip_d_bottom - 2 * grip_wall

    top_inner = (
        cq.Workplane("XY")
        .transformed(offset=(grip_cx, 0, body_bottom_z))
        .rect(inner_w, inner_d_top)
    )
    bottom_inner = (
        top_inner.workplane(offset=-grip_h + grip_wall)
        .transformed(offset=(0, y_tilt * 0.9, 0))
        .rect(inner_w - 4.0, inner_d_bottom)
    )

    try:
        grip_inner = top_inner.loft(combine=False, ruled=True)
    except Exception:
        grip_inner = (
            cq.Workplane("XY")
            .box(inner_w, inner_d_bottom, grip_h - grip_wall)
            .translate((grip_cx, y_tilt / 2.0,
                        body_bottom_z - (grip_h - grip_wall) / 2.0))
        )

    grip = grip_outer.cut(grip_inner)

    # Apply comfort fillets on grip edges
    try:
        grip = grip.edges().fillet(SCULPT.grip_fillet)
    except Exception:
        try:
            grip = grip.edges("|Z").fillet(SCULPT.grip_fillet / 2.0)
        except Exception:
            pass

    shell = shell.union(grip)
    return shell


def _add_finger_recess(shell: cq.Workplane) -> cq.Workplane:
    """Add circular finger recess next to cartridge door edge."""
    recess_dia = SCULPT.finger_recess_dia     # 12mm
    recess_depth = SCULPT.finger_recess_depth  # 1.5mm

    # Position: on right face (+X), adjacent to cartridge door, centered vertically
    recess_x = HALF_L - SPLIT_CLEARANCE / 2.0
    recess_y = -CART_DOOR_H / 2.0 - recess_dia / 2.0 - 2.0  # below door opening
    recess_z = CART_Z

    recess = (
        cq.Workplane("YZ")
        .transformed(offset=(0, recess_z, recess_y))
        .circle(recess_dia / 2.0)
        .extrude(recess_depth)
        .translate((recess_x - recess_depth, 0, 0))
    )
    shell = shell.cut(recess)
    return shell


def _add_internal_features(shell: cq.Workplane) -> cq.Workplane:
    """Add all internal features.

    Coordinates auto-adjust via HALF_L, BODY_H, BODY_D module-level constants.
    """
    # --- Cartridge loading door opening (right face) ---
    door_opening = (
        cq.Workplane("YZ")
        .rect(CART_DOOR_H, CART_DOOR_W)
        .extrude(WALL + 1.0)
        .translate((HALF_L - WALL, 0, CART_Z))
    )
    shell = shell.cut(door_opening)

    # --- Light trap ledge around door opening ---
    trap_depth = 1.5
    trap_width = 2.0
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

    # --- Film exit/entry slots ---
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
    lug_hole = (
        cq.Workplane("XZ")
        .transformed(offset=(HALF_L, 0, BODY_H / 2.0 - 15.0))
        .circle(1.5)
        .extrude(4.0)
        .translate((0, -2.0, 0))
    )
    shell = shell.cut(lug_hole)

    # --- Dovetail rail on interior right wall ---
    RAIL_LENGTH = 30.0
    rail_x = HALF_L - WALL - 4.0
    rail = (
        make_dovetail_rail(RAIL_LENGTH)
        .rotate((0, 0, 0), (0, 1, 0), -90)
        .translate((rail_x, 0, 0))
    )
    shell = shell.union(rail)

    # 2x M3 tapped holes for thumbscrew retention
    for ty in [-10.0, 10.0]:
        m3_hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, 0, ty))
            .circle(M3_TAP_DIA / 2.0)
            .extrude(8.0)
            .translate((rail_x + DOVETAIL_DEPTH, 0, 0))
        )
        shell = shell.cut(m3_hole)

    # --- 2x Snap pockets near top edge for top plate latches ---
    PLATE_L_APPROX = BODY_L - 2.0
    PLATE_D_APPROX = BODY_D - 2.0
    snap_top_positions = [
        (PLATE_L_APPROX / 2.0 - 8.0, -PLATE_D_APPROX / 2.0 + 8.0),
        (PLATE_L_APPROX / 2.0 - 8.0,  PLATE_D_APPROX / 2.0 - 8.0),
    ]
    for sx, sy in snap_top_positions:
        if sx > 0:
            pocket = (
                make_snap_pocket()
                .rotate((0, 0, 0), (1, 0, 0), 180)
                .translate((sx, sy, BODY_H / 2.0 - WALL))
            )
            shell = shell.cut(pocket)

    # --- 2x Snap pockets near cartridge door for door latches ---
    for dz in [-CART_DOOR_H / 4.0, CART_DOOR_H / 4.0]:
        door_pocket = (
            make_snap_pocket()
            .rotate((0, 0, 0), (0, 0, 1), -90)
            .translate((HALF_L - WALL, -CART_DOOR_W / 2.0, CART_Z + dz))
        )
        shell = shell.cut(door_pocket)

    # --- Cartridge receiver pocket (cut LAST to override internal bosses) ---
    pocket_l = CARTRIDGE.length + 15.0  # 82mm
    pocket_w = CARTRIDGE.width + 15.0   # 77mm
    pocket_d = CARTRIDGE.width + 15.0   # 77mm
    cart_pocket = (
        cq.Workplane("XY")
        .box(pocket_l, pocket_d, pocket_w)
        .translate((CART_X, CART_Y, CART_Z))
    )
    shell = shell.cut(cart_pocket)

    return shell


def build() -> cq.Workplane:
    """Build the right body half-shell.

    Shell extends from X=0 (split line) to X=+HALF_L (right edge).
    """
    shell = _make_outer_shell()
    shell = _hollow_interior(shell)
    shell = _add_pistol_grip(shell)
    shell = _add_finger_recess(shell)
    shell = _add_internal_features(shell)
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
