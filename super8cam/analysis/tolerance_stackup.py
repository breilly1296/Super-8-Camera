"""Tolerance stack-up analysis — critical dimension chains through the camera.

Performs worst-case and RSS (root sum square) tolerance stack-ups for:

1. Flange focal distance: lens mount face to film plane
2. Film registration accuracy: frame-to-frame positioning error
3. Shutter-to-gate clearance: can the shutter ever touch the gate?

Each stack-up prints a full report table with contributor name, nominal value,
tolerance, and sensitivity coefficient.
"""

import math
import os
from super8cam.specs.master_specs import (
    FILM, CMOUNT, CAMERA, TOL, BEARINGS, MATERIALS,
)


# =========================================================================
# 1. FLANGE FOCAL DISTANCE STACK-UP
# =========================================================================

def flange_distance_stackup() -> dict:
    """Analyze the C-mount flange-to-film-plane dimension chain.

    The C-mount standard requires the distance from the lens mounting
    flange face to the film emulsion surface to be 17.526 mm +/- 0.02 mm.

    Dimension chain (front to back, all positive toward film):
        + Front wall thickness            2.500 mm  +/- 0.050 mm
        + Lens boss protrusion            4.000 mm  +/- 0.050 mm
        + Shutter-to-gate clearance       0.300 mm  +/- 0.050 mm
        + Shutter disc thickness          0.800 mm  +/- 0.020 mm
        + Gate plate (front face to       2.900 mm  +/- 0.020 mm
          film channel surface)

    Note: the last contributor is gate_plate_thick minus gate_channel_depth
    because the film rides in a shallow channel cut into the gate face.

    Must equal CMOUNT.flange_focal_dist (17.526 mm) within tolerance.
    """
    contributors = [
        {
            "name": "Front wall thickness",
            "nominal": CAMERA.wall_thickness,
            "tolerance": TOL.cnc_general,
            "sensitivity": 1.0,
            "note": f"Aluminum 6061 body, CNC general +/-{TOL.cnc_general} mm",
        },
        {
            "name": "Lens boss protrusion",
            "nominal": CAMERA.lens_boss_protrusion,
            "tolerance": TOL.cnc_general,
            "sensitivity": 1.0,
            "note": f"Boss machined integral with body, +/-{TOL.cnc_general} mm",
        },
        {
            "name": "Shutter-to-gate clearance",
            "nominal": CAMERA.shutter_to_gate_clearance,
            "tolerance": TOL.shutter_clearance,
            "sensitivity": 1.0,
            "note": f"Set by bearing seat depth, +/-{TOL.shutter_clearance} mm",
        },
        {
            "name": "Shutter disc thickness",
            "nominal": CAMERA.shutter_thickness,
            "tolerance": 0.02,
            "sensitivity": 1.0,
            "note": "Sheet aluminum, rolled to tolerance +/-0.02 mm",
        },
        {
            "name": "Gate plate (front to channel)",
            "nominal": CAMERA.gate_plate_thick - CAMERA.gate_channel_depth,
            "tolerance": TOL.cnc_fine,
            "sensitivity": 1.0,
            "note": f"Brass C360 precision ground, +/-{TOL.cnc_fine} mm. "
                    f"gate_thick ({CAMERA.gate_plate_thick}) - "
                    f"channel_depth ({CAMERA.gate_channel_depth})",
        },
    ]

    # Extract simple (name, nominal, tolerance) list for backward compatibility
    contributors_simple = [(c["name"], c["nominal"], c["tolerance"]) for c in contributors]

    nominal_total = sum(c["nominal"] for c in contributors)
    target = CMOUNT.flange_focal_dist
    error = nominal_total - target

    # Worst-case: all tolerances add up linearly
    worst_case_tol = sum(abs(c["sensitivity"]) * c["tolerance"] for c in contributors)

    # RSS (statistical): root sum square assuming independent normal distributions
    rss_tol = math.sqrt(sum((c["sensitivity"] * c["tolerance"]) ** 2 for c in contributors))

    # Spec check: error + tolerance band must keep us within +/-0.02 mm
    spec_band = 0.02  # mm — industry spec for C-mount
    in_spec_worst = abs(error) + worst_case_tol <= spec_band
    in_spec_rss = abs(error) + rss_tol <= spec_band

    return {
        "target_mm": target,
        "nominal_total_mm": nominal_total,
        "error_mm": error,
        "contributors": contributors_simple,
        "contributors_detail": contributors,
        "worst_case_tol_mm": worst_case_tol,
        "rss_tol_mm": rss_tol,
        "spec_band_mm": spec_band,
        "in_spec_worst": in_spec_worst,
        "in_spec_rss": in_spec_rss,
    }


# =========================================================================
# 2. FILM REGISTRATION ACCURACY STACK-UP
# =========================================================================

def registration_accuracy() -> dict:
    """Analyze registration pin positioning accuracy.

    How precisely is each frame positioned relative to the optical axis?
    The pin must locate each frame to within the Kodak spec of +/-0.025 mm.

    Error contributors:
        1. Pin hole position in gate        +/- 0.010 mm  (CNC boring)
        2. Pin diameter tolerance            +/- 0.0025 mm (ground pin)
        3. Perforation size tolerance (film) +/- 0.020 mm  (Kodak spec)
        4. Gate to body alignment            +/- 0.020 mm  (CNC fine)
        5. Claw pulldown accuracy            +/- 0.010 mm  (cam profile)
        6. Gate aperture position tolerance  +/- 0.005 mm  (precision ground)

    All sensitivities are 1:1 (linear contributors).
    """
    contributors = [
        {
            "name": "Pin hole position in gate",
            "nominal": 0.0,
            "tolerance": TOL.reg_pin_position,
            "sensitivity": 1.0,
            "note": f"CNC bored in brass gate, +/-{TOL.reg_pin_position} mm",
        },
        {
            "name": "Pin diameter tolerance",
            "nominal": 0.0,
            "tolerance": (TOL.reg_pin_dia_plus + TOL.reg_pin_dia_minus) / 2,
            "sensitivity": 1.0,
            "note": f"Ground steel pin {CAMERA.reg_pin_dia} mm "
                    f"+{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm. "
                    f"Pin-in-hole clearance creates lateral play.",
        },
        {
            "name": "Perforation size tolerance (film)",
            "nominal": 0.0,
            "tolerance": 0.02,
            "sensitivity": 1.0,
            "note": "Kodak Super 8 perforation tolerance per SMPTE spec",
        },
        {
            "name": "Gate to body alignment",
            "nominal": 0.0,
            "tolerance": TOL.cnc_fine,
            "sensitivity": 1.0,
            "note": f"Gate mounting screws + dowel pins, +/-{TOL.cnc_fine} mm",
        },
        {
            "name": "Claw pulldown accuracy",
            "nominal": 0.0,
            "tolerance": 0.01,
            "sensitivity": 1.0,
            "note": "Cam profile / lost motion error, estimated +/-0.01 mm",
        },
        {
            "name": "Gate aperture position tolerance",
            "nominal": 0.0,
            "tolerance": TOL.gate_aperture,
            "sensitivity": 1.0,
            "note": f"Aperture position rel. to pin hole, +/-{TOL.gate_aperture} mm",
        },
    ]

    contributors_simple = [(c["name"], c["nominal"], c["tolerance"]) for c in contributors]

    worst_case = sum(abs(c["sensitivity"]) * c["tolerance"] for c in contributors)
    rss = math.sqrt(sum((c["sensitivity"] * c["tolerance"]) ** 2 for c in contributors))

    target_accuracy = 0.025  # mm — Kodak spec max registration error
    # Also check against our tighter target
    tight_target = 0.05  # mm — our design target (more lenient for initial pass)

    return {
        "target_accuracy_mm": tight_target,
        "kodak_spec_mm": target_accuracy,
        "worst_case_error_mm": worst_case,
        "rss_error_mm": rss,
        "in_spec_worst": worst_case <= tight_target,
        "in_spec_rss": rss <= tight_target,
        "in_kodak_worst": worst_case <= target_accuracy,
        "in_kodak_rss": rss <= target_accuracy,
        "contributors": contributors_simple,
        "contributors_detail": contributors,
    }


# =========================================================================
# 3. SHUTTER-TO-GATE CLEARANCE STACK-UP
# =========================================================================

def shutter_clearance_stackup() -> dict:
    """Analyze whether the shutter disc can ever contact the film gate.

    Nominal clearance is 0.3 mm.  Under worst-case tolerance stack-up,
    the gap can shrink.  If it reaches zero, the shutter hits the gate.

    Error contributors (reduce the gap):
        1. Shaft bearing radial play        +/- 0.005 mm  (694ZZ bearing)
        2. Shutter disc flatness            +/- 0.030 mm  (sheet metal)
        3. Bearing seat axial tolerance     +/- 0.050 mm  (CNC general)
        4. Shutter disc thickness tolerance +/- 0.020 mm  (rolled sheet)
        5. Gate plate flatness              +/- 0.010 mm  (precision ground)
        6. Shutter disc runout (TIR)        +/- 0.020 mm  (mounted on shaft)

    Sensitivity: all contributors reduce the gap (sensitivity = -1).
    The minimum clearance = nominal_gap - worst_case_stack.
    """
    nominal_gap = CAMERA.shutter_to_gate_clearance  # 0.3 mm

    contributors = [
        {
            "name": "Shaft bearing radial play",
            "nominal": 0.0,
            "tolerance": 0.005,
            "sensitivity": 1.0,
            "note": f"694ZZ miniature bearing, C3 clearance class. "
                    f"Radial play converts to axial wobble at shutter OD.",
        },
        {
            "name": "Shutter disc flatness",
            "nominal": 0.0,
            "tolerance": 0.03,
            "sensitivity": 1.0,
            "note": "Aluminum sheet stamped/laser-cut, post-flattened. "
                    "TIR across disc face.",
        },
        {
            "name": "Bearing seat axial tolerance",
            "nominal": 0.0,
            "tolerance": TOL.cnc_general,
            "sensitivity": 1.0,
            "note": f"Sets axial position of shaft/shutter, +/-{TOL.cnc_general} mm",
        },
        {
            "name": "Shutter disc thickness tolerance",
            "nominal": 0.0,
            "tolerance": 0.02,
            "sensitivity": 1.0,
            "note": f"Rolled aluminum sheet, nominal {CAMERA.shutter_thickness} mm",
        },
        {
            "name": "Gate plate flatness",
            "nominal": 0.0,
            "tolerance": 0.01,
            "sensitivity": 1.0,
            "note": "Precision ground brass face",
        },
        {
            "name": "Shutter disc runout (TIR)",
            "nominal": 0.0,
            "tolerance": 0.02,
            "sensitivity": 1.0,
            "note": "Total indicated runout when mounted on shaft with keyway",
        },
    ]

    contributors_simple = [(c["name"], c["nominal"], c["tolerance"]) for c in contributors]

    worst_case_reduction = sum(abs(c["sensitivity"]) * c["tolerance"] for c in contributors)
    rss_reduction = math.sqrt(sum((c["sensitivity"] * c["tolerance"]) ** 2 for c in contributors))

    min_clearance_worst = nominal_gap - worst_case_reduction
    min_clearance_rss = nominal_gap - rss_reduction

    return {
        "nominal_gap_mm": nominal_gap,
        "worst_case_reduction_mm": worst_case_reduction,
        "rss_reduction_mm": rss_reduction,
        "min_clearance_worst_mm": min_clearance_worst,
        "min_clearance_rss_mm": min_clearance_rss,
        "contact_possible_worst": min_clearance_worst <= 0,
        "contact_possible_rss": min_clearance_rss <= 0,
        "contributors": contributors_simple,
        "contributors_detail": contributors,
    }


# =========================================================================
# Bearing fit check (preserved from original)
# =========================================================================

def bearing_fit_check() -> dict:
    """Verify bearing seat and shaft fits against ISO tolerance bands."""
    brg = BEARINGS["main_shaft"]
    shaft_dia = CAMERA.shaft_dia

    return {
        "bearing": brg.designation,
        "bore": brg.bore,
        "od": brg.od,
        "shaft_dia_nom": shaft_dia,
        "housing_bore_tolerance": TOL.bearing_seat,
        "shaft_tolerance": "k6",
        "note": (f"Shaft {shaft_dia}mm {TOL.bearing_seat}/{TOL.press_fit_shaft} "
                 f"transition fit for bearing {brg.designation}"),
    }


# =========================================================================
# Full report
# =========================================================================

def _print_contributor_table(contributors: list, title: str):
    """Print a formatted table of stack-up contributors."""
    print(f"\n  {title}")
    print("  " + "-" * 72)
    print(f"    {'#':>2s}  {'Contributor':<35s}  {'Nominal':>8s}  {'Tol +/-':>8s}  {'Sens':>5s}")
    print("    " + "-" * 68)
    for i, c in enumerate(contributors, 1):
        nom = c.get("nominal", 0.0) if isinstance(c, dict) else c[1]
        tol = c.get("tolerance", 0.0) if isinstance(c, dict) else c[2]
        sens = c.get("sensitivity", 1.0) if isinstance(c, dict) else 1.0
        name = c.get("name", c[0]) if isinstance(c, dict) else c[0]
        note = c.get("note", "") if isinstance(c, dict) else ""
        print(f"    {i:>2d}  {name:<35s}  {nom:>8.3f}  {tol:>8.4f}  {sens:>5.1f}")
        if note:
            print(f"        {note}")


def print_stackup_report():
    """Print full tolerance stack-up reports for all three analyses."""
    sep = "=" * 72
    print(sep)
    print("  TOLERANCE STACK-UP ANALYSIS")
    print(sep)

    # --- 1. Flange focal distance ---
    fs = flange_distance_stackup()
    _print_contributor_table(fs["contributors_detail"],
                             "1. FLANGE FOCAL DISTANCE (lens mount → film plane)")
    print(f"\n    Target (C-mount spec):  {fs['target_mm']:.3f} mm")
    print(f"    Nominal chain total:    {fs['nominal_total_mm']:.3f} mm")
    print(f"    Nominal error:          {fs['error_mm']:.3f} mm")
    print(f"    Worst-case tolerance:   +/-{fs['worst_case_tol_mm']:.3f} mm")
    print(f"    RSS tolerance:          +/-{fs['rss_tol_mm']:.3f} mm")
    print(f"    Spec band:              +/-{fs['spec_band_mm']:.3f} mm")
    print(f"    In spec (worst-case):   {'PASS' if fs['in_spec_worst'] else 'FAIL'}")
    print(f"    In spec (RSS):          {'PASS' if fs['in_spec_rss'] else 'FAIL'}")

    # --- 2. Registration accuracy ---
    ra = registration_accuracy()
    _print_contributor_table(ra["contributors_detail"],
                             "2. FILM REGISTRATION ACCURACY")
    print(f"\n    Our design target:       +/-{ra['target_accuracy_mm']:.3f} mm")
    print(f"    Kodak spec:              +/-{ra['kodak_spec_mm']:.3f} mm")
    print(f"    Worst-case error:        {ra['worst_case_error_mm']:.4f} mm")
    print(f"    RSS error:               {ra['rss_error_mm']:.4f} mm")
    print(f"    Meets design (worst):    {'PASS' if ra['in_spec_worst'] else 'FAIL'}")
    print(f"    Meets design (RSS):      {'PASS' if ra['in_spec_rss'] else 'FAIL'}")
    print(f"    Meets Kodak (worst):     {'PASS' if ra['in_kodak_worst'] else 'FAIL'}")
    print(f"    Meets Kodak (RSS):       {'PASS' if ra['in_kodak_rss'] else 'FAIL'}")

    # --- 3. Shutter-to-gate clearance ---
    sc = shutter_clearance_stackup()
    _print_contributor_table(sc["contributors_detail"],
                             "3. SHUTTER-TO-GATE CLEARANCE")
    print(f"\n    Nominal gap:             {sc['nominal_gap_mm']:.3f} mm")
    print(f"    Worst-case reduction:    {sc['worst_case_reduction_mm']:.3f} mm")
    print(f"    RSS reduction:           {sc['rss_reduction_mm']:.3f} mm")
    print(f"    Min clearance (worst):   {sc['min_clearance_worst_mm']:.3f} mm")
    print(f"    Min clearance (RSS):     {sc['min_clearance_rss_mm']:.3f} mm")
    print(f"    Contact possible (worst): {'YES — REDESIGN' if sc['contact_possible_worst'] else 'NO'}")
    print(f"    Contact possible (RSS):   {'YES — REDESIGN' if sc['contact_possible_rss'] else 'NO'}")

    # --- 4. Bearing fit ---
    bf = bearing_fit_check()
    print(f"\n  4. BEARING FIT CHECK")
    print("  " + "-" * 72)
    print(f"    {bf['note']}")

    print("\n  " + sep)


if __name__ == "__main__":
    print_stackup_report()
