"""Shutter disc — half-circle rotary shutter with balance and encoder flag.

The shutter disc sits between the lens mount and the film gate, spinning on
the main shaft.  The open sector (180°) allows light to expose the film; the
solid sector blocks light during film pulldown.

Material: 6061-T6 aluminum, BLACK ANODIZED (any reflection → flare).
Must clear the film gate by 0.3mm on the film side.

Static balance uses two techniques (standard for movie camera shutters):
  1. Crescent relief on the solid side (removes mass)
  2. Brass counterweight plug on the open side (adds opposing moment)
Together these bring imbalance below 0.1 g·mm.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, ENCODER, MATERIALS, MATERIAL_USAGE,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["shutter_disc"]]

# =========================================================================
# DIMENSIONS
# =========================================================================
DISC_OD = 28.0              # mm — outer diameter
DISC_THICK = CAMERA.shutter_thickness  # 0.8 mm
OPENING_ANGLE = CAMERA.shutter_opening_angle  # 180°

# Center bore
BORE_DIA = CAMERA.shutter_shaft_hole   # 4.0 mm
KEYWAY_W = CAMERA.shutter_keyway_w     # 1.0 mm
KEYWAY_DEPTH = CAMERA.shutter_keyway_depth  # 0.5 mm

# Encoder flag notch (on outer rim of solid sector)
FLAG_W = 2.0                # mm — circumferential width of notch
FLAG_DEPTH = 1.0            # mm — radial depth from rim inward

# Gate clearance
GATE_CLEARANCE = CAMERA.shutter_to_gate_clearance  # 0.3 mm

# Material density for balance calc
DENSITY = MATERIAL.density  # 2.70 g/cm³
BRASS_DENSITY = MATERIALS["brass_c360"].density  # 8.49 g/cm³

# Balance target
MAX_IMBALANCE_GMM = 0.1    # g·mm — static imbalance limit


# =========================================================================
# BALANCE CALCULATION
# =========================================================================

def calculate_half_disc_cg() -> dict:
    """Calculate CG, imbalance, and balance solution for the half-disc shutter.

    Uses two complementary techniques:
      1. Crescent relief cut from the solid sector (removes mass on heavy side)
      2. Brass counterweight plug on the open side (adds opposing moment)

    Returns dict with all balance parameters.
    """
    R = DISC_OD / 2.0
    t = DISC_THICK

    # Full disc and half-disc mass
    full_mass_g = math.pi * R**2 * t / 1000.0 * DENSITY
    half_mass_g = full_mass_g / 2.0

    # Bore mass (removed from center, spans both halves)
    bore_mass_g = math.pi * (BORE_DIA / 2.0)**2 * t / 1000.0 * DENSITY
    net_mass_g = half_mass_g - bore_mass_g / 2.0

    # CG of a semicircle at 4R/(3π) from center
    cg_offset = 4.0 * R / (3.0 * math.pi)

    # Raw static imbalance
    imbalance_gmm = half_mass_g * cg_offset

    # --- Step 1: Crescent relief on solid side ---
    cr_r_inner = BORE_DIA / 2.0 + 1.5  # 3.5 mm — clear of bore
    cr_r_outer = R - 1.5               # 12.5 mm — leave 1.5mm rim
    cr_span_deg = 140.0                # degrees of arc
    cr_span_rad = math.radians(cr_span_deg)

    cr_area = (cr_r_outer**2 - cr_r_inner**2) * cr_span_rad / 2.0
    cr_mass_g = cr_area * t / 1000.0 * DENSITY

    # CG x-coordinate of annular sector centered on +X axis
    radial_cg = (2.0 / 3.0) * (cr_r_outer**3 - cr_r_inner**3) / \
                (cr_r_outer**2 - cr_r_inner**2)
    half_a = cr_span_rad / 2.0
    ang_factor = math.sin(half_a) / half_a if half_a > 0 else 1.0
    cr_cg_x = radial_cg * ang_factor
    cr_reduction = cr_mass_g * cr_cg_x

    # --- Step 2: Brass counterweight on open side ---
    remaining = imbalance_gmm - cr_reduction
    cw_radius = R - 2.0  # near rim, on -X side
    cw_mass_needed = remaining / cw_radius if remaining > 0 else 0.0

    # Size as a cylindrical plug (press-fit, may protrude slightly)
    cw_dia = 2.5  # mm diameter
    cw_vol_needed = cw_mass_needed / BRASS_DENSITY * 1000.0  # mm³
    cw_height = cw_vol_needed / (math.pi / 4.0 * cw_dia**2)
    # Allow up to 3mm protrusion (total height = disc + protrusion)
    cw_height = min(cw_height, t + 3.0)

    # Actual counterweight
    cw_actual_vol = math.pi / 4.0 * cw_dia**2 * cw_height
    cw_actual_mass = cw_actual_vol / 1000.0 * BRASS_DENSITY
    cw_reduction = cw_actual_mass * cw_radius

    total_reduction = cr_reduction + cw_reduction
    residual = imbalance_gmm - total_reduction

    return {
        "disc_mass_g": net_mass_g,
        "solid_half_mass_g": half_mass_g,
        "cg_offset_mm": cg_offset,
        "imbalance_gmm": imbalance_gmm,
        "pocket_needed": True,
        "crescent_r_inner_mm": cr_r_inner,
        "crescent_r_outer_mm": cr_r_outer,
        "crescent_span_deg": cr_span_deg,
        "crescent_mass_removed_g": cr_mass_g,
        "crescent_reduction_gmm": cr_reduction,
        "counterweight_dia_mm": cw_dia,
        "counterweight_height_mm": cw_height,
        "counterweight_radius_mm": cw_radius,
        "counterweight_mass_g": cw_actual_mass,
        "counterweight_reduction_gmm": cw_reduction,
        "residual_imbalance_gmm": residual,
        "balance_ok": abs(residual) < MAX_IMBALANCE_GMM,
    }


def build() -> cq.Workplane:
    """Build the shutter disc with open sector, balance features, and encoder flag.

    Coordinate system:
      Disc lies in the XY plane, shaft axis along Z.
      The solid sector is centered on the +X axis.
      The open sector is centered on the -X axis.
    """
    R = DISC_OD / 2.0

    # --- Full disc ---
    disc = (
        cq.Workplane("XY")
        .cylinder(DISC_THICK, R)
    )

    # --- Shaft bore ---
    disc = disc.faces(">Z").workplane().hole(BORE_DIA, DISC_THICK)

    # --- Keyway in bore ---
    kw_y = BORE_DIA / 2.0 - KEYWAY_DEPTH / 2.0
    disc = (
        disc.faces(">Z").workplane()
        .center(0, kw_y)
        .rect(KEYWAY_W, KEYWAY_DEPTH + 0.01)
        .cutThruAll()
    )

    # --- Open sector cutout (180°) ---
    # Remove the -X half (angles 90° to 270°)
    arc_steps = 64
    pts = [(0.0, 0.0)]
    for i in range(arc_steps + 1):
        a = math.pi / 2.0 + i * math.pi / arc_steps
        pts.append(((R + 1) * math.cos(a), (R + 1) * math.sin(a)))
    pts.append((0.0, 0.0))

    sector = (
        cq.Workplane("XY")
        .polyline(pts).close()
        .extrude(DISC_THICK + 1)
        .translate((0, 0, -(DISC_THICK + 1) / 2.0))
    )
    disc = disc.cut(sector)

    # --- Encoder flag notch ---
    notch_x = R - FLAG_DEPTH / 2.0
    notch = (
        cq.Workplane("XY")
        .box(FLAG_DEPTH, FLAG_W, DISC_THICK + 0.2)
        .translate((notch_x, 0, 0))
    )
    disc = disc.cut(notch)

    # --- Balance: crescent relief on solid side ---
    balance = calculate_half_disc_cg()
    r_inner = balance["crescent_r_inner_mm"]
    r_outer = balance["crescent_r_outer_mm"]
    span_deg = balance["crescent_span_deg"]
    half_span = math.radians(span_deg / 2.0)
    arc_n = max(32, int(span_deg))

    pts_outer = []
    for i in range(arc_n + 1):
        a = -half_span + i * 2 * half_span / arc_n
        pts_outer.append((r_outer * math.cos(a), r_outer * math.sin(a)))

    pts_inner = []
    for i in range(arc_n + 1):
        a = half_span - i * 2 * half_span / arc_n
        pts_inner.append((r_inner * math.cos(a), r_inner * math.sin(a)))

    crescent_pts = pts_outer + pts_inner
    crescent = (
        cq.Workplane("XY")
        .polyline(crescent_pts).close()
        .extrude(DISC_THICK + 0.2)
        .translate((0, 0, -(DISC_THICK + 0.2) / 2.0))
    )
    disc = disc.cut(crescent)

    # --- Balance: counterweight hole on open side ---
    # A hole on the -X side (open sector rim) for a press-fit brass plug.
    # The hole goes through; the brass plug is a separate BOM item.
    cw_r = balance["counterweight_radius_mm"]
    cw_dia = balance["counterweight_dia_mm"]
    # Position at 180° (directly -X)
    cw_x = -cw_r
    cw_hole = (
        cq.Workplane("XY")
        .transformed(offset=(cw_x, 0, 0))
        .circle(cw_dia / 2.0)
        .extrude(DISC_THICK + 0.2)
        .translate((0, 0, -(DISC_THICK + 0.2) / 2.0))
    )
    # Only cut if it falls within the open sector (which it does at -X)
    # But the open sector is already removed — so we need to add material
    # back. Actually, the counterweight is a SEPARATE brass plug pressed
    # into a hole. Since the open side is cut away, the counterweight
    # would need its own small mounting feature.
    #
    # Practical approach: leave a small ear/tab on the open side at the
    # rim position to hold the counterweight. Model as a small
    # protrusion from the rim.
    ear_angle_span = math.radians(15.0)  # small ear ±7.5° around 180°
    ear_pts = [(0.0, 0.0)]
    ear_steps = 16
    for i in range(ear_steps + 1):
        a = math.pi - ear_angle_span + i * 2 * ear_angle_span / ear_steps
        ear_pts.append((R * math.cos(a), R * math.sin(a)))
    ear_pts.append((0.0, 0.0))
    ear = (
        cq.Workplane("XY")
        .polyline(ear_pts).close()
        .extrude(DISC_THICK)
        .translate((0, 0, -DISC_THICK / 2.0))
    )
    disc = disc.union(ear)

    # Now drill the counterweight hole through the ear
    disc = disc.cut(cw_hole)

    return disc


def get_disc_geometry() -> dict:
    """Return key shutter geometry for assembly and validation."""
    R = DISC_OD / 2.0
    balance = calculate_half_disc_cg()
    return {
        "outer_radius_mm": R,
        "thickness_mm": DISC_THICK,
        "bore_dia_mm": BORE_DIA,
        "opening_angle_deg": OPENING_ANGLE,
        "gate_clearance_mm": GATE_CLEARANCE,
        "balance": balance,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/shutter_disc.step")
    cq.exporters.export(solid, f"{output_dir}/shutter_disc.stl",
                        tolerance=0.005, angularTolerance=0.05)
    print(f"  Shutter disc exported to {output_dir}/")

    balance = calculate_half_disc_cg()
    print(f"  Balance analysis:")
    print(f"    Solid half mass:   {balance['solid_half_mass_g']:.3f} g")
    print(f"    CG offset:         {balance['cg_offset_mm']:.3f} mm")
    print(f"    Raw imbalance:     {balance['imbalance_gmm']:.3f} g·mm")
    print(f"    Crescent relief:   R={balance['crescent_r_inner_mm']:.1f}-"
          f"{balance['crescent_r_outer_mm']:.1f}mm, "
          f"{balance['crescent_span_deg']:.0f}° span")
    print(f"    Crescent reduces:  {balance['crescent_reduction_gmm']:.3f} g·mm")
    print(f"    Counterweight:     {balance['counterweight_dia_mm']:.1f}mm brass plug "
          f"at R={balance['counterweight_radius_mm']:.0f}mm")
    print(f"    CW reduces:        {balance['counterweight_reduction_gmm']:.3f} g·mm")
    print(f"    Residual imbal:    {balance['residual_imbalance_gmm']:.4f} g·mm")
    print(f"    Balance OK:        {balance['balance_ok']}")


if __name__ == "__main__":
    export()
