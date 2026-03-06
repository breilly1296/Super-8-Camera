"""Body left half — left side of the camera shell (gearbox/motor/PCB side).

Split-shell design: the left and right halves mate along the X=0 plane
(vertical center plane). 0.1mm clearance gap at the split line.

Internal layout references the film plane center as (0,0,0):
  X = left/right (- = left, toward gearbox/motor)
  Y = front/back (- = toward lens, + = toward film/rear)
  Z = vertical   (+ = up)

Key internal features on the left side:
  - Main shaft bearing housing (integrated bore at Z=+8mm)
  - Gearbox mount bosses (2× M3 threaded)
  - Motor mount pocket (cylindrical, 20.5mm bore)
  - PCB standoffs (4× M2, 6mm tall)
  - Left half of lens mount boss
  - Bottom: half of battery compartment, tripod mount boss

Material: 6061-T6 aluminum, black anodize Type II.
Wall thickness: 2.5mm.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    CAMERA, CMOUNT, MOTOR, GEARBOX, BEARINGS, FASTENERS, PCB,
)

# =========================================================================
# BODY ENVELOPE
# =========================================================================
WALL = CAMERA.wall_thickness          # 2.5 mm
BODY_L = CAMERA.body_length           # 148 mm (X total)
BODY_H = CAMERA.body_height           # 88 mm (Z)
BODY_D = CAMERA.body_depth            # 52 mm (Y)
FILLET = CAMERA.body_fillet            # 4 mm

HALF_L = BODY_L / 2.0                 # 74 mm — each half
SPLIT_CLEARANCE = 0.1                  # mm — gap at split line

# =========================================================================
# INTERNAL COMPONENT POSITIONS (from film plane origin)
# =========================================================================
# Main shaft: horizontal along X, center at Z=+8mm, Y=0
SHAFT_Z = 8.0                          # mm above film center
SHAFT_Y = 0.0                          # on optical axis

# Bearing bore: 694ZZ → 11mm OD, need H7 seat
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

# PCB standoffs (4× M2, on left interior wall)
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


def build() -> cq.Workplane:
    """Build the left body half-shell.

    The shell extends from X=0 (split line) to X=-HALF_L (left edge).
    Origin is at body center; the shell is shifted so its +X face is at X=0.
    """
    # --- Outer shell (left half) ---
    shell = (
        cq.Workplane("XY")
        .box(HALF_L - SPLIT_CLEARANCE / 2.0, BODY_D, BODY_H)
        .translate((-(HALF_L - SPLIT_CLEARANCE / 2.0) / 2.0, 0, 0))
    )

    # Fillets on outer edges (exclude split face)
    try:
        shell = shell.edges("|X").fillet(FILLET)
    except Exception:
        pass  # fillet may fail on some edges, continue

    # --- Hollow interior ---
    inner_l = HALF_L - WALL - SPLIT_CLEARANCE / 2.0
    inner = (
        cq.Workplane("XY")
        .box(inner_l,
             BODY_D - 2 * WALL,
             BODY_H - 2 * WALL)
        .translate((-(inner_l / 2.0 + WALL / 2.0), 0, 0))
    )
    shell = shell.cut(inner)

    # --- Lens mount boss opening (left portion) ---
    # The lens mount bore is at X=LENS_X, Y=-BODY_D/2.
    # Cut a half-circle from the front face for the mount.
    lens_bore_r = CMOUNT.thread_major_dia / 2.0 + 1.0  # 13.7mm clearance
    # Only cut if the lens axis is on the left side
    if LENS_X < 0:
        lens_cut = (
            cq.Workplane("XZ")
            .transformed(offset=(LENS_X, 0, 0))
            .circle(lens_bore_r)
            .extrude(WALL + 2.0)
            .translate((0, -BODY_D / 2.0, 0))
        )
        shell = shell.cut(lens_cut)

    # --- Main shaft bearing housing bore ---
    # Integrated into the left wall, at the split line face
    # The bearing sits at a known Z position on the shaft
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

    # --- Gearbox mounting bosses (2× M3 threaded) ---
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
    # Cylindrical recess in left wall interior for motor body
    motor_pocket = (
        cq.Workplane("YZ")
        .transformed(offset=(0, MOTOR_Z, MOTOR_Y))
        .circle(MOTOR.body_dia / 2.0 + 0.3)  # 0.3mm clearance
        .extrude(MOTOR.body_length + 2.0)
        .translate((-HALF_L + WALL, 0, 0))
    )
    shell = shell.cut(motor_pocket)

    # --- PCB standoffs (4× M2, 6mm tall) ---
    m2 = FASTENERS["M2x8_shcs"]
    pcb_positions = [
        (PCB_X, -PCB_SH, -PCB_SW / 2.0),
        (PCB_X, -PCB_SH, PCB_SW / 2.0),
        (PCB_X, PCB_SH, -PCB_SW / 2.0),
        (PCB_X, PCB_SH, PCB_SW / 2.0),
    ]
    for px, py, pz in pcb_positions:
        # Only add if within left shell bounds
        if px < 0:
            standoff = (
                cq.Workplane("XY")
                .cylinder(PCB_STANDOFF_H, CAMERA.pcb_standoff_dia / 2.0)
                .translate((px, py, pz))
            )
            shell = shell.union(standoff)
            # M2 hole through standoff
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
        # M2.5 tapped hole from split face
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, sz, sy))
            .circle(M25.tap_hole / 2.0)
            .extrude(M25.length)
            .translate((0, 0, 0))
        )
        shell = shell.cut(hole)

    # --- Tripod mount boss (left half) ---
    # 1/4"-20 helicoil at bottom center — boss straddles split line
    tripod_boss = (
        cq.Workplane("XY")
        .cylinder(CAMERA.tripod_boss_depth, CAMERA.tripod_boss_dia / 2.0)
        .translate((0, 0, -BODY_H / 2.0 + CAMERA.tripod_boss_depth / 2.0))
    )
    # Clip to left half only
    clip_left = (
        cq.Workplane("XY")
        .box(HALF_L, BODY_D, BODY_H)
        .translate((-HALF_L / 2.0, 0, 0))
    )
    tripod_boss_left = tripod_boss.intersect(clip_left)
    shell = shell.union(tripod_boss_left)

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
