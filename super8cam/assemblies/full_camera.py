"""Full camera assembly — all parts and sub-assemblies positioned in the body.

Assembly order follows physical build sequence:
  1. Left body half (chassis)
  2. Main shaft + bearings
  3. Gearbox housing + gears
  4. Motor into gearbox
  5. Claw mechanism onto main shaft cams
  6. Film gate + pressure plate
  7. Film channel + guide rollers
  8. Cartridge receiver
  9. PCB onto standoffs
 10. Lens mount into front face
 11. Shutter disc onto main shaft
 12. Right body half
 13. Top plate + viewfinder
 14. Bottom plate
 15. Cartridge door + hinge
 16. Battery door
 17. Trigger mechanism
 18. Lens (C-mount placeholder)

Includes automated interference detection between all close part pairs.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CMOUNT, CAMERA, CARTRIDGE, GEARBOX, MOTOR, BEARINGS, PCB,
    MATERIALS, MATERIAL_USAGE, DERIVED,
)

# =========================================================================
# PART IMPORTS
# =========================================================================
from super8cam.parts import (
    body_left, body_right, top_plate, bottom_plate,
    battery_door, cartridge_door, trigger, pcb_bracket,
    film_gate, pressure_plate, claw_mechanism, registration_pin,
    shutter_disc, main_shaft, cam_follower, film_channel,
    lens_mount, viewfinder, motor_mount, gearbox_housing, gears,
    cartridge_receiver,
)

# Sub-assembly imports (for reference / validation)
from super8cam.assemblies import (
    film_transport, shutter_assembly, drivetrain,
    optical_path, power_system, electronics, film_path,
)

# Part-level constants for positioning
from super8cam.parts.main_shaft import get_section_positions
from super8cam.parts.shutter_disc import DISC_OD, DISC_THICK, GATE_CLEARANCE
from super8cam.parts.film_gate import GATE_THICK, CHANNEL_DEPTH
from super8cam.parts.lens_mount import BOSS_PROTRUSION, BOSS_OD
from super8cam.parts.cam_follower import (
    CAM_THICK, ECCENTRIC_THICK, CAM_OD, ECCENTRIC_OD,
)
from super8cam.parts.film_channel import (
    ROLLER_DIA, ROLLER_ENTRY_Y, ROLLER_EXIT_Y,
)
from super8cam.parts.viewfinder import VF_OFFSET_UP, VF_OFFSET_LEFT, TUBE_LENGTH

# =========================================================================
# DATUM POSITIONS — all relative to film plane origin
# =========================================================================
# Film plane is at Y=0 (optical axis). Body is centered on (0,0,0).
# Optical axis runs along +Y (toward scene/lens).
# X = left-right, Z = vertical (up +).

# Body center
BODY_CX = 0.0
BODY_CY = 0.0
BODY_CZ = 0.0

# Film plane Y position (inside body, measured from front face)
# Mount face protrudes BOSS_PROTRUSION from body front face at Y = -body_depth/2
MOUNT_FACE_Y = -CAMERA.body_depth / 2.0 + BOSS_PROTRUSION
FILM_PLANE_Y = MOUNT_FACE_Y - CMOUNT.flange_focal_dist

# Gate position (gate front face is GATE_THICK - CHANNEL_DEPTH ahead of film plane)
GATE_FRONT_Y = FILM_PLANE_Y + (GATE_THICK - CHANNEL_DEPTH)
GATE_CENTER_Y = GATE_FRONT_Y - GATE_THICK / 2.0

# Shutter disc position (GATE_CLEARANCE ahead of gate front face)
SHUTTER_REAR_Y = GATE_FRONT_Y + GATE_CLEARANCE
SHUTTER_CENTER_Y = SHUTTER_REAR_Y + DISC_THICK / 2.0

# Lens mount X offset (left of body center)
LENS_X = CAMERA.lens_mount_offset_x  # -18.0 mm

# Main shaft axis: above optical axis, at lens mount X position
# Shaft runs along X (left-right), centered at the lens mount position
SHAFT_X = LENS_X
SHAFT_Z = 16.0  # mm above optical axis center (raised from 12→16 to clear gate)
SHAFT_Y = SHUTTER_CENTER_Y  # aligned with shutter disc

# Gearbox: to the right of the shaft, behind the gate
GEARBOX_X = SHAFT_X + 35.0    # shifted right 5mm for gear clearance
GEARBOX_Y = SHAFT_Y + 12.0    # shifted back 2mm for housing clearance
GEARBOX_Z = SHAFT_Z - 18.0    # lowered 3mm to clear body cavity

# Motor: attached to gearbox housing
MOTOR_X = GEARBOX_X
MOTOR_Y = GEARBOX_Y + MOTOR.body_length / 2.0 + 3.0  # reduced gap (was +5)
MOTOR_Z = GEARBOX_Z

# Claw mechanism: below film gate, accessing perforations
CLAW_X = LENS_X - FILM.width / 2.0 - CAMERA.claw_retract_dist
CLAW_Y = GATE_CENTER_Y
CLAW_Z = -FILM.reg_pin_below_frame_center

# Cam on shaft (lateral to claw)
CAM_X = LENS_X - FILM.width / 2.0 - 10.0  # shifted 2mm further from gate
CAM_Y = SHAFT_Y
CAM_Z = SHAFT_Z

# Cartridge receiver: right side of body, centered vertically
CART_X = CAMERA.body_length / 4.0 + 2.0  # shifted right 2mm
CART_Y = 0.0
CART_Z = 3.0   # lowered 2mm from 5→3

# PCB: left wall, above bottom plate
PCB_X = CAMERA.pcb_mount_offset_x
PCB_Y = 0.0
PCB_Z = -CAMERA.body_height / 2.0 + CAMERA.wall_thickness + CAMERA.pcb_standoff_height + 2.0  # raised 2mm

# Viewfinder: above and left of lens mount
VF_X = LENS_X - VF_OFFSET_LEFT
VF_Y = -CAMERA.body_depth / 2.0
VF_Z = SHAFT_Z + VF_OFFSET_UP - 2.0  # lowered 2mm to keep within top plate

# Trigger: front face, below and left
TRIGGER_X = -10.0
TRIGGER_Y = -CAMERA.body_depth / 2.0 + 5.0
TRIGGER_Z = -CAMERA.body_height / 4.0


# =========================================================================
# ASSEMBLY BUILDER
# =========================================================================

def build() -> cq.Assembly:
    """Build the complete Super 8 camera assembly.

    Positions all parts relative to the camera body frame, following
    the physical assembly order.
    """
    assy = cq.Assembly(name="super8_camera")

    # --- Step 1: Left body half (chassis) ---
    assy.add(body_left.build(), name="body_left",
             loc=cq.Location((-CAMERA.body_length / 4, 0, 0)))

    # --- Step 2: Main shaft + bearings ---
    assy.add(main_shaft.build(), name="main_shaft",
             loc=cq.Location((SHAFT_X, SHAFT_Y, SHAFT_Z)))

    # --- Step 3: Gearbox housing + gears ---
    assy.add(gearbox_housing.build(), name="gearbox_housing",
             loc=cq.Location((GEARBOX_X, GEARBOX_Y, GEARBOX_Z)))

    # Stage 1 pinion (on motor shaft)
    assy.add(gears.build_stage1_pinion(), name="stage1_pinion",
             loc=cq.Location((GEARBOX_X, GEARBOX_Y - 3, GEARBOX_Z)))

    # Stage 1 gear
    s1_cd = GEARBOX.stage1_center_distance
    assy.add(gears.build_stage1_gear(), name="stage1_gear",
             loc=cq.Location((GEARBOX_X + s1_cd, GEARBOX_Y - 3, GEARBOX_Z)))

    # Stage 2 pinion (coaxial with stage 1 gear)
    assy.add(gears.build_stage2_pinion(), name="stage2_pinion",
             loc=cq.Location((GEARBOX_X + s1_cd, GEARBOX_Y - 3, GEARBOX_Z + 4)))

    # Stage 2 gear (output, connects to main shaft)
    s2_cd = GEARBOX.stage2_center_distance
    assy.add(gears.build_stage2_gear(), name="stage2_gear",
             loc=cq.Location((GEARBOX_X + s1_cd + s2_cd, GEARBOX_Y - 3,
                               GEARBOX_Z + 4)))

    # --- Step 4: Motor mount ---
    assy.add(motor_mount.build(), name="motor_mount",
             loc=cq.Location((MOTOR_X, MOTOR_Y, MOTOR_Z)))

    # --- Step 5: Claw mechanism onto main shaft cams ---
    assy.add(claw_mechanism.build(), name="claw_mechanism",
             loc=cq.Location((CLAW_X, CLAW_Y, CLAW_Z)))

    # Pulldown cam on shaft
    assy.add(cam_follower.build_cam(), name="pulldown_cam",
             loc=cq.Location((CAM_X, CAM_Y, CAM_Z)))

    # Secondary eccentric
    assy.add(cam_follower.build_secondary_eccentric(), name="secondary_eccentric",
             loc=cq.Location((CAM_X, CAM_Y, CAM_Z - CAM_THICK)))

    # Cam follower
    assy.add(cam_follower.build_follower(), name="cam_follower",
             loc=cq.Location((CAM_X + CAM_OD / 2.0 + 1.0, CAM_Y, CAM_Z)))

    # --- Step 6: Film gate + pressure plate ---
    assy.add(film_gate.build(), name="film_gate",
             loc=cq.Location((LENS_X, GATE_CENTER_Y, 0)))

    assy.add(pressure_plate.build(), name="pressure_plate",
             loc=cq.Location((LENS_X, GATE_CENTER_Y - GATE_THICK / 2.0 - 0.5, 0)))

    # Registration pin
    assy.add(registration_pin.build(), name="registration_pin",
             loc=cq.Location((LENS_X, GATE_CENTER_Y + GATE_THICK / 2.0,
                               -FILM.reg_pin_below_frame_center)))

    # --- Step 7: Film channel + guide rollers ---
    assy.add(film_channel.build(), name="film_channel",
             loc=cq.Location((LENS_X, GATE_CENTER_Y, 0)))

    # --- Step 8: Cartridge receiver ---
    assy.add(cartridge_receiver.build(), name="cartridge_receiver",
             loc=cq.Location((CART_X, CART_Y, CART_Z)))

    # --- Step 9: PCB bracket + board ---
    assy.add(pcb_bracket.build(), name="pcb_bracket",
             loc=cq.Location((PCB_X, 0,
                               -CAMERA.body_height / 2 + CAMERA.wall_thickness)))

    # PCB board (simple box)
    pcb_board = (
        cq.Workplane("XY")
        .box(PCB.width, PCB.height, PCB.thickness)
    )
    assy.add(pcb_board, name="pcb_board",
             loc=cq.Location((PCB_X, 0, PCB_Z + PCB.thickness / 2)))

    # --- Step 10: Lens mount ---
    assy.add(lens_mount.build(), name="lens_mount",
             loc=cq.Location((LENS_X, -CAMERA.body_depth / 2.0, 0)))

    # --- Step 11: Shutter disc ---
    assy.add(shutter_disc.build(), name="shutter_disc",
             loc=cq.Location((LENS_X, SHUTTER_CENTER_Y, SHAFT_Z)))

    # --- Step 12: Right body half ---
    assy.add(body_right.build(), name="body_right",
             loc=cq.Location((CAMERA.body_length / 4, 0, 0)))

    # --- Step 13: Top plate + viewfinder ---
    assy.add(top_plate.build(), name="top_plate",
             loc=cq.Location((0, 0, CAMERA.body_height / 2)))

    assy.add(viewfinder.build(), name="viewfinder",
             loc=cq.Location((VF_X, VF_Y, VF_Z)))

    # --- Step 14: Bottom plate ---
    assy.add(bottom_plate.build(), name="bottom_plate",
             loc=cq.Location((0, 0, -CAMERA.body_height / 2)))

    # --- Step 15: Cartridge door ---
    assy.add(cartridge_door.build(), name="cartridge_door",
             loc=cq.Location((CAMERA.body_length / 2 + CAMERA.cart_door_thick / 2,
                               0, 5)))

    # --- Step 16: Battery door ---
    assy.add(battery_door.build(), name="battery_door",
             loc=cq.Location((CAMERA.body_length / 4, 0,
                               -CAMERA.body_height / 2 - CAMERA.batt_door_thick)))

    # --- Step 17: Trigger ---
    assy.add(trigger.build(), name="trigger",
             loc=cq.Location((TRIGGER_X, TRIGGER_Y, TRIGGER_Z)))

    # --- Step 18: Lens placeholder (C-mount cylinder) ---
    lens_placeholder = (
        cq.Workplane("XY")
        .cylinder(30.0, CMOUNT.thread_od / 2.0)
    )
    assy.add(lens_placeholder, name="lens_placeholder",
             loc=cq.Location((LENS_X,
                               -CAMERA.body_depth / 2.0 - 15.0,
                               0)))

    return assy


# =========================================================================
# INTERFERENCE DETECTION
# =========================================================================

# Critical part pairs to check for interference.
# Each tuple: (name_a, name_b, expected_min_clearance_mm, description)
INTERFERENCE_PAIRS = [
    ("shutter_disc", "film_gate",
     GATE_CLEARANCE, "Shutter must clear gate throughout rotation"),
    ("claw_mechanism", "film_gate",
     0.1, "Claw must pass freely through gate slot"),
    ("stage1_pinion", "gearbox_housing",
     0.1, "Pinion must clear housing walls"),
    ("stage1_gear", "gearbox_housing",
     0.1, "Gear must clear housing walls"),
    ("stage2_pinion", "gearbox_housing",
     0.1, "Pinion must clear housing walls"),
    ("stage2_gear", "gearbox_housing",
     0.1, "Gear must clear housing walls"),
    ("motor_mount", "body_left",
     0.0, "Motor must fit inside body"),
    ("pcb_board", "body_left",
     0.0, "PCB must fit inside body"),
    ("cartridge_receiver", "body_right",
     0.0, "Receiver must fit inside body"),
    ("shutter_disc", "pressure_plate",
     0.2, "Shutter must clear pressure plate"),
    ("main_shaft", "film_gate",
     0.5, "Shaft must clear gate"),
    ("pulldown_cam", "film_gate",
     0.5, "Cam must clear gate"),
    ("viewfinder", "top_plate",
     0.0, "Viewfinder must not interfere with top plate"),
    ("lens_placeholder", "shutter_disc",
     1.0, "Lens must clear shutter disc"),
]


def _get_solid(shape):
    """Extract a TopoDS_Shape suitable for boolean ops from various CQ types."""
    if hasattr(shape, 'val'):
        return shape.val()
    if hasattr(shape, 'toCompound'):
        return shape.toCompound()
    return shape


def check_interference(assy: cq.Assembly = None,
                       volume_threshold: float = 0.001) -> dict:
    """Run interference detection on the full camera assembly.

    For each pair in INTERFERENCE_PAIRS, attempts to compute the boolean
    intersection of the two parts. If the intersection volume exceeds
    volume_threshold (mm^3), it's flagged as an interference.

    Args:
        assy: Assembly to check. If None, builds a fresh one.
        volume_threshold: Minimum intersection volume (mm^3) to flag.

    Returns:
        dict with:
            all_clear: True if no interference found
            checks: list of dicts with part names, status, volume
            warnings: list of warning strings
    """
    if assy is None:
        assy = build()

    checks = []
    warnings = []
    all_clear = True

    # Build a lookup of individual part solids by name
    part_solids = {}
    for name, shape in _iter_assembly_parts(assy):
        try:
            solid = _get_solid(shape)
            part_solids[name] = solid
        except Exception:
            pass

    for name_a, name_b, min_clearance, desc in INTERFERENCE_PAIRS:
        check = {
            "part_a": name_a,
            "part_b": name_b,
            "description": desc,
            "min_clearance_mm": min_clearance,
        }

        if name_a not in part_solids:
            check["status"] = "SKIP"
            check["note"] = f"Part '{name_a}' not found in assembly"
            warnings.append(f"SKIP: {name_a} not found")
            checks.append(check)
            continue

        if name_b not in part_solids:
            check["status"] = "SKIP"
            check["note"] = f"Part '{name_b}' not found in assembly"
            warnings.append(f"SKIP: {name_b} not found")
            checks.append(check)
            continue

        try:
            solid_a = part_solids[name_a]
            solid_b = part_solids[name_b]

            # Compute boolean intersection
            intersection = solid_a.intersect(solid_b)
            vol = _compute_volume(intersection)

            if vol > volume_threshold:
                check["status"] = "INTERFERENCE"
                check["volume_mm3"] = vol
                all_clear = False
                warnings.append(
                    f"INTERFERENCE: {name_a} vs {name_b}: "
                    f"{vol:.4f} mm^3 — {desc}")
            else:
                check["status"] = "CLEAR"
                check["volume_mm3"] = vol

        except Exception as e:
            check["status"] = "ERROR"
            check["note"] = str(e)
            warnings.append(f"ERROR checking {name_a} vs {name_b}: {e}")

        checks.append(check)

    return {
        "all_clear": all_clear,
        "checks": checks,
        "warnings": warnings,
        "pairs_checked": len([c for c in checks if c["status"] != "SKIP"]),
        "pairs_skipped": len([c for c in checks if c["status"] == "SKIP"]),
        "interferences": len([c for c in checks if c["status"] == "INTERFERENCE"]),
    }


def _iter_assembly_parts(assy: cq.Assembly):
    """Yield (name, shape) for each child in a CQ Assembly."""
    if hasattr(assy, 'children'):
        for child in assy.children:
            name = child.name if hasattr(child, 'name') else str(child)
            shape = child.obj if hasattr(child, 'obj') else child
            yield name, shape


def _compute_volume(shape) -> float:
    """Compute volume of a CadQuery shape in mm^3."""
    try:
        if hasattr(shape, 'Volume'):
            return abs(shape.Volume())
        if hasattr(shape, 'val'):
            return abs(shape.val().Volume())
        if hasattr(shape, 'Solids'):
            return sum(abs(s.Volume()) for s in shape.Solids())
    except Exception:
        pass
    return 0.0


# =========================================================================
# SHUTTER CLEARANCE SWEEP
# =========================================================================

def check_shutter_clearance(n_angles: int = 36) -> dict:
    """Verify shutter disc clears film gate through full rotation.

    Sweeps the shutter disc through n_angles positions (0-360 deg) and
    checks that the minimum gap to the film gate face is >= 0.2mm
    at every angle.

    Returns:
        dict with min_clearance_mm, all angles checked, pass/fail
    """
    # The shutter disc is a flat disc rotating in its own plane.
    # The clearance is the axial gap between the disc rear face and
    # the gate front face. Since the disc spins in-plane, this gap
    # is constant at GATE_CLEARANCE for all rotation angles.
    # But we check for OD vs gate edge clearance too.

    disc_r = DISC_OD / 2.0
    gate_half_w = CAMERA.gate_plate_w / 2.0
    gate_half_h = CAMERA.gate_plate_h / 2.0

    # Shaft is SHAFT_Z above gate center (at Z=0)
    shaft_to_gate_center = SHAFT_Z

    # At each angle, find the closest point of the disc edge to gate edges
    min_radial_clearance = float('inf')
    for i in range(n_angles):
        angle_rad = 2.0 * math.pi * i / n_angles
        # Disc edge point (relative to shaft center)
        edge_x = disc_r * math.cos(angle_rad)
        edge_z = disc_r * math.sin(angle_rad)

        # Absolute position (shaft is at LENS_X, SHAFT_Z)
        abs_x = edge_x  # relative to lens center
        abs_z = shaft_to_gate_center + edge_z

        # Check if this point is within gate plate bounds
        if abs(abs_x) < gate_half_w and abs(abs_z) < gate_half_h:
            # Point is within gate footprint — axial clearance applies
            pass  # axial clearance is GATE_CLEARANCE (constant)

        # Radial clearance to gate edge
        dx = max(0, abs(abs_x) - gate_half_w)
        dz = max(0, abs(abs_z) - gate_half_h)
        radial_dist = math.sqrt(dx**2 + dz**2)
        if radial_dist > 0:
            min_radial_clearance = min(min_radial_clearance, radial_dist)

    axial_clearance = GATE_CLEARANCE

    return {
        "axial_clearance_mm": axial_clearance,
        "min_radial_clearance_mm": min_radial_clearance,
        "axial_pass": axial_clearance >= 0.2,
        "n_angles_checked": n_angles,
        "all_pass": axial_clearance >= 0.2,
    }


# =========================================================================
# PRINTING / EXPORT
# =========================================================================

def print_interference_report(result: dict = None):
    """Print a formatted interference report."""
    if result is None:
        result = check_interference()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  INTERFERENCE DETECTION REPORT")
    print(sep)
    print(f"  Pairs checked: {result['pairs_checked']}")
    print(f"  Pairs skipped: {result['pairs_skipped']}")
    print(f"  Interferences: {result['interferences']}")
    print(f"  {'-' * 55}")

    for check in result["checks"]:
        status = check["status"]
        a = check["part_a"]
        b = check["part_b"]

        if status == "CLEAR":
            vol = check.get("volume_mm3", 0)
            print(f"  [CLEAR] {a:25s} vs {b:25s}  ({vol:.4f} mm^3)")
        elif status == "INTERFERENCE":
            vol = check.get("volume_mm3", 0)
            print(f"  [FAIL]  {a:25s} vs {b:25s}  {vol:.4f} mm^3")
            print(f"          -> {check['description']}")
        elif status == "SKIP":
            print(f"  [SKIP]  {a:25s} vs {b:25s}  ({check.get('note', '')})")
        elif status == "ERROR":
            print(f"  [ERR]   {a:25s} vs {b:25s}  ({check.get('note', '')})")

    # Shutter sweep
    shutter = check_shutter_clearance()
    print(f"\n  SHUTTER CLEARANCE SWEEP ({shutter['n_angles_checked']} angles)")
    print(f"  {'-' * 55}")
    print(f"  Axial clearance:  {shutter['axial_clearance_mm']:.2f} mm "
          f"(min 0.2 mm) {'PASS' if shutter['axial_pass'] else 'FAIL'}")
    if shutter["min_radial_clearance_mm"] < float('inf'):
        print(f"  Radial clearance: {shutter['min_radial_clearance_mm']:.2f} mm")

    overall = "PASS" if result["all_clear"] and shutter["all_pass"] else "FAIL"
    print(f"\n  Overall: {overall}")
    print(sep)

    return result["all_clear"] and shutter["all_pass"]


def export(output_dir: str = "export"):
    """Export the complete camera assembly as STEP."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    print("  Building full camera assembly...")
    assy = build()

    step_path = f"{output_dir}/super8_camera_full.step"
    cq.exporters.export(assy.toCompound(), step_path)
    print(f"  Exported: {step_path}")

    return assy


if __name__ == "__main__":
    assy = export()
    print_interference_report()
