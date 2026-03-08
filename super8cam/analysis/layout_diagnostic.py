"""Layout diagnostic — analyse internal packing efficiency and envelope fit.

Builds every internal part, computes world-position bounding boxes (using
assembly offsets from full_camera.py), prints a formatted table, and checks
which parts exceed a target envelope.

Usage:
    conda run -n super8 python -m super8cam.analysis.layout_diagnostic
"""

from __future__ import annotations
import sys
from typing import Tuple

import cadquery as cq

from super8cam.specs.master_specs import CAMERA


# ---------------------------------------------------------------------------
# Part builders + assembly offsets (imported lazily to give clear errors)
# ---------------------------------------------------------------------------

def _build_parts() -> list[tuple[str, cq.Workplane, Tuple[float, float, float]]]:
    """Return (name, solid, (cx, cy, cz)) for every internal part."""
    from super8cam.parts import (
        body_left, body_right, top_plate, bottom_plate,
        film_gate, pressure_plate, claw_mechanism, registration_pin,
        shutter_disc, main_shaft, cam_follower, film_channel,
        lens_mount, viewfinder, motor_mount, gearbox_housing, gears,
        cartridge_receiver, trigger, pcb_bracket, battery_door, cartridge_door,
    )
    from super8cam.assemblies.full_camera import (
        SHAFT_X, SHAFT_Y, SHAFT_Z,
        GEARBOX_X, GEARBOX_Y, GEARBOX_Z,
        MOTOR_X, MOTOR_Y, MOTOR_Z,
        CLAW_X, CLAW_Y, CLAW_Z,
        CAM_X, CAM_Y, CAM_Z,
        CART_X, CART_Y, CART_Z,
        PCB_X, PCB_Z,
        VF_X, VF_Y, VF_Z,
        TRIGGER_X, TRIGGER_Y, TRIGGER_Z,
        LENS_X,
        GATE_CENTER_Y, SHUTTER_CENTER_Y,
    )
    from super8cam.specs.master_specs import (
        GEARBOX, MOTOR, PCB, CMOUNT, BEARINGS,
    )
    from super8cam.parts.film_gate import GATE_THICK
    from super8cam.parts.cam_follower import CAM_THICK, CAM_OD

    s1_cd = GEARBOX.stage1_center_distance
    s2_cd = GEARBOX.stage2_center_distance
    gear_cx = (s1_cd + s2_cd) / 2.0

    parts = [
        ("body_left",           body_left.build,                (0, 0, 0)),
        ("body_right",          body_right.build,               (0, 0, 0)),
        ("top_plate",           top_plate.build,                (0, 0, CAMERA.body_height / 2)),
        ("bottom_plate",        bottom_plate.build,             (0, 0, -CAMERA.body_height / 2)),
        ("main_shaft",          main_shaft.build,               (SHAFT_X, SHAFT_Y, SHAFT_Z)),
        ("gearbox_housing",     gearbox_housing.build,          (GEARBOX_X + gear_cx, GEARBOX_Y, GEARBOX_Z)),
        ("motor_mount",         motor_mount.build,              (MOTOR_X, MOTOR_Y, MOTOR_Z)),
        ("film_gate",           film_gate.build,                (LENS_X, GATE_CENTER_Y, 0)),
        ("shutter_disc",        shutter_disc.build,             (LENS_X, SHUTTER_CENTER_Y, SHAFT_Z)),
        ("claw_mechanism",      claw_mechanism.build,           (CLAW_X, CLAW_Y, CLAW_Z)),
        ("pulldown_cam",        cam_follower.build_cam,         (CAM_X, CAM_Y, CAM_Z)),
        ("cartridge_receiver",  cartridge_receiver.build,       (CART_X, CART_Y, CART_Z)),
        ("lens_mount",          lens_mount.build,               (LENS_X, -CAMERA.body_depth / 2.0, 0)),
        ("viewfinder",          viewfinder.build,               (VF_X, VF_Y, VF_Z)),
        ("trigger",             trigger.build,                  (TRIGGER_X, TRIGGER_Y, TRIGGER_Z)),
    ]

    results = []
    for name, builder, offset in parts:
        try:
            solid = builder()
            results.append((name, solid, offset))
        except Exception as e:
            print(f"  WARNING: could not build '{name}': {e}")
    return results


# ---------------------------------------------------------------------------
# Bounding-box utilities
# ---------------------------------------------------------------------------

def _bb(solid: cq.Workplane) -> Tuple[float, float, float, float, float, float]:
    """Return (xmin, ymin, zmin, xmax, ymax, zmax) for a CQ solid."""
    bb = solid.val().BoundingBox()
    return bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax


def _bb_volume(bb_tuple) -> float:
    xmin, ymin, zmin, xmax, ymax, zmax = bb_tuple
    return (xmax - xmin) * (ymax - ymin) * (zmax - zmin)


# ---------------------------------------------------------------------------
# Main diagnostic
# ---------------------------------------------------------------------------

def run(target_x: float = 135.0, target_z: float = 80.0, target_y: float = 48.0):
    """Run the full layout diagnostic and print results."""
    print()
    print("=" * 78)
    print("  LAYOUT DIAGNOSTIC — Internal Packing Analysis")
    print("=" * 78)
    print(f"  Current body envelope: {CAMERA.body_length:.0f} x "
          f"{CAMERA.body_height:.0f} x {CAMERA.body_depth:.0f} mm (X x Z x Y)")
    print(f"  Target envelope:       {target_x:.0f} x {target_z:.0f} x {target_y:.0f} mm")
    print()

    parts = _build_parts()

    # Header
    fmt = "  {:<22s}  {:>7s} {:>7s} {:>7s}  {:>9s}  {}"
    print(fmt.format("Part", "X(mm)", "Y(mm)", "Z(mm)", "Vol(mm3)", "Status"))
    print("  " + "-" * 74)

    total_parts_vol = 0.0
    issues = []

    half_x = target_x / 2.0
    half_y = target_y / 2.0
    half_z = target_z / 2.0

    for name, solid, (ox, oy, oz) in parts:
        try:
            xmin, ymin, zmin, xmax, ymax, zmax = _bb(solid)
            # Shift to world coordinates
            wxmin, wymin, wzmin = xmin + ox, ymin + oy, zmin + oz
            wxmax, wymax, wzmax = xmax + ox, ymax + oy, zmax + oz

            dx = wxmax - wxmin
            dy = wymax - wymin
            dz = wzmax - wzmin
            vol = dx * dy * dz
            total_parts_vol += vol

            # Check if within target envelope
            exceeds = []
            if wxmax > half_x or wxmin < -half_x:
                exceeds.append(f"X[{wxmin:.1f}..{wxmax:.1f}]")
            if wymax > half_y or wymin < -half_y:
                exceeds.append(f"Y[{wymin:.1f}..{wymax:.1f}]")
            if wzmax > half_z or wzmin < -half_z:
                exceeds.append(f"Z[{wzmin:.1f}..{wzmax:.1f}]")

            status = "OK" if not exceeds else "EXCEEDS " + ", ".join(exceeds)
            if exceeds:
                issues.append((name, exceeds))

            row = fmt.format(name,
                             f"{dx:.1f}", f"{dy:.1f}", f"{dz:.1f}",
                             f"{vol:.0f}", status)
            print(row)

        except Exception as e:
            print(f"  {name:<22s}  ERROR: {e}")

    # Cavity volume
    cavity_x = CAMERA.body_length - 2 * CAMERA.wall_thickness
    cavity_y = CAMERA.body_depth - 2 * CAMERA.wall_thickness
    cavity_z = CAMERA.body_height - 2 * CAMERA.wall_thickness
    cavity_vol = cavity_x * cavity_y * cavity_z

    packing = (total_parts_vol / cavity_vol * 100.0) if cavity_vol > 0 else 0.0

    print()
    print(f"  Total bounding-box volume of parts: {total_parts_vol:,.0f} mm^3")
    print(f"  Internal cavity volume:             {cavity_vol:,.0f} mm^3")
    print(f"  Packing efficiency:                 {packing:.1f}%")
    print()

    if issues:
        print(f"  {len(issues)} part(s) exceed target {target_x:.0f}x{target_z:.0f}x{target_y:.0f} envelope:")
        for name, exc in issues:
            print(f"    - {name}: {', '.join(exc)}")
    else:
        print(f"  All parts fit within {target_x:.0f}x{target_z:.0f}x{target_y:.0f} envelope.")

    print("=" * 78)
    return len(issues) == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
