"""Main shaft — stepped hardened steel shaft carrying shutter, cam, and gear.

The main shaft is the mechanical backbone of the camera.  It receives power
from the gearbox at one end, carries the pulldown cam and secondary eccentric
in the middle, and drives the shutter disc near the front.  An encoder disc
at the far end provides position feedback.

Material: AISI 4140 chrome-moly steel, through-hardened HRC 28-32.
Bearing seats ground to h6 tolerance.

All dimensions from master_specs.

Shaft layout (Z axis, rear=−Z to front=+Z):
  Section 1:  Gear end       3mm dia × 8mm   (keyway for driven gear)
  Shoulder:   3mm → 4mm      0.3mm × 45° chamfer
  Section 2:  Bearing seat 1 4mm dia × 4mm   (694ZZ press-fit, h6)
  Section 3:  Cam section    4mm dia × 6mm   (pulldown cam + eccentric, keyed)
  Section 4:  Bearing seat 2 4mm dia × 4mm   (694ZZ press-fit, h6)
  Section 5:  Shutter seat   4mm dia × 3mm   (shutter disc, keyed)
  Shoulder:   4mm → 3mm      0.3mm × 45° chamfer
  Section 6:  Encoder end    3mm dia × 4mm   (encoder disc, M3 thread at tip)
  Total:      8+4+6+4+3+4 = 29mm usable + shoulders ≈ 30mm
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    CAMERA, MATERIALS, MATERIAL_USAGE, BEARINGS, SHAFT_DIMS,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["main_shaft"]]

# =========================================================================
# SHAFT SECTION DIMENSIONS
# =========================================================================

# Section 1: Gear end (rear)
SEC1_DIA = SHAFT_DIMS.sec1_dia          # 3.0 mm
SEC1_LEN = SHAFT_DIMS.sec1_len          # 8.0 mm
SEC1_KEYWAY_W = SHAFT_DIMS.sec1_keyway_w     # 0.6 mm
SEC1_KEYWAY_DEPTH = SHAFT_DIMS.sec1_keyway_depth  # 0.3 mm

# Section 2: Bearing seat 1
SEC2_DIA = CAMERA.shaft_dia             # 4.0 mm (already uses CAMERA)
SEC2_LEN = BEARINGS["main_shaft"].width  # 4.0 mm (already uses BEARINGS)

# Section 3: Cam section
SEC3_DIA = CAMERA.shaft_dia
SEC3_LEN = SHAFT_DIMS.sec3_len          # 6.0 mm
SEC3_KEYWAY_W = SHAFT_DIMS.sec3_keyway_w     # 1.0 mm
SEC3_KEYWAY_DEPTH = SHAFT_DIMS.sec3_keyway_depth  # 0.5 mm

# Section 4: Bearing seat 2
SEC4_DIA = CAMERA.shaft_dia
SEC4_LEN = BEARINGS["main_shaft"].width

# Section 5: Shutter section
SEC5_DIA = CAMERA.shaft_dia
SEC5_LEN = SHAFT_DIMS.sec5_len          # 3.0 mm
SEC5_KEYWAY_W = CAMERA.shutter_keyway_w      # 1.0 mm (already uses CAMERA)
SEC5_KEYWAY_DEPTH = CAMERA.shutter_keyway_depth  # 0.5 mm (already uses CAMERA)

# Section 6: Encoder end (front)
SEC6_DIA = SHAFT_DIMS.sec6_dia          # 3.0 mm
SEC6_LEN = SHAFT_DIMS.sec6_len          # 4.0 mm
SEC6_THREAD_DIA = SHAFT_DIMS.sec6_thread_dia  # 3.0 mm
SEC6_THREAD_LEN = SHAFT_DIMS.sec6_thread_len  # 3.0 mm

# Transitions
CHAMFER = SHAFT_DIMS.chamfer            # 0.3 mm

# Total length
SHAFT_LENGTH = SEC1_LEN + SEC2_LEN + SEC3_LEN + SEC4_LEN + SEC5_LEN + SEC6_LEN

# Section Z positions (start of each section, rear = Z=0)
SEC1_Z0 = 0.0
SEC2_Z0 = SEC1_LEN
SEC3_Z0 = SEC2_Z0 + SEC2_LEN
SEC4_Z0 = SEC3_Z0 + SEC3_LEN
SEC5_Z0 = SEC4_Z0 + SEC4_LEN
SEC6_Z0 = SEC5_Z0 + SEC5_LEN


def build() -> cq.Workplane:
    """Build the complete stepped main shaft.

    The shaft is oriented along the Z axis with the rear (gear) end
    at Z=0 and the front (encoder) end at Z=SHAFT_LENGTH.
    Origin is at the rear end, on the shaft centerline.
    """
    # Build via revolution of a stepped profile.
    # We construct the half-profile as a series of lines, then revolve.
    # CadQuery approach: stack cylinders and union them.

    # Start with the full-length 4mm cylinder (sections 2-5)
    main_len = SEC2_LEN + SEC3_LEN + SEC4_LEN + SEC5_LEN
    shaft = (
        cq.Workplane("XY")
        .center(0, 0)
        .circle(SEC2_DIA / 2.0)
        .extrude(main_len)
        .translate((0, 0, SEC2_Z0))
    )

    # Section 1: 3mm diameter gear end
    sec1 = (
        cq.Workplane("XY")
        .circle(SEC1_DIA / 2.0)
        .extrude(SEC1_LEN)
        .translate((0, 0, SEC1_Z0))
    )
    shaft = shaft.union(sec1)

    # Section 6: 3mm diameter encoder end
    sec6 = (
        cq.Workplane("XY")
        .circle(SEC6_DIA / 2.0)
        .extrude(SEC6_LEN)
        .translate((0, 0, SEC6_Z0))
    )
    shaft = shaft.union(sec6)

    # --- Chamfers at diameter transitions ---
    # Transition 1→2 (3mm→4mm) at Z = SEC2_Z0
    # Chamfer the shoulder edge on the 4mm section
    # We cut a small cone to create the 0.3mm×45° chamfer
    chamfer_cone_1 = (
        cq.Workplane("XY")
        .circle(SEC2_DIA / 2.0)
        .circle(SEC1_DIA / 2.0)
        .extrude(-CHAMFER)
        .translate((0, 0, SEC2_Z0))
    )
    # Actually, use CadQuery chamfer on edges. Let's select shoulder edges.
    # It's easier to chamfer via a small taper cut.
    taper1 = (
        cq.Workplane("XY")
        .circle(SEC2_DIA / 2.0 + 0.01)
        .circle(SEC1_DIA / 2.0)
        .extrude(CHAMFER)
        .translate((0, 0, SEC2_Z0 - CHAMFER))
    )
    shaft = shaft.cut(taper1)

    # Transition 5→6 (4mm→3mm) at Z = SEC6_Z0
    taper2 = (
        cq.Workplane("XY")
        .circle(SEC5_DIA / 2.0 + 0.01)
        .circle(SEC6_DIA / 2.0)
        .extrude(CHAMFER)
        .translate((0, 0, SEC6_Z0))
    )
    shaft = shaft.cut(taper2)

    # --- Keyway: Section 1 (gear end) ---
    # A slot along the top of section 1
    kw1 = (
        cq.Workplane("XY")
        .box(SEC1_KEYWAY_W, SEC1_DIA, SEC1_LEN)
        .translate((0, SEC1_DIA / 2.0 - SEC1_KEYWAY_DEPTH, SEC1_Z0 + SEC1_LEN / 2.0))
    )
    shaft = shaft.cut(kw1)

    # --- Keyway: Section 3 (cam section) ---
    kw3 = (
        cq.Workplane("XY")
        .box(SEC3_KEYWAY_W, SEC3_DIA, SEC3_LEN)
        .translate((0, SEC3_DIA / 2.0 - SEC3_KEYWAY_DEPTH, SEC3_Z0 + SEC3_LEN / 2.0))
    )
    shaft = shaft.cut(kw3)

    # --- Keyway: Section 5 (shutter section) ---
    kw5 = (
        cq.Workplane("XY")
        .box(SEC5_KEYWAY_W, SEC5_DIA, SEC5_LEN)
        .translate((0, SEC5_DIA / 2.0 - SEC5_KEYWAY_DEPTH, SEC5_Z0 + SEC5_LEN / 2.0))
    )
    shaft = shaft.cut(kw5)

    # --- M3 thread at tip of section 6 ---
    # Model as a reduced-diameter cylinder (thread minor diameter ~2.46mm)
    thread_minor = 2.46  # mm — M3 minor dia
    thread_start_z = SEC6_Z0 + SEC6_LEN - SEC6_THREAD_LEN
    # Cut the thread relief (reduce OD to thread minor)
    thread_relief = (
        cq.Workplane("XY")
        .circle(SEC6_DIA / 2.0 + 0.01)
        .circle(thread_minor / 2.0)
        .extrude(SEC6_THREAD_LEN)
        .translate((0, 0, thread_start_z))
    )
    shaft = shaft.cut(thread_relief)

    # End chamfer on encoder tip
    tip_chamfer = (
        cq.Workplane("XY")
        .circle(thread_minor / 2.0 + 0.01)
        .circle(thread_minor / 2.0 - CHAMFER)
        .extrude(CHAMFER)
        .translate((0, 0, SEC6_Z0 + SEC6_LEN - CHAMFER))
    )
    shaft = shaft.cut(tip_chamfer)

    return shaft


def get_section_positions() -> dict:
    """Return Z positions and diameters for each shaft section.

    Used by assembly modules to position components on the shaft.
    All Z values are from the rear (gear) end of the shaft.
    """
    return {
        "gear_end":     {"z0": SEC1_Z0, "z1": SEC1_Z0 + SEC1_LEN, "dia": SEC1_DIA},
        "bearing_1":    {"z0": SEC2_Z0, "z1": SEC2_Z0 + SEC2_LEN, "dia": SEC2_DIA},
        "cam_section":  {"z0": SEC3_Z0, "z1": SEC3_Z0 + SEC3_LEN, "dia": SEC3_DIA},
        "bearing_2":    {"z0": SEC4_Z0, "z1": SEC4_Z0 + SEC4_LEN, "dia": SEC4_DIA},
        "shutter":      {"z0": SEC5_Z0, "z1": SEC5_Z0 + SEC5_LEN, "dia": SEC5_DIA},
        "encoder_end":  {"z0": SEC6_Z0, "z1": SEC6_Z0 + SEC6_LEN, "dia": SEC6_DIA},
        "total_length": SHAFT_LENGTH,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/main_shaft.step")
    cq.exporters.export(solid, f"{output_dir}/main_shaft.stl",
                        tolerance=0.005, angularTolerance=0.05)
    secs = get_section_positions()
    print(f"  Main shaft exported ({secs['total_length']:.0f}mm total)")
    for name, s in secs.items():
        if isinstance(s, dict):
            print(f"    {name:15s} Z={s['z0']:.0f}-{s['z1']:.0f}mm, dia={s['dia']:.0f}mm")


if __name__ == "__main__":
    export()
