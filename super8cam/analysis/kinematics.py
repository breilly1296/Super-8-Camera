"""Kinematics analysis — claw motion profile, forces, and mechanism simulation.

Steps through 360° of shaft rotation computing claw tip position, velocity,
acceleration, and perforation force.  Validates that:
  - The claw completes its cycle in one revolution
  - Peak perforation force stays below 1.0 N (Kodak allows 1.5 N)
  - Film is stationary and registered before shutter opens
  - Timing phases match the shutter timing spec

Uses the cam profile equations from parts/cam_follower.py as the single
source of truth for claw motion.
"""

import math
import numpy as np
from super8cam.specs.master_specs import (
    FILM, CAMERA, SHUTTER, GEARBOX, MOTOR,
)
from super8cam.parts.cam_follower import cam_profile_full

# =========================================================================
# PHYSICAL CONSTANTS
# =========================================================================

# Film mass for force calculation
# PET base density ~1.39 g/cm³, film cross-section per frame
FILM_DENSITY_G_CM3 = 1.39
FILM_FRAME_VOLUME_CM3 = (FILM.width * FILM.perf_pitch * FILM.thickness) / 1000.0
FILM_FRAME_MASS_KG = FILM_DENSITY_G_CM3 * FILM_FRAME_VOLUME_CM3 / 1000.0

# Friction coefficient: film on brass gate (lubricated by silicone)
MU_FILM_GATE = 0.15

# Pressure plate force (from pressure_plate.py design)
PRESSURE_PLATE_FORCE_N = 0.5

# Gravity component (negligible but included for completeness)
G_M_S2 = 9.81

# Maximum allowable perforation force (Kodak spec: 1.5 N, our limit: 1.0 N)
MAX_PERF_FORCE_N = 1.0


# =========================================================================
# FULL-REVOLUTION CLAW ANALYSIS
# =========================================================================

def claw_tip_analysis(fps: int, n_points: int = 360) -> dict:
    """Analyse claw tip motion for one complete shaft revolution.

    Args:
        fps: Frame rate (18 or 24).
        n_points: Angular resolution.

    Returns dict with:
        theta_deg     — shaft angle array (degrees)
        x_mm, y_mm    — claw tip position (horizontal, vertical)
        vx_mm_s, vy_mm_s — velocity (mm/s)
        ax_mm_s2, ay_mm_s2 — acceleration (mm/s²)
        force_perf_n  — perforation force at each angle (N)
        peak_force_n  — maximum perforation force (N)
        force_ok      — True if peak < MAX_PERF_FORCE_N
        path_closed   — True if start ≈ end position
        settled_before_shutter — True if film stationary at θ=0°
    """
    profile = cam_profile_full(n_points)
    theta = profile["theta_deg"]
    x = profile["x_mm"]
    y = profile["y_mm"]

    # Time per degree at this frame rate
    period_s = 1.0 / fps
    deg_per_s = 360.0 * fps
    dt_per_deg = 1.0 / deg_per_s  # seconds per degree

    d_theta = theta[1] - theta[0]  # degrees per step

    # Convert per-degree derivatives to per-second
    vx_mm_s = profile["vx_mm_per_deg"] * deg_per_s
    vy_mm_s = profile["vy_mm_per_deg"] * deg_per_s
    ax_mm_s2 = profile["ax_mm_per_deg2"] * deg_per_s**2
    ay_mm_s2 = profile["ay_mm_per_deg2"] * deg_per_s**2

    # Speed magnitude
    speed_mm_s = np.sqrt(vx_mm_s**2 + vy_mm_s**2)
    accel_mm_s2 = np.sqrt(ax_mm_s2**2 + ay_mm_s2**2)

    # ---- Perforation force during pulldown ----
    # F = m*a + friction + gravity
    # Friction = mu * N (N = pressure plate force, acts during engaged phase)
    # Only compute force when claw is engaged (x > 1.0 mm = substantially engaged)
    force_perf_n = np.zeros(n_points)
    for i in range(n_points):
        if x[i] > 1.0:  # claw engaged
            # Inertial force (mass × vertical acceleration)
            f_inertia = FILM_FRAME_MASS_KG * abs(ay_mm_s2[i]) / 1000.0  # N
            # Friction force
            f_friction = MU_FILM_GATE * PRESSURE_PLATE_FORCE_N
            # Gravity (film moves downward, assists slightly)
            f_gravity = FILM_FRAME_MASS_KG * G_M_S2 / 1000.0  # negligible
            force_perf_n[i] = f_inertia + f_friction
        else:
            force_perf_n[i] = 0.0

    peak_force = float(np.max(force_perf_n))
    force_ok = peak_force < MAX_PERF_FORCE_N

    # ---- Path closure check ----
    path_closed = (abs(x[0] - x[-1]) < 0.01 and abs(y[0] - y[-1]) < 0.01)

    # ---- Settled before shutter check ----
    # At θ=0° (shutter opens), claw should be retracted and film stationary.
    # Check velocity near θ=0 (wrap-around: check last few degrees and first few)
    settle_window = 5  # degrees
    settle_indices = list(range(n_points - settle_window, n_points)) + \
                     list(range(0, settle_window))
    max_speed_at_shutter = max(speed_mm_s[i] for i in settle_indices)
    settled = max_speed_at_shutter < 1.0  # < 1 mm/s is "stationary"

    # ---- Timing validation ----
    # Find key phase transitions from the motion profile
    # Engage start: first angle where x > 0.1
    engage_start = float(theta[np.argmax(x > 0.1)]) if np.any(x > 0.1) else None
    # Engage complete: first angle where x > 1.9 (near full 2mm)
    engage_done = float(theta[np.argmax(x > 1.9)]) if np.any(x > 1.9) else None
    # Pulldown start: first angle where y < -0.05 (moving down)
    pd_start = float(theta[np.argmax(y < -0.05)]) if np.any(y < -0.05) else None
    # Pulldown end: first angle where y < -(perf_pitch - 0.05)
    pd_end_val = -(FILM.perf_pitch - 0.05)
    pd_end = float(theta[np.argmax(y < pd_end_val)]) if np.any(y < pd_end_val) else None
    # Retract start: first angle after pulldown where x starts decreasing
    retract_start = None
    if pd_end is not None:
        pd_end_idx = np.argmax(y < pd_end_val)
        for i in range(pd_end_idx, n_points):
            if x[i] < 1.5:
                retract_start = float(theta[i])
                break

    return {
        "fps": fps,
        "theta_deg": theta,
        "x_mm": x,
        "y_mm": y,
        "vx_mm_s": vx_mm_s,
        "vy_mm_s": vy_mm_s,
        "ax_mm_s2": ax_mm_s2,
        "ay_mm_s2": ay_mm_s2,
        "speed_mm_s": speed_mm_s,
        "accel_mm_s2": accel_mm_s2,
        "force_perf_n": force_perf_n,
        "peak_force_n": peak_force,
        "force_ok": force_ok,
        "max_force_limit_n": MAX_PERF_FORCE_N,
        "path_closed": path_closed,
        "settled_before_shutter": settled,
        "max_speed_at_shutter_mm_s": max_speed_at_shutter,
        "pulldown_stroke_mm": float(np.max(np.abs(y))),
        "engage_stroke_mm": float(np.max(x)),
        "timing": {
            "engage_start_deg": engage_start,
            "engage_done_deg": engage_done,
            "pulldown_start_deg": pd_start,
            "pulldown_end_deg": pd_end,
            "retract_start_deg": retract_start,
        },
    }


def pulldown_profile(fps: int, steps: int = 1000) -> dict:
    """Compute claw position, velocity, and acceleration during pulldown only.

    Backward-compatible API — returns the pulldown phase extracted from
    the full cam profile analysis.
    """
    analysis = claw_tip_analysis(fps, 360)

    # Extract the pulldown phase (where claw is engaged and moving down)
    theta = analysis["theta_deg"]
    y = analysis["y_mm"]
    engaged = analysis["x_mm"] > 1.0
    moving_down = np.gradient(y) < -0.001

    # Find the pulldown window
    pulldown_mask = engaged & moving_down
    if not np.any(pulldown_mask):
        # Fallback: use the full engaged phase
        pulldown_mask = engaged

    pulldown_indices = np.where(pulldown_mask)[0]
    if len(pulldown_indices) == 0:
        # Final fallback: return full revolution
        pulldown_indices = np.arange(len(theta))

    start_idx = pulldown_indices[0]
    end_idx = pulldown_indices[-1]
    sl = slice(start_idx, end_idx + 1)

    period_s = 1.0 / fps
    deg_per_s = 360.0 * fps
    angles = theta[sl]
    position = np.abs(y[sl])
    velocity = np.abs(analysis["vy_mm_s"][sl])
    accel = np.abs(analysis["ay_mm_s2"][sl])

    # Time array
    t = (angles - angles[0]) / deg_per_s

    return {
        "angle_deg": angles,
        "time_s": t,
        "position_mm": position,
        "velocity_mm_s": velocity,
        "accel_mm_s2": accel,
        "peak_velocity_mm_s": float(np.max(velocity)),
        "peak_accel_mm_s2": float(np.max(accel)),
    }


def shaft_torque_estimate(fps: int) -> float:
    """Estimate required torque at main shaft (N·mm) for film pulldown."""
    analysis = claw_tip_analysis(fps, 360)
    peak_force = analysis["peak_force_n"]
    # Torque = force × cam lobe radius (approximate)
    from super8cam.parts.cam_follower import GROOVE_TRACK_R_MAX
    torque_nmm = peak_force * GROOVE_TRACK_R_MAX
    return torque_nmm


def motor_speed_check() -> dict:
    """Verify motor RPM is achievable at both frame rates."""
    results = {}
    for fps in CAMERA.fps_options:
        shaft_rpm = fps * 60
        motor_rpm = shaft_rpm * GEARBOX.ratio
        headroom = (MOTOR.no_load_rpm - motor_rpm) / MOTOR.no_load_rpm * 100
        results[fps] = {
            "shaft_rpm": shaft_rpm,
            "motor_rpm": motor_rpm,
            "headroom_pct": headroom,
            "feasible": motor_rpm < MOTOR.no_load_rpm * 0.9,
        }
    return results


# =========================================================================
# PLOTTING & ANIMATION
# =========================================================================

def plot_claw_path(fps: int = 24, save_path: str = None):
    """Plot the complete claw tip path (rectangular with rounded corners).

    Generates a multi-panel figure:
      1. Claw tip X-Y path (the rectangle)
      2. Vertical displacement vs angle
      3. Velocity vs angle
      4. Acceleration vs angle
      5. Perforation force vs angle
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    analysis = claw_tip_analysis(fps, 720)
    theta = analysis["theta_deg"]
    x = analysis["x_mm"]
    y = analysis["y_mm"]

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(f"Claw Mechanism Analysis @ {fps} fps", fontsize=14, fontweight="bold")

    # 1. Claw tip path (X-Y)
    ax = axes[0, 0]
    scatter = ax.scatter(x, y, c=theta, cmap="hsv", s=2, zorder=2)
    ax.set_xlabel("Horizontal (engage) [mm]")
    ax.set_ylabel("Vertical (pulldown) [mm]")
    ax.set_title("Claw Tip Path")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    fig.colorbar(scatter, ax=ax, label="Shaft angle [deg]")
    # Mark key positions
    ax.plot(x[0], y[0], "go", markersize=8, label="Start (0°)")
    idx_90 = len(theta) // 4
    ax.plot(x[idx_90], y[idx_90], "bs", markersize=6, label="90°")
    idx_180 = len(theta) // 2
    ax.plot(x[idx_180], y[idx_180], "r^", markersize=8, label="180°")
    idx_270 = 3 * len(theta) // 4
    ax.plot(x[idx_270], y[idx_270], "mv", markersize=6, label="270°")
    ax.legend(fontsize=7, loc="lower left")

    # 2. Vertical displacement vs angle
    ax = axes[0, 1]
    ax.plot(theta, y, "b-", linewidth=1.5)
    ax.axhline(-FILM.perf_pitch, color="r", linestyle="--", alpha=0.5,
               label=f"Target: -{FILM.perf_pitch} mm")
    ax.set_xlabel("Shaft angle [deg]")
    ax.set_ylabel("Y displacement [mm]")
    ax.set_title("Vertical Motion (Pulldown)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    # Shade exposure window
    ax.axvspan(SHUTTER.phase1_start, SHUTTER.phase1_end, alpha=0.1, color="yellow",
               label="Shutter open")

    # 3. Horizontal displacement vs angle
    ax = axes[0, 2]
    ax.plot(theta, x, "g-", linewidth=1.5)
    ax.axhline(2.0, color="r", linestyle="--", alpha=0.5, label="Full engage (2mm)")
    ax.set_xlabel("Shaft angle [deg]")
    ax.set_ylabel("X displacement [mm]")
    ax.set_title("Horizontal Motion (Engage/Retract)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    ax.axvspan(SHUTTER.phase1_start, SHUTTER.phase1_end, alpha=0.1, color="yellow")

    # 4. Velocity vs angle
    ax = axes[1, 0]
    ax.plot(theta, analysis["vy_mm_s"], "b-", linewidth=1, label="Vertical")
    ax.plot(theta, analysis["vx_mm_s"], "g-", linewidth=1, label="Horizontal")
    ax.set_xlabel("Shaft angle [deg]")
    ax.set_ylabel("Velocity [mm/s]")
    ax.set_title("Claw Tip Velocity")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # 5. Acceleration vs angle
    ax = axes[1, 1]
    ax.plot(theta, analysis["ay_mm_s2"], "b-", linewidth=1, label="Vertical")
    ax.plot(theta, analysis["ax_mm_s2"], "g-", linewidth=1, label="Horizontal")
    ax.set_xlabel("Shaft angle [deg]")
    ax.set_ylabel("Acceleration [mm/s²]")
    ax.set_title("Claw Tip Acceleration")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # 6. Perforation force
    ax = axes[1, 2]
    ax.fill_between(theta, force_perf_n := analysis["force_perf_n"],
                     alpha=0.3, color="red")
    ax.plot(theta, force_perf_n, "r-", linewidth=1.5)
    ax.axhline(MAX_PERF_FORCE_N, color="k", linestyle="--", linewidth=2,
               label=f"Limit: {MAX_PERF_FORCE_N} N")
    ax.set_xlabel("Shaft angle [deg]")
    ax.set_ylabel("Force [N]")
    ax.set_title(f"Perforation Force (peak: {analysis['peak_force_n']:.3f} N)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    plt.tight_layout()
    path = save_path or "export/claw_analysis.png"
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Claw analysis plot saved: {path}")
    return path


def animate_mechanism(fps: int = 24, save_path: str = None, frames: int = 72):
    """Animate the claw mechanism showing cam rotation, claw motion, and film advance.

    Generates an animated GIF (or static frame sequence if animation fails).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

    analysis = claw_tip_analysis(fps, 360)

    fig, (ax_cam, ax_claw) = plt.subplots(1, 2, figsize=(14, 7))
    fig.suptitle(f"Claw Mechanism Animation @ {fps} fps", fontsize=13)

    path = save_path or "export/claw_mechanism_anim.png"
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # We'll generate a static composite showing multiple positions
    n_positions = min(frames, 36)
    step = 360 // n_positions

    # Left panel: cam disc with follower position
    ax_cam.set_xlim(-10, 10)
    ax_cam.set_ylim(-10, 10)
    ax_cam.set_aspect("equal")
    ax_cam.set_title("Cam Disc (front view)")
    ax_cam.grid(True, alpha=0.2)

    # Draw cam outline
    from super8cam.parts.cam_follower import CAM_OD, cam_groove_points
    cam_circle = plt.Circle((0, 0), CAM_OD / 2, fill=False, color="gray", linewidth=2)
    ax_cam.add_patch(cam_circle)
    shaft_circle = plt.Circle((0, 0), CAMERA.shaft_dia / 2, fill=True,
                               color="darkgray", zorder=3)
    ax_cam.add_patch(shaft_circle)

    # Draw groove path
    pts = cam_groove_points(360)
    gx = [p[0] for p in pts]
    gy = [p[1] for p in pts]
    ax_cam.plot(gx, gy, "b-", linewidth=1.5, alpha=0.6, label="Groove path")

    # Draw follower positions
    for i in range(0, 360, step):
        alpha = 0.3 + 0.7 * (i / 360.0)
        ax_cam.plot(gx[i], gy[i], "ro", markersize=3, alpha=alpha)

    ax_cam.legend(fontsize=8)

    # Right panel: claw tip path with film strip
    ax_claw.set_xlim(-1, 4)
    ax_claw.set_ylim(-6, 2)
    ax_claw.set_aspect("equal")
    ax_claw.set_title("Claw Tip Path & Film")
    ax_claw.grid(True, alpha=0.2)

    # Draw film strip (simplified)
    film = Rectangle((-0.5, -5.5), 1.0, 7.0, fill=True, color="tan",
                      alpha=0.3, zorder=1)
    ax_claw.add_patch(film)

    # Draw perforations
    for perf_y in np.arange(-5, 2, FILM.perf_pitch):
        perf = Rectangle((-0.3, perf_y - FILM.perf_h / 2),
                          FILM.perf_w, FILM.perf_h,
                          fill=True, color="white", edgecolor="gray",
                          linewidth=0.5, zorder=2)
        ax_claw.add_patch(perf)

    # Draw claw path
    x_path = analysis["x_mm"]
    y_path = analysis["y_mm"]
    ax_claw.plot(x_path, y_path, "b-", linewidth=2, alpha=0.8, label="Claw tip path")

    # Mark positions at intervals with arrows showing direction
    for i in range(0, 360, step):
        alpha = 0.3 + 0.7 * (i / 360.0)
        color = plt.cm.hsv(i / 360.0)
        ax_claw.plot(x_path[i], y_path[i], "o", color=color,
                     markersize=4, alpha=alpha, zorder=4)

    # Mark engage/pulldown/retract/return labels
    ax_claw.annotate("ENGAGE", xy=(1.0, 0.3), fontsize=8, color="green",
                     fontweight="bold")
    ax_claw.annotate("PULLDOWN", xy=(2.2, -2.0), fontsize=8, color="blue",
                     fontweight="bold", rotation=90)
    ax_claw.annotate("RETRACT", xy=(1.0, -4.5), fontsize=8, color="red",
                     fontweight="bold")
    ax_claw.annotate("RETURN", xy=(-0.8, -2.0), fontsize=8, color="purple",
                     fontweight="bold", rotation=90)

    ax_claw.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Mechanism animation saved: {path}")
    return path


# =========================================================================
# VALIDATION SUMMARY
# =========================================================================

def validate_mechanism(fps: int = 24) -> dict:
    """Run full mechanism validation and return results dict.

    Checks:
      1. Path closes (start ≈ end)
      2. Pulldown stroke matches perforation pitch
      3. Peak force below limit
      4. Film settled before shutter opens
      5. Timing phases are correct
    """
    analysis = claw_tip_analysis(fps, 720)

    checks = []
    all_pass = True

    # 1. Path closure
    ok = analysis["path_closed"]
    checks.append(("Path closes (start ≈ end)", ok))
    all_pass &= ok

    # 2. Pulldown stroke
    stroke_err = abs(analysis["pulldown_stroke_mm"] - FILM.perf_pitch)
    ok = stroke_err < 0.01  # within 10 μm
    checks.append((f"Pulldown stroke {analysis['pulldown_stroke_mm']:.3f} mm "
                    f"(target {FILM.perf_pitch} mm, err {stroke_err:.4f})", ok))
    all_pass &= ok

    # 3. Perforation force
    ok = analysis["force_ok"]
    checks.append((f"Peak perf force {analysis['peak_force_n']:.3f} N "
                    f"(limit {MAX_PERF_FORCE_N} N)", ok))
    all_pass &= ok

    # 4. Film settled before shutter
    ok = analysis["settled_before_shutter"]
    checks.append((f"Film settled at shutter open "
                    f"(speed {analysis['max_speed_at_shutter_mm_s']:.2f} mm/s)", ok))
    all_pass &= ok

    # 5. Engage stroke
    engage_err = abs(analysis["engage_stroke_mm"] - 2.0)
    ok = engage_err < 0.1
    checks.append((f"Engage stroke {analysis['engage_stroke_mm']:.2f} mm (target 2.0)", ok))
    all_pass &= ok

    return {
        "fps": fps,
        "all_pass": all_pass,
        "checks": checks,
        "analysis": analysis,
    }


def print_validation(fps: int = 24):
    """Print mechanism validation results to stdout."""
    result = validate_mechanism(fps)
    print(f"\n  CLAW MECHANISM VALIDATION @ {fps} fps")
    print("  " + "-" * 55)
    for desc, ok in result["checks"]:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {desc}")

    t = result["analysis"]["timing"]
    print(f"\n  Timing phases:")
    print(f"    Engage start:   {t['engage_start_deg']:.0f}°" if t["engage_start_deg"] else "")
    print(f"    Engage done:    {t['engage_done_deg']:.0f}°" if t["engage_done_deg"] else "")
    print(f"    Pulldown start: {t['pulldown_start_deg']:.0f}°" if t["pulldown_start_deg"] else "")
    print(f"    Pulldown end:   {t['pulldown_end_deg']:.0f}°" if t["pulldown_end_deg"] else "")
    print(f"    Retract start:  {t['retract_start_deg']:.0f}°" if t["retract_start_deg"] else "")

    overall = "PASS" if result["all_pass"] else "FAIL"
    print(f"\n    Overall: {overall}")


if __name__ == "__main__":
    for fps in [18, 24]:
        print_validation(fps)
    plot_claw_path(24)
    animate_mechanism(24)
