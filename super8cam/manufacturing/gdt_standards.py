"""GD&T standards reference — ISO tolerance bands and surface finish specs."""

from super8cam.specs.master_specs import TOL

# ISO 286-1 fundamental deviations (subset used in this project)
ISO_TOLERANCE_BANDS = {
    "H7": {"description": "Hole basis clearance/transition", "grade": 7},
    "k6": {"description": "Shaft basis transition fit", "grade": 6},
    "p6": {"description": "Shaft basis interference fit", "grade": 6},
}


def h7_limits(nominal_mm: float) -> dict:
    """Return H7 hole tolerance limits for a given nominal diameter."""
    # Simplified — covers 1-6mm and 6-10mm ranges
    if nominal_mm <= 3:
        tol_um = 10
    elif nominal_mm <= 6:
        tol_um = 12
    elif nominal_mm <= 10:
        tol_um = 15
    else:
        tol_um = 18

    return {
        "nominal": nominal_mm,
        "min_mm": nominal_mm,
        "max_mm": nominal_mm + tol_um / 1000,
        "tolerance_um": tol_um,
    }


def k6_limits(nominal_mm: float) -> dict:
    """Return k6 shaft tolerance limits."""
    if nominal_mm <= 3:
        dev_low, dev_high = 0, 6
    elif nominal_mm <= 6:
        dev_low, dev_high = 1, 9
    elif nominal_mm <= 10:
        dev_low, dev_high = 1, 10
    else:
        dev_low, dev_high = 1, 12

    return {
        "nominal": nominal_mm,
        "min_mm": nominal_mm + dev_low / 1000,
        "max_mm": nominal_mm + dev_high / 1000,
    }


SURFACE_FINISH_STANDARDS = {
    "N1": 0.025, "N2": 0.05, "N3": 0.1, "N4": 0.2,
    "N5": 0.4, "N6": 0.8, "N7": 1.6, "N8": 3.2,
    "N9": 6.3, "N10": 12.5,
}
