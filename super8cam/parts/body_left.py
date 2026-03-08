"""Body left half — left side of the camera shell (gearbox/motor/PCB side).

Split-shell design: the left and right halves mate along the X=0 plane
(vertical center plane). 0.1mm clearance gap at the split line.

Sculpted exterior: multi-section lofted shell creating Canon 514XL-style
organic proportions. Lens boss ring on front face, chevron vent slots
over motor area. All internal features remain at their exact coordinates.

Internal layout references the film plane center as (0,0,0):
  X = left/right (- = left, toward gearbox/motor)
  Y = front/back (- = toward lens, + = toward film/rear)
  Z = vertical   (+ = up)

Key internal features on the left side:
  - Main shaft bearing housing (integrated bore at Z=+8mm)
  - Gearbox mount bosses (2x M3 threaded)
  - Motor mount pocket (cylindrical, 20.5mm bore)
  - PCB standoffs (4x M2, 6mm tall)
  - Left half of lens mount boss
  - Bottom: half of battery compartment, tripod mount boss

Material: 6061-T6 aluminum, black anodize Type II.
Wall thickness: 2.5mm.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    CAMERA, CMOUNT, MOTOR, GEARBOX, BEARINGS, FASTENERS, PCB, SCULPT,
)
from super8cam.parts.interfaces import (
    make_dovetail_rail, make_snap_pocket,
    DOVETAIL_DEPTH, M3_TAP_DIA,
)

# =========================================================================
# BODY ENVELOPE
# =========================================================================
WALL = CAMERA.wall_thickness          # 2.5 mm
BODY_L = CAMERA.body_length           # 135 mm (X total)
BODY_H = CAMERA.body_height           # 80 mm (Z)
BODY_D = CAMERA.body_depth            # 48 mm (Y)
FILLET = CAMERA.body_fillet            # 4 mm
TAPER = SCULPT.front_taper            # 4.0 mm total Y reduction at front

HALF_L = BODY_L / 2.0                 # 67.5 mm — each half
SPLIT_CLEARANCE = 0.1                  # mm — gap at split line

# =========================================================================
# INTERNAL COMPONENT POSITIONS (from film plane origin)
# =========================================================================
# Main shaft: horizontal along X, center at Z=+8mm, Y=0
SHAFT_Z = 8.0                          # mm above film center
SHAFT_Y = 0.0                          # on optical axis

# Bearing bore: 694ZZ -> 11mm OD, need H7 seat
BRG = BEARINGS["main_shaft"]
BRG_BORE_DIA = BRG.od + 0.05          # 11.05mm H7 fit

# Gearbox: to the left of shaft, mounts on interior wall
# Gearbox M3 bosses: two holes for gearbox housing screws
GBOX_BOSS_X = -30.0                    # mm — left of center
GBOX_BOSS_Z_1 = SHAFT_Z + 8.0         # above shaft
GBOX_BOSS_Z_2 = SHAFT_Z - 8.0         # below shaft
GBOX_BOSS_Y = 0.0

# Motor pocket: behind and to the left
MOTOR_X = -(HALF_L - WALL - MOTOR.body_dia / 2.0 - 2.0)  # near left wall
MOTOR_Z = SHAFT_Z                      # same height as shaft
MOTOR_Y = MOTOR.body_length / 2.0 + 5.0  # behind optical axis

# PCB standoffs (4x M2, on left interior wall)
PCB_X = CAMERA.pcb_mount_offset_x      # -15mm
PCB_SW = CAMERA.pcb_standoff_rect_w / 2.0  # half-spacing W
PCB_SH = CAMERA.pcb_standoff_rect_h / 2.0  # half-spacing H
PCB_STANDOFF_H = CAMERA.pcb_standoff_height  # 6mm (was 8 in spec, using actual)

# Lens mount: straddles split line, left half contributes its portion
LENS_Y = -BODY_D / 2.0                # at front face
LENS_X = CAMERA.lens_mount_offset_x   # -18mm from center (on left side)

# Battery compartment: bottom of camera
BATT_X = 20.0                          # right of center (under cartridge)
BATT_Z = -BODY_H / 2.0 + WALL + CAMERA.batt_pocket_depth / 2.0

# Tripod mount: bottom center
TRIPOD_X = 0.0
TRIPOD_Z = -BODY_H / 2.0

# Assembly screws along split line (M2.5)
M25 = FASTENERS["M2_5x6_shcs"]
SPLIT_SCREW_POSITIONS = [
    (0, -BODY_H / 2.0 + 10.0),   # bottom-front
    (0, 0.0),                      # center
    (0, BODY_H / 2.0 - 10.0),     # top
    (-BODY_D / 4.0, -BODY_H / 2.0 + 10.0),  # bottom-rear
    (-BODY_D / 4.0, BODY_H / 2.0 - 10.0),   # top-rear
]


# =========================================================================
# LOFT PROFILE STATIONS (Left half: X from -HALF_L to 0)
# =========================================================================
# Each station: (x_position, y_extent, z_extent)
# y_extent and z_extent are full widths at that station
_LOFT_STATIONS = [
    (-HALF_L,  40.0, 72.0),   # Left edge: tapered, rounded
    (-40.0,    46.0, 78.0),   # Lens area: wider for lens boss
    (-15.0,    BODY_D, BODY_H),  # Near split: full size
    (0.0,      BODY_D, BODY_H),  # Split face: flat rectangle
]


# =========================================================================
# SCULPTED OUTER SHELL — MULTI-SECTION LOFT
# =========================================================================

def _make_outer_shell() -> cq.Workplane:
    """Create the lofted outer shell (left half).

    Uses multi-section loft through YZ cross-section profiles at different
    X stations to create organic, Canon 514XL-style proportions.
    Left edge is tapered/narrowed; split face is full-size rectangle.
    """
    half_len = HALF_L - SPLIT_CLEARANCE / 2.0

    # Try lofted approach first, fall back to box+wedge
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

    # Build cross-section profiles as wires at each X station
    # CadQuery loft needs chained workplanes with .rect() calls
    wp = cq.Workplane("YZ")

    # First station
    x0, y0, z0 = stations[0]
    wp = wp.transformed(offset=(x0, 0, 0)).rect(y0, z0)

    # Subsequent stations — use offset from previous X position
    prev_x = x0
    for x, y, z in stations[1:]:
        dx = x - prev_x
        wp = wp.workplane(offset=dx).rect(y, z)
        prev_x = x

    shell = wp.loft(ruled=ruled)

    # Clip to exact half-length (trim the split-face side to account for
    # SPLIT_CLEARANCE)
    if half_len < HALF_L:
        clip = (
            cq.Workplane("XY")
            .box(half_len + 0.01, BODY_D + 2, BODY_H + 2)
            .translate((-(half_len / 2.0 + 0.005), 0, 0))
        )
        shell = shell.intersect(clip)

    # Apply exterior fillets
    try:
        shell = shell.edges("|X").fillet(SCULPT.exterior_fillet)
    except Exception:
        try:
            shell = shell.edges("|X").fillet(FILLET)
        except Exception:
            pass

    return shell


def _box_outer_shell(half_len: float) -> cq.Workplane:
    """Fallback: box + wedge taper approach (proven working)."""
    taper_per_side = TAPER / 2.0

    shell = (
        cq.Workplane("XY")
        .box(half_len, BODY_D, BODY_H)
        .translate((-half_len / 2.0, 0, 0))
    )

    for y_sign in [-1, 1]:
        wedge = (
            cq.Workplane("XZ")
            .transformed(offset=(0, 0, 0))
            .rect(half_len, BODY_H)
            .workplane(offset=taper_per_side)
            .rect(0.001, BODY_H)
            .loft()
        )
        y_pos = y_sign * BODY_D / 2.0
        if y_sign < 0:
            wedge = wedge.translate((-half_len / 2.0, y_pos, 0))
        else:
            wedge = (
                wedge
                .rotate((0, 0, 0), (0, 0, 1), 180)
                .translate((-half_len / 2.0, y_pos, 0))
            )
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

    # Inner cavity stations: outer dimensions reduced by wall thickness
    inner_stations = [
        (x, max(y - w2, 4.0), max(z - w2, 4.0))
        for x, y, z in _LOFT_STATIONS
    ]
    # Shift X inward by WALL at left edge
    inner_stations[0] = (inner_stations[0][0] + WALL, inner_stations[0][1], inner_stations[0][2])
    # Shift X inward by WALL/2 at split face (open at split)
    inner_stations[-1] = (0.0, inner_stations[-1][1], inner_stations[-1][2])

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
        .translate((-(inner_l / 2.0 + WALL / 2.0), 0, 0))
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
            inner_wedge = inner_wedge.translate(
                (-(inner_l / 2.0 + WALL / 2.0), y_pos, 0))
        else:
            inner_wedge = (
                inner_wedge
                .rotate((0, 0, 0), (0, 0, 1), 180)
                .translate((-(inner_l / 2.0 + WALL / 2.0), y_pos, 0))
            )
        inner = inner.cut(inner_wedge)

    shell = shell.cut(inner)
    return shell


def _add_lens_boss(shell: cq.Workplane) -> cq.Workplane:
    """Add lens boss ring on front face and cut lens bore."""
    lens_bore_r = CMOUNT.thread_major_dia / 2.0 + 1.0  # 13.7mm clearance
    boss_r = CAMERA.lens_boss_od / 2.0  # 15mm
    boss_protrusion = 3.0  # reduced from 5mm for printability

    if LENS_X < 0:
        # Lens boss ring: cylinder protruding from front face
        front_y = -BODY_D / 2.0 + TAPER / 2.0  # adjusted for taper at split
        boss_ring = (
            cq.Workplane("XZ")
            .transformed(offset=(LENS_X, 0, 0))
            .circle(boss_r)
            .extrude(boss_protrusion)
            .translate((0, front_y - boss_protrusion, 0))
        )
        # Clip boss to left half only (it may extend past X=0)
        clip_left = (
            cq.Workplane("XY")
            .box(HALF_L + 2, BODY_D + 20, BODY_H + 20)
            .translate((-HALF_L / 2.0, 0, 0))
        )
        boss_ring = boss_ring.intersect(clip_left)
        shell = shell.union(boss_ring)

        # Cut the lens bore through the boss and body wall
        lens_cut = (
            cq.Workplane("XZ")
            .transformed(offset=(LENS_X, 0, 0))
            .circle(lens_bore_r)
            .extrude(WALL + boss_protrusion + 2.0)
            .translate((0, front_y - boss_protrusion - 1.0, 0))
        )
        shell = shell.cut(lens_cut)

    return shell


def _add_vent_slots(shell: cq.Workplane) -> cq.Workplane:
    """Add chevron ventilation slots on the left wall over motor area."""
    slot_l = SCULPT.vent_slot_length   # 10mm
    slot_w = SCULPT.vent_slot_width    # 2.5mm
    n_slots = SCULPT.vent_slot_count   # 4
    spacing = SCULPT.vent_slot_spacing # 5mm
    angle = SCULPT.vent_slot_angle     # 15 degrees

    # Vent slots are on the left wall (X = -HALF_L + SPLIT_CLEARANCE/2)
    # Near motor area: Z ~ SHAFT_Z (8mm), Y ~ MOTOR_Y (17.5mm)
    slot_x = -(HALF_L - SPLIT_CLEARANCE / 2.0)
    slot_base_z = SHAFT_Z
    slot_base_y = MOTOR_Y - 5.0

    for i in range(n_slots):
        z_offset = (i - (n_slots - 1) / 2.0) * spacing
        # Alternating chevron angle
        slot_angle = angle if (i % 2 == 0) else -angle

        # Create pill-shaped slot (stadium profile)
        slot = (
            cq.Workplane("XY")
            .slot2D(slot_l, slot_w)
            .extrude(WALL + 1.0)
        )
        # Rotate for chevron pattern and position on left wall
        slot = (
            slot
            .rotate((0, 0, 0), (0, 0, 1), slot_angle)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((slot_x, slot_base_y, slot_base_z + z_offset))
        )
        shell = shell.cut(slot)

    return shell


def _add_internal_features(shell: cq.Workplane) -> cq.Workplane:
    """Add all internal features.

    Coordinates auto-adjust via HALF_L, BODY_H, BODY_D module-level constants.
    """
    # --- Main shaft bearing housing bore ---
    brg_boss = (
        cq.Workplane("YZ")
        .transformed(offset=(0, SHAFT_Z, SHAFT_Y))
        .circle(BRG_BORE_DIA / 2.0 + 2.0)  # boss OD = bearing OD + 4mm
        .extrude(8.0)
        .translate((-WALL, 0, 0))
    )
    shell = shell.union(brg_boss)

    # Bearing bore through the boss
    brg_hole = (
        cq.Workplane("YZ")
        .transformed(offset=(0, SHAFT_Z, SHAFT_Y))
        .circle(BRG_BORE_DIA / 2.0)
        .extrude(BRG.width + 1.0)
        .translate((-WALL, 0, 0))
    )
    shell = shell.cut(brg_hole)

    # --- Gearbox mounting bosses (2x M3 threaded) ---
    m3 = FASTENERS["M3x8_shcs"]
    for gz in [GBOX_BOSS_Z_1, GBOX_BOSS_Z_2]:
        boss = (
            cq.Workplane("XY")
            .cylinder(8.0, 4.0)  # 8mm tall, 4mm radius boss
            .translate((GBOX_BOSS_X, GBOX_BOSS_Y, gz))
        )
        shell = shell.union(boss)
        # M3 tapped hole
        hole = (
            cq.Workplane("XY")
            .transformed(offset=(GBOX_BOSS_X, GBOX_BOSS_Y, gz))
            .circle(m3.tap_hole / 2.0)
            .extrude(8.0)
            .translate((0, 0, -4.0))
        )
        shell = shell.cut(hole)

    # --- Motor mount pocket ---
    motor_pocket = (
        cq.Workplane("YZ")
        .transformed(offset=(0, MOTOR_Z, MOTOR_Y))
        .circle(MOTOR.body_dia / 2.0 + 0.3)  # 0.3mm clearance
        .extrude(MOTOR.body_length + 2.0)
        .translate((-HALF_L + WALL, 0, 0))
    )
    shell = shell.cut(motor_pocket)

    # --- PCB standoffs (4x M2, 6mm tall) ---
    m2 = FASTENERS["M2x8_shcs"]
    pcb_positions = [
        (PCB_X, -PCB_SH, -PCB_SW / 2.0),
        (PCB_X, -PCB_SH, PCB_SW / 2.0),
        (PCB_X, PCB_SH, -PCB_SW / 2.0),
        (PCB_X, PCB_SH, PCB_SW / 2.0),
    ]
    for px, py, pz in pcb_positions:
        if px < 0:
            standoff = (
                cq.Workplane("XY")
                .cylinder(PCB_STANDOFF_H, CAMERA.pcb_standoff_dia / 2.0)
                .translate((px, py, pz))
            )
            shell = shell.union(standoff)
            so_hole = (
                cq.Workplane("XY")
                .transformed(offset=(px, py, pz))
                .circle(m2.tap_hole / 2.0)
                .extrude(PCB_STANDOFF_H)
                .translate((0, 0, -PCB_STANDOFF_H / 2.0))
            )
            shell = shell.cut(so_hole)

    # --- Split line screw bosses (M2.5 tapped) ---
    for sy, sz in SPLIT_SCREW_POSITIONS:
        boss = (
            cq.Workplane("YZ")
            .transformed(offset=(0, sz, sy))
            .circle(M25.head_dia / 2.0 + 0.5)
            .extrude(6.0)
            .translate((-6.0, 0, 0))
        )
        shell = shell.union(boss)
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, sz, sy))
            .circle(M25.tap_hole / 2.0)
            .extrude(M25.length)
            .translate((0, 0, 0))
        )
        shell = shell.cut(hole)

    # --- Tripod mount boss (left half) ---
    tripod_boss = (
        cq.Workplane("XY")
        .cylinder(CAMERA.tripod_boss_depth, CAMERA.tripod_boss_dia / 2.0)
        .translate((0, 0, -BODY_H / 2.0 + CAMERA.tripod_boss_depth / 2.0))
    )
    clip_left = (
        cq.Workplane("XY")
        .box(HALF_L, BODY_D, BODY_H)
        .translate((-HALF_L / 2.0, 0, 0))
    )
    tripod_boss_left = tripod_boss.intersect(clip_left)
    shell = shell.union(tripod_boss_left)

    # --- Dovetail rail on interior left wall ---
    RAIL_LENGTH = 30.0
    rail_x = -HALF_L + WALL + 4.0
    rail = (
        make_dovetail_rail(RAIL_LENGTH)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((rail_x, 0, 0))
    )
    shell = shell.union(rail)

    # 2x M3 tapped holes for thumbscrew retention
    m3 = FASTENERS["M3x8_shcs"]
    for ty in [-10.0, 10.0]:
        m3_hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, 0, ty))
            .circle(M3_TAP_DIA / 2.0)
            .extrude(8.0)
            .translate((rail_x - DOVETAIL_DEPTH, 0, 0))
        )
        shell = shell.cut(m3_hole)

    # --- 2x Snap pockets near top edge for top plate latches ---
    PLATE_L_APPROX = BODY_L - 2.0
    PLATE_D_APPROX = BODY_D - 2.0
    snap_top_positions = [
        (-PLATE_L_APPROX / 2.0 + 8.0, -PLATE_D_APPROX / 2.0 + 8.0),
        (-PLATE_L_APPROX / 2.0 + 8.0,  PLATE_D_APPROX / 2.0 - 8.0),
    ]
    for sx, sy in snap_top_positions:
        if sx < 0:
            pocket = (
                make_snap_pocket()
                .rotate((0, 0, 0), (1, 0, 0), 180)
                .translate((sx, sy, BODY_H / 2.0 - WALL))
            )
            shell = shell.cut(pocket)

    # --- PCB board clearance pocket (cut LAST to override screw bosses) ---
    pcb_board_z = -BODY_H / 2.0 + WALL + PCB_STANDOFF_H + PCB.thickness / 2.0
    pcb_pocket = (
        cq.Workplane("XY")
        .box(PCB.width + 6, PCB.height + 6, PCB.thickness + 10)
        .translate((PCB_X, 0, pcb_board_z + 2.0))
    )
    shell = shell.cut(pcb_pocket)

    return shell


def build() -> cq.Workplane:
    """Build the left body half-shell.

    The shell extends from X=0 (split line) to X=-HALF_L (left edge).
    Origin is at body center; the shell is shifted so its +X face is at X=0.
    """
    shell = _make_outer_shell()
    shell = _hollow_interior(shell)
    shell = _add_lens_boss(shell)
    shell = _add_vent_slots(shell)
    shell = _add_internal_features(shell)
    return shell


def get_internal_layout() -> dict:
    """Return internal component positions for assembly verification."""
    return {
        "shaft_center": (0, SHAFT_Y, SHAFT_Z),
        "gearbox_bosses": [
            (GBOX_BOSS_X, GBOX_BOSS_Y, GBOX_BOSS_Z_1),
            (GBOX_BOSS_X, GBOX_BOSS_Y, GBOX_BOSS_Z_2),
        ],
        "motor_center": (MOTOR_X, MOTOR_Y, MOTOR_Z),
        "pcb_center": (PCB_X, 0, 0),
        "lens_axis": (LENS_X, LENS_Y, 0),
        "battery_center": (BATT_X, 0, BATT_Z),
        "tripod_center": (TRIPOD_X, 0, TRIPOD_Z),
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/body_left.step")
    cq.exporters.export(solid, f"{output_dir}/body_left.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Body left half exported to {output_dir}/")


if __name__ == "__main__":
    export()
