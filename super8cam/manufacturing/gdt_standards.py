"""gdt_standards.py — GD&T symbols, tolerance bands, surface finish specs.

Provides drawing annotation helpers for engineering drawings:
  - ISO 286-1 fundamental deviations (H7, k6, p6)
  - GD&T feature control frame definitions
  - Surface finish callout standards (ISO 1302)
  - Part-specific GD&T requirements for critical features
"""

from dataclasses import dataclass
from typing import Optional

from super8cam.specs.master_specs import TOL, CAMERA, FILM


# =========================================================================
# ISO 286-1 FUNDAMENTAL DEVIATIONS
# =========================================================================

ISO_TOLERANCE_BANDS = {
    "H7": {"description": "Hole basis clearance/transition", "grade": 7},
    "k6": {"description": "Shaft basis transition fit", "grade": 6},
    "p6": {"description": "Shaft basis interference fit", "grade": 6},
}


def h7_limits(nominal_mm: float) -> dict:
    """Return H7 hole tolerance limits for a given nominal diameter."""
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


def p6_limits(nominal_mm: float) -> dict:
    """Return p6 shaft tolerance limits (interference fit)."""
    if nominal_mm <= 3:
        dev_low, dev_high = 6, 12
    elif nominal_mm <= 6:
        dev_low, dev_high = 12, 20
    elif nominal_mm <= 10:
        dev_low, dev_high = 15, 24
    else:
        dev_low, dev_high = 18, 29
    return {
        "nominal": nominal_mm,
        "min_mm": nominal_mm + dev_low / 1000,
        "max_mm": nominal_mm + dev_high / 1000,
    }


# =========================================================================
# SURFACE FINISH (ISO 1302 / ASME Y14.36)
# =========================================================================

SURFACE_FINISH_STANDARDS = {
    "N1": 0.025, "N2": 0.05, "N3": 0.1, "N4": 0.2,
    "N5": 0.4, "N6": 0.8, "N7": 1.6, "N8": 3.2,
    "N9": 6.3, "N10": 12.5,
}

FINISH_BY_APPLICATION = {
    "film_contact":     ("N5", 0.4),    # mirror polish
    "bearing_seat":     ("N6", 0.8),
    "general_machined": ("N7", 1.6),
    "body_exterior":    ("N6", 0.8),    # anodize-ready
    "gear_tooth":       ("N7", 1.6),
    "mating_face":      ("N6", 0.8),
}


# =========================================================================
# GD&T FEATURE CONTROL FRAMES
# =========================================================================

# Unicode GD&T symbols (ISO 1101 / ASME Y14.5)
GDT_SYMBOLS = {
    "position":       "\u2316",   # position (crosshair)
    "flatness":       "\u23E5",   # flatness
    "cylindricity":   "\u232D",   # cylindricity
    "concentricity":  "\u25CE",   # concentricity
    "perpendicularity": "\u27C2", # perpendicularity
    "parallelism":    "\u2225",   # parallelism
    "runout":         "\u2197",   # circular runout
    "total_runout":   "\u21D7",   # total runout
    "circularity":    "\u25CB",   # circularity
    "straightness":   "\u2014",   # straightness
    "profile_line":   "\u2312",   # profile of a line
    "profile_surface":"\u2313",   # profile of a surface
}

# ASCII fallback symbols for matplotlib (when Unicode not available)
GDT_SYMBOLS_ASCII = {
    "position":       "(+)",
    "flatness":       "/_/",
    "cylindricity":   "//O//",
    "concentricity":  "(O)",
    "perpendicularity": "_|_",
    "parallelism":    "//",
    "runout":         "^",
    "total_runout":   "^^",
    "circularity":    "O",
    "straightness":   "---",
    "profile_line":   "D",
    "profile_surface":"DD",
}


@dataclass(frozen=True)
class FeatureControlFrame:
    """A single GD&T feature control frame callout."""
    symbol: str             # key into GDT_SYMBOLS
    tolerance_mm: float     # tolerance zone diameter/width
    datum_a: Optional[str] = None
    datum_b: Optional[str] = None
    datum_c: Optional[str] = None
    modifier: Optional[str] = None  # "M" for MMC, "L" for LMC
    note: str = ""

    def to_text(self, use_ascii: bool = True) -> str:
        """Format as text string for drawing annotation."""
        syms = GDT_SYMBOLS_ASCII if use_ascii else GDT_SYMBOLS
        sym = syms.get(self.symbol, self.symbol)
        parts = [f"|{sym}|{self.tolerance_mm:.3f}"]
        if self.modifier:
            parts[-1] += f" {self.modifier}"
        for d in [self.datum_a, self.datum_b, self.datum_c]:
            if d:
                parts.append(d)
        return "|".join(parts) + "|"


# =========================================================================
# PART-SPECIFIC GD&T REQUIREMENTS
# =========================================================================

FILM_GATE_GDT = {
    "aperture_position": FeatureControlFrame(
        symbol="position",
        tolerance_mm=0.01,
        datum_a="A",
        note="Aperture center position relative to datum A (mounting holes)",
    ),
    "channel_flatness": FeatureControlFrame(
        symbol="flatness",
        tolerance_mm=0.005,
        note="Film channel contact surface flatness",
    ),
    "reg_pin_hole_position": FeatureControlFrame(
        symbol="position",
        tolerance_mm=TOL.reg_pin_position,
        datum_a="A",
        datum_b="B",
        note="Registration pin hole true position",
    ),
    "channel_perpendicularity": FeatureControlFrame(
        symbol="perpendicularity",
        tolerance_mm=0.01,
        datum_a="A",
        note="Channel walls perpendicular to contact face",
    ),
}

MAIN_SHAFT_GDT = {
    "bearing_seat_cylindricity": FeatureControlFrame(
        symbol="cylindricity",
        tolerance_mm=0.01,
        note="Bearing journal cylindricity",
    ),
    "bearing_seat_concentricity": FeatureControlFrame(
        symbol="concentricity",
        tolerance_mm=0.005,
        datum_a="A",
        datum_b="B",
        note="Front and rear bearing seats concentric to each other",
    ),
    "keyway_position": FeatureControlFrame(
        symbol="position",
        tolerance_mm=0.02,
        datum_a="A",
        note="Shutter keyway angular position relative to cam lobe",
    ),
}

GEARBOX_HOUSING_GDT = {
    "bore_cylindricity": FeatureControlFrame(
        symbol="cylindricity",
        tolerance_mm=0.01,
        note="Bearing bore cylindricity",
    ),
    "bore_concentricity": FeatureControlFrame(
        symbol="concentricity",
        tolerance_mm=0.01,
        datum_a="A",
        note="All bearing bores concentric to primary axis",
    ),
    "face_parallelism": FeatureControlFrame(
        symbol="parallelism",
        tolerance_mm=0.02,
        datum_a="A",
        note="Housing halves mating faces parallel",
    ),
}

SHUTTER_DISC_GDT = {
    "flatness": FeatureControlFrame(
        symbol="flatness",
        tolerance_mm=0.05,
        note="Disc must be flat to clear film gate",
    ),
    "bore_concentricity": FeatureControlFrame(
        symbol="concentricity",
        tolerance_mm=0.02,
        datum_a="A",
        note="Shaft bore concentric to disc OD",
    ),
    "runout": FeatureControlFrame(
        symbol="runout",
        tolerance_mm=0.03,
        datum_a="A",
        note="Disc face runout relative to shaft axis",
    ),
}

BODY_SHELL_GDT = {
    "mating_face_flatness": FeatureControlFrame(
        symbol="flatness",
        tolerance_mm=0.05,
        note="Body half mating face flatness for light-tight seal",
    ),
    "lens_boss_position": FeatureControlFrame(
        symbol="position",
        tolerance_mm=0.05,
        datum_a="A",
        datum_b="B",
        note="Lens mount boss position relative to film gate datums",
    ),
    "lens_boss_perpendicularity": FeatureControlFrame(
        symbol="perpendicularity",
        tolerance_mm=0.03,
        datum_a="A",
        note="Lens boss axis perpendicular to film plane",
    ),
}

# Collected by part name for easy lookup
PART_GDT = {
    "film_gate":        FILM_GATE_GDT,
    "main_shaft":       MAIN_SHAFT_GDT,
    "gearbox_housing":  GEARBOX_HOUSING_GDT,
    "shutter_disc":     SHUTTER_DISC_GDT,
    "body_left":        BODY_SHELL_GDT,
    "body_right":       BODY_SHELL_GDT,
}


def get_gdt_callouts(part_name: str) -> dict:
    """Return GD&T feature control frames for a given part."""
    return PART_GDT.get(part_name, {})


def get_surface_finish(application: str) -> tuple:
    """Return (ISO_grade, Ra_um) for a given application."""
    return FINISH_BY_APPLICATION.get(application, ("N7", 1.6))
