#!/usr/bin/env python3
"""build.py — Master build script for the Super 8 Camera project.

Orchestrates:
  1. Validate specs and timing
  2. Build all CadQuery parts → export STEP + STL
  3. Build assemblies → export STEP
  4. Run analysis (kinematics, tolerance, thermal)
  5. Generate manufacturing outputs (BOM, drawings, checklist)

Usage:
    python -m super8cam.build                 # full build
    python -m super8cam.build --parts-only    # only export parts
    python -m super8cam.build --analysis-only # only run analysis
    python -m super8cam.build --specs         # print specs summary
"""

import argparse
import os
import sys
import time


def ensure_export_dir():
    os.makedirs("export", exist_ok=True)


def run_specs():
    """Print master specifications."""
    from super8cam.specs.master_specs import print_specs
    print_specs()


def run_validation():
    """Run timing and tolerance validation."""
    from super8cam.analysis.timing_validation import validate_timing
    from super8cam.analysis.tolerance_stackup import (
        flange_distance_stackup, registration_accuracy,
    )

    print("\n  TIMING VALIDATION")
    print("  " + "-" * 50)
    tv = validate_timing()
    for phase in tv["phases"]:
        print(f"    {phase[0]}: {phase[1]:.0f} - {phase[2]:.0f} deg")
    print(f"    Pulldown @18fps: {tv['pulldown_time_18ms']:.2f} ms")
    print(f"    Pulldown @24fps: {tv['pulldown_time_24ms']:.2f} ms")
    print(f"    Result: {'PASS' if tv['valid'] else 'FAIL'}")
    if tv["errors"]:
        for e in tv["errors"]:
            print(f"    ERROR: {e}")

    print("\n  FLANGE DISTANCE STACKUP")
    print("  " + "-" * 50)
    fs = flange_distance_stackup()
    print(f"    Target: {fs['target_mm']:.3f} mm")
    print(f"    Nominal: {fs['nominal_total_mm']:.3f} mm")
    print(f"    Error: {fs['error_mm']:.3f} mm")
    print(f"    Worst-case tol: +/-{fs['worst_case_tol_mm']:.3f} mm")
    print(f"    RSS tol: +/-{fs['rss_tol_mm']:.3f} mm")

    print("\n  REGISTRATION ACCURACY")
    print("  " + "-" * 50)
    ra = registration_accuracy()
    print(f"    Worst-case: {ra['worst_case_error_mm']:.4f} mm "
          f"({'PASS' if ra['in_spec_worst'] else 'FAIL'})")
    print(f"    RSS: {ra['rss_error_mm']:.4f} mm "
          f"({'PASS' if ra['in_spec_rss'] else 'FAIL'})")


def run_analysis():
    """Run kinematic and thermal analysis."""
    from super8cam.analysis.kinematics import pulldown_profile, motor_speed_check
    from super8cam.analysis.thermal import motor_heat_estimate

    print("\n  KINEMATICS")
    print("  " + "-" * 50)
    for fps in [18, 24]:
        p = pulldown_profile(fps)
        print(f"    @{fps}fps: peak vel = {p['peak_velocity_mm_s']:.1f} mm/s, "
              f"peak accel = {p['peak_accel_mm_s2']:.0f} mm/s^2")

    print("\n  MOTOR SPEED CHECK")
    print("  " + "-" * 50)
    mc = motor_speed_check()
    for fps, data in mc.items():
        print(f"    @{fps}fps: motor {data['motor_rpm']:.0f} RPM, "
              f"headroom {data['headroom_pct']:.1f}%, "
              f"{'OK' if data['feasible'] else 'OVER SPEED'}")

    print("\n  THERMAL")
    print("  " + "-" * 50)
    th = motor_heat_estimate(24)
    print(f"    Motor current: {th['motor_current_ma']:.0f} mA")
    print(f"    Heat: {th['heat_dissipation_w']:.2f} W")
    print(f"    Body temp rise: {th['temp_rise_degc']:.1f} degC")
    print(f"    Gate expansion: {th['gate_expansion_um']:.2f} um")


def run_parts_export():
    """Build and export all CadQuery parts."""
    ensure_export_dir()
    import cadquery as cq

    # Import all part modules
    from super8cam.parts import (
        film_gate, pressure_plate, claw_mechanism, registration_pin,
        shutter_disc, main_shaft, cam_follower, film_channel,
        lens_mount, viewfinder, motor_mount, gearbox_housing,
        body_left, body_right, top_plate, bottom_plate,
        battery_door, cartridge_door, trigger, pcb_bracket,
    )

    parts = {
        "film_gate": film_gate.build,
        "pressure_plate": pressure_plate.build,
        "claw_mechanism": claw_mechanism.build,
        "registration_pin": registration_pin.build,
        "shutter_disc": shutter_disc.build,
        "main_shaft": main_shaft.build,
        "cam": cam_follower.build_cam,
        "cam_follower": cam_follower.build_follower,
        "film_channel": film_channel.build,
        "lens_mount": lens_mount.build,
        "viewfinder": viewfinder.build,
        "motor_mount": motor_mount.build,
        "gearbox_housing": gearbox_housing.build,
        "body_left": body_left.build,
        "body_right": body_right.build,
        "top_plate": top_plate.build,
        "bottom_plate": bottom_plate.build,
        "battery_door": battery_door.build,
        "cartridge_door": cartridge_door.build,
        "trigger": trigger.build,
        "pcb_bracket": pcb_bracket.build,
    }

    print(f"\n  EXPORTING {len(parts)} PARTS")
    print("  " + "-" * 50)

    for name, builder in parts.items():
        try:
            solid = builder()
            step_path = f"export/{name}.step"
            stl_path = f"export/{name}.stl"
            cq.exporters.export(solid, step_path)
            cq.exporters.export(solid, stl_path, tolerance=0.01, angularTolerance=0.1)
            print(f"    {name:25s} STEP + STL")
        except Exception as e:
            print(f"    {name:25s} FAILED: {e}")


def run_manufacturing():
    """Generate manufacturing outputs."""
    from super8cam.manufacturing.generate_bom import export_csv
    print("\n  MANUFACTURING OUTPUTS")
    print("  " + "-" * 50)
    export_csv("export/bom.csv")


def main():
    parser = argparse.ArgumentParser(description="Super 8 Camera Build System")
    parser.add_argument("--specs", action="store_true", help="Print specs only")
    parser.add_argument("--parts-only", action="store_true", help="Export parts only")
    parser.add_argument("--analysis-only", action="store_true", help="Run analysis only")
    args = parser.parse_args()

    sep = "=" * 60
    print(sep)
    print("  SUPER 8 CAMERA — PROJECT BUILD")
    print(sep)

    start = time.time()

    if args.specs:
        run_specs()
    elif args.parts_only:
        run_parts_export()
    elif args.analysis_only:
        run_validation()
        run_analysis()
    else:
        # Full build
        run_specs()
        run_validation()
        run_analysis()
        run_parts_export()
        run_manufacturing()

    elapsed = time.time() - start
    print(f"\n  Build complete in {elapsed:.1f}s")
    print("  " + sep)


if __name__ == "__main__":
    main()
