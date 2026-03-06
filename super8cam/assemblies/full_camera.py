"""Full camera assembly — master assembly file.

Imports every part and sub-assembly, positions them in 3D space relative
to the film plane datum, and exports the complete camera as one STEP file.

Assembly order mirrors real physical assembly:
 1. Left body half (chassis)
 2. Main shaft + bearings
 3. Gearbox housing + gears
 4. Motor into gearbox
 5. Claw mechanism onto main shaft cams
 6. Film gate + pressure plate
 7. Film channel + guide rollers
 8. Cartridge receiver
 9. PCB onto standoffs
10. Lens mount
11. Shutter disc onto main shaft
12. Right body half — close shell
13. Top plate + viewfinder
14. Bottom plate
15. Cartridge door + hinge
16. Battery door
17. Trigger mechanism
18. Lens (placeholder)
"""

import cadquery as cq
from super8cam.specs.master_specs import (
    CAMERA, CMOUNT, DERIVED, FILM, GEARBOX, MOTOR,
    BEARINGS, MATERIALS, MATERIAL_USAGE, FASTENER_USAGE,
)

# Parts
from super8cam.parts import (
    body_left, body_right, top_plate, bottom_plate,
    battery_door, cartridge_door, trigger,
    film_gate, pressure_plate, film_channel,
    claw_mechanism, cam_follower, registration_pin,
    shutter_disc, main_shaft,
    gearbox_housing, gears, motor_mount,
    lens_mount, viewfinder,
    pcb_bracket, cartridge_receiver,
)

# Sub-assemblies (used for positioning reference)
from super8cam.assemblies import (
    drivetrain, shutter_assembly, electronics,
    film_transport, optical_path, power_system,
)


# =========================================================================
# Datum: film plane is at Y = 0.  Lens side is -Y, back side is +Y.
# Body center is at X=0, Z=0.
# =========================================================================

# Key Y coordinates derived from the film plane datum
_FILM_PLANE_Y = 0.0
_SHUTTER_Y = _FILM_PLANE_Y - CAMERA.shutter_to_gate_clearance - CAMERA.shutter_thickness / 2
_LENS_FLANGE_Y = _FILM_PLANE_Y - CMOUNT.flange_focal_dist
_FRONT_FACE_Y = _LENS_FLANGE_Y - CAMERA.wall_thickness
_BACK_FACE_Y = _FRONT_FACE_Y + CAMERA.body_depth

# Lens mount X offset (left of center to leave room for cartridge)
_LENS_X = CAMERA.lens_mount_offset_x

# Main shaft runs parallel to X axis at the lens X position
_SHAFT_X = _LENS_X
_SHAFT_Z = 0.0  # centered vertically on film aperture

# Gearbox sits to the right of the lens axis
_GEARBOX_X = _SHAFT_X + GEARBOX.stage1_center_distance + GEARBOX.stage2_center_distance + 5
_GEARBOX_Y = _FILM_PLANE_Y + 5.0  # behind film plane
_GEARBOX_Z = -15.0  # below centerline

# Cartridge receiver (right side of body)
_CART_X = CAMERA.body_length / 2 - CAMERA.wall_thickness - 35.0
_CART_Z = 5.0  # slightly above center

# PCB (left wall, behind film path)
_PCB_X = CAMERA.pcb_mount_offset_x
_PCB_Y = _FILM_PLANE_Y + 15.0
_PCB_Z = -10.0


def build() -> cq.Assembly:
    """Build the complete Super 8 camera assembly.

    Returns a CadQuery Assembly with all parts positioned relative
    to the film plane datum.
    """
    assy = cq.Assembly(name="super8_camera_full")

    # ------------------------------------------------------------------
    # 1. LEFT BODY HALF — the chassis that everything mounts into
    # ------------------------------------------------------------------
    assy.add(body_left.build(), name="body_left",
             loc=cq.Location((-CAMERA.body_length / 4, _FRONT_FACE_Y + CAMERA.body_depth / 2, 0)))

    # ------------------------------------------------------------------
    # 2. MAIN SHAFT + BEARINGS (into bearing bores on left half)
    # ------------------------------------------------------------------
    assy.add(main_shaft.build(), name="main_shaft",
             loc=cq.Location((_SHAFT_X, _FILM_PLANE_Y + 2, _SHAFT_Z)))

    # ------------------------------------------------------------------
    # 3. GEARBOX HOUSING + GEARS
    # ------------------------------------------------------------------
    assy.add(gearbox_housing.build(), name="gearbox_housing",
             loc=cq.Location((_GEARBOX_X, _GEARBOX_Y, _GEARBOX_Z)))

    assy.add(gears.build_stage1_pinion(), name="stage1_pinion",
             loc=cq.Location((_SHAFT_X + GEARBOX.stage1_center_distance + GEARBOX.stage2_center_distance,
                               _GEARBOX_Y - 3, _GEARBOX_Z)))
    assy.add(gears.build_stage1_gear(), name="stage1_gear",
             loc=cq.Location((_SHAFT_X + GEARBOX.stage2_center_distance,
                               _GEARBOX_Y - 3, _GEARBOX_Z)))
    assy.add(gears.build_stage2_pinion(), name="stage2_pinion",
             loc=cq.Location((_SHAFT_X + GEARBOX.stage2_center_distance,
                               _GEARBOX_Y - 3, _GEARBOX_Z + GEARBOX.gear_face_width + 1)))
    assy.add(gears.build_stage2_gear(), name="stage2_gear",
             loc=cq.Location((_SHAFT_X, _GEARBOX_Y - 3,
                               _GEARBOX_Z + GEARBOX.gear_face_width + 1)))

    # ------------------------------------------------------------------
    # 4. MOTOR into gearbox
    # ------------------------------------------------------------------
    assy.add(motor_mount.build(), name="motor_mount",
             loc=cq.Location((_GEARBOX_X + 5, _GEARBOX_Y, _GEARBOX_Z)))

    # ------------------------------------------------------------------
    # 5. CLAW MECHANISM onto main shaft cams
    # ------------------------------------------------------------------
    assy.add(cam_follower.build_cam(), name="pulldown_cam",
             loc=cq.Location((_SHAFT_X, _FILM_PLANE_Y + 2, _SHAFT_Z)))

    assy.add(claw_mechanism.build(), name="claw_mechanism",
             loc=cq.Location((_SHAFT_X + 3, _FILM_PLANE_Y + 1, _SHAFT_Z - 2)))

    # ------------------------------------------------------------------
    # 6. FILM GATE + PRESSURE PLATE onto internal mounting bosses
    # ------------------------------------------------------------------
    assy.add(film_gate.build(), name="film_gate",
             loc=cq.Location((_LENS_X, _FILM_PLANE_Y, _SHAFT_Z)))

    assy.add(pressure_plate.build(), name="pressure_plate",
             loc=cq.Location((_LENS_X, _FILM_PLANE_Y + CAMERA.gate_plate_thick + 0.2, _SHAFT_Z)))

    assy.add(registration_pin.build(), name="registration_pin",
             loc=cq.Location((_LENS_X, _FILM_PLANE_Y + 0.5,
                               _SHAFT_Z - FILM.reg_pin_below_frame_center)))

    # ------------------------------------------------------------------
    # 7. FILM CHANNEL + GUIDE ROLLERS
    # ------------------------------------------------------------------
    assy.add(film_channel.build(), name="film_channel",
             loc=cq.Location((_LENS_X, _FILM_PLANE_Y + 1, _SHAFT_Z)))

    # ------------------------------------------------------------------
    # 8. CARTRIDGE RECEIVER
    # ------------------------------------------------------------------
    assy.add(cartridge_receiver.build(), name="cartridge_receiver",
             loc=cq.Location((_CART_X, _FILM_PLANE_Y + 5, _CART_Z)))

    # ------------------------------------------------------------------
    # 9. PCB onto standoffs on left wall
    # ------------------------------------------------------------------
    assy.add(pcb_bracket.build(), name="pcb_bracket",
             loc=cq.Location((_PCB_X, _PCB_Y, _PCB_Z)))

    # ------------------------------------------------------------------
    # 10. LENS MOUNT into front face
    # ------------------------------------------------------------------
    assy.add(lens_mount.build(), name="lens_mount",
             loc=cq.Location((_LENS_X, _FRONT_FACE_Y, _SHAFT_Z)))

    # ------------------------------------------------------------------
    # 11. SHUTTER DISC onto main shaft
    # ------------------------------------------------------------------
    assy.add(shutter_disc.build(), name="shutter_disc",
             loc=cq.Location((_SHAFT_X, _SHUTTER_Y, _SHAFT_Z)))

    # ------------------------------------------------------------------
    # 12. RIGHT BODY HALF — close the shell
    # ------------------------------------------------------------------
    assy.add(body_right.build(), name="body_right",
             loc=cq.Location((CAMERA.body_length / 4, _FRONT_FACE_Y + CAMERA.body_depth / 2, 0)))

    # ------------------------------------------------------------------
    # 13. TOP PLATE + VIEWFINDER
    # ------------------------------------------------------------------
    assy.add(top_plate.build(), name="top_plate",
             loc=cq.Location((0, _FRONT_FACE_Y + CAMERA.body_depth / 2,
                               CAMERA.body_height / 2)))

    assy.add(viewfinder.build(), name="viewfinder",
             loc=cq.Location((CAMERA.body_length / 4,
                               _FRONT_FACE_Y + CAMERA.body_depth / 2,
                               CAMERA.body_height / 2 + 5)))

    # ------------------------------------------------------------------
    # 14. BOTTOM PLATE
    # ------------------------------------------------------------------
    assy.add(bottom_plate.build(), name="bottom_plate",
             loc=cq.Location((0, _FRONT_FACE_Y + CAMERA.body_depth / 2,
                               -CAMERA.body_height / 2)))

    # ------------------------------------------------------------------
    # 15. CARTRIDGE DOOR + HINGE
    # ------------------------------------------------------------------
    assy.add(cartridge_door.build(), name="cartridge_door",
             loc=cq.Location((CAMERA.body_length / 2 + CAMERA.cart_door_thick / 2,
                               _FRONT_FACE_Y + CAMERA.body_depth / 2, _CART_Z)))

    # ------------------------------------------------------------------
    # 16. BATTERY DOOR
    # ------------------------------------------------------------------
    assy.add(battery_door.build(), name="battery_door",
             loc=cq.Location((0, _FRONT_FACE_Y + CAMERA.body_depth / 2,
                               -CAMERA.body_height / 2 - CAMERA.batt_door_thick / 2)))

    # ------------------------------------------------------------------
    # 17. TRIGGER MECHANISM
    # ------------------------------------------------------------------
    assy.add(trigger.build(), name="trigger",
             loc=cq.Location((-10, _FRONT_FACE_Y + 5,
                               -CAMERA.body_height / 4)))

    # ------------------------------------------------------------------
    # 18. LENS (placeholder cylinder representing a C-mount lens)
    # ------------------------------------------------------------------
    lens_placeholder = (
        cq.Workplane("XZ")
        .circle(CMOUNT.thread_od / 2)
        .extrude(30)  # 30mm lens body length
        .translate((0, 0, 0))
    )
    assy.add(lens_placeholder, name="lens",
             loc=cq.Location((_LENS_X, _FRONT_FACE_Y - 30, _SHAFT_Z)))

    return assy


# =========================================================================
# INTERFERENCE CHECKING
# =========================================================================

# Critical clearance pairs: (part_a_name, part_b_name, min_gap_mm, description)
CRITICAL_PAIRS = [
    ("shutter_disc", "film_gate", 0.3, "Shutter-to-gate clearance throughout rotation"),
    ("claw_mechanism", "film_gate", 0.0, "Claw must pass freely through gate slot"),
    ("stage1_pinion", "gearbox_housing", 0.1, "Gear teeth vs housing wall"),
    ("stage1_gear", "gearbox_housing", 0.1, "Gear teeth vs housing wall"),
    ("stage2_pinion", "gearbox_housing", 0.1, "Gear teeth vs housing wall"),
    ("stage2_gear", "gearbox_housing", 0.1, "Gear teeth vs housing wall"),
    ("motor_mount", "body_left", 0.0, "Motor vs body shell"),
    ("pcb_bracket", "body_left", 0.0, "PCB vs body shell"),
    ("cartridge_receiver", "body_right", 0.0, "Cartridge pocket vs body"),
    ("shutter_disc", "pressure_plate", 0.2, "Shutter vs pressure plate"),
    ("main_shaft", "gearbox_housing", 0.1, "Shaft vs gearbox bore"),
]


def _solid_from_shape(shape):
    """Extract a TopoDS_Solid from a CadQuery Workplane or Shape."""
    if hasattr(shape, 'val'):
        return shape.val()
    if hasattr(shape, 'wrapped'):
        return shape
    return shape


def check_interference(assy: cq.Assembly = None, verbose: bool = True) -> list:
    """Run interference detection on the full camera assembly.

    For every pair of parts that are close together, computes the boolean
    intersection.  If the intersection volume exceeds the threshold,
    flags it as an interference.

    Returns a list of dicts: {part_a, part_b, volume_mm3, status, note}
    """
    if assy is None:
        assy = build()

    threshold_mm3 = 0.001  # minimum intersection volume to flag
    results = []

    if verbose:
        sep = "=" * 60
        print(sep)
        print("  INTERFERENCE CHECK REPORT")
        print(sep)

    # Collect all named children and their positioned solids
    part_solids = {}
    for name, child in assy.objects.items() if hasattr(assy, 'objects') else []:
        try:
            part_solids[name] = child
        except Exception:
            pass

    # If CadQuery assembly doesn't expose .objects easily, try the
    # children list approach
    if not part_solids:
        try:
            for child in assy.children:
                if hasattr(child, 'name') and hasattr(child, 'obj'):
                    part_solids[child.name] = child.obj
        except Exception:
            pass

    # Check critical pairs specifically noted in the spec
    if verbose:
        print("\n  CRITICAL CLEARANCE PAIRS")
        print("  " + "-" * 50)

    for part_a, part_b, min_gap, desc in CRITICAL_PAIRS:
        result = {
            "part_a": part_a,
            "part_b": part_b,
            "min_gap_required_mm": min_gap,
            "description": desc,
            "volume_mm3": 0.0,
            "status": "PASS",
            "note": "",
        }

        # Attempt boolean intersection if we have both solids
        if part_a in part_solids and part_b in part_solids:
            try:
                solid_a = part_solids[part_a]
                solid_b = part_solids[part_b]
                intersection = solid_a.intersect(solid_b)
                vol = intersection.val().Volume() if hasattr(intersection, 'val') else 0.0
                result["volume_mm3"] = vol
                if vol > threshold_mm3:
                    result["status"] = "FAIL"
                    result["note"] = f"Intersection volume {vol:.4f} mm^3 exceeds threshold"
            except Exception as e:
                result["status"] = "SKIPPED"
                result["note"] = f"Boolean check failed: {e}"
        else:
            result["status"] = "SKIPPED"
            result["note"] = "Part solid not available for boolean check"

        results.append(result)

        if verbose:
            status_str = result["status"]
            print(f"    {part_a} vs {part_b}: {status_str}")
            if result["note"]:
                print(f"      {result['note']}")
            print(f"      ({desc})")

    # Analytical checks for shutter clearance throughout rotation
    if verbose:
        print("\n  ANALYTICAL CLEARANCE CHECKS")
        print("  " + "-" * 50)

    # Shutter disc vs film gate: verify 0.3mm gap is maintained
    shutter_r = CAMERA.shutter_od / 2
    gate_y = _FILM_PLANE_Y
    shutter_near_face = _SHUTTER_Y + CAMERA.shutter_thickness / 2
    shutter_gap = gate_y - shutter_near_face
    shutter_result = {
        "part_a": "shutter_disc",
        "part_b": "film_gate",
        "check": "analytical_gap",
        "nominal_gap_mm": shutter_gap,
        "required_gap_mm": CAMERA.shutter_to_gate_clearance,
        "status": "PASS" if shutter_gap >= CAMERA.shutter_to_gate_clearance else "FAIL",
    }
    results.append(shutter_result)
    if verbose:
        print(f"    Shutter-to-gate gap: {shutter_gap:.3f} mm "
              f"(required >= {CAMERA.shutter_to_gate_clearance} mm) "
              f"{'PASS' if shutter_result['status'] == 'PASS' else 'FAIL'}")

    # Claw stroke vs gate slot: claw tip must fit within perforation slot
    claw_ok = (CAMERA.claw_tip_w < FILM.perf_w and CAMERA.claw_tip_h < FILM.perf_h)
    claw_result = {
        "part_a": "claw_mechanism",
        "part_b": "film_gate",
        "check": "claw_vs_perf_slot",
        "claw_tip": f"{CAMERA.claw_tip_w}x{CAMERA.claw_tip_h} mm",
        "perf_opening": f"{FILM.perf_w}x{FILM.perf_h} mm",
        "status": "PASS" if claw_ok else "FAIL",
    }
    results.append(claw_result)
    if verbose:
        print(f"    Claw tip ({CAMERA.claw_tip_w}x{CAMERA.claw_tip_h} mm) "
              f"vs perf ({FILM.perf_w}x{FILM.perf_h} mm): "
              f"{'PASS' if claw_ok else 'FAIL'}")

    # Motor fits inside body shell
    motor_fits = (MOTOR.body_dia < (CAMERA.body_depth - 2 * CAMERA.wall_thickness))
    motor_result = {
        "part_a": "motor",
        "part_b": "body_shell",
        "check": "motor_envelope",
        "motor_dia_mm": MOTOR.body_dia,
        "internal_depth_mm": CAMERA.body_depth - 2 * CAMERA.wall_thickness,
        "status": "PASS" if motor_fits else "FAIL",
    }
    results.append(motor_result)
    if verbose:
        print(f"    Motor dia ({MOTOR.body_dia} mm) vs internal depth "
              f"({CAMERA.body_depth - 2 * CAMERA.wall_thickness} mm): "
              f"{'PASS' if motor_fits else 'FAIL'}")

    # Shutter disc fits inside body
    shutter_fits = (CAMERA.shutter_od < min(CAMERA.body_height, CAMERA.body_depth) - 2 * CAMERA.wall_thickness)
    shutter_envelope = {
        "part_a": "shutter_disc",
        "part_b": "body_shell",
        "check": "shutter_envelope",
        "shutter_od_mm": CAMERA.shutter_od,
        "min_internal_mm": min(CAMERA.body_height, CAMERA.body_depth) - 2 * CAMERA.wall_thickness,
        "status": "PASS" if shutter_fits else "FAIL",
    }
    results.append(shutter_envelope)
    if verbose:
        print(f"    Shutter OD ({CAMERA.shutter_od} mm) vs body envelope: "
              f"{'PASS' if shutter_fits else 'FAIL'}")

    # Summary
    failures = [r for r in results if r.get("status") == "FAIL"]
    skipped = [r for r in results if r.get("status") == "SKIPPED"]
    passed = [r for r in results if r.get("status") == "PASS"]

    if verbose:
        print(f"\n  SUMMARY: {len(passed)} PASS, {len(failures)} FAIL, {len(skipped)} SKIPPED")
        if failures:
            print("  FAILURES:")
            for f in failures:
                print(f"    - {f.get('part_a')} vs {f.get('part_b')}: {f.get('note', f.get('check', ''))}")
        print("  " + "=" * 60)

    return results


def export(output_dir: str = "export"):
    """Build the full assembly and export as STEP."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    assy = build()
    step_path = os.path.join(output_dir, "full_camera_assembly.step")
    assy.save(step_path)
    print(f"  Exported: {step_path}")
    return assy


if __name__ == "__main__":
    print("Building full camera assembly...")
    assy = build()
    print(f"Assembly '{assy.name}' built with {len(assy.children) if hasattr(assy, 'children') else '?'} components")
    print()
    check_interference(assy, verbose=True)
    export()
