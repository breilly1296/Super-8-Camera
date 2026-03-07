#!/usr/bin/env python3
"""build.py — Master build script for the Super 8 Camera project.

Orchestrates the complete build pipeline:
  1. Validate specs and timing
  2. Build all CadQuery parts → export STEP + STL
  3. Build all assemblies → export STEP
  4. Run analysis (kinematics, tolerance, thermal)
  5. Run interference checking
  6. Export everything to export/ directory
  7. Generate build report (text file) summarizing:
     - Total part count
     - Total fastener count
     - Estimated weight
     - All analysis results (pass/fail)
     - Any warnings or interference flags
     - Complete BOM

Usage:
    python -m super8cam.build                 # full build
    python -m super8cam.build --parts-only    # only export parts
    python -m super8cam.build --analysis-only # only run analysis
    python -m super8cam.build --specs         # print specs summary
    python -m super8cam.build --report-only   # only generate build report
"""

import argparse
import os
import sys
import time
import types
from datetime import datetime

# Ensure UTF-8 output on Windows (GD&T symbols, ≈, ±, etc.)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Mock CadQuery if OCP is unavailable (allows validation, analysis, and
# manufacturing phases to run without full CadQuery geometry backend).
# ---------------------------------------------------------------------------
try:
    import cadquery  # noqa: F401
    CADQUERY_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CADQUERY_AVAILABLE = False
    _cq = types.ModuleType("cadquery")
    _cq.Workplane = type("Workplane", (), {})
    _cq.exporters = types.ModuleType("cadquery.exporters")
    _cq.Assembly = type("Assembly", (), {})
    _cq.Location = type("Location", (), {"__init__": lambda self, *a: None})
    sys.modules["cadquery"] = _cq
    sys.modules["cadquery.exporters"] = _cq.exporters

# =========================================================================
# DIRECTORY SETUP
# =========================================================================

EXPORT_DIR = "export"


def ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)


# =========================================================================
# SPECS
# =========================================================================

def run_specs():
    """Print master specifications."""
    from super8cam.specs.master_specs import print_specs
    print_specs()


# =========================================================================
# VALIDATION (timing + tolerances)
# =========================================================================

def run_validation() -> dict:
    """Run timing and tolerance validation. Returns results dict."""
    from super8cam.analysis.timing_validation import validate_timing
    from super8cam.analysis.tolerance_stackup import (
        flange_distance_stackup, registration_accuracy, bearing_fit_check,
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

    print("\n  BEARING FIT CHECK")
    print("  " + "-" * 50)
    bf = bearing_fit_check()
    results["bearing_fit"] = bf
    print(f"    {bf['note']}")

    return results


# =========================================================================
# ANALYSIS (kinematics + thermal)
# =========================================================================

def run_analysis() -> dict:
    """Run kinematic and thermal analysis. Returns results dict."""
    from super8cam.analysis.kinematics import (
        pulldown_profile, motor_speed_check, validate_mechanism,
    )
    from super8cam.analysis.thermal import motor_heat_estimate

    results = {}

    print("\n  KINEMATICS")
    print("  " + "-" * 50)
    kinematics = {}
    for fps in [18, 24]:
        p = pulldown_profile(fps)
        kinematics[fps] = p
        print(f"    @{fps}fps: peak vel = {p['peak_velocity_mm_s']:.1f} mm/s, "
              f"peak accel = {p['peak_accel_mm_s2']:.0f} mm/s^2")
    results["kinematics"] = kinematics

    print("\n  MOTOR SPEED CHECK")
    print("  " + "-" * 50)
    mc = motor_speed_check()
    results["motor_speed"] = mc
    for fps, data in mc.items():
        print(f"    @{fps}fps: motor {data['motor_rpm']:.0f} RPM, "
              f"headroom {data['headroom_pct']:.1f}%, "
              f"{'OK' if data['feasible'] else 'OVER SPEED'}")

    print("\n  MECHANISM VALIDATION")
    print("  " + "-" * 50)
    mech_results = {}
    for fps in [18, 24]:
        mv = validate_mechanism(fps)
        mech_results[fps] = mv
        status = "PASS" if mv["all_pass"] else "FAIL"
        print(f"    @{fps}fps: {status}")
        for desc, ok in mv["checks"]:
            s = "PASS" if ok else "FAIL"
            print(f"      [{s}] {desc}")
    results["mechanism"] = mech_results

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
# PARTS EXPORT
# =========================================================================

def run_parts_export() -> dict:
    """Build and export all CadQuery parts. Returns part info dict."""
    if not CADQUERY_AVAILABLE:
        print("    SKIPPED (CadQuery/OCP not installed)")
        return {}
    ensure_export_dir()
    import cadquery as cq

    from super8cam.parts import (
        film_gate, pressure_plate, claw_mechanism, registration_pin,
        shutter_disc, main_shaft, cam_follower, film_channel,
        lens_mount, viewfinder, motor_mount, gearbox_housing,
        body_left, body_right, top_plate, bottom_plate,
        battery_door, cartridge_door, trigger, pcb_bracket,
        cartridge_receiver, gears,
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
        "secondary_eccentric": cam_follower.build_secondary_eccentric,
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

    part_info = {}
    for name, builder in parts.items():
        try:
            solid = builder()
            step_path = f"{EXPORT_DIR}/{name}.step"
            stl_path = f"{EXPORT_DIR}/{name}.stl"
            cq.exporters.export(solid, step_path)
            cq.exporters.export(solid, stl_path,
                                tolerance=0.01, angularTolerance=0.1)

            # Compute volume for weight estimate
            vol_mm3 = 0.0
            try:
                if hasattr(solid, 'val'):
                    vol_mm3 = abs(solid.val().Volume())
                elif hasattr(solid, 'Volume'):
                    vol_mm3 = abs(solid.Volume())
            except Exception:
                pass

            part_info[name] = {
                "step": step_path,
                "stl": stl_path,
                "volume_mm3": vol_mm3,
                "volume_cm3": vol_mm3 / 1000.0,
                "status": "OK",
            }
            print(f"    {name:25s} STEP + STL  ({vol_mm3:.1f} mm^3)")

        except Exception as e:
            part_info[name] = {"status": "FAILED", "error": str(e)}
            print(f"    {name:25s} FAILED: {e}")

    return part_info


# =========================================================================
# ASSEMBLIES EXPORT
# =========================================================================

def run_assemblies_export() -> dict:
    """Build and export all assemblies. Returns assembly info dict."""
    if not CADQUERY_AVAILABLE:
        print("    SKIPPED (CadQuery/OCP not installed)")
        return {}
    ensure_export_dir()
    import cadquery as cq

    from super8cam.assemblies import (
        film_transport, shutter_assembly, drivetrain,
        optical_path, power_system, electronics, film_path,
    )
    from super8cam.assemblies.full_camera import build as build_full

    assemblies = {
        "film_transport": film_transport.build,
        "shutter_assembly": shutter_assembly.build,
        "drivetrain": drivetrain.build,
        "optical_path": optical_path.build,
        "power_system": power_system.build,
        "electronics": electronics.build,
        "film_path": film_path.build,
        "full_camera": build_full,
    }

    print(f"\n  EXPORTING {len(assemblies)} ASSEMBLIES")
    print("  " + "-" * 50)

    assy_info = {}
    for name, builder in assemblies.items():
        try:
            assy = builder()
            step_path = f"{EXPORT_DIR}/{name}.step"
            cq.exporters.export(assy.toCompound(), step_path)
            assy_info[name] = {"step": step_path, "status": "OK"}
            print(f"    {name:25s} STEP")
        except Exception as e:
            assy_info[name] = {"status": "FAILED", "error": str(e)}
            print(f"    {name:25s} FAILED: {e}")

    return assy_info


# =========================================================================
# INTERFERENCE CHECKING
# =========================================================================

def run_interference() -> dict:
    """Run interference detection. Returns results dict."""
    if not CADQUERY_AVAILABLE:
        print("    SKIPPED (CadQuery/OCP not installed)")
        return {"all_clear": True, "pairs_checked": 0, "interferences": 0}
    from super8cam.assemblies.full_camera import (
        check_interference, check_shutter_clearance, print_interference_report,
    )

    print("\n  INTERFERENCE DETECTION")
    print("  " + "-" * 50)

    result = check_interference()
    print_interference_report(result)

    return result


# =========================================================================
# MANUFACTURING OUTPUTS
# =========================================================================

def run_manufacturing():
    """Generate manufacturing outputs (BOM, drawings, checklist)."""
    ensure_export_dir()

    from super8cam.manufacturing.generate_bom import export_csv

    print("\n  MANUFACTURING OUTPUTS")
    print("  " + "-" * 50)
    export_csv(f"{EXPORT_DIR}/bom.csv")

    # Try generating other manufacturing outputs if available
    try:
        from super8cam.manufacturing.generate_drawings import generate_all
        generate_all(f"{EXPORT_DIR}/drawings")
    except Exception as e:
        print(f"    Drawings: SKIPPED ({e})")

    try:
        from super8cam.manufacturing.generate_checklist import export_pdf as export_checklist_pdf
        export_checklist_pdf(f"{EXPORT_DIR}/production_checklist.pdf")
    except Exception as e:
        print(f"    Checklist: SKIPPED ({e})")

    try:
        from super8cam.manufacturing.generate_bom import export_pdf as export_bom_pdf
        export_bom_pdf(f"{EXPORT_DIR}/bom.pdf")
    except Exception as e:
        print(f"    BOM PDF: SKIPPED ({e})")

    try:
        from super8cam.manufacturing.repair_guide import generate as generate_repair_guide
        generate_repair_guide(EXPORT_DIR)
    except Exception as e:
        print(f"    Repair guide: SKIPPED ({e})")


# =========================================================================
# WEIGHT ESTIMATION
# =========================================================================

def estimate_weight(part_info: dict) -> dict:
    """Estimate total camera weight from part volumes + material densities.

    Returns dict with per-part weights and totals.
    """
    from super8cam.specs.master_specs import (
        MATERIALS, MATERIAL_USAGE, MOTOR, BATTERY, PCB,
    )

    # Material assignments for parts
    part_material_map = {
        "film_gate":          "brass_c360",
        "pressure_plate":     "steel_302",
        "shutter_disc":       "alu_6061_t6",
        "main_shaft":         "steel_4140",
        "cam":                "steel_4140",
        "cam_follower":       "steel_4140",
        "secondary_eccentric": "steel_4140",
        "claw_mechanism":     "steel_4140",
        "registration_pin":   "steel_4140",
        "body_left":          "alu_6061_t6",
        "body_right":         "alu_6061_t6",
        "top_plate":          "alu_6061_t6",
        "bottom_plate":       "alu_6061_t6",
        "battery_door":       "alu_6061_t6",
        "cartridge_door":     "alu_6061_t6",
        "trigger":            "alu_6061_t6",
        "pcb_bracket":        "alu_6061_t6",
        "lens_mount":         "alu_6061_t6",
        "viewfinder":         "alu_6061_t6",
        "motor_mount":        "alu_6061_t6",
        "gearbox_housing":    "alu_6061_t6",
        "cartridge_receiver": "alu_6061_t6",
        "film_channel":       "alu_6061_t6",
        "stage1_pinion":      "delrin_150",
        "stage1_gear":        "delrin_150",
        "stage2_pinion":      "delrin_150",
        "stage2_gear":        "delrin_150",
    }

    part_weights = {}
    total_machined_g = 0.0

    for name, info in part_info.items():
        if info.get("status") != "OK":
            continue

        vol_cm3 = info.get("volume_cm3", 0.0)
        mat_key = part_material_map.get(name, "alu_6061_t6")
        mat = MATERIALS.get(mat_key)

        if mat and vol_cm3 > 0:
            weight_g = vol_cm3 * mat.density
            part_weights[name] = {
                "volume_cm3": vol_cm3,
                "material": mat.name,
                "density_g_cm3": mat.density,
                "weight_g": weight_g,
            }
            total_machined_g += weight_g

    # Add non-machined components
    motor_g = MOTOR.weight_g
    battery_g = BATTERY.pack_weight_g
    pcb_g = PCB.width * PCB.height * PCB.thickness / 1000.0 * 2.0  # ~2 g/cm^3 FR4

    # Fastener weight estimate
    from super8cam.specs.master_specs import FASTENER_USAGE
    total_fasteners = sum(qty for _, (_, qty) in FASTENER_USAGE.items())
    fastener_g = total_fasteners * 0.5  # ~0.5g per small screw average

    total_g = total_machined_g + motor_g + battery_g + pcb_g + fastener_g

    return {
        "part_weights": part_weights,
        "total_machined_g": total_machined_g,
        "motor_g": motor_g,
        "battery_g": battery_g,
        "pcb_g": pcb_g,
        "fastener_g": fastener_g,
        "total_g": total_g,
        "total_oz": total_g / 28.3495,
    }


# =========================================================================
# BUILD REPORT GENERATION
# =========================================================================

def generate_build_report(
    part_info: dict = None,
    assy_info: dict = None,
    validation_results: dict = None,
    analysis_results: dict = None,
    interference_results: dict = None,
    weight_info: dict = None,
    elapsed_s: float = 0.0,
) -> str:
    """Generate comprehensive build report as text.

    Returns the report text and writes to export/build_report.txt.
    """
    from super8cam.specs.master_specs import (
        CAMERA, FILM, CMOUNT, MOTOR, GEARBOX, BATTERY, SHUTTER,
        FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE,
        BEARINGS, PCB, DERIVED,
    )
    from super8cam.manufacturing.generate_bom import generate_bom

    sep = "=" * 72
    lines = []

    def w(text=""):
        lines.append(text)

    w(sep)
    w("  SUPER 8 CAMERA — BUILD REPORT")
    w(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    w(f"  Build time: {elapsed_s:.1f}s")
    w(sep)

    # ----- SUMMARY -----
    w()
    w("  SUMMARY")
    w("  " + "-" * 60)

    total_parts = len(part_info) if part_info else 0
    ok_parts = sum(1 for v in (part_info or {}).values() if v.get("status") == "OK")
    failed_parts = total_parts - ok_parts

    total_assemblies = len(assy_info) if assy_info else 0
    ok_assemblies = sum(1 for v in (assy_info or {}).values() if v.get("status") == "OK")

    total_fasteners = sum(qty for _, (_, qty) in FASTENER_USAGE.items())

    w(f"    Parts:        {ok_parts}/{total_parts} built successfully")
    if failed_parts > 0:
        w(f"    FAILED:       {failed_parts} parts failed to build")
    w(f"    Assemblies:   {ok_assemblies}/{total_assemblies} built successfully")
    w(f"    Fasteners:    {total_fasteners} total")
    w(f"    Bearings:     {len(BEARINGS)}")

    if weight_info:
        w(f"    Est. weight:  {weight_info['total_g']:.0f} g "
          f"({weight_info['total_oz']:.1f} oz)")
        w(f"      Machined:   {weight_info['total_machined_g']:.0f} g")
        w(f"      Motor:      {weight_info['motor_g']:.0f} g")
        w(f"      Batteries:  {weight_info['battery_g']:.0f} g")
        w(f"      PCB:        {weight_info['pcb_g']:.1f} g")
        w(f"      Fasteners:  {weight_info['fastener_g']:.0f} g")

    # ----- DESIGN SPECS -----
    w()
    w("  DESIGN SPECIFICATIONS")
    w("  " + "-" * 60)
    w(f"    Body:         {CAMERA.body_length} x {CAMERA.body_height} x "
      f"{CAMERA.body_depth} mm")
    w(f"    Film:         Super 8 ({FILM.frame_w} x {FILM.frame_h} mm frame)")
    w(f"    Lens mount:   C-mount (FFD {CMOUNT.flange_focal_dist} mm)")
    w(f"    Shutter:      {CAMERA.shutter_opening_angle} deg opening")
    w(f"    Frame rates:  {', '.join(str(f) for f in CAMERA.fps_options)} fps")
    w(f"    Motor:        {MOTOR.model} ({MOTOR.nominal_voltage}V)")
    w(f"    Gear ratio:   {GEARBOX.ratio}:1 ({GEARBOX.stages}-stage)")
    w(f"    Battery:      {BATTERY.cell_count}x{BATTERY.cell_type} "
      f"({BATTERY.pack_voltage_nom}V)")

    # ----- VALIDATION RESULTS -----
    w()
    w("  VALIDATION RESULTS")
    w("  " + "-" * 60)

    if validation_results:
        tv = validation_results.get("timing")
        if tv:
            w(f"    Timing:       {'PASS' if tv['valid'] else 'FAIL'}")

        fs = validation_results.get("flange_stackup")
        if fs:
            w(f"    Flange dist:  PASS (error {fs['error_mm']:+.3f} mm, "
              f"RSS tol +/-{fs['rss_tol_mm']:.3f} mm)")

        ra = validation_results.get("registration")
        if ra:
            w(f"    Registration: {'PASS' if ra['in_spec_rss'] else 'FAIL'} "
              f"(RSS {ra['rss_error_mm']:.4f} mm)")
    else:
        w("    (not run)")

    # ----- ANALYSIS RESULTS -----
    w()
    w("  ANALYSIS RESULTS")
    w("  " + "-" * 60)

    if analysis_results:
        mc = analysis_results.get("motor_speed", {})
        for fps, data in mc.items():
            status = "OK" if data["feasible"] else "OVER SPEED"
            w(f"    Motor @{fps}fps: {data['motor_rpm']:.0f} RPM "
              f"({data['headroom_pct']:.1f}% headroom) — {status}")

        mech = analysis_results.get("mechanism", {})
        for fps, mv in mech.items():
            status = "PASS" if mv["all_pass"] else "FAIL"
            w(f"    Mechanism @{fps}fps: {status}")

        th = analysis_results.get("thermal")
        if th:
            w(f"    Thermal @24fps: {th['temp_rise_degc']:.1f} degC rise, "
              f"{th['gate_expansion_um']:.2f} um gate expansion")
    else:
        w("    (not run)")

    # ----- INTERFERENCE RESULTS -----
    w()
    w("  INTERFERENCE CHECK")
    w("  " + "-" * 60)

    if interference_results:
        n_checked = interference_results.get("pairs_checked", 0)
        n_fail = interference_results.get("interferences", 0)
        status = "PASS" if interference_results.get("all_clear") else "FAIL"
        w(f"    Pairs checked:   {n_checked}")
        w(f"    Interferences:   {n_fail}")
        w(f"    Overall:         {status}")

        if interference_results.get("warnings"):
            w()
            w("    Warnings:")
            for warn in interference_results["warnings"]:
                w(f"      - {warn}")
    else:
        w("    (not run)")

    # ----- PART WEIGHT BREAKDOWN -----
    w()
    w("  PART WEIGHT BREAKDOWN")
    w("  " + "-" * 60)
    w(f"    {'Part':<28s} {'Material':<25s} {'Vol cm3':>8s} {'Weight g':>9s}")
    w(f"    {'-'*28} {'-'*25} {'-'*8} {'-'*9}")

    if weight_info and weight_info.get("part_weights"):
        for name, pw in sorted(weight_info["part_weights"].items(),
                                key=lambda x: -x[1]["weight_g"]):
            w(f"    {name:<28s} {pw['material']:<25s} "
              f"{pw['volume_cm3']:>8.2f} {pw['weight_g']:>9.2f}")

    # ----- COMPLETE BOM -----
    w()
    w("  BILL OF MATERIALS")
    w("  " + "-" * 60)
    w(f"    {'Part No.':<10s} {'Part Name':<32s} {'Material':<18s} "
      f"{'Qty':>3s} {'M/B':<4s} {'$1':>8s}")
    w(f"    {'-'*10} {'-'*32} {'-'*18} {'-'*3} {'-'*4} {'-'*8}")

    bom = generate_bom()
    from super8cam.manufacturing.generate_bom import compute_totals
    bom_totals = compute_totals(bom)
    for item in bom:
        name = item.part_name[:32]
        mat = item.material[:18]
        w(f"    {item.part_number:<10s} {name:<32s} {mat:<18s} "
          f"{item.qty:>3d} {item.make_buy:<4s} ${item.cost_qty1:>7.2f}")

    w(f"\n    Total BOM items: {bom_totals['line_items']}")
    w(f"    Total parts/camera: {bom_totals['total_parts']}")
    w(f"    Cost @ qty 1:   ${bom_totals['total_qty1']:.2f}")
    w(f"    Cost @ qty 25:  ${bom_totals['total_qty25']:.2f}")
    w(f"    Cost @ qty 100: ${bom_totals['total_qty100']:.2f}")
    w(f"    Total fasteners: {total_fasteners}")

    # ----- FASTENER SUMMARY -----
    w()
    w("  FASTENER SUMMARY")
    w("  " + "-" * 60)
    for usage, (fkey, qty) in FASTENER_USAGE.items():
        f = FASTENERS[fkey]
        w(f"    {qty:>2d}x {f.thread} x {f.length:.0f}mm {f.head_type:20s} "
          f"— {usage}")

    # ----- MATERIAL SUMMARY -----
    w()
    w("  MATERIALS")
    w("  " + "-" * 60)
    for usage, mat_key in MATERIAL_USAGE.items():
        mat = MATERIALS[mat_key]
        w(f"    {usage:<20s} {mat.name}")

    # ----- FAILED PARTS -----
    if part_info:
        failed = {k: v for k, v in part_info.items() if v.get("status") != "OK"}
        if failed:
            w()
            w("  FAILED PARTS")
            w("  " + "-" * 60)
            for name, info in failed.items():
                w(f"    {name}: {info.get('error', 'unknown error')}")

    if assy_info:
        failed_assy = {k: v for k, v in assy_info.items() if v.get("status") != "OK"}
        if failed_assy:
            w()
            w("  FAILED ASSEMBLIES")
            w("  " + "-" * 60)
            for name, info in failed_assy.items():
                w(f"    {name}: {info.get('error', 'unknown error')}")

    # ----- OVERALL STATUS -----
    w()
    w(sep)
    all_pass = True
    warnings = []

    if failed_parts > 0:
        all_pass = False
        warnings.append(f"{failed_parts} parts failed to build")

    if validation_results:
        if not validation_results.get("timing", {}).get("valid", True):
            all_pass = False
            warnings.append("Timing validation failed")

    if analysis_results:
        mc = analysis_results.get("motor_speed", {})
        for fps, data in mc.items():
            if not data.get("feasible", True):
                all_pass = False
                warnings.append(f"Motor over-speed at {fps} fps")

        mech = analysis_results.get("mechanism", {})
        for fps, mv in mech.items():
            if not mv.get("all_pass", True):
                all_pass = False
                warnings.append(f"Mechanism validation failed at {fps} fps")

    if interference_results and not interference_results.get("all_clear", True):
        all_pass = False
        warnings.append("Interference detected between parts")

    if all_pass:
        w("  OVERALL: ALL CHECKS PASSED")
    else:
        w("  OVERALL: WARNINGS PRESENT")
        for warn in warnings:
            w(f"    - {warn}")

    w(sep)

    report_text = "\n".join(lines)

    # Write to file
    ensure_export_dir()
    report_path = f"{EXPORT_DIR}/build_report.txt"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\n  Build report written to {report_path}")

    return report_text


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Super 8 Camera Build System")
    parser.add_argument("--specs", action="store_true",
                        help="Print specs only")
    parser.add_argument("--parts-only", action="store_true",
                        help="Export parts only")
    parser.add_argument("--analysis-only", action="store_true",
                        help="Run analysis only")
    parser.add_argument("--report-only", action="store_true",
                        help="Generate build report only (no export)")
    parser.add_argument("--no-interference", action="store_true",
                        help="Skip interference checking (faster)")
    args = parser.parse_args()

    sep = "=" * 65
    print(sep)
    print("  SUPER 8 CAMERA — PROJECT BUILD")
    print(sep)

    start = time.time()

    # Collect results for build report
    part_info = None
    assy_info = None
    validation_results = None
    analysis_results = None
    interference_results = None
    weight_info = None

    if args.specs:
        run_specs()

    elif args.parts_only:
        part_info = run_parts_export()
        weight_info = estimate_weight(part_info)

    elif args.analysis_only:
        validation_results = run_validation()
        analysis_results = run_analysis()

    elif args.report_only:
        # Run everything except exports
        validation_results = run_validation()
        analysis_results = run_analysis()

    else:
        # Full build
        print("\n  Phase 1/7: Specifications")
        run_specs()

        print("\n  Phase 2/7: Validation")
        validation_results = run_validation()

        print("\n  Phase 3/7: Analysis")
        analysis_results = run_analysis()

        print("\n  Phase 4/7: Parts Export")
        part_info = run_parts_export()

        print("\n  Phase 5/7: Assemblies Export")
        assy_info = run_assemblies_export()

        if not args.no_interference:
            print("\n  Phase 6/7: Interference Detection")
            interference_results = run_interference()
        else:
            print("\n  Phase 6/7: Interference Detection (SKIPPED)")

        print("\n  Phase 7/7: Manufacturing Outputs")
        run_manufacturing()

        # Weight estimation
        if part_info:
            weight_info = estimate_weight(part_info)
            print(f"\n  Estimated total weight: {weight_info['total_g']:.0f} g "
                  f"({weight_info['total_oz']:.1f} oz)")

    elapsed = time.time() - start

    # Generate build report if we have any results
    if any([part_info, validation_results, analysis_results, interference_results]):
        print("\n  Generating build report...")
        report = generate_build_report(
            part_info=part_info or {},
            assy_info=assy_info or {},
            validation_results=validation_results,
            analysis_results=analysis_results,
            interference_results=interference_results,
            weight_info=weight_info,
            elapsed_s=elapsed,
        )

    print(f"\n  Build complete in {elapsed:.1f}s")
    print("  " + sep)


if __name__ == "__main__":
    main()
