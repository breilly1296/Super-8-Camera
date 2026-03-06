"""Cam and follower — eccentric cam system on main shaft drives the claw pulldown.

The mechanism uses a face cam (groove cam) on the main shaft to produce the
claw's vertical pulldown motion, and a secondary eccentric to produce the
horizontal engage/retract motion.  Together they create a rectangular claw
tip path: engage → pulldown → retract → return.

Cam profile uses a modified trapezoidal (1/4-1/2-1/4) acceleration pattern
for the pulldown phase to minimise jerk and prevent film tearing.

All dimensions from master_specs.
"""

import math
import numpy as np
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, MATERIALS, MATERIAL_USAGE,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["cam"]]

# =========================================================================
# CAM DISC (pulldown face cam)
# =========================================================================
CAM_OD = 16.0              # mm — outer diameter of disc
CAM_BORE = CAMERA.shaft_dia  # 4.0 mm — main shaft bore
CAM_THICK = 3.0             # mm — axial thickness
CAM_KEYWAY_W = 1.0          # mm — drive keyway width
CAM_KEYWAY_DEPTH = 0.5      # mm

# Groove in front face
GROOVE_W = 1.5              # mm — groove width
GROOVE_DEPTH = 1.0          # mm — groove depth into face
GROOVE_TRACK_R_MIN = 4.5    # mm — inner edge of groove center at dwell
GROOVE_TRACK_R_MAX = 4.5 + FILM.perf_pitch  # ~8.734 mm — after pulldown lift

# =========================================================================
# SECONDARY ECCENTRIC (engage / retract)
# =========================================================================
ECCENTRIC_OD = 10.0         # mm — outer diameter
ECCENTRIC_BORE = CAM_BORE   # mm — same shaft
ECCENTRIC_THICK = 3.0       # mm
ECCENTRIC_OFFSET = 0.8      # mm — eccentricity (produces ~2mm claw travel via link)
ECCENTRIC_PHASE = 90.0      # degrees ahead of pulldown cam

# =========================================================================
# FOLLOWER PIN (rides in cam groove)
# =========================================================================
FOLLOWER_PIN_DIA = 0.8      # mm — rides in the 1.5mm groove
FOLLOWER_PIN_LENGTH = 3.0   # mm

# =========================================================================
# CONNECTING LINK (eccentric → claw horizontal motion)
# =========================================================================
LINK_LENGTH = 8.0           # mm — center-to-center
LINK_W = 3.0                # mm — width
LINK_THICK = 1.0            # mm — thickness
LINK_BORE_ECCENTRIC = ECCENTRIC_OD + 0.1  # bearing bore on eccentric end
LINK_BORE_CLAW = 1.5        # mm — pivot pin bore on claw end

# =========================================================================
# GUIDE RAIL PINS (constrain claw to vertical travel)
# =========================================================================
GUIDE_PIN_DIA = 1.5         # mm
GUIDE_PIN_LENGTH = 15.0     # mm
GUIDE_PIN_SPACING = 10.0    # mm — between the two guide pins

# =========================================================================
# E-CLIP placeholders
# =========================================================================
ECLIP_OD = 3.0              # mm
ECLIP_THICK = 0.3           # mm
ECLIP_BORE = 1.5            # mm


# =========================================================================
# CAM PROFILE MATH
# =========================================================================

def _modified_trapezoid(theta_norm):
    """Modified trapezoidal motion (1/4-1/2-1/4 acceleration pattern).

    theta_norm in [0, 1] → displacement in [0, 1].

    Segments:
      0.00–0.25 : acceleration ramp-up   (sine accel)
      0.25–0.75 : constant velocity       (linear)
      0.75–1.00 : deceleration ramp-down  (sine decel)

    This gives smooth acceleration at start and end while maintaining
    nearly constant velocity through the middle of the stroke.
    """
    scalar = np.ndim(theta_norm) == 0
    s = np.atleast_1d(np.asarray(theta_norm, dtype=float))
    d = np.zeros_like(s)

    # Phase 1: sine ramp-up  [0, 0.25] → d in [0, 0.125]
    m1 = s <= 0.25
    t1 = s[m1] / 0.25  # normalise to [0,1]
    d[m1] = 0.125 * (t1 - (1.0 / (2.0 * np.pi)) * np.sin(2.0 * np.pi * t1))

    # Phase 2: constant velocity  [0.25, 0.75] → d in [0.125, 0.875]
    m2 = (s > 0.25) & (s <= 0.75)
    d[m2] = 0.125 + 0.75 * (s[m2] - 0.25) / 0.5

    # Phase 3: sine ramp-down  [0.75, 1.0] → d in [0.875, 1.0]
    m3 = s > 0.75
    t3 = (s[m3] - 0.75) / 0.25
    d[m3] = 0.875 + 0.125 * (t3 - (1.0 / (2.0 * np.pi)) * np.sin(2.0 * np.pi * t3))

    return float(d[0]) if scalar else d


def cam_profile_full(n_points: int = 360) -> dict:
    """Compute claw tip (x, y) for one full shaft revolution.

    Coordinate convention (looking at film gate from rear):
        x = horizontal (positive = toward film, engage direction)
        y = vertical   (positive = upward, negative = pulldown direction)

    Phase map (shaft angle θ):
        0°–10°   : dwell at top  (claw at top, retracted)
        10°–30°  : engage        (claw moves toward film horizontally)
        30°–170° : pulldown      (claw pulls film down 4.234 mm)
        170°–190°: retract       (claw moves away from film)
        190°–350°: return        (claw returns to top, no film contact)
        350°–360°: dwell at top  (film settling before next shutter open)

    Returns dict with arrays: theta_deg, x_mm, y_mm, vx_mm_per_deg,
    vy_mm_per_deg, ax, ay.
    """
    theta = np.linspace(0, 360, n_points, endpoint=False)
    x = np.zeros(n_points)  # horizontal (engage/retract)
    y = np.zeros(n_points)  # vertical (pulldown)

    stroke_v = FILM.perf_pitch  # 4.234 mm vertical pulldown
    stroke_h = 2.0              # mm horizontal engage/retract

    for i, th in enumerate(theta):
        # ----- VERTICAL (y) -----
        if th < 10.0:
            # Dwell at top
            y[i] = 0.0
        elif th < 30.0:
            # Engage phase — vertical stays at top
            y[i] = 0.0
        elif th < 170.0:
            # Pulldown: modified trapezoidal 30°→170° (140° arc)
            t_norm = (th - 30.0) / 140.0
            y[i] = -stroke_v * _modified_trapezoid(t_norm)
        elif th < 190.0:
            # Retract — vertical stays at bottom
            y[i] = -stroke_v
        elif th < 350.0:
            # Return stroke: 190°→350° (160° arc) — sine return
            t_norm = (th - 190.0) / 160.0
            y[i] = -stroke_v * (1.0 - (1.0 - math.cos(math.pi * t_norm)) / 2.0)
        else:
            # Dwell at top (350°→360°): film settling before shutter opens
            y[i] = 0.0

        # ----- HORIZONTAL (x) -----
        if th < 10.0:
            # Retracted
            x[i] = 0.0
        elif th < 30.0:
            # Engage: smooth sine 10°→30°
            t_norm = (th - 10.0) / 20.0
            x[i] = stroke_h * (1.0 - math.cos(math.pi * t_norm)) / 2.0
        elif th < 170.0:
            # Engaged — full depth
            x[i] = stroke_h
        elif th < 190.0:
            # Retract: smooth sine 170°→190°
            t_norm = (th - 170.0) / 20.0
            x[i] = stroke_h * (1.0 + math.cos(math.pi * t_norm)) / 2.0
        else:
            # Retracted
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
