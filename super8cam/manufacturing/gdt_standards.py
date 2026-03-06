"""gdt_standards.py — GD&T Standards Reference and Tolerance Calculators

ISO 286-1 tolerance bands, GD&T symbol definitions, surface finish grades,
and helper functions for generating engineering drawings and inspection criteria.

All tolerances in millimetres unless stated otherwise.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# =========================================================================
# ISO 286-1 FUNDAMENTAL DEVIATIONS
#
# Subset covering the tolerance bands used in this camera project.
# Keys are (band, nominal_range_max_mm) for lookup.
# Values are (lower_deviation_um, upper_deviation_um) relative to nominal.
# =========================================================================

@dataclass(frozen=True)
class ToleranceBand:
    """ISO tolerance band definition for a diameter range."""
    band: str                   # e.g. "H7", "k6", "p6"
    nom_min: float              # mm — range lower bound (exclusive)
    nom_max: float              # mm — range upper bound (inclusive)
    lower_dev_um: float         # µm — lower deviation from nominal
    upper_dev_um: float         # µm — upper deviation from nominal
    description: str = ""

    @property
    def lower_dev_mm(self) -> float:
        return self.lower_dev_um / 1000.0

    @property
    def upper_dev_mm(self) -> float:
        return self.upper_dev_um / 1000.0


# ISO 286-1 Table excerpts for grades used in the project
# Hole bands (capital letter = hole basis)
_ISO_BANDS: List[ToleranceBand] = [
    # ---- H7 (hole, clearance/transition) ----
    ToleranceBand("H7", 0,  3,   0,  10, "Hole basis, clearance fit"),
    ToleranceBand("H7", 3,  6,   0,  12, "Hole basis, clearance fit"),
    ToleranceBand("H7", 6, 10,   0,  15, "Hole basis, clearance fit"),
    ToleranceBand("H7", 10, 18,  0,  18, "Hole basis, clearance fit"),
    ToleranceBand("H7", 18, 30,  0,  21, "Hole basis, clearance fit"),
    ToleranceBand("H7", 30, 50,  0,  25, "Hole basis, clearance fit"),

    # ---- k6 (shaft, transition fit for bearings) ----
    ToleranceBand("k6", 0,  3,   0,   6, "Shaft transition fit"),
    ToleranceBand("k6", 3,  6,   1,   9, "Shaft transition fit"),
    ToleranceBand("k6", 6, 10,   1,  10, "Shaft transition fit"),
    ToleranceBand("k6", 10, 18,  1,  12, "Shaft transition fit"),
    ToleranceBand("k6", 18, 30,  2,  15, "Shaft transition fit"),

    # ---- p6 (shaft, interference fit for pressed parts) ----
    ToleranceBand("p6", 0,  3,   6,  12, "Shaft interference fit"),
    ToleranceBand("p6", 3,  6,  12,  20, "Shaft interference fit"),
    ToleranceBand("p6", 6, 10,  15,  24, "Shaft interference fit"),
    ToleranceBand("p6", 10, 18, 18,  29, "Shaft interference fit"),

    # ---- h6 (shaft, basic size, for dowels/pins) ----
    ToleranceBand("h6", 0,  3,  -6,   0, "Shaft basic size"),
    ToleranceBand("h6", 3,  6,  -8,   0, "Shaft basic size"),
    ToleranceBand("h6", 6, 10,  -9,   0, "Shaft basic size"),
    ToleranceBand("h6", 10, 18, -11,  0, "Shaft basic size"),

    # ---- H11 (hole, wide clearance for cartridge slot etc.) ----
    ToleranceBand("H11", 0,  3,   0,  60, "Hole wide clearance"),
    ToleranceBand("H11", 3,  6,   0,  75, "Hole wide clearance"),
    ToleranceBand("H11", 6, 10,   0,  90, "Hole wide clearance"),
]


def get_tolerance_band(band: str, nominal_mm: float) -> Optional[ToleranceBand]:
    """Look up the ISO tolerance band for a given nominal diameter."""
    for tb in _ISO_BANDS:
        if tb.band == band and tb.nom_min < nominal_mm <= tb.nom_max:
            return tb
    return None


def get_limits(band: str, nominal_mm: float) -> Dict:
    """Return min/max limits for a given band and nominal dimension.

    Returns dict with:
        nominal, min_mm, max_mm, tolerance_um, lower_dev_um, upper_dev_um
    """
    tb = get_tolerance_band(band, nominal_mm)
    if tb is None:
        return {
            "nominal": nominal_mm,
            "min_mm": nominal_mm,
            "max_mm": nominal_mm,
            "tolerance_um": 0,
            "lower_dev_um": 0,
            "upper_dev_um": 0,
            "note": f"Band {band} not found for {nominal_mm}mm",
        }
    return {
        "nominal": nominal_mm,
        "min_mm": nominal_mm + tb.lower_dev_mm,
        "max_mm": nominal_mm + tb.upper_dev_mm,
        "tolerance_um": tb.upper_dev_um - tb.lower_dev_um,
        "lower_dev_um": tb.lower_dev_um,
        "upper_dev_um": tb.upper_dev_um,
        "description": tb.description,
    }


# Convenience wrappers matching the old API
def h7_limits(nominal_mm: float) -> Dict:
    """Return H7 hole tolerance limits."""
    return get_limits("H7", nominal_mm)

def k6_limits(nominal_mm: float) -> Dict:
    """Return k6 shaft tolerance limits."""
    return get_limits("k6", nominal_mm)

def p6_limits(nominal_mm: float) -> Dict:
    """Return p6 shaft tolerance limits."""
    return get_limits("p6", nominal_mm)

def h6_limits(nominal_mm: float) -> Dict:
    """Return h6 shaft tolerance limits."""
    return get_limits("h6", nominal_mm)


# =========================================================================
# GD&T SYMBOL DEFINITIONS (ASME Y14.5 / ISO 1101)
#
# Symbols and their Unicode/text representations for drawing annotations.
# =========================================================================

@dataclass(frozen=True)
class GDTSymbol:
    """Geometric Dimensioning and Tolerancing symbol."""
    name: str               # Human-readable name
    symbol: str             # Unicode or text representation
    category: str           # "form", "orientation", "location", "runout"
    requires_datum: bool    # True if a datum reference is required
    description: str = ""


GDT_SYMBOLS: Dict[str, GDTSymbol] = {
    # Form tolerances (no datum required)
    "flatness": GDTSymbol(
        "Flatness", "\u23e5", "form", False,
        "Surface must lie between two parallel planes"),
    "straightness": GDTSymbol(
        "Straightness", "\u23e4", "form", False,
        "Line element must lie between two parallel lines"),
    "circularity": GDTSymbol(
        "Circularity", "\u25cb", "form", False,
        "Cross-section must lie between two concentric circles"),
    "cylindricity": GDTSymbol(
        "Cylindricity", "\u232d", "form", False,
        "Surface must lie between two coaxial cylinders"),

    # Orientation tolerances (require datum)
    "parallelism": GDTSymbol(
        "Parallelism", "\u2225", "orientation", True,
        "Surface/axis must lie between two planes parallel to datum"),
    "perpendicularity": GDTSymbol(
        "Perpendicularity", "\u27c2", "orientation", True,
        "Surface/axis must be perpendicular to datum"),
    "angularity": GDTSymbol(
        "Angularity", "\u2220", "orientation", True,
        "Surface/axis at specified angle to datum"),

    # Location tolerances (require datum)
    "position": GDTSymbol(
        "Position", "\u2316", "location", True,
        "Feature center must lie within tolerance zone relative to datum"),
    "concentricity": GDTSymbol(
        "Concentricity", "\u25ce", "location", True,
        "Center points must lie within cylindrical zone about datum axis"),
    "symmetry": GDTSymbol(
        "Symmetry", "\u232f", "location", True,
        "Median points must lie between two planes equidistant from datum"),

    # Runout tolerances (require datum)
    "circular_runout": GDTSymbol(
        "Circular Runout", "\u2197", "runout", True,
        "Surface elements must not vary more than tolerance during rotation"),
    "total_runout": GDTSymbol(
        "Total Runout", "\u2197\u2197", "runout", True,
        "Entire surface must not vary more than tolerance during rotation"),
}


def feature_control_frame(symbol_key: str, tolerance_mm: float,
                          datum_refs: str = "",
                          modifier: str = "") -> str:
    """Build a GD&T feature control frame text string.

    Args:
        symbol_key: Key into GDT_SYMBOLS (e.g. "position", "flatness")
        tolerance_mm: Tolerance value in mm
        datum_refs: Datum reference string (e.g. "A", "A|B", "A|B|C")
        modifier: Material condition modifier ("M"=MMC, "L"=LMC, ""=RFS)

    Returns:
        Formatted string like "⌖ ⌀0.010 A|B"
    """
    sym = GDT_SYMBOLS.get(symbol_key)
    if sym is None:
        return f"[{symbol_key}] {tolerance_mm:.3f}"

    parts = [sym.symbol]

    # Diameter symbol for cylindrical zones
    if symbol_key in ("position", "concentricity", "cylindricity",
                      "circular_runout", "total_runout"):
        parts.append(f"\u2300{tolerance_mm:.3f}")
    else:
        parts.append(f"{tolerance_mm:.3f}")

    if modifier:
        parts[-1] += f" ({modifier})"

    if datum_refs:
        parts.append(datum_refs)

    return " ".join(parts)


# =========================================================================
# SURFACE FINISH STANDARDS (ISO 1302 / ASME B46.1)
#
# Ra values in micrometres (µm).  N-grade mapping per ISO 1302.
# =========================================================================

SURFACE_FINISH_STANDARDS: Dict[str, float] = {
    "N1":  0.025,
    "N2":  0.05,
    "N3":  0.1,
    "N4":  0.2,
    "N5":  0.4,       # Lapping / polishing
    "N6":  0.8,       # Fine grinding / honing
    "N7":  1.6,       # Precision machining
    "N8":  3.2,       # General machining
    "N9":  6.3,       # Rough machining
    "N10": 12.5,      # As-cast / as-forged
}

# Reverse lookup: Ra → N-grade
SURFACE_FINISH_BY_RA: Dict[float, str] = {v: k for k, v in
                                           SURFACE_FINISH_STANDARDS.items()}


def ra_to_ngrade(ra_um: float) -> str:
    """Find the closest N-grade for a given Ra value."""
    best = "N7"
    best_diff = float("inf")
    for grade, val in SURFACE_FINISH_STANDARDS.items():
        diff = abs(val - ra_um)
        if diff < best_diff:
            best_diff = diff
            best = grade
    return best


def surface_finish_callout(ra_um: float, process: str = "") -> str:
    """Format a surface finish callout string.

    Args:
        ra_um: Surface roughness Ra in micrometres
        process: Optional manufacturing process note

    Returns:
        String like "Ra 0.4 µm (N5) — lapped"
    """
    grade = ra_to_ngrade(ra_um)
    text = f"Ra {ra_um} \u00b5m ({grade})"
    if process:
        text += f" \u2014 {process}"
    return text


# =========================================================================
# CAMERA-SPECIFIC GD&T CALLOUTS
#
# Pre-defined feature control frames for critical camera features.
# These are referenced by generate_drawings.py.
# =========================================================================

from super8cam.specs.master_specs import TOL, CAMERA, BEARINGS

# Film gate
GATE_GDT = {
    "aperture_position": feature_control_frame(
        "position", TOL.reg_pin_position, "A"),
    "channel_flatness": feature_control_frame(
        "flatness", 0.005),
    "channel_surface": surface_finish_callout(
        TOL.gate_surface_ra, "lapped / polished"),
    "reg_pin_hole_position": feature_control_frame(
        "position", TOL.reg_pin_position, "A"),
}

# Main shaft bearing seats
SHAFT_GDT = {
    "bearing_seat_cylindricity": feature_control_frame(
        "cylindricity", 0.01),
    "seat_concentricity": feature_control_frame(
        "concentricity", 0.005, "A"),
    "bearing_seat_surface": surface_finish_callout(
        TOL.bearing_seat_ra, "ground"),
}

# Bearing housing bores
HOUSING_GDT = {
    "bore_cylindricity": feature_control_frame(
        "cylindricity", 0.01),
    "bore_perpendicularity": feature_control_frame(
        "perpendicularity", 0.02, "A"),
    "bore_surface": surface_finish_callout(
        TOL.bearing_seat_ra, "reamed"),
}

# Shutter disc
SHUTTER_GDT = {
    "flatness": feature_control_frame(
        "flatness", 0.05),
    "bore_concentricity": feature_control_frame(
        "concentricity", 0.02, "A"),
    "surface": surface_finish_callout(1.6, "machined"),
}

# Cam
CAM_GDT = {
    "profile_position": feature_control_frame(
        "position", 0.02, "A"),
    "bore_concentricity": feature_control_frame(
        "concentricity", 0.01, "A"),
}


# =========================================================================
# TORQUE SPECIFICATIONS
# =========================================================================

TORQUE_SPECS: Dict[str, float] = {
    "M2":    0.2,       # N·m
    "M2.5":  0.4,       # N·m
    "M3":    0.7,       # N·m
    "1/4-20": 0.5,      # N·m (helicoil in aluminium)
}


# =========================================================================
# Convenience: print summary
# =========================================================================

def print_standards_summary():
    """Print a human-readable summary of GD&T standards used."""
    sep = "=" * 60
    print(sep)
    print("  GD&T STANDARDS REFERENCE — SUPER 8 CAMERA")
    print(sep)

    print("\n  ISO TOLERANCE BANDS USED:")
    for band_name in ("H7", "k6", "p6"):
        lim = get_limits(band_name, CAMERA.shaft_dia)
        print(f"    {band_name} @ {CAMERA.shaft_dia}mm: "
              f"{lim['min_mm']:.4f} – {lim['max_mm']:.4f} mm "
              f"(tol {lim['tolerance_um']} µm)")

    print("\n  FILM GATE GD&T:")
    for label, callout in GATE_GDT.items():
        print(f"    {label}: {callout}")

    print("\n  MAIN SHAFT GD&T:")
    for label, callout in SHAFT_GDT.items():
        print(f"    {label}: {callout}")

    print("\n  SURFACE FINISH GRADES:")
    for grade in ("N5", "N6", "N7", "N8"):
        print(f"    {grade}: Ra {SURFACE_FINISH_STANDARDS[grade]} µm")

    print("\n  TORQUE SPECS:")
    for thread, torque in TORQUE_SPECS.items():
        print(f"    {thread}: {torque} N·m")

    print("\n" + sep)


if __name__ == "__main__":
    print_standards_summary()
