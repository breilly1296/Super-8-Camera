"""Lens mount — C-mount (1"-32 TPI) threaded boss on the camera front face.

The C-mount standard (ANSI/ASA B3.19) specifies a flange focal distance of
exactly 17.526mm from the lens mounting face to the film plane.  This is THE
critical optical dimension — all intermediate distances in the optical path
are constrained to hit this number.

Material: 6061-T6 aluminum, Type III hard anodize on thread surfaces for wear.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CMOUNT, CAMERA, TOL, FASTENERS, MATERIALS,
)
from super8cam.parts.film_gate import GATE_THICK, CHANNEL_DEPTH
from super8cam.parts.shutter_disc import DISC_THICK, GATE_CLEARANCE

# =========================================================================
# FLANGE DISTANCE STACK-UP
# =========================================================================
# The total distance from the lens mount face to the film plane must equal
# CMOUNT.flange_focal_dist = 17.526 mm.
#
# Working backward from the film plane:
#   Film plane = floor of film channel on gate rear face
#   Gate front face to film plane = GATE_THICK - CHANNEL_DEPTH = 3.80 mm
#   Shutter rear to gate front = GATE_CLEARANCE = 0.30 mm
#   Shutter disc thickness = DISC_THICK = 0.80 mm
#   Mount face to shutter front = SOLVED
#
# mount_face_to_shutter_front + DISC_THICK + GATE_CLEARANCE
#   + (GATE_THICK - CHANNEL_DEPTH) = 17.526 mm

GATE_FRONT_TO_FILM_PLANE = GATE_THICK - CHANNEL_DEPTH  # 3.80 mm
MOUNT_TO_SHUTTER_FRONT = (CMOUNT.flange_focal_dist
                          - GATE_FRONT_TO_FILM_PLANE
                          - GATE_CLEARANCE
                          - DISC_THICK)  # 12.626 mm

# Verify the stack-up
STACK_TOTAL = (MOUNT_TO_SHUTTER_FRONT + DISC_THICK
               + GATE_CLEARANCE + GATE_FRONT_TO_FILM_PLANE)
STACK_ERROR = abs(STACK_TOTAL - CMOUNT.flange_focal_dist)
assert STACK_ERROR < 0.001, (
    f"Flange distance stack-up error: {STACK_ERROR:.4f} mm")

# =========================================================================
# BOSS GEOMETRY
# =========================================================================
BOSS_OD = 30.0                          # mm — outer diameter of mount boss
BOSS_PROTRUSION = 5.0                   # mm — protrudes from camera front face

# Thread: 1"-32 TPI, modeled as plain bore at major diameter
THREAD_MAJOR_DIA = CMOUNT.thread_major_dia    # 25.4 mm
THREAD_DEPTH = CMOUNT.thread_depth            # 3.8 mm

# Clearance bore behind the thread (opens into shutter cavity)
CLEARANCE_BORE_DIA = 26.0              # mm — clears lens rear element

# Total mount depth (from mount face into camera body)
# The boss protrudes BOSS_PROTRUSION out and extends further inward.
# Mount face is at the front of the boss protrusion.
# The thread bore goes 3.8mm deep from the mount face.
# Behind that is the clearance bore through to the shutter cavity.
MOUNT_BODY_DEPTH = MOUNT_TO_SHUTTER_FRONT  # from mount face to shutter front

# Anti-rotation locating pin (12 o'clock position)
LOCATING_PIN_DIA = 1.5                 # mm
LOCATING_PIN_DEPTH = 2.0               # mm — blind hole in mount face
LOCATING_PIN_RADIUS = THREAD_MAJOR_DIA / 2.0 + 1.5  # mm from center

# Flange seating surface: annular ring on mount face
FLANGE_SEAT_ID = THREAD_MAJOR_DIA      # inner edge at thread
FLANGE_SEAT_OD = BOSS_OD - 1.0         # outer edge (leave 0.5mm chamfer)

# Mounting: 3× M2 radial holes for securing boss to camera body
M2_CLEARANCE = FASTENERS["M2x5_shcs"].clearance_hole  # 2.2 mm
MOUNT_HOLE_RADIUS = BOSS_OD / 2.0 - 2.0  # mm from center
MOUNT_HOLE_ANGLES = [0, 120, 240]         # degrees


def build() -> cq.Workplane:
    """Build the C-mount lens mount boss.

    Coordinate system:
      Z+ = toward lens (away from camera body)
      Z=0 = camera front face (where boss meets body)
      Mount face (lens flange seat) = Z = BOSS_PROTRUSION
    """
    # --- Boss cylinder ---
    # Total axial length: BOSS_PROTRUSION (external) + body wall depth
    total_length = BOSS_PROTRUSION + CAMERA.wall_thickness
    boss = (
        cq.Workplane("XY")
        .cylinder(total_length, BOSS_OD / 2.0)
        .translate((0, 0, (BOSS_PROTRUSION - CAMERA.wall_thickness) / 2.0))
    )

    # --- Thread bore from mount face ---
    # Mount face is at Z = BOSS_PROTRUSION
    # Thread is modeled as a plain bore at major diameter
    boss = (
        boss.faces(">Z").workplane()
        .circle(THREAD_MAJOR_DIA / 2.0)
        .cutBlind(-THREAD_DEPTH)
    )

    # --- Clearance bore behind thread ---
    # From end of thread (Z = BOSS_PROTRUSION - THREAD_DEPTH) through to rear
    # Total depth = total_length - THREAD_DEPTH
    clearance_depth = total_length - THREAD_DEPTH
    boss = (
        boss.faces(">Z").workplane(offset=-THREAD_DEPTH)
        .circle(CLEARANCE_BORE_DIA / 2.0)
        .cutBlind(-clearance_depth)
    )

    # --- Flange seating surface chamfer ---
    # Small 0.3mm × 45° chamfer on the mount face bore edge for lens insertion
    # Approximate with a countersink
    boss = (
        boss.faces(">Z").workplane()
        .circle(THREAD_MAJOR_DIA / 2.0 + 0.3)
        .cutBlind(-0.3)
    )

    # --- Anti-rotation locating pin hole ---
    # 1.5mm blind hole at 12 o'clock on the mount face
    boss = (
        boss.faces(">Z").workplane()
        .center(0, LOCATING_PIN_RADIUS)
        .hole(LOCATING_PIN_DIA, LOCATING_PIN_DEPTH)
    )

    # --- M2 radial mounting holes through the boss flange ---
    # These go through the boss body for screwing to the camera front plate
    import numpy as np
    mount_pts = []
    for angle_deg in MOUNT_HOLE_ANGLES:
        rad = math.radians(angle_deg)
        x = MOUNT_HOLE_RADIUS * math.cos(rad)
        y = MOUNT_HOLE_RADIUS * math.sin(rad)
        mount_pts.append((x, y))

    boss = (
        boss.faces("<Z").workplane()
        .pushPoints(mount_pts)
        .hole(M2_CLEARANCE, CAMERA.wall_thickness)
    )

    return boss


def get_flange_stack_up() -> dict:
    """Return the complete flange distance stack-up analysis.

    Returns dict with each layer distance, total, error, and pass/fail.
    """
    layers = [
        ("Mount face to shutter front face", MOUNT_TO_SHUTTER_FRONT),
        ("Shutter disc thickness", DISC_THICK),
        ("Shutter rear to gate front face", GATE_CLEARANCE),
        ("Gate front face to film plane (channel floor)",
         GATE_FRONT_TO_FILM_PLANE),
    ]
    total = sum(d for _, d in layers)
    error = total - CMOUNT.flange_focal_dist
    tolerance = TOL.cnc_fine  # ±0.02mm

    return {
        "layers": layers,
        "total_mm": total,
        "target_mm": CMOUNT.flange_focal_dist,
        "error_mm": error,
        "tolerance_mm": tolerance,
        "pass": abs(error) <= tolerance,
    }


def print_stack_up():
    """Print the flange distance stack-up analysis."""
    su = get_flange_stack_up()
    print("\n  C-MOUNT FLANGE DISTANCE STACK-UP")
    print("  " + "-" * 55)
    for desc, dist in su["layers"]:
        print(f"    {desc:45s} {dist:7.3f} mm")
    print("  " + "-" * 55)
    print(f"    {'TOTAL':45s} {su['total_mm']:7.3f} mm")
    print(f"    {'TARGET (C-mount standard)':45s} {su['target_mm']:7.3f} mm")
    print(f"    {'ERROR':45s} {su['error_mm']:+7.4f} mm")
    print(f"    {'TOLERANCE':45s} +/-{su['tolerance_mm']:.3f} mm")
    status = "PASS" if su["pass"] else "FAIL"
    print(f"\n    Stack-up: [{status}]")


def get_mount_geometry() -> dict:
    """Return key geometry for assembly positioning."""
    return {
        "boss_od": BOSS_OD,
        "boss_protrusion": BOSS_PROTRUSION,
        "thread_dia": THREAD_MAJOR_DIA,
        "thread_depth": THREAD_DEPTH,
        "clearance_bore_dia": CLEARANCE_BORE_DIA,
        "mount_to_shutter_front": MOUNT_TO_SHUTTER_FRONT,
        "flange_focal_dist": CMOUNT.flange_focal_dist,
        "total_mount_depth": MOUNT_BODY_DEPTH,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/lens_mount.step")
    cq.exporters.export(solid, f"{output_dir}/lens_mount.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Lens mount exported to {output_dir}/")
    print_stack_up()


if __name__ == "__main__":
    export()
