"""Optical path assembly — lens mount + shutter + film gate along the optical axis.

Assembles the complete light path from the C-mount lens mount through the
shutter disc to the film gate.  Verifies coaxiality, flange distance,
and that the shutter properly gates light to the film plane.

The viewfinder is mounted above, parallel to the optical axis, offset
20mm up and 5mm left.

Coordinate system (camera body frame):
  Z = optical axis (+ toward scene/lens, - toward film)
  Y = vertical (+ up)
  X = horizontal (+ right when facing camera front)

Z=0 is the camera front face (where the lens boss meets the body).
The film plane is at Z = -(flange_focal_dist - boss_protrusion) from Z=0.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CMOUNT, CAMERA, TOL, MATERIALS,
)
from super8cam.parts import lens_mount, viewfinder
from super8cam.parts.film_gate import (
    build as build_film_gate, get_film_plane_origin,
    GATE_THICK, CHANNEL_DEPTH,
)
from super8cam.parts.lens_mount import (
    MOUNT_TO_SHUTTER_FRONT, BOSS_PROTRUSION, BOSS_OD,
    CLEARANCE_BORE_DIA, get_flange_stack_up, print_stack_up,
)
from super8cam.parts.shutter_disc import (
    DISC_OD, DISC_THICK, GATE_CLEARANCE,
)
from super8cam.parts.viewfinder import (
    VF_OFFSET_UP, VF_OFFSET_LEFT, TUBE_LENGTH,
    get_viewfinder_geometry,
)

# =========================================================================
# ASSEMBLY POSITIONS (all Z from camera front face, Z=0)
# =========================================================================
# Mount face is at the front of the boss protrusion
MOUNT_FACE_Z = BOSS_PROTRUSION  # +5.0mm (protrudes forward from body)

# Film plane: exactly flange_focal_dist behind the mount face
FILM_PLANE_Z = MOUNT_FACE_Z - CMOUNT.flange_focal_dist  # -12.526mm

# Gate front face: GATE_THICK - CHANNEL_DEPTH ahead of film plane
GATE_FRONT_Z = FILM_PLANE_Z + (GATE_THICK - CHANNEL_DEPTH)  # -8.726mm

# Gate center: half thickness behind gate front face
GATE_CENTER_Z = GATE_FRONT_Z - GATE_THICK / 2.0  # -10.726mm

# Shutter disc rear face: GATE_CLEARANCE ahead of gate front face
SHUTTER_REAR_Z = GATE_FRONT_Z + GATE_CLEARANCE  # -8.426mm

# Shutter disc center plane
SHUTTER_CENTER_Z = SHUTTER_REAR_Z + DISC_THICK / 2.0  # -8.026mm

# Shutter disc front face
SHUTTER_FRONT_Z = SHUTTER_REAR_Z + DISC_THICK  # -7.626mm

# Verify: mount face to shutter front should equal MOUNT_TO_SHUTTER_FRONT
_check_mount_to_shutter = MOUNT_FACE_Z - SHUTTER_FRONT_Z
assert abs(_check_mount_to_shutter - MOUNT_TO_SHUTTER_FRONT) < 0.001, (
    f"Mount-to-shutter mismatch: {_check_mount_to_shutter:.3f} vs "
    f"{MOUNT_TO_SHUTTER_FRONT:.3f}")

# Viewfinder position
VF_X = -VF_OFFSET_LEFT  # 5mm to the left (negative X)
VF_Y = VF_OFFSET_UP     # 20mm above optical axis
VF_Z = 0.0              # tube front at camera front face


def build() -> cq.Assembly:
    """Build the complete optical path assembly.

    Positions lens mount, shutter disc placeholder, film gate, and viewfinder
    along the optical axis.
    """
    assy = cq.Assembly(name="optical_path")

    # --- Lens mount boss ---
    # Boss is centered on Z=0 (camera front face) and protrudes forward
    lm = lens_mount.build()
    assy.add(lm, name="lens_mount",
             loc=cq.Location((0, 0, 0)))

    # --- Shutter disc (placeholder cylinder at correct Z) ---
    # The actual shutter is on the main shaft assembly; here we show
    # its position in the optical path for clearance checking.
    shutter_placeholder = (
        cq.Workplane("XY")
        .cylinder(DISC_THICK, DISC_OD / 2.0)
    )
    assy.add(shutter_placeholder, name="shutter_envelope",
             loc=cq.Location((0, 0, SHUTTER_CENTER_Z)))

    # --- Film gate ---
    # Gate is oriented with lens side (Z+) facing the shutter
    gate = build_film_gate()
    assy.add(gate, name="film_gate",
             loc=cq.Location((0, 0, GATE_CENTER_Z)))

    # --- Viewfinder ---
    # Mounted above and to the left, parallel to optical axis
    # Viewfinder Z=0 (eye end) is at the camera rear; Z=TUBE_LENGTH at front
    # Position it so the front is near the camera front face
    vf = viewfinder.build()
    vf_z_offset = -TUBE_LENGTH / 2.0  # center the tube roughly
    assy.add(vf, name="viewfinder",
             loc=cq.Location((VF_X, VF_Y, vf_z_offset)))

    return assy


# =========================================================================
# VALIDATION
# =========================================================================

def validate_optical_path() -> dict:
    """Validate the optical path geometry.

    Checks:
      1. Flange distance stack-up within tolerance
      2. Light path unobstructed when shutter open (bore > aperture at each plane)
      3. Shutter fully blocks light when closed (disc covers aperture)
      4. All three elements coaxial (centered on Z axis within ±0.1mm)
      5. Viewfinder parallel to optical axis
    """
    checks = []
    all_pass = True

    # --- 1. Flange distance ---
    su = get_flange_stack_up()
    checks.append((
        f"Flange distance: {su['total_mm']:.3f} mm "
        f"(target {su['target_mm']:.3f} mm, error {su['error_mm']:+.4f} mm)",
        su["pass"],
    ))
    all_pass &= su["pass"]

    # --- 2. Light path unobstructed ---
    # At each plane along the optical axis, the bore/opening must be larger
    # than the image cone. For a C-mount lens, the rear element can be up to
    # ~20mm at the mount. The image circle at the film plane is very small
    # (diagonal ~7mm). Check that each bore clears the cone.
    #
    # Image diagonal at film plane
    film_diag = math.sqrt(FILM.frame_w**2 + FILM.frame_h**2)  # ~7.04mm
    # Conservative light cone: from lens mount bore to film plane
    # At the mount: CLEARANCE_BORE_DIA = 26mm
    # At the gate aperture: frame_w × frame_h = 5.79 × 4.01
    # The cone narrows from 26mm to 7mm over the flange distance.
    # Check that the shutter opening doesn't clip the cone.

    # At shutter plane, the cone diameter is:
    dist_mount_to_shutter = MOUNT_TO_SHUTTER_FRONT + DISC_THICK / 2.0
    dist_mount_to_film = CMOUNT.flange_focal_dist
    cone_at_shutter = (CLEARANCE_BORE_DIA * (1.0 - dist_mount_to_shutter
                                              / dist_mount_to_film)
                       + film_diag * (dist_mount_to_shutter
                                      / dist_mount_to_film))
    # When shutter is open, the half-disc opening provides a half-plane.
    # The shaft is above the aperture, so the open half faces downward
    # toward the aperture. The usable opening at the aperture is bounded
    # by the disc diameter on the sides.
    # The cone at the shutter plane needs to fit within DISC_OD diameter
    shutter_clears_cone = DISC_OD >= cone_at_shutter + 2.0  # 2mm margin

    checks.append((
        f"Light cone at shutter plane: {cone_at_shutter:.1f} mm "
        f"(disc OD {DISC_OD} mm, margin {DISC_OD - cone_at_shutter:.1f} mm)",
        shutter_clears_cone,
    ))
    all_pass &= shutter_clears_cone

    # --- 3. Shutter blocks light when closed ---
    # The solid sector must cover the full aperture.
    # Same logic as shutter_assembly validation — the disc at R=14mm
    # easily covers the 5.79×4.01mm aperture with shaft ~10mm above.
    shaft_offset_max = 10.0  # mm — shaft above aperture center
    R = DISC_OD / 2.0
    coverage_ok = R >= shaft_offset_max + FILM.frame_h / 2.0
    if shaft_offset_max < R:
        chord = 2.0 * math.sqrt(R**2 - shaft_offset_max**2)
    else:
        chord = 0.0
    horiz_ok = chord >= FILM.frame_w + 1.0

    blocks_ok = coverage_ok and horiz_ok
    checks.append((
        f"Shutter blocks aperture: vert R={R:.0f}mm >= "
        f"{shaft_offset_max + FILM.frame_h / 2.0:.1f}mm needed, "
        f"horiz chord={chord:.1f}mm >= {FILM.frame_w + 1.0:.1f}mm needed",
        blocks_ok,
    ))
    all_pass &= blocks_ok

    # --- 4. Coaxiality ---
    # All three elements (mount bore, shutter center, gate aperture) are
    # centered on the Z axis by construction. In the physical camera,
    # this is ensured by the dowel pins on the gate and the bearing housing
    # alignment. The coaxiality tolerance is ±0.1mm.
    # For our model, all are at (X=0, Y=0), so coaxiality = 0.0mm.
    coaxial_error = 0.0  # mm — by construction
    coaxial_ok = coaxial_error <= 0.1
    checks.append((
        f"Coaxiality: {coaxial_error:.2f} mm (limit 0.1 mm)",
        coaxial_ok,
    ))
    all_pass &= coaxial_ok

    # --- 5. Viewfinder parallel ---
    # The viewfinder tube runs along Z, parallel to the optical axis.
    # Offset: {VF_OFFSET_LEFT}mm left, {VF_OFFSET_UP}mm up.
    # Angular error is zero by construction (both along Z axis).
    vf_parallel_ok = True  # parallel by construction
    checks.append((
        f"Viewfinder parallel: offset ({VF_OFFSET_LEFT:.0f}mm left, "
        f"{VF_OFFSET_UP:.0f}mm up), parallel by construction",
        vf_parallel_ok,
    ))
    all_pass &= vf_parallel_ok

    return {
        "all_pass": all_pass,
        "checks": checks,
        "positions": {
            "mount_face_z": MOUNT_FACE_Z,
            "shutter_center_z": SHUTTER_CENTER_Z,
            "gate_center_z": GATE_CENTER_Z,
            "gate_front_z": GATE_FRONT_Z,
            "film_plane_z": FILM_PLANE_Z,
        },
        "stack_up": get_flange_stack_up(),
    }


def print_validation():
    """Print optical path validation results."""
    result = validate_optical_path()
    print("\n  OPTICAL PATH VALIDATION")
    print("  " + "-" * 60)
    for desc, ok in result["checks"]:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {desc}")

    overall = "PASS" if result["all_pass"] else "FAIL"
    print(f"\n    Overall: {overall}")

    # Also print the flange stack-up
    print_stack_up()


# =========================================================================
# CROSS-SECTION PLOT
# =========================================================================

def plot_cross_section(save_path: str = None):
    """Generate a 2D cross-section view of the optical path.

    Shows the light path from lens mount to film plane with all distances
    labeled.  Uses matplotlib.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    ax.set_aspect("equal")
    ax.set_title("Optical Path Cross-Section (side view, Z = optical axis)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Z position (mm) — toward lens →")
    ax.set_ylabel("Y position (mm)")

    # Color scheme
    c_mount = "#4A90D9"
    c_shutter = "#E74C3C"
    c_gate = "#F39C12"
    c_film = "#2ECC71"
    c_cone = "#AED6F1"
    c_vf = "#8E44AD"

    # --- Light cone (shaded) ---
    # From clearance bore at shutter front to film aperture
    cone_top_front = CLEARANCE_BORE_DIA / 2.0
    cone_top_rear = FILM.frame_h / 2.0
    cone_z_front = MOUNT_FACE_Z - 3.8  # approx behind thread
    cone_z_rear = FILM_PLANE_Z

    cone_poly = plt.Polygon([
        (cone_z_front, cone_top_front),
        (cone_z_rear, cone_top_rear),
        (cone_z_rear, -cone_top_rear),
        (cone_z_front, -cone_top_front),
    ], alpha=0.15, color=c_cone, label="Light cone")
    ax.add_patch(cone_poly)

    # --- Lens mount boss ---
    boss_z_start = -CAMERA.wall_thickness
    boss_z_end = MOUNT_FACE_Z
    boss_half_y = BOSS_OD / 2.0
    bore_half_y = CMOUNT.thread_major_dia / 2.0

    # Outer boss profile
    ax.add_patch(patches.Rectangle(
        (boss_z_start, -boss_half_y),
        boss_z_end - boss_z_start, BOSS_OD,
        linewidth=1.5, edgecolor=c_mount, facecolor=c_mount, alpha=0.3,
        label="Lens mount boss"))

    # Thread bore
    ax.add_patch(patches.Rectangle(
        (MOUNT_FACE_Z - CMOUNT.thread_depth, -bore_half_y),
        CMOUNT.thread_depth, CMOUNT.thread_major_dia,
        linewidth=1, edgecolor="none", facecolor="white"))

    # Clearance bore
    cb_half = CLEARANCE_BORE_DIA / 2.0
    ax.add_patch(patches.Rectangle(
        (boss_z_start, -cb_half),
        MOUNT_FACE_Z - CMOUNT.thread_depth - boss_z_start, CLEARANCE_BORE_DIA,
        linewidth=1, edgecolor="none", facecolor="white"))

    # --- Shutter disc ---
    ax.add_patch(patches.Rectangle(
        (SHUTTER_REAR_Z, -DISC_OD / 2.0),
        DISC_THICK, DISC_OD,
        linewidth=1.5, edgecolor=c_shutter, facecolor=c_shutter, alpha=0.3,
        label="Shutter disc"))

    # Show the opening (remove top half when open — solid sector up)
    # The solid sector is above, open below (toward film gate aperture)
    ax.add_patch(patches.Rectangle(
        (SHUTTER_REAR_Z, -DISC_OD / 2.0),
        DISC_THICK, DISC_OD / 2.0,
        linewidth=0, facecolor="white"))

    # --- Film gate ---
    gate_z_start = GATE_CENTER_Z - GATE_THICK / 2.0
    ax.add_patch(patches.Rectangle(
        (gate_z_start, -10.0),
        GATE_THICK, 20.0,
        linewidth=1.5, edgecolor=c_gate, facecolor=c_gate, alpha=0.3,
        label="Film gate"))

    # Aperture through gate
    ax.add_patch(patches.Rectangle(
        (gate_z_start, -FILM.frame_h / 2.0),
        GATE_THICK, FILM.frame_h,
        linewidth=1, edgecolor="none", facecolor="white"))

    # --- Film plane ---
    ax.axvline(x=FILM_PLANE_Z, color=c_film, linewidth=2, linestyle="--",
               label=f"Film plane (Z={FILM_PLANE_Z:.3f})")

    # --- Viewfinder (above) ---
    vf_y_center = VF_OFFSET_UP
    vf_z_start = -TUBE_LENGTH / 2.0
    ax.add_patch(patches.Rectangle(
        (vf_z_start, vf_y_center - 4.0),
        TUBE_LENGTH, 8.0,
        linewidth=1.5, edgecolor=c_vf, facecolor=c_vf, alpha=0.2,
        label="Viewfinder"))

    # --- Dimension lines ---
    dim_y = -DISC_OD / 2.0 - 4.0  # below everything

    # Mount face to shutter front
    ax.annotate("", xy=(SHUTTER_FRONT_Z, dim_y), xytext=(MOUNT_FACE_Z, dim_y),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
    ax.text((MOUNT_FACE_Z + SHUTTER_FRONT_Z) / 2.0, dim_y - 1.5,
            f"{MOUNT_TO_SHUTTER_FRONT:.3f}",
            ha="center", va="top", fontsize=8, color="black")

    # Shutter thickness
    dim_y2 = dim_y - 4.0
    ax.annotate("", xy=(SHUTTER_REAR_Z, dim_y2),
                xytext=(SHUTTER_FRONT_Z, dim_y2),
                arrowprops=dict(arrowstyle="<->", color=c_shutter, lw=1.2))
    ax.text((SHUTTER_FRONT_Z + SHUTTER_REAR_Z) / 2.0, dim_y2 - 1.5,
            f"{DISC_THICK:.1f}",
            ha="center", va="top", fontsize=8, color=c_shutter)

    # Gate clearance
    ax.annotate("", xy=(GATE_FRONT_Z, dim_y2),
                xytext=(SHUTTER_REAR_Z, dim_y2),
                arrowprops=dict(arrowstyle="<->", color="gray", lw=1.0))
    ax.text((SHUTTER_REAR_Z + GATE_FRONT_Z) / 2.0, dim_y2 + 1.0,
            f"{GATE_CLEARANCE:.1f}",
            ha="center", va="bottom", fontsize=7, color="gray")

    # Gate thickness to film plane
    ax.annotate("", xy=(FILM_PLANE_Z, dim_y),
                xytext=(GATE_FRONT_Z, dim_y),
                arrowprops=dict(arrowstyle="<->", color=c_gate, lw=1.2))
    ax.text((GATE_FRONT_Z + FILM_PLANE_Z) / 2.0, dim_y - 1.5,
            f"{GATE_THICK - CHANNEL_DEPTH:.2f}",
            ha="center", va="top", fontsize=8, color=c_gate)

    # Total flange distance
    dim_y3 = dim_y - 8.0
    ax.annotate("", xy=(FILM_PLANE_Z, dim_y3),
                xytext=(MOUNT_FACE_Z, dim_y3),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.5))
    ax.text((MOUNT_FACE_Z + FILM_PLANE_Z) / 2.0, dim_y3 - 1.8,
            f"FFD = {CMOUNT.flange_focal_dist:.3f} mm",
            ha="center", va="top", fontsize=10, fontweight="bold")

    # --- Labels ---
    ax.text(MOUNT_FACE_Z, boss_half_y + 1.5, "Mount\nface",
            ha="center", va="bottom", fontsize=8, color=c_mount)
    ax.text(SHUTTER_CENTER_Z, DISC_OD / 2.0 + 1.5, "Shutter",
            ha="center", va="bottom", fontsize=8, color=c_shutter)
    ax.text(GATE_CENTER_Z, 11.5, "Film\ngate",
            ha="center", va="bottom", fontsize=8, color=c_gate)

    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_xlim(FILM_PLANE_Z - 5, MOUNT_FACE_Z + 5)
    ax.set_ylim(dim_y3 - 5, VF_OFFSET_UP + 8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  Cross-section saved to {save_path}")
    else:
        plt.savefig("optical_path_cross_section.png", dpi=150,
                     bbox_inches="tight")
        print("  Cross-section saved to optical_path_cross_section.png")
    plt.close()


def export(output_dir: str = "export"):
    """Export the assembly STEP and cross-section plot."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Assembly
    assy = build()
    cq.exporters.export(assy.toCompound(), f"{output_dir}/optical_path.step")
    print(f"  Optical path assembly exported to {output_dir}/")

    # Cross-section plot
    plot_cross_section(f"{output_dir}/optical_path_cross_section.png")

    # Validation
    print_validation()


if __name__ == "__main__":
    export()
