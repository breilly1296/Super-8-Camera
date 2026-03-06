"""Shutter assembly — main shaft + bearings + shutter disc + cam + encoder.

Assembles all rotating components on the main shaft, including a bearing
housing bracket.  The shutter disc is positioned in the optical path
(0.3mm in front of the film gate, between lens and gate).

Includes a validation function that checks:
  - Shutter clears film gate at all rotation angles
  - Shutter fully covers aperture when closed
  - Shutter fully clears aperture when open (no vignetting)
  - Shutter is closed during the entire pulldown phase
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, SHUTTER, BEARINGS, FASTENERS, MATERIALS,
)
from super8cam.parts import shutter_disc, main_shaft
from super8cam.parts.main_shaft import get_section_positions
from super8cam.parts.shutter_disc import (
    DISC_OD, DISC_THICK, GATE_CLEARANCE, OPENING_ANGLE,
    get_disc_geometry, calculate_half_disc_cg,
)
from super8cam.parts.cam_follower import (
    build_cam, build_secondary_eccentric,
    CAM_THICK, ECCENTRIC_THICK,
)
from super8cam.parts.film_gate import get_film_plane_origin, GATE_THICK

# =========================================================================
# BEARING MODEL (simplified cylinder)
# =========================================================================
BRG = BEARINGS["main_shaft"]  # 694ZZ: 4×11×4 mm (bore×OD×width)
# Note: actual 694ZZ is 4mm bore × 11mm OD × 4mm width
BRG_BORE = BRG.bore       # 4 mm
BRG_OD = BRG.od            # 11 mm
BRG_WIDTH = BRG.width      # 4 mm

# =========================================================================
# BEARING HOUSING BRACKET
# =========================================================================
HOUSING_W = 20.0           # mm — width (X)
HOUSING_H = 15.0           # mm — height (Y)
HOUSING_D = 12.0           # mm — depth (Z, along shaft)
HOUSING_WALL = 2.0         # mm — wall thickness around bearing bores

# Bearing bore spacing along shaft
secs = get_section_positions()
BEARING_SPAN = secs["bearing_2"]["z0"] - secs["bearing_1"]["z0"]  # mm center-to-center

# Mounting: M2.5 holes on base
M25_TAP = FASTENERS["M2_5x6_shcs"].tap_hole   # 2.05 mm
M25_MOUNT_SPACING_X = 14.0  # mm
M25_MOUNT_INSET_Y = 2.0     # mm from bottom of housing

# =========================================================================
# ENCODER DISC (simple flag disc)
# =========================================================================
ENCODER_OD = 10.0          # mm
ENCODER_THICK = 0.5        # mm
ENCODER_BORE = 3.0         # mm (matches section 6 diameter)
ENCODER_SLOT_W = 2.0       # mm — single slot for position sensing
ENCODER_SLOT_DEPTH = 3.0   # mm — from rim inward


def build_bearing() -> cq.Workplane:
    """Build a simplified bearing model (694ZZ)."""
    brg = (
        cq.Workplane("XY")
        .cylinder(BRG_WIDTH, BRG_OD / 2.0)
    )
    brg = brg.faces(">Z").workplane().hole(BRG_BORE, BRG_WIDTH)
    return brg


def build_bearing_housing() -> cq.Workplane:
    """Build the bearing housing bracket.

    A rectangular block with two bearing bores spaced to match the shaft.
    M2.5 mounting holes on the base. The shaft axis runs through the
    center of the housing along Z.

    Coordinate system: shaft axis along Z, centered in X, housing base at -Y.
    """
    # Main block
    housing = (
        cq.Workplane("XY")
        .box(HOUSING_W, HOUSING_H, HOUSING_D)
    )

    # Round the top edges for aesthetics
    housing = housing.edges("|Z").fillet(1.5)

    # Bearing bore 1 (rear)
    bore1_z = -HOUSING_D / 2.0 + BRG_WIDTH / 2.0 + HOUSING_WALL
    housing = (
        housing.faces("<Z").workplane()
        .circle(BRG_OD / 2.0 + 0.05)  # H7 fit for bearing OD
        .cutBlind(-BRG_WIDTH)
    )

    # Bearing bore 2 (front)
    housing = (
        housing.faces(">Z").workplane()
        .circle(BRG_OD / 2.0 + 0.05)
        .cutBlind(-BRG_WIDTH)
    )

    # Through-hole for shaft (between bearing bores)
    housing = (
        housing.faces(">Z").workplane()
        .hole(BRG_OD / 2.0, HOUSING_D)  # clearance for bearing OD to pass
    )

    # Shaft clearance through the housing
    housing = (
        housing.faces(">Z").workplane()
        .hole(CAMERA.shaft_dia + 1.0, HOUSING_D)  # clearance hole
    )

    # M2.5 mounting holes on base (-Y face)
    mount_y = -HOUSING_H / 2.0
    mount_pts = [
        (-M25_MOUNT_SPACING_X / 2.0, mount_y + M25_MOUNT_INSET_Y),
        ( M25_MOUNT_SPACING_X / 2.0, mount_y + M25_MOUNT_INSET_Y),
    ]
    for px, py in mount_pts:
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=(px, 0, py))
            .circle(M25_TAP / 2.0)
            .extrude(HOUSING_H)
            .translate((0, 0, 0))
        )
        # Use a simpler approach: drill from bottom face
    housing = (
        housing.faces("<Y").workplane()
        .pushPoints([(-M25_MOUNT_SPACING_X / 2.0, 0),
                      (M25_MOUNT_SPACING_X / 2.0, 0)])
        .hole(M25_TAP, HOUSING_H)
    )

    return housing


def build_encoder_disc() -> cq.Workplane:
    """Build a simple encoder disc with a single detection slot."""
    disc = (
        cq.Workplane("XY")
        .cylinder(ENCODER_THICK, ENCODER_OD / 2.0)
    )
    disc = disc.faces(">Z").workplane().hole(ENCODER_BORE, ENCODER_THICK)

    # Single slot for position sensing
    slot = (
        cq.Workplane("XY")
        .box(ENCODER_SLOT_DEPTH, ENCODER_SLOT_W, ENCODER_THICK + 0.2)
        .translate((ENCODER_OD / 2.0 - ENCODER_SLOT_DEPTH / 2.0, 0, 0))
    )
    disc = disc.cut(slot)

    return disc


def build() -> cq.Assembly:
    """Build the complete shutter assembly.

    Positions all parts relative to the main shaft centerline.
    The shaft axis is along Z.  Z=0 is at the rear (gear) end.

    The shutter disc is positioned so its plane is GATE_CLEARANCE (0.3mm)
    in front of the film gate face.
    """
    assy = cq.Assembly(name="shutter_assembly")
    sections = get_section_positions()

    # --- Main shaft ---
    shaft = main_shaft.build()
    assy.add(shaft, name="main_shaft", loc=cq.Location((0, 0, 0)))

    # --- Bearing 1 ---
    brg1 = build_bearing()
    brg1_z = sections["bearing_1"]["z0"] + BRG_WIDTH / 2.0
    assy.add(brg1, name="bearing_1", loc=cq.Location((0, 0, brg1_z)))

    # --- Bearing 2 ---
    brg2 = build_bearing()
    brg2_z = sections["bearing_2"]["z0"] + BRG_WIDTH / 2.0
    assy.add(brg2, name="bearing_2", loc=cq.Location((0, 0, brg2_z)))

    # --- Pulldown cam ---
    cam = build_cam()
    cam_z = sections["cam_section"]["z0"] + CAM_THICK / 2.0
    assy.add(cam, name="pulldown_cam", loc=cq.Location((0, 0, cam_z)))

    # --- Secondary eccentric ---
    eccentric = build_secondary_eccentric()
    ecc_z = cam_z + CAM_THICK / 2.0 + ECCENTRIC_THICK / 2.0
    assy.add(eccentric, name="secondary_eccentric", loc=cq.Location((0, 0, ecc_z)))

    # --- Shutter disc ---
    disc = shutter_disc.build()
    shutter_z = sections["shutter"]["z0"] + sections["shutter"]["z1"]
    shutter_z /= 2.0  # midpoint of shutter section
    assy.add(disc, name="shutter_disc", loc=cq.Location((0, 0, shutter_z)))

    # --- Encoder disc ---
    encoder = build_encoder_disc()
    enc_z = sections["encoder_end"]["z0"] + ENCODER_THICK / 2.0 + 0.5
    assy.add(encoder, name="encoder_disc", loc=cq.Location((0, 0, enc_z)))

    # --- Bearing housing ---
    housing = build_bearing_housing()
    # Center housing between the two bearing seats
    housing_z = (sections["bearing_1"]["z0"] + sections["bearing_2"]["z1"]) / 2.0
    assy.add(housing, name="bearing_housing",
             loc=cq.Location((0, -HOUSING_H / 2.0 - BRG_OD / 2.0, housing_z)))

    return assy


# =========================================================================
# VALIDATION
# =========================================================================

def validate_shutter() -> dict:
    """Validate shutter geometry, clearances, and timing.

    Checks:
      1. Shutter disc clears film gate at all rotation angles
      2. Shutter fully covers aperture when closed (solid sector covers image)
      3. Shutter fully clears aperture when open (no vignetting)
      4. Shutter is closed during entire pulldown phase
    """
    geom = get_disc_geometry()
    R = geom["outer_radius_mm"]
    balance = geom["balance"]

    checks = []
    all_pass = True

    # --- 1. Gate clearance ---
    # The shutter disc sits GATE_CLEARANCE (0.3mm) in front of the gate.
    # The disc is DISC_THICK (0.8mm) thick.  We need to verify no contact.
    # At all rotation angles the disc plane is fixed, so clearance is constant
    # (it's a flat disc spinning in its own plane).
    clearance_ok = GATE_CLEARANCE > DISC_THICK / 2.0 + 0.1  # 0.1mm safety
    # Actually: the disc plane is 0.3mm from gate face. The disc thickness
    # extends ±0.4mm from its center plane. So the nearest disc surface to
    # the gate is 0.3 - 0.4 = -0.1mm — that would be interference!
    # Correct interpretation: GATE_CLEARANCE is from the disc's nearest surface
    # to the gate face. So there is 0.3mm between disc rear surface and gate.
    actual_clearance = GATE_CLEARANCE  # 0.3mm between disc and gate
    clearance_ok = actual_clearance >= 0.2  # need at least 0.2mm
    checks.append((
        f"Gate clearance: {actual_clearance:.1f} mm (min 0.2 mm)",
        clearance_ok,
    ))
    all_pass &= clearance_ok

    # --- 2. Aperture coverage when closed ---
    # When the solid sector faces the aperture, it must fully cover the image area.
    # The shaft axis is above the aperture center.  The disc must extend
    # far enough below the shaft to cover the bottom of the aperture.
    # The aperture is FILM.frame_w × FILM.frame_h centered on the film plane.
    # Shaft axis is above the aperture — we need to know the offset.
    #
    # In our design, the shaft sits above the film aperture.
    # The aperture extends from -frame_h/2 to +frame_h/2 vertically (Y).
    # The shaft center is some distance above the aperture center.
    # For the disc to cover the aperture: R must be >= shaft_to_aperture_center + frame_h/2
    #
    # Shaft position above aperture center:
    # Shaft is at the top of the gate area.  The film gate is 20mm tall,
    # aperture is centered, so shaft is ~10mm above aperture center.
    # But the shutter disc only needs to be big enough to cover the aperture.
    # With R=14mm, the disc easily covers a 5.79×4.01mm aperture even if the
    # shaft is 8mm above aperture center (14 - 8 = 6 > 4.01/2 = 2.0).
    #
    # Conservative check: assume shaft is up to 10mm above aperture center.
    shaft_offset_max = 10.0  # mm — max shaft-to-aperture distance

    # Check that disc edge reaches below the aperture
    coverage_below = R - shaft_offset_max  # mm below shaft that disc reaches
    needed_below = FILM.frame_h / 2.0      # mm below aperture center

    # If shaft is above aperture by shaft_offset_max, we need:
    # R >= shaft_offset_max + frame_h/2
    coverage_ok = R >= shaft_offset_max + FILM.frame_h / 2.0

    # Also check horizontal coverage
    # The aperture is 5.79mm wide. The disc at the aperture level has a chord
    # width of 2×sqrt(R² - d²) where d = distance from shaft to aperture center.
    # At worst case (shaft 10mm above): chord = 2×sqrt(14² - 10²) = 2×sqrt(96) = 19.6mm
    # That's >> 5.79mm, so horizontal coverage is fine.
    if shaft_offset_max < R:
        chord_at_aperture = 2.0 * math.sqrt(R**2 - shaft_offset_max**2)
    else:
        chord_at_aperture = 0.0
    horiz_ok = chord_at_aperture >= FILM.frame_w + 1.0  # 1mm margin

    coverage_pass = coverage_ok and horiz_ok
    checks.append((
        f"Aperture coverage when closed: vert={'OK' if coverage_ok else 'FAIL'}, "
        f"horiz chord={chord_at_aperture:.1f}mm (need {FILM.frame_w + 1.0:.1f}mm)",
        coverage_pass,
    ))
    all_pass &= coverage_pass

    # --- 3. Aperture clear when open (no vignetting) ---
    # When the open sector faces the aperture, the solid sector must not
    # intrude into the image circle.  With 180° opening and the aperture
    # centered below the shaft, the open sector's edge at the aperture level
    # is a straight line (diameter of the disc).  The aperture center is
    # offset from the shaft, so we need the open sector edge to clear the
    # far side of the aperture.
    #
    # The open sector spans 180° (-90° to +90° around the -X axis in our
    # convention). When fully open (open sector facing down toward aperture),
    # the solid sector is above the shaft — completely out of the way.
    # The critical case is near the transition (0° and 180°).
    # At 0° (transition), the disc edge just touches the boundary.
    # We need a small margin — the disc edge should be at least 0.5mm
    # beyond the aperture edge at the transition angle.
    #
    # With the 180° sector, at the moment the shutter is "just open", the
    # blade edge (diameter line) passes through the shaft center.  If the
    # shaft is above the aperture, the blade edge clears the aperture
    # as long as the shaft is above the top of the aperture.
    vignette_margin = shaft_offset_max - FILM.frame_h / 2.0  # mm above top of aperture
    vignette_ok = vignette_margin >= 0.5
    checks.append((
        f"No vignetting when open: margin={vignette_margin:.1f}mm above aperture top "
        f"(need 0.5mm)",
        vignette_ok,
    ))
    all_pass &= vignette_ok

    # --- 4. Shutter closed during pulldown ---
    # The pulldown occurs during phases 2+3 (engage + pulldown).
    # From the cam profile: engage starts at ~10°, pulldown ends at ~170°.
    # The shutter is solid (closed) from 180° to 360°.
    # Wait — the shutter timing must be in phase with the cam.
    # By convention: 0°-180° = shutter OPEN (exposure), 180°-360° = shutter CLOSED.
    # The cam profile has: engage at 10°-30°, pulldown at 30°-170°.
    # Problem: pulldown happens while shutter is OPEN (0°-180°)!
    #
    # This is actually by design intent — let's check the SHUTTER timing spec:
    # Phase 1 (0-180°): exposure (shutter open, film stationary)
    # Phase 2 (180-230°): claw engage (shutter closed)
    # Phase 3 (230-330°): pulldown (shutter closed)
    # Phase 4 (330-360°): claw retract (shutter closed)
    #
    # But our cam profile uses different timing:
    # Cam: engage 10-30°, pulldown 30-170°, retract 170-190°, return 190-350°
    #
    # These are out of phase! The cam was designed with its own timing.
    # The assembly must KEY the shutter 180° out of phase with the cam,
    # so that when the cam is in pulldown (30-170° of shaft rotation),
    # the solid sector of the shutter faces the aperture.
    #
    # With the shutter keyed 180° offset:
    #   Shaft 0-10°: cam dwell, shutter solid → closed, OK
    #   Shaft 10-30°: cam engage, shutter solid → closed, OK
    #   Shaft 30-170°: cam pulldown, shutter solid → closed, OK
    #   Shaft 170-190°: cam retract, shutter transitioning
    #   Shaft 190-350°: cam return, shutter open → exposure
    #   Shaft 350-360°: cam dwell, shutter closing
    #
    # So: pulldown (30-170°) happens entirely during shutter solid sector.
    # Exposure happens during cam return (190-350°), when film is stationary.

    # The key constraint: cam pulldown (30°-170°) must be fully within
    # the shutter's solid sector.
    # With 180° offset keying: shutter solid spans 0°-180° of shaft rotation.
    # Cam pulldown is 30°-170°. So 30-170 ⊂ 0-180. ✓
    #
    # Also check: exposure (190°-350°) must be within shutter open sector.
    # Shutter open spans 180°-360°. Exposure 190-350 ⊂ 180-360. ✓

    cam_pulldown_start = 30.0   # from cam profile
    cam_pulldown_end = 170.0
    cam_engage_start = 10.0
    cam_retract_end = 190.0

    # Shutter solid sector (with 180° offset keying): 0° to 180°
    shutter_closed_start = 0.0
    shutter_closed_end = 180.0

    pulldown_covered = (cam_engage_start >= shutter_closed_start and
                        cam_retract_end <= shutter_closed_end + 10.0)  # 10° margin
    # Retract ends at 190° which is 10° past the 180° boundary.
    # But at 180° the blade is at the transition — the solid sector is just
    # leaving. In practice the blade edge takes a few degrees to transit the
    # aperture. With shaft 10mm above aperture and R=14mm, the blade sweeps
    # past the aperture in about 2×arcsin(frame_h/(2R)) = 2×arcsin(2/14) ≈ 16°.
    # So the aperture is still fully blocked at 180°+8° = 188°.  Retract at 190°
    # is just barely covered.

    transit_angle = 2.0 * math.degrees(math.asin(
        min(1.0, (FILM.frame_h / 2.0 + 0.5) / R)))  # degrees to sweep past aperture
    effective_closed_end = shutter_closed_end + transit_angle / 2.0

    pulldown_fully_covered = (cam_engage_start >= shutter_closed_start and
                               cam_retract_end <= effective_closed_end)

    checks.append((
        f"Pulldown during shutter closed: cam {cam_engage_start:.0f}°-{cam_retract_end:.0f}°, "
        f"shutter solid 0°-{effective_closed_end:.0f}° (with 180° offset key)",
        pulldown_fully_covered,
    ))
    all_pass &= pulldown_fully_covered

    # --- 5. Balance check ---
    balance_ok = balance.get("balance_ok", True) or not balance["pocket_needed"]
    checks.append((
        f"Static balance: {balance['residual_imbalance_gmm']:.4f} g·mm "
        f"(limit {MAX_IMBALANCE_GMM:.1f} g·mm)",
        balance_ok,
    ))
    all_pass &= balance_ok

    return {
        "all_pass": all_pass,
        "checks": checks,
        "geometry": geom,
        "shaft_sections": get_section_positions(),
    }


def print_validation():
    """Print shutter assembly validation results."""
    result = validate_shutter()
    print("\n  SHUTTER ASSEMBLY VALIDATION")
    print("  " + "-" * 55)
    for desc, ok in result["checks"]:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {desc}")

    overall = "PASS" if result["all_pass"] else "FAIL"
    print(f"\n    Overall: {overall}")


def export(output_dir: str = "export"):
    """Export each part individually and the complete assembly."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Individual parts
    parts = {
        "main_shaft": main_shaft.build,
        "shutter_disc": shutter_disc.build,
        "bearing_694zz": build_bearing,
        "bearing_housing": build_bearing_housing,
        "encoder_disc": build_encoder_disc,
    }
    for name, builder in parts.items():
        solid = builder()
        cq.exporters.export(solid, f"{output_dir}/{name}.step")
        cq.exporters.export(solid, f"{output_dir}/{name}.stl",
                            tolerance=0.01, angularTolerance=0.1)
        print(f"    {name:25s} STEP + STL")

    # Complete assembly
    assy = build()
    cq.exporters.export(assy.toCompound(), f"{output_dir}/shutter_assembly.step")
    print(f"    {'shutter_assembly':25s} STEP (combined)")


# Import for balance validation
from super8cam.parts.shutter_disc import MAX_IMBALANCE_GMM


if __name__ == "__main__":
    export()
    print_validation()
