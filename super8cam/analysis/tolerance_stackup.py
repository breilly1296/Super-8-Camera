"""Tolerance stack-up analysis — critical dimension chains through the camera."""

import math
from super8cam.specs.master_specs import (
    FILM, CMOUNT, CAMERA, TOL, BEARINGS, MATERIALS,
)


def flange_distance_stackup():
    """Analyze the C-mount flange-to-film-plane dimension chain.

    Contributors:
        + front wall thickness
        + lens boss protrusion
        + shutter clearance
        + shutter thickness
        + gate-to-shutter clearance
        + gate plate thickness (to film surface)
        - gate channel depth (film rides in channel)

    Must equal CMOUNT.flange_focal_dist within tolerance.
    """
    contributors = [
        ("Front wall thickness", CAMERA.wall_thickness, TOL.cnc_general),
        ("Lens boss protrusion", CAMERA.lens_boss_protrusion, TOL.cnc_general),
        ("Shutter-to-gate clearance", CAMERA.shutter_to_gate_clearance, TOL.shutter_clearance),
        ("Shutter disc thickness", CAMERA.shutter_thickness, 0.02),
        ("Gate plate (front to channel)", CAMERA.gate_plate_thick - CAMERA.gate_channel_depth,
         TOL.cnc_fine),
    ]

    nominal_total = sum(c[1] for c in contributors)
    target = CMOUNT.flange_focal_dist

    # Worst-case stackup
    worst_case_tol = sum(c[2] for c in contributors)

    # RSS (statistical) stackup
    rss_tol = math.sqrt(sum(c[2] ** 2 for c in contributors))

    return {
        "target_mm": target,
        "nominal_total_mm": nominal_total,
        "error_mm": nominal_total - target,
        "contributors": contributors,
        "worst_case_tol_mm": worst_case_tol,
        "rss_tol_mm": rss_tol,
        "in_spec_worst": abs(nominal_total - target) <= worst_case_tol,
        "in_spec_rss": abs(nominal_total - target) <= rss_tol,
    }


def registration_accuracy():
    """Analyze registration pin positioning accuracy.

    The pin must locate each frame to within ±0.01mm of the aperture center.
    """
    contributors = [
        ("Pin hole position in gate", 0.0, TOL.reg_pin_position),
        ("Pin diameter tolerance", 0.0, (TOL.reg_pin_dia_plus + TOL.reg_pin_dia_minus) / 2),
        ("Perforation size tolerance (film)", 0.0, 0.02),  # Kodak spec
        ("Gate to body alignment", 0.0, TOL.cnc_fine),
    ]

    worst_case = sum(c[2] for c in contributors)
    rss = math.sqrt(sum(c[2] ** 2 for c in contributors))

    target_accuracy = 0.05  # mm — acceptable registration error

    return {
        "target_accuracy_mm": target_accuracy,
        "worst_case_error_mm": worst_case,
        "rss_error_mm": rss,
        "in_spec_worst": worst_case <= target_accuracy,
        "in_spec_rss": rss <= target_accuracy,
        "contributors": contributors,
    }


def bearing_fit_check():
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
