#!/usr/bin/env python3
"""Super 8 Camera Pulldown Claw Mechanism Model

Models the claw as a scotch-yoke (eccentric cam) converting rotary main-shaft
motion into linear pulldown.  Computes the full motion profile (position,
velocity, acceleration) over one shaft revolution and checks forces against
Kodak perforation pull-strength limits.

Outputs:
  - Console summary for 18 fps and 24 fps
  - Matplotlib figure saved to super8_claw_plots.png
"""

import math
import numpy as np
from scipy.signal import argrelextrema
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
FRAME_ADVANCE = 4.234e-3          # m  (one Super 8 frame)
SHUTTER_ANGLE_DEG = 180           # degrees open
FRAME_RATES = [18, 24]            # fps

# Film friction drag inside cartridge
FRICTION_MIN = 0.1                # N
FRICTION_MAX = 0.3                # N
FRICTION_NOMINAL = 0.2            # N  (mid-estimate for calculations)

# Kodak perforation pull strength (must not exceed)
PERF_PULL_STRENGTH = 1.5          # N

# Claw tip geometry (hardened steel)
CLAW_WIDTH = 0.5e-3               # m
CLAW_THICKNESS = 0.3e-3           # m
CLAW_CROSS_SECTION = CLAW_WIDTH * CLAW_THICKNESS  # m^2

# Film strip effective mass moved during pulldown (film in gate + feed path)
FILM_MASS = 0.6e-3                # kg  (~0.6 g of film in motion)

# Yield strength of hardened tool steel (approximate)
STEEL_YIELD = 1500e6              # Pa  (1500 MPa)

# Scotch-yoke geometry: crank radius chosen so peak-to-peak stroke equals
# the frame advance distance.  The yoke converts crank rotation into pure
# sinusoidal linear motion along the pulldown axis.
CRANK_RADIUS = FRAME_ADVANCE / 2  # m  (stroke = 2·r)

# Angular resolution
N_POINTS = 3600  # 0.1 degree steps


# ---------------------------------------------------------------------------
# Mechanism model
# ---------------------------------------------------------------------------

def scotch_yoke_profiles(fps, n=N_POINTS):
    """Return arrays of shaft angle (deg), position, velocity, acceleration.

    The scotch-yoke produces sinusoidal displacement:
        y(theta) = r·cos(theta)

    Convention: theta = 0  -> claw at top (film seated, shutter about to open)
                theta = 180 -> shutter closes, pulldown begins
                theta = 360 -> claw returns to top, next frame seated

    With a 180-degree shutter the mapping is:
        Shutter open:   0 <= theta < 180   (claw disengaged / returning)
        Shutter closed: 180 <= theta < 360 (claw engaged, pulling film down)

    We phase the cosine so that the downward stroke (decreasing y) happens
    during the closed phase.  Setting:
        y(theta) = -r·cos(theta)
    gives  y(0)=−r (top), y(180)=+r (bottom of stroke, mid-pulldown isn't
    quite right).  Instead we want the full downward travel during 180-360.

    Better mapping — use a shifted cosine so that:
        y(180°) = 0        (start of pulldown)
        y(360°) = −4.234mm (end of pulldown, one frame advanced)

    For a scotch-yoke the displacement over 360° is inherently symmetric.
    The pulldown (negative-going half-stroke) naturally spans 180° of crank
    rotation.  We align that half with the shutter-closed phase.

    Phase choice:
        y(theta) = r·cos(theta)
        At theta=0:   y = +r  (claw at top, film seated, shutter opens)
        At theta=180: y = -r  (claw at bottom, pulldown done, before return)

    Shutter open  : 0–180°  -> claw travels +r to −r  (BUT shutter is open,
                     claw must NOT pull film here — claw is retracted laterally
                     by a cam and performs a free return stroke.)
    Shutter closed: 180–360° -> claw travels −r to +r (upward — wrong sense)

    We need the *downward* (film-advancing) stroke during shutter-closed.
    Flip sign:
        y(theta) = -r·cos(theta)
        0–180° (open):   y goes from −r to +r  (return stroke, claw retracted)
        180–360° (closed): y goes from +r to −r (pulldown, claw engaged)

    Displacement relative to pulldown start:
        y_pull(theta) = y(theta) - y(180°) = -r·cos(theta) - r
                      = -r·(1 + cos(theta))

    At theta=180: y_pull = 0  (start)
    At theta=360: y_pull = -r·(1+1) = -2r = -FRAME_ADVANCE  ✓
    """
    omega = 2 * math.pi * fps  # rad/s  (shaft angular velocity)
    theta = np.linspace(0, 2 * math.pi, n, endpoint=False)
    theta_deg = np.degrees(theta)

    r = CRANK_RADIUS

    # Absolute claw position (mm) — zero at pulldown start (theta=180°)
    position = -r * (1 + np.cos(theta))  # m

    # Velocity  dy/dt = dy/dtheta · dtheta/dt = r·sin(theta)·omega
    velocity = r * np.sin(theta) * omega  # m/s

    # Acceleration  d²y/dt² = r·cos(theta)·omega²
    acceleration = r * np.cos(theta) * omega**2  # m/s²

    return theta_deg, position, velocity, acceleration, omega


def analyze(fps):
    """Run full analysis for a given frame rate. Returns a results dict."""
    theta_deg, pos, vel, acc, omega = scotch_yoke_profiles(fps)

    # Identify closed-phase indices (180° to 360°)
    closed_mask = (theta_deg >= 180) & (theta_deg < 360)

    # Peak values during pulldown (closed phase only)
    peak_vel = np.max(np.abs(vel[closed_mask]))
    peak_acc = np.max(np.abs(acc[closed_mask]))

    # Inertial force on film during peak acceleration
    inertial_force = FILM_MASS * peak_acc  # N

    # Total peak force on claw tip = inertial + friction
    total_peak_force = inertial_force + FRICTION_MAX  # worst-case friction

    # Bending stress on claw tip (cantilever approximation)
    # The claw engages a perforation; model as a short cantilever loaded at
    # the tip.  Engagement depth ~0.3mm, loaded by total_peak_force.
    engagement_depth = 0.3e-3  # m  (how far claw pokes through perf)
    # sigma = M·c / I,  M = F·L,  c = t/2,  I = w·t³/12
    moment = total_peak_force * engagement_depth
    c = CLAW_THICKNESS / 2
    I = CLAW_WIDTH * CLAW_THICKNESS**3 / 12
    bending_stress = moment * c / I  # Pa

    # Perforation safety
    perf_violation = total_peak_force > PERF_PULL_STRENGTH

    # Timing
    frame_period = 1.0 / fps
    closed_time = frame_period * (360 - SHUTTER_ANGLE_DEG) / 360
    # In the scotch-yoke the pulldown uses the full closed phase (180°).
    # Dwell occurs at the bottom-dead-centre region where velocity ≈ 0.
    # Define dwell as the angular range where |velocity| < 5% of peak.
    dwell_threshold = 0.05 * peak_vel
    dwell_mask = closed_mask & (np.abs(vel) < dwell_threshold)
    dwell_angle = np.sum(dwell_mask) * (360.0 / N_POINTS)
    dwell_time = (dwell_angle / 360.0) * frame_period

    return {
        "fps": fps,
        "omega_rad_s": omega,
        "frame_period_ms": frame_period * 1e3,
        "closed_time_ms": closed_time * 1e3,
        "peak_velocity_mm_s": peak_vel * 1e3,
        "peak_accel_m_s2": peak_acc,
        "inertial_force_N": inertial_force,
        "friction_force_N": FRICTION_NOMINAL,
        "total_peak_force_N": total_peak_force,
        "bending_stress_MPa": bending_stress / 1e6,
        "steel_yield_MPa": STEEL_YIELD / 1e6,
        "stress_safety_factor": STEEL_YIELD / bending_stress,
        "dwell_angle_deg": dwell_angle,
        "dwell_time_ms": dwell_time * 1e3,
        "perf_violation": perf_violation,
        "theta_deg": theta_deg,
        "position_mm": pos * 1e3,
        "velocity_mm_s": vel * 1e3,
        "acceleration_m_s2": acc,
    }


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_report(results_list):
    sep = "=" * 68
    print(sep)
    print("  SUPER 8 PULLDOWN CLAW MECHANISM ANALYSIS")
    print(sep)
    print()
    print(f"  Mechanism type:        Scotch-yoke (eccentric cam)")
    print(f"  Crank radius:          {CRANK_RADIUS*1e3:.3f} mm")
    print(f"  Frame advance (stroke):{FRAME_ADVANCE*1e3:.3f} mm")
    print(f"  Shutter opening angle: {SHUTTER_ANGLE_DEG} deg")
    print(f"  Film mass in motion:   {FILM_MASS*1e3:.1f} g")
    print(f"  Cartridge friction:    {FRICTION_MIN}-{FRICTION_MAX} N "
          f"(nominal {FRICTION_NOMINAL} N)")
    print(f"  Claw tip:              {CLAW_WIDTH*1e3:.1f} x "
          f"{CLAW_THICKNESS*1e3:.1f} mm hardened steel")
    print(f"  Perforation limit:     {PERF_PULL_STRENGTH} N (Kodak spec)")
    print()

    header = (
        f"  {'Parameter':<36}"
        + "".join(f"  {'@'+str(r['fps'])+' fps':>12}" for r in results_list)
    )
    print(header)
    print("  " + "-" * (36 + 14 * len(results_list)))

    rows = [
        ("Shaft angular velocity",   "omega_rad_s",        "rad/s", 1),
        ("Frame period",             "frame_period_ms",     "ms",    2),
        ("Shutter-closed time",      "closed_time_ms",      "ms",    2),
        ("Peak claw velocity",       "peak_velocity_mm_s",  "mm/s",  1),
        ("Peak claw acceleration",   "peak_accel_m_s2",     "m/s^2", 1),
        ("Inertial force on film",   "inertial_force_N",    "N",     3),
        ("Friction force (nominal)",  "friction_force_N",   "N",     1),
        ("Total peak force on claw", "total_peak_force_N",  "N",     3),
        ("Claw bending stress",      "bending_stress_MPa",  "MPa",   1),
        ("Steel yield strength",     "steel_yield_MPa",     "MPa",   0),
        ("Stress safety factor",     "stress_safety_factor", "x",    1),
        ("Dwell angle (|v|<5%peak)", "dwell_angle_deg",     "deg",   1),
        ("Dwell time",               "dwell_time_ms",       "ms",    2),
    ]

    for label, key, unit, dec in rows:
        vals = "".join(
            f"  {r[key]:>{12-len(unit)-1}.{dec}f} {unit}" for r in results_list
        )
        print(f"  {label:<36}{vals}")

    print()

    # Violations
    any_violation = False
    for r in results_list:
        if r["perf_violation"]:
            any_violation = True
            print(f"  *** VIOLATION @ {r['fps']} fps: Peak claw force "
                  f"{r['total_peak_force_N']:.3f} N EXCEEDS perforation "
                  f"pull strength {PERF_PULL_STRENGTH} N ***")

    if not any_violation:
        print("  All frame rates within perforation safety limits.")

    print()
    print(sep)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_profiles(results_list, filename="super8_claw_plots.png"):
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    fig.suptitle("Super 8 Pulldown Claw – Scotch-Yoke Motion Profiles",
                 fontsize=13, fontweight="bold")

    colors = {18: "#2563eb", 24: "#dc2626"}

    for r in results_list:
        fps = r["fps"]
        theta = r["theta_deg"]
        c = colors[fps]
        lbl = f"{fps} fps"

        axes[0].plot(theta, r["position_mm"], color=c, linewidth=1.4, label=lbl)
        axes[1].plot(theta, r["velocity_mm_s"], color=c, linewidth=1.4, label=lbl)
        axes[2].plot(theta, r["acceleration_m_s2"], color=c, linewidth=1.4, label=lbl)

    # Shade shutter-closed region on every subplot
    for ax in axes:
        ax.axvspan(180, 360, color="#fee2e2", alpha=0.45, zorder=0,
                   label="_closed")
        ax.axvline(180, color="grey", linestyle="--", linewidth=0.7)
        ax.axvline(360, color="grey", linestyle="--", linewidth=0.7)
        ax.set_xlim(0, 360)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=9)

    axes[0].set_ylabel("Claw position (mm)")
    axes[0].annotate("Shutter OPEN\n(claw retracted,\nreturn stroke)",
                     xy=(90, 0), fontsize=8, ha="center", color="grey")
    axes[0].annotate("Shutter CLOSED\n(claw engaged,\npulldown)",
                     xy=(270, 0), fontsize=8, ha="center", color="grey")

    axes[1].set_ylabel("Claw velocity (mm/s)")
    axes[1].axhline(0, color="black", linewidth=0.5)

    axes[2].set_ylabel("Claw acceleration (m/s²)")
    axes[2].axhline(0, color="black", linewidth=0.5)
    axes[2].set_xlabel("Main shaft angle (degrees)")

    # Mark perforation force limit as equivalent acceleration
    perf_acc_limit = (PERF_PULL_STRENGTH - FRICTION_MAX) / FILM_MASS
    axes[2].axhline(perf_acc_limit, color="#f59e0b", linestyle="-.",
                    linewidth=1.2, label=f"Perf limit ({perf_acc_limit:.0f} m/s²)")
    axes[2].axhline(-perf_acc_limit, color="#f59e0b", linestyle="-.",
                    linewidth=1.2)
    axes[2].legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    fig.savefig(filename, dpi=150)
    print(f"\n  Plot saved to {filename}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    results_list = [analyze(fps) for fps in FRAME_RATES]
    print_report(results_list)
    plot_profiles(results_list)


if __name__ == "__main__":
    main()
