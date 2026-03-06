#!/usr/bin/env python3
"""build.py — Master build script for the Super 8 Camera project.

Orchestrates the entire design pipeline in one command:
  1. Print and validate master specifications
  2. Run timing and tolerance validation
  3. Run kinematic and thermal analysis
  4. Build and export all CadQuery parts (STEP + STL)
  5. Build and export all assemblies (STEP)
  6. Run interference checking on full assembly
  7. Generate manufacturing outputs (BOM, drawings, checklist)
  8. Generate a comprehensive build report

Usage:
    python build.py                      # full build (from repo root)
    python -m super8cam.build            # full build (as module)
    python -m super8cam.build --specs    # print specs summary only
    python -m super8cam.build --parts-only    # export parts only
    python -m super8cam.build --analysis-only # run analysis only
    python -m super8cam.build --assembly-only # build assemblies only
"""

import argparse
import math
import os
import sys
import time
from datetime import datetime
from io import StringIO


# =========================================================================
# Directory setup
# =========================================================================

EXPORT_DIR = "export"


def ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)


# =========================================================================
# 1. Specs
# =========================================================================

def run_specs():
    """Print master specifications."""
    from super8cam.specs.master_specs import print_specs
    print_specs()


# =========================================================================
# 2. Timing + tolerance validation
# =========================================================================

def run_validation():
    """Run timing and tolerance validation.  Returns dict of results."""
    from super8cam.analysis.timing_validation import validate_timing
    from super8cam.analysis.tolerance_stackup import (
        flange_distance_stackup, registration_accuracy,
    )

    results = {}

    print("\n  TIMING VALIDATION")
    print("  " + "-" * 50)
    tv = validate_timing()
    results["timing"] = tv
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
    results["flange_stackup"] = fs
    print(f"    Target: {fs['target_mm']:.3f} mm")
    print(f"    Nominal: {fs['nominal_total_mm']:.3f} mm")
    print(f"    Error: {fs['error_mm']:.3f} mm")
    print(f"    Worst-case tol: +/-{fs['worst_case_tol_mm']:.3f} mm")
    print(f"    RSS tol: +/-{fs['rss_tol_mm']:.3f} mm")

    print("\n  REGISTRATION ACCURACY")
    print("  " + "-" * 50)
    ra = registration_accuracy()
    results["registration"] = ra
    print(f"    Worst-case: {ra['worst_case_error_mm']:.4f} mm "
          f"({'PASS' if ra['in_spec_worst'] else 'FAIL'})")
    print(f"    RSS: {ra['rss_error_mm']:.4f} mm "
          f"({'PASS' if ra['in_spec_rss'] else 'FAIL'})")

    return results


# =========================================================================
# 3. Analysis (kinematics + thermal)
# =========================================================================

def run_analysis():
    """Run kinematic and thermal analysis.  Returns dict of results."""
    from super8cam.analysis.kinematics import pulldown_profile, motor_speed_check
    from super8cam.analysis.thermal import motor_heat_estimate

    results = {}

    print("\n  KINEMATICS")
    print("  " + "-" * 50)
    results["pulldown"] = {}
    for fps in [18, 24]:
        p = pulldown_profile(fps)
        results["pulldown"][fps] = p
        print(f"    @{fps}fps: peak vel = {p['peak_velocity_mm_s']:.1f} mm/s, "
              f"peak accel = {p['peak_accel_mm_s2']:.0f} mm/s^2")

    print("\n  MOTOR SPEED CHECK")
    print("  " + "-" * 50)
    mc = motor_speed_check()
    results["motor_check"] = mc
    for fps, data in mc.items():
        print(f"    @{fps}fps: motor {data['motor_rpm']:.0f} RPM, "
              f"headroom {data['headroom_pct']:.1f}%, "
              f"{'OK' if data['feasible'] else 'OVER SPEED'}")

    print("\n  THERMAL")
    print("  " + "-" * 50)
    th = motor_heat_estimate(24)
    results["thermal"] = th
    print(f"    Motor current: {th['motor_current_ma']:.0f} mA")
    print(f"    Heat: {th['heat_dissipation_w']:.2f} W")
    print(f"    Body temp rise: {th['temp_rise_degc']:.1f} degC")
    print(f"    Gate expansion: {th['gate_expansion_um']:.2f} um")

    return results


# =========================================================================
# 4. Parts export
# =========================================================================

def run_parts_export():
    """Build and export all CadQuery parts.  Returns dict of results."""
    ensure_export_dir()
    import cadquery as cq

    from super8cam.parts import (
        film_gate, pressure_plate, claw_mechanism, registration_pin,
        shutter_disc, main_shaft, cam_follower, film_channel,
        lens_mount, viewfinder, motor_mount, gearbox_housing,
        body_left, body_right, top_plate, bottom_plate,
        battery_door, cartridge_door, trigger, pcb_bracket,
        gears, cartridge_receiver,
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
        "cartridge_receiver": cartridge_receiver.build,
        "stage1_pinion": gears.build_stage1_pinion,
        "stage1_gear": gears.build_stage1_gear,
        "stage2_pinion": gears.build_stage2_pinion,
        "stage2_gear": gears.build_stage2_gear,
    }

    print(f"\n  EXPORTING {len(parts)} PARTS")
    print("  " + "-" * 50)

    export_results = {}
    for name, builder in parts.items():
        try:
            solid = builder()
            step_path = os.path.join(EXPORT_DIR, f"{name}.step")
            stl_path = os.path.join(EXPORT_DIR, f"{name}.stl")
            cq.exporters.export(solid, step_path)
            cq.exporters.export(solid, stl_path, tolerance=0.01, angularTolerance=0.1)
            # Estimate volume (mm^3)
            vol = 0.0
            try:
                vol = solid.val().Volume()
            except Exception:
                pass
            export_results[name] = {"status": "OK", "volume_mm3": vol}
            print(f"    {name:25s} STEP + STL  (vol: {vol:.1f} mm^3)")
        except Exception as e:
            export_results[name] = {"status": "FAILED", "error": str(e)}
            print(f"    {name:25s} FAILED: {e}")

    return export_results


# =========================================================================
# 5. Assembly export
# =========================================================================

def run_assembly_export():
    """Build and export all assemblies.  Returns dict of results."""
    ensure_export_dir()

    from super8cam.assemblies import (
        drivetrain, shutter_assembly, film_transport,
        film_path, optical_path, power_system, electronics,
    )
    from super8cam.assemblies import full_camera

    assemblies = {
        "drivetrain": drivetrain.build,
        "shutter_assembly": shutter_assembly.build,
        "film_transport": film_transport.build,
        "film_path": film_path.build,
        "optical_path": optical_path.build,
        "power_system": power_system.build,
        "electronics": electronics.build,
        "full_camera_assembly": full_camera.build,
    }

    print(f"\n  EXPORTING {len(assemblies)} ASSEMBLIES")
    print("  " + "-" * 50)

    assy_results = {}
    for name, builder in assemblies.items():
        try:
            assy = builder()
            step_path = os.path.join(EXPORT_DIR, f"{name}.step")
            assy.save(step_path)
            n_children = len(assy.children) if hasattr(assy, 'children') else 0
            assy_results[name] = {"status": "OK", "children": n_children}
            print(f"    {name:30s} STEP  ({n_children} components)")
        except Exception as e:
            assy_results[name] = {"status": "FAILED", "error": str(e)}
            print(f"    {name:30s} FAILED: {e}")

    return assy_results


# =========================================================================
# 6. Interference checking
# =========================================================================

def run_interference():
    """Run interference checking on the full assembly.  Returns results list."""
    from super8cam.assemblies.full_camera import check_interference
    print("\n")
    results = check_interference(verbose=True)
    return results


# =========================================================================
# 7. Manufacturing outputs
# =========================================================================

def run_manufacturing():
    """Generate manufacturing outputs: BOM (CSV + PDF), drawings, checklist."""
    from super8cam.manufacturing.generate_bom import generate_all as bom_all
    from super8cam.manufacturing.generate_drawings import generate_all as drawings_all
    from super8cam.manufacturing.generate_checklist import generate_checklist

    print("\n  MANUFACTURING OUTPUTS")
    print("  " + "-" * 50)

    # BOM (CSV + PDF)
    bom_result = bom_all(EXPORT_DIR)
    t = bom_result["totals"]
    print(f"    BOM: {t['line_items']} items, "
          f"${t['total_qty1']:.0f}/@1, "
          f"${t['total_qty25']:.0f}/@25, "
          f"${t['total_qty100']:.0f}/@100")

    # Engineering drawings
    drawing_dir = os.path.join(EXPORT_DIR, "drawings")
    drawings = drawings_all(drawing_dir)
    print(f"    Drawings: {len(drawings)} PDFs")

    # Production checklist
    checklist_path = generate_checklist(EXPORT_DIR)

    return {
        "bom": bom_result,
        "drawings": drawings,
        "checklist": checklist_path,
    }


# =========================================================================
# 8. Build report
# =========================================================================

def _estimate_weight(part_volumes: dict) -> float:
    """Estimate total weight from part volumes and material densities.

    Returns weight in grams.
    """
    from super8cam.specs.master_specs import MATERIALS, MATERIAL_USAGE, MOTOR, BATTERY

    # Map part names to material keys
    part_material_map = {
        "film_gate": "brass_c360",
        "pressure_plate": "steel_302",
        "shutter_disc": "alu_6061_t6",
        "body_left": "alu_6061_t6",
        "body_right": "alu_6061_t6",
        "top_plate": "alu_6061_t6",
        "bottom_plate": "alu_6061_t6",
        "battery_door": "alu_6061_t6",
        "cartridge_door": "alu_6061_t6",
        "main_shaft": "steel_4140",
        "cam": "steel_4140",
        "cam_follower": "steel_4140",
        "claw_mechanism": "steel_4140",
        "registration_pin": "steel_4140",
        "gearbox_housing": "alu_6061_t6",
        "motor_mount": "alu_6061_t6",
        "lens_mount": "alu_6061_t6",
        "viewfinder": "alu_6061_t6",
        "trigger": "alu_6061_t6",
        "pcb_bracket": "alu_6061_t6",
        "cartridge_receiver": "alu_6061_t6",
        "film_channel": "alu_6061_t6",
        "stage1_pinion": "delrin_150",
        "stage1_gear": "delrin_150",
        "stage2_pinion": "delrin_150",
        "stage2_gear": "delrin_150",
    }

    total_g = 0.0
    for part_name, info in part_volumes.items():
        vol_mm3 = info.get("volume_mm3", 0.0)
        if vol_mm3 <= 0:
            continue
        mat_key = part_material_map.get(part_name, "alu_6061_t6")
        density = MATERIALS[mat_key].density  # g/cm^3
        vol_cm3 = vol_mm3 / 1000.0  # mm^3 -> cm^3
        total_g += vol_cm3 * density

    # Add known component weights
    total_g += MOTOR.weight_g
    total_g += BATTERY.pack_weight_g

    return total_g


def generate_build_report(
    validation_results: dict = None,
    analysis_results: dict = None,
    part_results: dict = None,
    assy_results: dict = None,
    interference_results: list = None,
):
    """Generate a comprehensive build report and write to export/build_report.txt."""
    ensure_export_dir()
    from super8cam.specs.master_specs import (
        CAMERA, CMOUNT, FILM, MOTOR, BATTERY, GEARBOX, SHUTTER, DERIVED,
        FASTENERS, FASTENER_USAGE, BEARINGS, MATERIALS, MATERIAL_USAGE,
    )
    from super8cam.manufacturing.generate_bom import generate_bom

    lines = []
    sep = "=" * 72
    lines.append(sep)
    lines.append("  SUPER 8 CAMERA — BUILD REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(sep)

    # --- Part count ---
    lines.append("")
    lines.append("  PART SUMMARY")
    lines.append("  " + "-" * 60)
    total_parts = len(part_results) if part_results else 0
    ok_parts = sum(1 for v in (part_results or {}).values() if v.get("status") == "OK")
    failed_parts = total_parts - ok_parts
    lines.append(f"    Total parts:      {total_parts}")
    lines.append(f"    Exported OK:      {ok_parts}")
    lines.append(f"    Failed:           {failed_parts}")
    if part_results:
        for name, info in sorted(part_results.items()):
            status = info.get("status", "?")
            vol = info.get("volume_mm3", 0)
            if status == "OK":
                lines.append(f"      {name:25s}  {vol:>10.1f} mm^3")
            else:
                lines.append(f"      {name:25s}  FAILED: {info.get('error', '')}")

    # --- Fastener count ---
    lines.append("")
    lines.append("  FASTENER SUMMARY")
    lines.append("  " + "-" * 60)
    total_fasteners = 0
    for usage, (fkey, qty) in FASTENER_USAGE.items():
        f = FASTENERS[fkey]
        lines.append(f"    {usage:25s}  {fkey:20s}  qty {qty}")
        total_fasteners += qty
    lines.append(f"    {'':25s}  {'TOTAL':20s}  qty {total_fasteners}")

    # --- Estimated weight ---
    lines.append("")
    lines.append("  WEIGHT ESTIMATE")
    lines.append("  " + "-" * 60)
    if part_results:
        weight_g = _estimate_weight(part_results)
        lines.append(f"    Machined parts + motor + batteries: {weight_g:.0f} g ({weight_g / 28.35:.1f} oz)")
    else:
        weight_g = DERIVED.total_weight_g
        lines.append(f"    Estimated (from specs): {weight_g:.0f} g")

    # --- Analysis results ---
    lines.append("")
    lines.append("  ANALYSIS RESULTS")
    lines.append("  " + "-" * 60)

    if validation_results:
        tv = validation_results.get("timing", {})
        lines.append(f"    Timing validation:      {'PASS' if tv.get('valid') else 'FAIL'}")
        if tv.get("errors"):
            for e in tv["errors"]:
                lines.append(f"      ERROR: {e}")

        fs = validation_results.get("flange_stackup", {})
        lines.append(f"    Flange distance error:  {fs.get('error_mm', 0):.3f} mm")
        lines.append(f"    Flange RSS tolerance:   +/-{fs.get('rss_tol_mm', 0):.3f} mm")

        ra = validation_results.get("registration", {})
        lines.append(f"    Reg. accuracy (worst):  {ra.get('worst_case_error_mm', 0):.4f} mm "
                      f"({'PASS' if ra.get('in_spec_worst') else 'FAIL'})")
        lines.append(f"    Reg. accuracy (RSS):    {ra.get('rss_error_mm', 0):.4f} mm "
                      f"({'PASS' if ra.get('in_spec_rss') else 'FAIL'})")
    else:
        lines.append("    (validation not run)")

    if analysis_results:
        for fps in [18, 24]:
            p = analysis_results.get("pulldown", {}).get(fps, {})
            lines.append(f"    Pulldown @{fps}fps:        peak vel {p.get('peak_velocity_mm_s', 0):.1f} mm/s, "
                          f"peak accel {p.get('peak_accel_mm_s2', 0):.0f} mm/s^2")

        mc = analysis_results.get("motor_check", {})
        for fps, data in mc.items():
            feasible = data.get("feasible", False)
            lines.append(f"    Motor @{fps}fps:            {data.get('motor_rpm', 0):.0f} RPM, "
                          f"{'OK' if feasible else 'OVER SPEED'}")

        th = analysis_results.get("thermal", {})
        lines.append(f"    Thermal: {th.get('heat_dissipation_w', 0):.2f} W dissipation, "
                      f"{th.get('temp_rise_degc', 0):.1f} degC rise")
    else:
        lines.append("    (analysis not run)")

    # --- Interference results ---
    lines.append("")
    lines.append("  INTERFERENCE CHECK")
    lines.append("  " + "-" * 60)
    if interference_results:
        passes = sum(1 for r in interference_results if r.get("status") == "PASS")
        fails = sum(1 for r in interference_results if r.get("status") == "FAIL")
        skips = sum(1 for r in interference_results if r.get("status") == "SKIPPED")
        lines.append(f"    {passes} PASS, {fails} FAIL, {skips} SKIPPED")
        for r in interference_results:
            if r.get("status") == "FAIL":
                lines.append(f"    FAIL: {r.get('part_a')} vs {r.get('part_b')}: "
                              f"{r.get('note', r.get('check', ''))}")
    else:
        lines.append("    (not run)")

    # --- Warnings ---
    lines.append("")
    lines.append("  WARNINGS")
    lines.append("  " + "-" * 60)
    warnings = []
    if failed_parts > 0:
        warnings.append(f"{failed_parts} part(s) failed to export")
    if interference_results:
        fails = [r for r in interference_results if r.get("status") == "FAIL"]
        if fails:
            warnings.append(f"{len(fails)} interference failure(s) detected")
    if validation_results:
        tv = validation_results.get("timing", {})
        if not tv.get("valid"):
            warnings.append("Timing validation FAILED")
        ra = validation_results.get("registration", {})
        if not ra.get("in_spec_worst"):
            warnings.append("Registration accuracy out of spec (worst-case)")
    if analysis_results:
        mc = analysis_results.get("motor_check", {})
        for fps, data in mc.items():
            if not data.get("feasible"):
                warnings.append(f"Motor over-speed at {fps} fps")
    if not warnings:
        warnings.append("None")
    for w in warnings:
        lines.append(f"    {w}")

    # --- Complete BOM ---
    lines.append("")
    lines.append("  BILL OF MATERIALS")
    lines.append("  " + "-" * 60)
    bom = generate_bom()
    lines.append(f"    {'#':<4s} {'Part No':<10s} {'Part Name':<25s} {'Qty':>4s}  {'M/B':<5s}  {'Cost @1':>10s}")
    lines.append("    " + "-" * 70)
    for item in bom:
        lines.append(f"    {item.item_number:<4d} {item.part_number:<10s} "
                      f"{item.part_name:<25s} {item.qty:>4d}  "
                      f"{item.make_or_buy:<5s}  ${item.cost_qty1:>8.2f}")

    # Estimated costs from BOM
    lines.append("")
    lines.append("  ESTIMATED COSTS")
    lines.append("  " + "-" * 60)
    from super8cam.manufacturing.generate_bom import calculate_totals
    totals = calculate_totals(bom)
    for cat, data in sorted(totals["by_category"].items()):
        lines.append(f"    {cat:20s}  @1: ${data['qty1']:>8.2f}  "
                      f"@25: ${data['qty25']:>8.2f}  "
                      f"@100: ${data['qty100']:>8.2f}")
    lines.append(f"    {'TOTAL':20s}  @1: ${totals['total_qty1']:>8.2f}  "
                  f"@25: ${totals['total_qty25']:>8.2f}  "
                  f"@100: ${totals['total_qty100']:>8.2f}")
    lines.append(f"    (Note: assembly labor not included)")

    lines.append("")
    lines.append(sep)

    report_text = "\n".join(lines)
    report_path = os.path.join(EXPORT_DIR, "build_report.txt")
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\n  Build report written to: {report_path}")
    print(report_text)

    return report_text


# =========================================================================
# Main
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Super 8 Camera — Master Build Script")
    parser.add_argument("--specs", action="store_true", help="Print specs only")
    parser.add_argument("--parts-only", action="store_true", help="Export parts only")
    parser.add_argument("--analysis-only", action="store_true", help="Run analysis only")
    parser.add_argument("--assembly-only", action="store_true", help="Build assemblies only")
    parser.add_argument("--report-only", action="store_true", help="Generate report only (no CAD)")
    args = parser.parse_args()

    sep = "=" * 60
    print(sep)
    print("  SUPER 8 CAMERA — MASTER BUILD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(sep)

    start = time.time()

    validation_results = None
    analysis_results = None
    part_results = None
    assy_results = None
    interference_results = None

    if args.specs:
        run_specs()
    elif args.parts_only:
        part_results = run_parts_export()
    elif args.analysis_only:
        validation_results = run_validation()
        analysis_results = run_analysis()
    elif args.assembly_only:
        assy_results = run_assembly_export()
    elif args.report_only:
        validation_results = run_validation()
        analysis_results = run_analysis()
        generate_build_report(
            validation_results=validation_results,
            analysis_results=analysis_results,
        )
    else:
        # ---- Full build pipeline ----
        # Step 1: Specs
        run_specs()

        # Step 2: Validation
        validation_results = run_validation()

        # Step 3: Analysis
        analysis_results = run_analysis()

        # Step 4: Parts export
        part_results = run_parts_export()

        # Step 5: Assembly export
        assy_results = run_assembly_export()

        # Step 6: Interference checking
        interference_results = run_interference()

        # Step 7: Manufacturing outputs
        run_manufacturing()

        # Step 8: Build report
        generate_build_report(
            validation_results=validation_results,
            analysis_results=analysis_results,
            part_results=part_results,
            assy_results=assy_results,
            interference_results=interference_results,
        )

    elapsed = time.time() - start
    print(f"\n  Build complete in {elapsed:.1f}s")
    print("  " + sep)


if __name__ == "__main__":
    main()
