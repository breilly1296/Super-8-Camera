"""Cam and follower — eccentric cam system on main shaft drives the claw pulldown.

The mechanism uses a face cam (groove cam) on the main shaft to produce the
claw's vertical pulldown motion, and a secondary eccentric to produce the
horizontal engage/retract motion.  Together they create a rectangular claw
tip path: engage → pulldown → retract → return.

Cam profile uses a modified sinusoidal (cycloidal) motion profile
for pulldown and return phases, ensuring zero velocity at stroke
endpoints and finite jerk throughout to prevent film tearing.

All dimensions from master_specs.
"""

import math
import numpy as np
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, MATERIALS, MATERIAL_USAGE, CAM_SPEC,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["cam"]]

# =========================================================================
# CAM DISC (pulldown face cam)
# =========================================================================
CAM_OD = CAM_SPEC.cam_od
CAM_BORE = CAMERA.shaft_dia
CAM_THICK = CAM_SPEC.cam_thick
CAM_KEYWAY_W = CAM_SPEC.cam_keyway_w
CAM_KEYWAY_DEPTH = CAM_SPEC.cam_keyway_depth

# Groove in front face
GROOVE_W = CAM_SPEC.groove_w
GROOVE_DEPTH = CAM_SPEC.groove_depth
GROOVE_TRACK_R_MIN = CAM_SPEC.groove_track_r_min
GROOVE_TRACK_R_MAX = CAM_SPEC.groove_track_r_min + FILM.perf_pitch

# =========================================================================
# SECONDARY ECCENTRIC (engage / retract)
# =========================================================================
ECCENTRIC_OD = CAM_SPEC.eccentric_od
ECCENTRIC_BORE = CAMERA.shaft_dia
ECCENTRIC_THICK = CAM_SPEC.eccentric_thick
ECCENTRIC_OFFSET = CAM_SPEC.eccentric_offset
ECCENTRIC_PHASE = CAM_SPEC.eccentric_phase

# =========================================================================
# FOLLOWER PIN (rides in cam groove)
# =========================================================================
FOLLOWER_PIN_DIA = CAM_SPEC.follower_pin_dia
FOLLOWER_PIN_LENGTH = CAM_SPEC.follower_pin_length

# =========================================================================
# CONNECTING LINK (eccentric -> claw horizontal motion)
# =========================================================================
LINK_LENGTH = CAM_SPEC.link_length
LINK_W = CAM_SPEC.link_w
LINK_THICK = CAM_SPEC.link_thick
LINK_BORE_ECCENTRIC = CAM_SPEC.eccentric_od + 0.1
LINK_BORE_CLAW = CAM_SPEC.link_bore_claw

# =========================================================================
# GUIDE RAIL PINS (constrain claw to vertical travel)
# =========================================================================
GUIDE_PIN_DIA = CAM_SPEC.guide_pin_dia
GUIDE_PIN_LENGTH = CAM_SPEC.guide_pin_length
GUIDE_PIN_SPACING = CAM_SPEC.guide_pin_spacing

# =========================================================================
# E-CLIP placeholders
# =========================================================================
ECLIP_OD = CAM_SPEC.eclip_od
ECLIP_THICK = CAM_SPEC.eclip_thick
ECLIP_BORE = CAM_SPEC.eclip_bore


# =========================================================================
# CAM PROFILE MATH
# =========================================================================

def _modified_sine(theta_norm):
    """Modified sinusoidal (cycloidal) motion profile.

    theta_norm in [0, 1] → displacement in [0, 1].

    Properties:
      - Displacement: continuous, monotonic
      - Velocity: zero at endpoints (smooth start/stop)
      - Acceleration: zero at endpoints
      - Jerk: finite everywhere (no discontinuities)

    This is the standard cycloidal cam profile, producing sinusoidal
    acceleration and ensuring zero velocity at both ends of the stroke.
    """
    scalar = np.ndim(theta_norm) == 0
    s = np.atleast_1d(np.asarray(theta_norm, dtype=float))
    d = s - np.sin(2.0 * np.pi * s) / (2.0 * np.pi)
    return float(d[0]) if scalar else d


def cam_profile_full(n_points: int = 360) -> dict:
    """Compute claw tip (x, y) for one full shaft revolution.

    Coordinate convention (looking at film gate from rear):
        x = horizontal (positive = toward film, engage direction)
        y = vertical   (positive = upward, negative = pulldown direction)

    Phase map (shaft angle θ):
          0°–180°: shutter OPEN  (exposure — film stationary, pin engaged)
        180°–185°: shutter CLOSES, reg pin disengages
        185°–190°: claw ENGAGES  (moves toward film, 2 mm horizontal)
        190°–330°: PULLDOWN      (claw pulls film down 4.234 mm)
        330°–335°: claw RETRACTS (moves away from film)
        335°–350°: RETURN stroke (claw moves back to top position)
        350°–360°: DWELL         (film settles, registration pin engages)

    Returns dict with arrays: theta_deg, x_mm, y_mm, vx_mm_per_deg,
    vy_mm_per_deg, ax, ay.
    """
    theta = np.linspace(0, 360, n_points, endpoint=False)
    x = np.zeros(n_points)  # horizontal (engage/retract)
    y = np.zeros(n_points)  # vertical (pulldown)

    stroke_v = FILM.perf_pitch  # 4.234 mm vertical pulldown
    stroke_h = CAM_SPEC.stroke_h  # mm horizontal engage/retract

    for i, th in enumerate(theta):
        # ----- VERTICAL (y) -----
        if th < 185.0:
            # Shutter open + close — claw at top, stationary
            y[i] = 0.0
        elif th < 190.0:
            # Engage phase — vertical stays at top
            y[i] = 0.0
        elif th < 330.0:
            # Pulldown: modified sine 190°→330° (140° arc)
            t_norm = (th - 190.0) / 140.0
            y[i] = -stroke_v * _modified_sine(t_norm)
        elif th < 335.0:
            # Retract — vertical stays at bottom
            y[i] = -stroke_v
        elif th < 350.0:
            # Return stroke: 335°→350° (15° arc) — modified sine return
            t_norm = (th - 335.0) / 15.0
            y[i] = -stroke_v * (1.0 - _modified_sine(t_norm))
        else:
            # Dwell: 350°→360° — claw at top, stationary
            y[i] = 0.0

        # ----- HORIZONTAL (x) -----
        if th < 185.0:
            # Retracted — no engagement during exposure + close
            x[i] = 0.0
        elif th < 190.0:
            # Engage: smooth sine 185°→190° (5° arc)
            t_norm = (th - 185.0) / 5.0
            x[i] = stroke_h * (1.0 - math.cos(math.pi * t_norm)) / 2.0
        elif th < 330.0:
            # Engaged during pulldown
            x[i] = stroke_h
        elif th < 335.0:
            # Retract: smooth sine 330°→335° (5° arc)
            t_norm = (th - 330.0) / 5.0
            x[i] = stroke_h * (1.0 + math.cos(math.pi * t_norm)) / 2.0
        else:
            # Retracted during return + dwell
            x[i] = 0.0

    # Numerical derivatives (per degree)
    d_theta = theta[1] - theta[0]
    vx = np.gradient(x, d_theta)
    vy = np.gradient(y, d_theta)
    ax = np.gradient(vx, d_theta)
    ay = np.gradient(vy, d_theta)

    return {
        "theta_deg": theta,
        "x_mm": x,
        "y_mm": y,
        "vx_mm_per_deg": vx,
        "vy_mm_per_deg": vy,
        "ax_mm_per_deg2": ax,
        "ay_mm_per_deg2": ay,
    }


def cam_groove_points(n_points: int = 360) -> list:
    """Generate the 3D spline points for the cam face groove centerline.

    The groove is cut into the front face of the cam disc.  The radial
    position encodes the vertical claw displacement: as the shaft rotates
    the follower pin rides at different radii, converting rotation into
    linear pulldown motion via a lever.

    Returns list of (x, y, z) points on the cam disc front face.
    """
    profile = cam_profile_full(n_points)
    points = []
    for i in range(n_points):
        th_rad = math.radians(profile["theta_deg"][i])
        # Map vertical displacement to radial position
        # y=0 (top) → r = GROOVE_TRACK_R_MIN
        # y=-4.234 (bottom) → r = GROOVE_TRACK_R_MAX
        r = GROOVE_TRACK_R_MIN + (-profile["y_mm"][i] / FILM.perf_pitch) * \
            (GROOVE_TRACK_R_MAX - GROOVE_TRACK_R_MIN)
        px = r * math.cos(th_rad)
        py = r * math.sin(th_rad)
        pz = 0.0  # on the disc face
        points.append((px, py, pz))
    return points


# =========================================================================
# CADQUERY PART BUILDERS
# =========================================================================

def build_cam() -> cq.Workplane:
    """Build the pulldown face cam disc with groove.

    The disc sits on the main shaft.  Its front face (+Z) has a spiral
    groove whose radial position encodes the claw's vertical displacement.
    """
    r = CAM_OD / 2.0

    # Base disc
    cam = (
        cq.Workplane("XY")
        .cylinder(CAM_THICK, r)
    )

    # Shaft bore
    cam = cam.faces(">Z").workplane().hole(CAM_BORE, CAM_THICK)

    # Keyway slot in bore
    cam = (
        cam.faces(">Z").workplane()
        .center(CAM_BORE / 2.0, 0)
        .rect(CAM_KEYWAY_DEPTH * 2, CAM_KEYWAY_W)
        .cutBlind(-CAM_THICK)
    )

    # Groove cut — we approximate the complex spiral groove as a series of
    # cylindrical cuts along the groove centerline.  For STEP export fidelity
    # we cut a simplified representation: a circular trough at the mean
    # groove radius with a radial modulation pocket.
    # Full parametric groove would require sweeping along a spline which is
    # fragile in CadQuery; instead we create the groove as a swept circle
    # along sample points on the cam face.
    pts = cam_groove_points(72)  # 72 points = every 5 degrees

    # Cut groove by sweeping small cylinders at each sample point.
    # This creates a faceted approximation of the continuous groove.
    groove_face = cam.faces(">Z").workplane()
    for i in range(len(pts)):
        px, py, _ = pts[i]
        # Small pocket at each point to approximate the groove
        groove_face = (
            cq.Workplane("XY")
            .transformed(offset=(px, py, CAM_THICK / 2.0))
            .circle(GROOVE_W / 2.0)
            .extrude(-GROOVE_DEPTH)
        )
        cam = cam.cut(groove_face)

    return cam


def build_secondary_eccentric() -> cq.Workplane:
    """Build the secondary eccentric for claw engage/retract motion.

    A disc with an offset bore — when mounted on the shaft and rotated,
    the outer circle oscillates ±ECCENTRIC_OFFSET producing horizontal
    claw travel via the connecting link.
    """
    r = ECCENTRIC_OD / 2.0

    # Outer disc centered at the eccentric offset
    eccentric = (
        cq.Workplane("XY")
        .cylinder(ECCENTRIC_THICK, r)
    )

    # Bore is offset from disc center by ECCENTRIC_OFFSET
    # When mounted on shaft, the disc center orbits the shaft center.
    eccentric = (
        eccentric.faces(">Z").workplane()
        .center(-ECCENTRIC_OFFSET, 0)
        .hole(ECCENTRIC_BORE, ECCENTRIC_THICK)
    )

    # Keyway in bore
    eccentric = (
        eccentric.faces(">Z").workplane()
        .center(-ECCENTRIC_OFFSET + ECCENTRIC_BORE / 2.0, 0)
        .rect(CAM_KEYWAY_DEPTH * 2, CAM_KEYWAY_W)
        .cutBlind(-ECCENTRIC_THICK)
    )

    return eccentric


def build_follower_pin() -> cq.Workplane:
    """Build the follower pin that rides in the cam groove."""
    pin = (
        cq.Workplane("XY")
        .cylinder(FOLLOWER_PIN_LENGTH, FOLLOWER_PIN_DIA / 2.0)
    )
    return pin


def build_connecting_link() -> cq.Workplane:
    """Build the connecting link from secondary eccentric to claw arm.

    A flat bar with a bearing bore at one end (fits around the eccentric)
    and a pivot pin bore at the other (connects to claw arm).
    """
    # Main bar
    link = (
        cq.Workplane("XY")
        .box(LINK_LENGTH, LINK_W, LINK_THICK)
        .edges("|Z").fillet(0.5)
    )

    # Eccentric end bore (larger, fits around eccentric OD)
    link = (
        link.faces(">Z").workplane()
        .center(-LINK_LENGTH / 2.0 + LINK_W / 2.0, 0)
        .hole(ECCENTRIC_OD + 0.1, LINK_THICK)
    )

    # Claw pivot end bore
    link = (
        link.faces(">Z").workplane()
        .center(LINK_LENGTH / 2.0 - LINK_W / 2.0, 0)
        .hole(LINK_BORE_CLAW, LINK_THICK)
    )

    return link


def build_guide_pins() -> cq.Workplane:
    """Build a pair of guide rail pins that constrain the claw to vertical motion.

    Returns both pins as a single solid, spaced GUIDE_PIN_SPACING apart.
    """
    pins = cq.Workplane("XY")
    for x_offset in [-GUIDE_PIN_SPACING / 2.0, GUIDE_PIN_SPACING / 2.0]:
        pin = (
            cq.Workplane("XY")
            .cylinder(GUIDE_PIN_LENGTH, GUIDE_PIN_DIA / 2.0)
            .translate((x_offset, 0, 0))
        )
        pins = pins.union(pin)
    return pins


def build_eclip() -> cq.Workplane:
    """Build an E-clip placeholder (retaining clip for pins)."""
    clip = (
        cq.Workplane("XY")
        .cylinder(ECLIP_THICK, ECLIP_OD / 2.0)
    )
    clip = clip.faces(">Z").workplane().hole(ECLIP_BORE, ECLIP_THICK)
    return clip


# =========================================================================
# ASSEMBLY
# =========================================================================

def build_assembly(shaft_angle_deg: float = 0.0) -> dict:
    """Return all cam/follower parts positioned relative to shaft centerline.

    The shaft center is at the origin, shaft axis along Z.
    The cam disc sits with its front face toward the film gate (-X direction).

    Args:
        shaft_angle_deg: Current shaft rotation for visualisation.

    Returns:
        Dict of {name: cq.Workplane} with each part translated/rotated
        into its assembled position.
    """
    parts = {}

    # Cam disc — front face toward gate, axis along Z
    cam = build_cam()
    parts["cam_disc"] = cam

    # Secondary eccentric — offset axially from cam disc
    eccentric = build_secondary_eccentric()
    eccentric = eccentric.translate((0, 0, -(CAM_THICK / 2.0 + ECCENTRIC_THICK / 2.0)))
    parts["secondary_eccentric"] = eccentric

    # Follower pin — positioned at the groove for current angle
    profile = cam_profile_full(360)
    angle_idx = int(shaft_angle_deg) % 360
    pts = cam_groove_points(360)
    px, py, _ = pts[angle_idx]
    follower = build_follower_pin()
    follower = follower.translate((px, py, CAM_THICK / 2.0 + FOLLOWER_PIN_LENGTH / 2.0))
    parts["follower_pin"] = follower

    # Guide pins — mounted to the camera frame, vertical orientation
    guides = build_guide_pins()
    # Rotate so pins are vertical (along Y axis) and position near the cam
    parts["guide_pins"] = guides.translate((CAM_OD / 2.0 + 5.0, 0, 0))

    # Connecting link
    link = build_connecting_link()
    parts["connecting_link"] = link.translate((
        0, 0, -(CAM_THICK / 2.0 + ECCENTRIC_THICK + LINK_THICK / 2.0)
    ))

    # E-clips (placeholders at pin ends)
    eclip = build_eclip()
    parts["eclip_placeholder"] = eclip.translate((0, 0, CAM_THICK / 2.0 + 2.0))

    return parts


def export(output_dir: str = "export"):
    """Export all cam/follower parts as individual STEP files."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    exports = {
        "cam_disc": build_cam,
        "secondary_eccentric": build_secondary_eccentric,
        "follower_pin": build_follower_pin,
        "connecting_link": build_connecting_link,
        "guide_pins": build_guide_pins,
        "eclip": build_eclip,
    }

    for name, builder in exports.items():
        solid = builder()
        step_path = f"{output_dir}/{name}.step"
        stl_path = f"{output_dir}/{name}.stl"
        cq.exporters.export(solid, step_path)
        cq.exporters.export(solid, stl_path, tolerance=0.01, angularTolerance=0.1)
        print(f"  {name:25s} STEP + STL")


# Legacy API — keep build() for compatibility with build.py
def build() -> cq.Workplane:
    """Return the cam disc (primary part for build system)."""
    return build_cam()


def build_follower() -> cq.Workplane:
    """Return the follower pin (legacy API)."""
    return build_follower_pin()


if __name__ == "__main__":
    export()
