"""Tolerance stack-up analysis — critical dimension chains through the camera.

Performs worst-case and RSS (root sum square) stack-ups for three critical
dimension chains:

1. FLANGE FOCAL DISTANCE: lens mount face → film plane
   Target: 17.526 mm (C-mount standard)
   Acceptance: ±0.02 mm

2. FILM REGISTRATION ACCURACY: frame-to-frame positioning
   Target: ±0.025 mm (Kodak specification)
   Contributors: pin position, pin diameter, perforation tolerance,
   gate alignment, claw pulldown accuracy

3. SHUTTER-TO-GATE CLEARANCE: minimum gap under worst-case stack-up
   Nominal: 0.3 mm
   Must remain >0 under all tolerance combinations

Each stack-up includes:
  - Contributor table with nominal, tolerance, and sensitivity coefficient
  - Worst-case total (sum of |sensitivity × tolerance|)
  - RSS total (sqrt of sum of (sensitivity × tolerance)²)
  - Pass/fail against acceptance criteria
"""

import math
from super8cam.specs.master_specs import (
    FILM, CMOUNT, CAMERA, TOL, BEARINGS, MATERIALS, ANALYSIS,
)


# =========================================================================
# STACK-UP DATA STRUCTURE
# =========================================================================

class StackUpContributor:
    """One link in a tolerance stack-up chain."""

    def __init__(self, name: str, nominal: float, tolerance: float,
                 sensitivity: float = 1.0, unit: str = "mm",
                 note: str = ""):
        self.name = name
        self.nominal = nominal        # nominal dimension (mm)
        self.tolerance = tolerance    # bilateral ± tolerance (mm)
        self.sensitivity = sensitivity  # di/dx (usually +1 or -1)
        self.unit = unit
        self.note = note

    @property
    def contribution_worst(self) -> float:
        """Worst-case contribution to total error."""
        return abs(self.sensitivity) * self.tolerance

    @property
    def contribution_rss(self) -> float:
        """RSS contribution (squared)."""
        return (self.sensitivity * self.tolerance) ** 2


def compute_stackup(contributors: list, target: float = None,
                    target_tol: float = None) -> dict:
    """Compute worst-case and RSS stack-up from a list of contributors.

    Args:
        contributors: list of StackUpContributor objects
        target: target dimension (mm). None to skip comparison.
        target_tol: acceptance tolerance ± (mm). None to skip.

    Returns:
        dict with nominal_total, worst_case_tol, rss_tol, error, pass/fail
    """
    nominal_total = sum(c.sensitivity * c.nominal for c in contributors)
    worst_case_tol = sum(c.contribution_worst for c in contributors)
    rss_tol = math.sqrt(sum(c.contribution_rss for c in contributors))

    result = {
        "nominal_total_mm": nominal_total,
        "worst_case_tol_mm": worst_case_tol,
        "rss_tol_mm": rss_tol,
        "contributors": contributors,
    }

    if target is not None:
        error = nominal_total - target
        result["target_mm"] = target
        result["error_mm"] = error

        if target_tol is not None:
            result["target_tol_mm"] = target_tol
            result["in_spec_worst"] = (
                abs(error) + worst_case_tol <= target_tol)
            result["in_spec_rss"] = (
                abs(error) + rss_tol <= target_tol)
            # Also check: can nominal error + worst tol exceed target tol?
            result["worst_case_range_mm"] = (
                nominal_total - worst_case_tol,
                nominal_total + worst_case_tol)
            result["rss_range_mm"] = (
                nominal_total - rss_tol,
                nominal_total + rss_tol)

    return result


# =========================================================================
# 1. FLANGE FOCAL DISTANCE
# =========================================================================

def flange_distance_stackup() -> dict:
    """Analyze the C-mount flange-to-film-plane dimension chain.

    Chain (from lens mount face to film plane):
      + Mount face to shutter front face (machined bore depth)
      + Shutter disc thickness
      + Shutter-to-gate clearance (gap)
      + Gate front face to film surface (gate_thick - channel_depth)

    Must equal 17.526 mm ± 0.02 mm.

    This chain matches the validated stack-up in parts/lens_mount.py:
      MOUNT_TO_SHUTTER_FRONT = 17.526 - 3.80 - 0.30 - 0.80 = 12.626 mm
    """
    # Import the validated mount-to-shutter distance from lens_mount
    from super8cam.parts.lens_mount import MOUNT_TO_SHUTTER_FRONT
    from super8cam.parts.film_gate import GATE_THICK, CHANNEL_DEPTH
    from super8cam.parts.shutter_disc import DISC_THICK, GATE_CLEARANCE

    gate_to_film = GATE_THICK - CHANNEL_DEPTH  # 4.0 - 0.20 = 3.80 mm

    contributors = [
        StackUpContributor(
            name="Mount face to shutter front",
            nominal=MOUNT_TO_SHUTTER_FRONT,
            tolerance=0.01,
            sensitivity=+1.0,
            note="Jig-bored mount cavity, 10um tolerance"),
        StackUpContributor(
            name="Shutter disc thickness",
            nominal=DISC_THICK,
            tolerance=0.005,
            sensitivity=+1.0,
            note="Precision ground aluminum disc"),
        StackUpContributor(
            name="Shutter-to-gate clearance",
            nominal=GATE_CLEARANCE,
            tolerance=TOL.shutter_clearance,
            sensitivity=+1.0,
            note="Precision ground shim sets gap"),
        StackUpContributor(
            name="Gate front to film surface",
            nominal=gate_to_film,
            tolerance=0.01,
            sensitivity=+1.0,
            note="Precision ground/lapped brass gate"),
    ]

    target = CMOUNT.flange_focal_dist  # 17.526 mm
    target_tol = ANALYSIS.flange_acceptance_tol  # ±0.02 mm acceptance

    result = compute_stackup(contributors, target, target_tol)

    # Legacy API compatibility
    result["target_mm"] = target
    result["nominal_total_mm"] = result["nominal_total_mm"]
    result["error_mm"] = result.get("error_mm", 0)
    result["in_spec_worst"] = result.get("in_spec_worst", True)
    result["in_spec_rss"] = result.get("in_spec_rss", True)

    return result


# =========================================================================
# 2. FILM REGISTRATION ACCURACY
# =========================================================================

def registration_accuracy() -> dict:
    """Analyze frame-to-frame registration accuracy.

    How precisely is each frame positioned relative to the aperture?
    The film is located by the registration pin engaging a perforation.

    Error contributors:
      1. Pin hole position in gate (relative to aperture center)
      2. Pin diameter tolerance (clearance in perforation)
      3. Perforation size tolerance (Kodak film manufacturing)
      4. Gate-to-body alignment (dowel pin precision)
      5. Claw pulldown accuracy (does claw stop at exactly 4.234mm?)
      6. Film stretch under tension (PET elastic strain)

    Kodak specification: ±0.025 mm frame-to-frame registration.
    """
    contributors = [
        StackUpContributor(
            name="Pin hole position in gate",
            nominal=0.0,
            tolerance=TOL.reg_pin_position,  # 0.01 mm
            sensitivity=1.0,
            note="CNC drilling position, fine tolerance"),
        StackUpContributor(
            name="Pin diameter tolerance",
            nominal=0.0,
            tolerance=(TOL.reg_pin_dia_plus + TOL.reg_pin_dia_minus) / 2,
            sensitivity=1.0,
            note="Ground pin, max play = (perf - pin_min) / 2"),
        StackUpContributor(
            name="Perforation size (Kodak spec)",
            nominal=0.0,
            tolerance=ANALYSIS.perf_size_tolerance,
            sensitivity=1.0,
            note="Kodak film manufacturing tolerance"),
        StackUpContributor(
            name="Gate-to-body alignment",
            nominal=0.0,
            tolerance=ANALYSIS.gate_body_alignment,
            sensitivity=1.0,
            note="Dowel pin alignment, H6 precision bore"),
        StackUpContributor(
            name="Claw pulldown accuracy",
            nominal=0.0,
            tolerance=ANALYSIS.claw_pulldown_accuracy,
            sensitivity=1.0,
            note="Cam profile + guided claw (0.03mm/side clearance)"),
        StackUpContributor(
            name="Film stretch under tension",
            nominal=0.0,
            tolerance=ANALYSIS.film_stretch_tolerance,
            sensitivity=1.0,
            note="PET base elastic strain at 0.5N: "
                 "ΔL = F·L / (E·A) ≈ 0.003mm per frame"),
    ]

    target_accuracy = ANALYSIS.kodak_registration_spec  # mm — Kodak spec

    result = compute_stackup(contributors, target=0.0,
                             target_tol=target_accuracy)

    # Override target semantics for registration (error accumulation, not chain)
    result["target_accuracy_mm"] = target_accuracy
    result["worst_case_error_mm"] = result["worst_case_tol_mm"]
    result["rss_error_mm"] = result["rss_tol_mm"]
    result["in_spec_worst"] = result["worst_case_tol_mm"] <= target_accuracy
    result["in_spec_rss"] = result["rss_tol_mm"] <= target_accuracy

    return result


# =========================================================================
# 3. SHUTTER-TO-GATE CLEARANCE
# =========================================================================

def shutter_gate_clearance_stackup() -> dict:
    """Analyze whether the shutter disc can ever contact the film gate.

    Nominal clearance: 0.3 mm (between disc rear face and gate front face).

    Error contributors that REDUCE clearance:
      1. Shaft bearing radial play (shaft deflects toward gate)
      2. Shutter disc flatness (wobble during rotation)
      3. Disc thickness tolerance (thicker disc reduces gap)
      4. Shutter spacer tolerance (gap set by spacer/shim)
      5. Gate plate flatness
      6. Thermal expansion differential (alu disc vs brass gate)
      7. Bearing seat alignment (housing bore tilt)

    The clearance must remain positive (>0) under worst-case stack-up.
    A minimum clearance of 0.05 mm is the design target.
    """
    # Bearing 694ZZ radial clearance (C2 class internal clearance)
    brg = BEARINGS["main_shaft"]
    # 694ZZ radial play: typically 3-10 μm per bearing.
    # With two bearings spanning ~10mm, the angular play produces a
    # radial deflection at the shutter disc position.
    # Worst case: both bearings at max play, same direction.
    bearing_radial_play = ANALYSIS.bearing_radial_play  # mm (10 μm per bearing, one side)

    # Shaft span from bearing to shutter disc center
    # Bearing span ~10mm, shutter disc at ~5mm beyond front bearing
    bearing_span = ANALYSIS.bearing_span  # mm approximate
    shutter_overhang = ANALYSIS.shutter_overhang  # mm past front bearing
    angular_tilt_factor = (bearing_span + shutter_overhang) / bearing_span

    # Disc flatness: 0.8mm thick aluminum disc, typical flatness
    disc_flatness = ANALYSIS.disc_flatness  # mm (precision stamped + ground)

    # Temperature differential: motor heats aluminum body (23.6 ppm/K),
    # brass gate is more stable (20.5 ppm/K). At ΔT=5°C:
    # The disc and gate expand axially along the shaft.
    # Differential: (23.6 - 20.5) × 5 × 0.3 / 1000 ≈ negligible
    # But the disc OD expands radially, and the gate plate expands in-plane.
    # The axial gap is not affected by in-plane expansion.
    # The critical thermal effect is shaft thermal growth:
    #   Shaft material: 4140 steel, 12.3 ppm/K
    #   ΔL = 12.3e-6 × 5 × 30mm (shaft length) = 0.002mm
    thermal_axial_shift = 0.002  # mm at ΔT=5°C

    contributors = [
        StackUpContributor(
            name="Nominal shutter-gate gap",
            nominal=CAMERA.shutter_to_gate_clearance,  # 0.3 mm
            tolerance=0.0,
            sensitivity=+1.0,
            note="Design intent clearance"),
        StackUpContributor(
            name="Shutter spacer/shim tolerance",
            nominal=0.0,
            tolerance=TOL.shutter_clearance,  # 0.05 mm
            sensitivity=-1.0,
            note="Spacer sets the axial gap"),
        StackUpContributor(
            name="Disc thickness tolerance",
            nominal=0.0,
            tolerance=0.02,
            sensitivity=-1.0,
            note="Thicker disc encroaches on gap"),
        StackUpContributor(
            name="Shaft bearing radial play (tilt)",
            nominal=0.0,
            tolerance=bearing_radial_play * angular_tilt_factor,
            sensitivity=-1.0,
            note=f"694ZZ play × tilt factor {angular_tilt_factor:.1f}"),
        StackUpContributor(
            name="Disc flatness (runout)",
            nominal=0.0,
            tolerance=disc_flatness,
            sensitivity=-1.0,
            note="Precision ground disc, TIR check"),
        StackUpContributor(
            name="Gate plate flatness",
            nominal=0.0,
            tolerance=ANALYSIS.gate_flatness,
            sensitivity=-1.0,
            note="Precision lapped brass"),
        StackUpContributor(
            name="Bearing seat alignment (tilt)",
            nominal=0.0,
            tolerance=0.01,
            sensitivity=-1.0,
            note="Housing bore perpendicularity"),
        StackUpContributor(
            name="Thermal expansion (shaft axial)",
            nominal=0.0,
            tolerance=thermal_axial_shift,
            sensitivity=-1.0,
            note=f"Steel 4140, ΔT=5°C, L=30mm"),
    ]

    # For clearance: the nominal gap minus all negative contributors
    # must remain positive.
    nominal_gap = CAMERA.shutter_to_gate_clearance  # 0.3 mm
    worst_case_reduction = sum(c.contribution_worst for c in contributors
                                if c.sensitivity < 0)
    rss_reduction = math.sqrt(sum(c.contribution_rss for c in contributors
                                   if c.sensitivity < 0))

    min_clearance_worst = nominal_gap - worst_case_reduction
    min_clearance_rss = nominal_gap - rss_reduction
    design_min = ANALYSIS.design_min_clearance  # mm — minimum acceptable clearance

    return {
        "nominal_gap_mm": nominal_gap,
        "worst_case_reduction_mm": worst_case_reduction,
        "rss_reduction_mm": rss_reduction,
        "min_clearance_worst_mm": min_clearance_worst,
        "min_clearance_rss_mm": min_clearance_rss,
        "design_min_mm": design_min,
        "pass_worst": min_clearance_worst >= design_min,
        "pass_rss": min_clearance_rss >= design_min,
        "contact_risk": min_clearance_worst <= 0,
        "contributors": contributors,
    }


# =========================================================================
# BEARING FIT CHECK
# =========================================================================

def bearing_fit_check() -> dict:
    """Verify bearing seat and shaft fits against ISO tolerance bands.

    694ZZ bearing: 4mm bore × 11mm OD × 4mm width.
    Shaft seat: k6 (transition fit for inner ring).
    Housing bore: H7 (clearance fit for outer ring).
    """
    brg = BEARINGS["main_shaft"]
    shaft_dia = CAMERA.shaft_dia

    # ISO k6 tolerance band for 4mm shaft:
    # k6: +0.009 to +0.001 mm (interference to transition)
    k6_upper = 0.009  # mm
    k6_lower = 0.001  # mm

    # ISO H7 tolerance band for 11mm housing bore:
    # H7: 0 to +0.018 mm (clearance)
    h7_upper = 0.018  # mm
    h7_lower = 0.000  # mm

    # Bearing inner ring: nominal 4.000mm, tolerance -0 to -0.008mm
    brg_inner_upper = 0.000  # mm
    brg_inner_lower = -0.008  # mm

    # Bearing outer ring: nominal 11.000mm, tolerance 0 to -0.008mm
    brg_outer_upper = 0.000  # mm
    brg_outer_lower = -0.008  # mm

    # Shaft interference range:
    # Max interference: shaft_max - ring_min = k6_upper - brg_inner_lower
    max_interference = k6_upper - brg_inner_lower  # 0.009 - (-0.008) = 0.017
    # Min interference: shaft_min - ring_max = k6_lower - brg_inner_upper
    min_interference = k6_lower - brg_inner_upper  # 0.001 - 0 = 0.001

    # Housing clearance range:
    # Max clearance: housing_max - ring_min = h7_upper - brg_outer_lower
    max_clearance = h7_upper - brg_outer_lower  # 0.018 - (-0.008) = 0.026
    # Min clearance: housing_min - ring_max = h7_lower - brg_outer_upper
    min_clearance = h7_lower - brg_outer_upper  # 0 - 0 = 0

    return {
        "bearing": brg.designation,
        "bore": brg.bore,
        "od": brg.od,
        "shaft_dia_nom": shaft_dia,
        "housing_bore_tolerance": TOL.bearing_seat,
        "shaft_tolerance": "k6",
        "shaft_fit": {
            "max_interference_mm": max_interference,
            "min_interference_mm": min_interference,
            "fit_type": "Transition (light press)",
        },
        "housing_fit": {
            "max_clearance_mm": max_clearance,
            "min_clearance_mm": min_clearance,
            "fit_type": "Clearance (push fit)",
        },
        "note": (f"Shaft {shaft_dia}mm k6/{TOL.bearing_seat} "
                 f"transition fit for bearing {brg.designation}. "
                 f"Shaft interference: {min_interference:.3f} to "
                 f"{max_interference:.3f} mm. "
                 f"Housing clearance: {min_clearance:.3f} to "
                 f"{max_clearance:.3f} mm."),
    }


# =========================================================================
# REPORTING
# =========================================================================

def _print_stackup_table(title: str, contributors: list,
                         nominal_total: float = None,
                         target: float = None,
                         target_tol: float = None,
                         worst_case: float = None,
                         rss: float = None):
    """Print a formatted stack-up contributor table."""
    sep = "-" * 72
    print(f"\n  {title}")
    print(f"  {sep}")
    print(f"  {'Contributor':<36s} {'Nominal':>8s} {'Tol ±':>8s} "
          f"{'Sens':>5s} {'WC ±':>8s}")
    print(f"  {sep}")

    for c in contributors:
        nom_str = f"{c.nominal:+.4f}" if c.nominal != 0 else "   —   "
        print(f"  {c.name:<36s} {nom_str:>8s} {c.tolerance:>8.4f} "
              f"{c.sensitivity:>+5.1f} {c.contribution_worst:>8.4f}")
        if c.note:
            print(f"    {'':36s} {c.note}")

    print(f"  {sep}")
    if nominal_total is not None:
        print(f"  {'NOMINAL TOTAL':<36s} {nominal_total:>+8.4f}")
    if target is not None:
        error = nominal_total - target if nominal_total is not None else 0
        print(f"  {'TARGET':<36s} {target:>+8.4f} "
              f"(error: {error:>+.4f} mm)")
    if worst_case is not None:
        print(f"  {'WORST-CASE TOLERANCE':<36s} {'':>8s} {worst_case:>8.4f}")
    if rss is not None:
        print(f"  {'RSS TOLERANCE':<36s} {'':>8s} {rss:>8.4f}")
    if target_tol is not None:
        print(f"  {'ACCEPTANCE':<36s} {'':>8s} ±{target_tol:.4f}")


def print_full_report():
    """Print all three tolerance stack-up analyses."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("  TOLERANCE STACK-UP ANALYSIS")
    print(sep)

    # ---- 1. Flange Distance ----
    fd = flange_distance_stackup()
    _print_stackup_table(
        "1. FLANGE FOCAL DISTANCE (C-mount → film plane)",
        fd["contributors"],
        nominal_total=fd["nominal_total_mm"],
        target=fd["target_mm"],
        target_tol=fd.get("target_tol_mm", 0.02),
        worst_case=fd["worst_case_tol_mm"],
        rss=fd["rss_tol_mm"],
    )
    fd_wc_pass = fd.get("in_spec_worst", True)
    fd_rss_pass = fd.get("in_spec_rss", True)
    print(f"\n  Worst-case: {'PASS' if fd_wc_pass else 'FAIL'} "
          f"(|error| + WC_tol = {abs(fd['error_mm']) + fd['worst_case_tol_mm']:.4f} "
          f"vs ±0.02)")
    print(f"  RSS:        {'PASS' if fd_rss_pass else 'FAIL'} "
          f"(|error| + RSS_tol = {abs(fd['error_mm']) + fd['rss_tol_mm']:.4f} "
          f"vs ±0.02)")

    # ---- 2. Registration Accuracy ----
    ra = registration_accuracy()
    _print_stackup_table(
        "2. FILM REGISTRATION ACCURACY (frame positioning)",
        ra["contributors"],
        target=0.0,
        target_tol=ra["target_accuracy_mm"],
        worst_case=ra["worst_case_error_mm"],
        rss=ra["rss_error_mm"],
    )
    ra_wc_pass = ra["in_spec_worst"]
    ra_rss_pass = ra["in_spec_rss"]
    print(f"\n  Kodak spec: ±{ra['target_accuracy_mm']:.3f} mm")
    print(f"  Worst-case: {'PASS' if ra_wc_pass else 'FAIL'} "
          f"(±{ra['worst_case_error_mm']:.4f} mm)")
    print(f"  RSS:        {'PASS' if ra_rss_pass else 'FAIL'} "
          f"(±{ra['rss_error_mm']:.4f} mm)")

    # ---- 3. Shutter-Gate Clearance ----
    sg = shutter_gate_clearance_stackup()
    _print_stackup_table(
        "3. SHUTTER-TO-GATE CLEARANCE",
        sg["contributors"],
        nominal_total=sg["nominal_gap_mm"],
        worst_case=sg["worst_case_reduction_mm"],
        rss=sg["rss_reduction_mm"],
    )
    print(f"\n  Nominal gap:         {sg['nominal_gap_mm']:.3f} mm")
    print(f"  Worst-case min gap:  {sg['min_clearance_worst_mm']:.3f} mm "
          f"({'PASS' if sg['pass_worst'] else 'FAIL'}, "
          f"need ≥{sg['design_min_mm']:.2f})")
    print(f"  RSS min gap:         {sg['min_clearance_rss_mm']:.3f} mm "
          f"({'PASS' if sg['pass_rss'] else 'FAIL'}, "
          f"need ≥{sg['design_min_mm']:.2f})")
    if sg["contact_risk"]:
        print(f"  *** WARNING: Contact possible under worst-case conditions! ***")

    # ---- 4. Bearing Fit ----
    bf = bearing_fit_check()
    print(f"\n  4. BEARING FIT CHECK")
    print(f"  {'-' * 60}")
    print(f"  {bf['note']}")
    sf = bf["shaft_fit"]
    hf = bf["housing_fit"]
    print(f"    Shaft k6:   interference {sf['min_interference_mm']:.3f} "
          f"to {sf['max_interference_mm']:.3f} mm ({sf['fit_type']})")
    print(f"    Housing H7: clearance {hf['min_clearance_mm']:.3f} "
          f"to {hf['max_clearance_mm']:.3f} mm ({hf['fit_type']})")

    # ---- Overall ----
    print(f"\n{sep}")
    all_pass = fd_rss_pass and ra_rss_pass and sg["pass_rss"]
    print(f"  Overall (RSS): {'ALL PASS' if all_pass else 'ISSUES FOUND'}")
    if not all_pass:
        if not fd_rss_pass:
            print("    -> Flange distance out of spec")
        if not ra_rss_pass:
            print("    -> Registration accuracy exceeds Kodak spec")
        if not sg["pass_rss"]:
            print("    -> Shutter clearance insufficient")
    print(sep)

    return {
        "flange_distance": fd,
        "registration": ra,
        "shutter_clearance": sg,
        "bearing_fit": bf,
        "all_pass_rss": all_pass,
    }


if __name__ == "__main__":
    print_full_report()
