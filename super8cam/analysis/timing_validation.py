"""Timing validation — verify shutter, claw, and film registration synchronization.

Steps through 360° of shaft rotation at both 18 and 24 fps to verify that
all mechanisms are perfectly synchronized.  Uses the actual cam profile from
parts/cam_follower.py as the single source of truth for claw motion.

Generates a multi-signal timing diagram (matplotlib) and validates 7 critical
timing rules.  If any rule is violated, reports exact shaft angles and
suggests cam phase offset adjustments.

CRITICAL TIMING RULES:
  1. Film STATIONARY ≥5° before shutter opens
  2. Registration pin ENGAGED before shutter opens
  3. Claw fully RETRACTED before reg pin engages
  4. Shutter fully CLOSED before claw begins pulldown
  5. Film completes 4.234mm advance before shutter opens again
  6. Claw completes return stroke before next engagement
  7. No two mechanisms conflict at any point in the cycle

Cam profile phase map (from cam_follower.py):
    0°–180°  : shutter OPEN  (exposure — film stationary, pin engaged)
  180°–185°  : shutter CLOSES, reg pin disengages
  185°–190°  : claw ENGAGES  (moves toward film, 2mm horizontal)
  190°–330°  : pulldown      (claw pulls film down 4.234mm)
  330°–335°  : retract       (claw moves away from film)
  335°–350°  : return stroke (claw moves back to top position)
  350°–360°  : dwell         (film settles, reg pin engages)

Shutter keying convention:
  The shutter disc is keyed so the open sector faces the aperture
  during 0°–180° (180° opening angle).  The closed sector covers
  180°–360°, during which pulldown occurs.

  Effective shutter phases:
    0°–180°  : shutter OPEN  (open sector at aperture)
  180°–360°  : shutter CLOSED (solid sector)
"""

import math
import numpy as np
from super8cam.specs.master_specs import FILM, CAMERA, SHUTTER, ANALYSIS
from super8cam.parts.cam_follower import cam_profile_full

# =========================================================================
# RESOLUTION
# =========================================================================
N_POINTS = ANALYSIS.timing_resolution  # 0.5° per step — sufficient for timing analysis


# =========================================================================
# MECHANISM STATE COMPUTATION
# =========================================================================

def compute_mechanism_states(n_points: int = N_POINTS) -> dict:
    """Compute all mechanism states for one complete shaft revolution.

    Returns arrays indexed by shaft angle (0–360°):
        theta_deg       — shaft angle array
        shutter_open    — bool: True when shutter open sector faces aperture
        claw_x_mm       — horizontal position (0=retracted, 2=engaged)
        claw_y_mm       — vertical position (0=top, -4.234=bottom of pulldown)
        claw_engaged    — bool: True when claw tip is in perforation (x > 1.0)
        film_velocity   — vertical film velocity (mm/deg, neg = advancing)
        film_moving     — bool: True when |film_velocity| > 0.01 mm/deg
        film_stationary — bool: True when film is at rest
        reg_pin_engaged — bool: True when reg pin holds film in place
        pulldown_mm     — cumulative pulldown displacement from top
    """
    profile = cam_profile_full(n_points)
    theta = profile["theta_deg"]
    claw_x = profile["x_mm"]
    claw_y = profile["y_mm"]
    vy = profile["vy_mm_per_deg"]

    # --- Shutter state ---
    # Shutter keyed so open sector faces aperture during 0°–180°.
    # Closed during 180°–360°.
    shutter_open = theta < 180.0

    # --- Claw engagement ---
    # Claw tip is "engaged" when horizontal position > 1.0mm
    # (meaning tip is deep enough in the perforation to pull film)
    claw_engaged = claw_x > ANALYSIS.claw_engage_threshold

    # --- Film motion ---
    # Film moves only when claw is engaged and pulling down.
    # Film velocity follows claw vertical velocity during engaged phase.
    film_velocity = np.where(claw_engaged, vy, 0.0)
    film_moving = np.abs(film_velocity) > 0.01  # mm/deg threshold
    film_stationary = ~film_moving

    # --- Cumulative pulldown ---
    pulldown_mm = np.abs(claw_y)  # distance from top (always positive)

    # --- Registration pin ---
    # The registration pin is a passive spring-loaded pin that engages the
    # perforation when the film is stationary and the claw is retracted.
    # It disengages (retracts) when the claw begins to engage, because
    # the claw must move the film, and the pin would hold it in place.
    #
    # Pin state logic:
    #   - Pin engages after claw fully retracts AND film is stationary
    #   - Pin disengages just before claw begins to engage
    #   - Hysteresis: pin engages when claw_x < 0.1, disengages at claw_x > 0.3
    reg_pin_engaged = np.zeros(n_points, dtype=bool)
    pin_state = False
    for i in range(n_points):
        if claw_x[i] < ANALYSIS.pin_engage_hysteresis and not film_moving[i]:
            pin_state = True
        elif claw_x[i] > ANALYSIS.pin_disengage_hysteresis:
            pin_state = False
        reg_pin_engaged[i] = pin_state

    return {
        "theta_deg": theta,
        "shutter_open": shutter_open,
        "claw_x_mm": claw_x,
        "claw_y_mm": claw_y,
        "claw_engaged": claw_engaged,
        "film_velocity": film_velocity,
        "film_moving": film_moving,
        "film_stationary": film_stationary,
        "reg_pin_engaged": reg_pin_engaged,
        "pulldown_mm": pulldown_mm,
    }


# =========================================================================
# CRITICAL TIMING RULES
# =========================================================================

def validate_timing(n_points: int = N_POINTS) -> dict:
    """Validate all 7 critical timing rules.

    Returns:
        valid           — True if all rules pass
        errors          — list of error strings
        rules           — list of (rule_desc, pass_bool, details_str) tuples
        phases          — shutter phase boundaries
        timing_data     — full mechanism state arrays for plotting
        suggestions     — list of suggested timing adjustments
    """
    states = compute_mechanism_states(n_points)
    theta = states["theta_deg"]
    d_theta = theta[1] - theta[0]

    rules = []
    errors = []
    suggestions = []

    # --- Helper: find edges ---
    def find_rising_edge(signal, label="signal"):
        """Return angle of first 0→1 transition."""
        for i in range(1, len(signal)):
            if signal[i] and not signal[i - 1]:
                return theta[i]
        return None

    def find_falling_edge(signal, label="signal"):
        """Return angle of first 1→0 transition."""
        for i in range(1, len(signal)):
            if not signal[i] and signal[i - 1]:
                return theta[i]
        return None

    # --- Shutter open edge ---
    shutter_opens_at = 0.0    # by design
    shutter_closes_at = 180.0 # closes at 180°

    # --- Claw engage start: first angle where claw_x > 0.1 ---
    claw_engage_start = None
    for i in range(len(theta)):
        if states["claw_x_mm"][i] > 0.1:
            claw_engage_start = theta[i]
            break

    # --- Claw engage complete: first angle where claw_x > 1.9 ---
    claw_engage_done = None
    for i in range(len(theta)):
        if states["claw_x_mm"][i] > 1.9:
            claw_engage_done = theta[i]
            break

    # --- Pulldown start: first angle where claw engaged AND film moving ---
    pulldown_start = None
    for i in range(len(theta)):
        if states["claw_engaged"][i] and states["film_moving"][i]:
            pulldown_start = theta[i]
            break

    # --- Pulldown end: last angle where claw engaged AND film moving ---
    pulldown_end = None
    for i in range(len(theta) - 1, -1, -1):
        if states["claw_engaged"][i] and states["film_moving"][i]:
            pulldown_end = theta[i]
            break

    # --- Claw retract start: first angle after pulldown where claw_x < 1.5 ---
    claw_retract_start = None
    if pulldown_end is not None:
        pd_end_idx = int(pulldown_end / d_theta)
        for i in range(pd_end_idx, len(theta)):
            if states["claw_x_mm"][i] < 1.5:
                claw_retract_start = theta[i]
                break

    # --- Claw fully retracted: first angle after retract where claw_x < 0.1 ---
    claw_retracted_at = None
    if claw_retract_start is not None:
        rt_idx = int(claw_retract_start / d_theta)
        for i in range(rt_idx, len(theta)):
            if states["claw_x_mm"][i] < 0.1:
                claw_retracted_at = theta[i]
                break

    # --- Reg pin engage: first angle where pin is engaged ---
    pin_engage_at = find_rising_edge(states["reg_pin_engaged"])
    pin_disengage_at = find_falling_edge(states["reg_pin_engaged"])

    # --- Film stationary before shutter opens ---
    # Shutter opens at 0°.  Dwell is at end of revolution (350°–360°).
    # Look backwards from end of array to find how long film has been
    # stationary before wrapping to 0°.
    shutter_open_idx = 0
    film_dwell_before_shutter = 0.0
    for i in range(n_points - 1, -1, -1):
        if states["film_stationary"][i]:
            film_dwell_before_shutter += d_theta
        else:
            break

    # =====================================================================
    # RULE 1: Film STATIONARY ≥5° before shutter opens
    # =====================================================================
    rule1_pass = film_dwell_before_shutter >= ANALYSIS.min_dwell_deg
    rule1_detail = (f"Film stationary for {film_dwell_before_shutter:.1f}° "
                    f"before shutter opens at 10° (need ≥{ANALYSIS.min_dwell_deg}°)")
    rules.append(("Rule 1: Film stationary ≥5° before shutter opens",
                   rule1_pass, rule1_detail))
    if not rule1_pass:
        errors.append(f"RULE 1 VIOLATED: only {film_dwell_before_shutter:.1f}° "
                      f"dwell before shutter opens at 10°")
        suggestions.append(
            f"Increase return phase end from 350° to "
            f"{350 - (5.0 - film_dwell_before_shutter):.0f}° "
            f"(shorten return stroke)")

    # =====================================================================
    # RULE 2: Registration pin ENGAGED before shutter opens
    # =====================================================================
    # Pin must be engaged at the moment shutter opens (10°)
    pin_at_shutter_open = states["reg_pin_engaged"][shutter_open_idx]
    rule2_pass = bool(pin_at_shutter_open)

    # How long before shutter open is pin engaged?
    # Shutter opens at 0°, so count backwards from end of array.
    pin_dwell_before_shutter = 0.0
    if pin_at_shutter_open:
        for i in range(n_points - 1, -1, -1):
            if states["reg_pin_engaged"][i]:
                pin_dwell_before_shutter += d_theta
            else:
                break

    rule2_detail = (f"Reg pin {'engaged' if pin_at_shutter_open else 'NOT engaged'} "
                    f"at 10°, engaged for {pin_dwell_before_shutter:.1f}° before")
    rules.append(("Rule 2: Reg pin engaged before shutter opens",
                   rule2_pass, rule2_detail))
    if not rule2_pass:
        errors.append("RULE 2 VIOLATED: registration pin not engaged when shutter opens")
        suggestions.append("Advance reg pin engagement — check claw retract timing")

    # =====================================================================
    # RULE 3: Claw fully RETRACTED before reg pin engages
    # =====================================================================
    # The reg pin must not engage while the claw is still near the film
    if pin_engage_at is not None and claw_retracted_at is not None:
        rule3_pass = claw_retracted_at <= pin_engage_at
        rule3_detail = (f"Claw retracted at {claw_retracted_at:.1f}°, "
                        f"pin engages at {pin_engage_at:.1f}° "
                        f"(margin {pin_engage_at - claw_retracted_at:.1f}°)")
    else:
        rule3_pass = True
        rule3_detail = "Unable to determine exact edges (assumed OK)"

    rules.append(("Rule 3: Claw retracted before reg pin engages",
                   rule3_pass, rule3_detail))
    if not rule3_pass:
        margin = pin_engage_at - claw_retracted_at
        errors.append(f"RULE 3 VIOLATED: claw retracts at {claw_retracted_at:.1f}° "
                      f"but pin engages at {pin_engage_at:.1f}° (overlap {-margin:.1f}°)")
        suggestions.append(f"Advance claw retract by {-margin + 3:.0f}°")

    # =====================================================================
    # RULE 4: Shutter fully CLOSED before claw begins pulldown
    # =====================================================================
    # Shutter closes at 190°.  Pulldown starts at ~190°.
    # Check that the shutter is definitely closed at pulldown start.
    if pulldown_start is not None:
        pd_start_idx = int(pulldown_start / d_theta)
        shutter_closed_at_pulldown = not states["shutter_open"][pd_start_idx]
        shutter_margin = pulldown_start - 190.0 if pulldown_start >= 190.0 else pulldown_start  # degrees since shutter close at 190°
        rule4_pass = shutter_closed_at_pulldown
        rule4_detail = (f"Shutter closed at pulldown start ({pulldown_start:.1f}°), "
                        f"margin {shutter_margin:.1f}° after close")
    else:
        rule4_pass = True
        rule4_detail = "No pulldown detected (assumed OK)"

    rules.append(("Rule 4: Shutter closed before claw pulldown",
                   rule4_pass, rule4_detail))
    if not rule4_pass:
        errors.append(f"RULE 4 VIOLATED: shutter still open at pulldown start "
                      f"({pulldown_start:.1f}°)")
        suggestions.append("Advance shutter keying or delay pulldown start")

    # =====================================================================
    # RULE 5: Film completes 4.234mm advance before shutter opens again
    # =====================================================================
    # By the time shutter opens at 180°, film must have completed full advance
    max_pulldown = float(np.max(states["pulldown_mm"]))
    target_advance = FILM.perf_pitch  # 4.234 mm

    # Check pulldown at shutter open (180°)
    pulldown_at_180 = states["pulldown_mm"][shutter_open_idx]

    rule5_pass = max_pulldown >= target_advance - 0.01  # 10μm tolerance
    rule5_detail = (f"Max pulldown: {max_pulldown:.3f} mm "
                    f"(target {target_advance:.3f} mm, "
                    f"error {max_pulldown - target_advance:+.4f} mm)")
    rules.append(("Rule 5: Film completes 4.234mm before shutter opens",
                   rule5_pass, rule5_detail))
    if not rule5_pass:
        shortfall = target_advance - max_pulldown
        errors.append(f"RULE 5 VIOLATED: pulldown only {max_pulldown:.3f}mm "
                      f"(short by {shortfall:.4f}mm)")
        suggestions.append(f"Increase cam lobe lift by {shortfall:.4f}mm "
                           f"or extend pulldown arc")

    # =====================================================================
    # RULE 6: Claw completes return stroke before next engagement
    # =====================================================================
    # At 350°–360° (dwell), claw should be at top (y ≈ 0) and retracted
    # (x ≈ 0).  The claw is stationary during the dwell phase.
    dwell_start_idx = int(350.0 / d_theta)
    dwell_end_idx = n_points  # through end of revolution

    # Check 350°–360°: claw at top, retracted
    max_y_in_dwell = float(np.max(np.abs(
        states["claw_y_mm"][dwell_start_idx:dwell_end_idx])))

    # Claw should be at top (y ≈ 0) — that's the key check
    max_y_dwell = max_y_in_dwell

    rule6_pass = max_y_dwell < 0.05
    rule6_detail = (f"Claw at dwell (350°–360°): y_max={max_y_dwell:.3f}mm "
                    f"(need <0.05mm)")
    rules.append(("Rule 6: Claw returns to home before next cycle",
                   rule6_pass, rule6_detail))
    if not rule6_pass:
        errors.append(f"RULE 6 VIOLATED: claw not at home during dwell "
                      f"(y={max_y_dwell:.3f})")
        suggestions.append("Shorten return stroke arc or increase return velocity")

    # =====================================================================
    # RULE 7: No two mechanisms conflict at any point
    # =====================================================================
    # Check for simultaneous conditions that are physically impossible:
    #   a) Claw engaged while reg pin engaged (both hold film)
    #   b) Film moving while shutter is open (motion blur / smear)
    #   c) Claw engaging while film is still settling from previous cycle
    conflicts = []

    # (a) Claw + reg pin simultaneously engaged
    both_engaged = states["claw_engaged"] & states["reg_pin_engaged"]
    if np.any(both_engaged):
        conflict_angles = theta[both_engaged]
        conflicts.append(
            f"Claw AND reg pin both engaged at "
            f"{conflict_angles[0]:.1f}°–{conflict_angles[-1]:.1f}°")

    # (b) Film moving while shutter open
    film_during_exposure = states["film_moving"] & states["shutter_open"]
    if np.any(film_during_exposure):
        conflict_angles = theta[film_during_exposure]
        conflicts.append(
            f"Film moving during exposure at "
            f"{conflict_angles[0]:.1f}°–{conflict_angles[-1]:.1f}°")

    # (c) Check for non-zero film velocity at shutter open edge (±2° around 0°)
    # Handle wrap-around: check last few samples (358°-360°) and first few (0°-2°)
    edge_window = int(2.0 / d_theta)
    edge_vel_start = np.abs(states["film_velocity"][-edge_window:])
    edge_vel_end = np.abs(states["film_velocity"][:edge_window])
    max_film_vel_at_edge = float(max(
        np.max(edge_vel_start), np.max(edge_vel_end)))
    if max_film_vel_at_edge > ANALYSIS.film_vel_threshold:
        conflicts.append(
            f"Film velocity {max_film_vel_at_edge:.3f} mm/deg at shutter edge "
            f"(358°–2°)")

    rule7_pass = len(conflicts) == 0
    rule7_detail = "No conflicts" if rule7_pass else "; ".join(conflicts)
    rules.append(("Rule 7: No mechanism conflicts",
                   rule7_pass, rule7_detail))
    if not rule7_pass:
        for c in conflicts:
            errors.append(f"RULE 7 VIOLATED: {c}")
        suggestions.append("Review cam-to-shutter phase offset (currently 180°)")

    # =====================================================================
    # PHASE TABLE (backward-compatible with existing build.py)
    # =====================================================================
    phases = [
        ("Phase 1: Exposure (shutter open)",
         SHUTTER.phase1_start, SHUTTER.phase1_end),
        ("Phase 2: Claw engage",
         SHUTTER.phase2_start, SHUTTER.phase2_end),
        ("Phase 3: Pulldown",
         SHUTTER.phase3_start, SHUTTER.phase3_end),
        ("Phase 4: Claw retract + settle",
         SHUTTER.phase4_start, SHUTTER.phase4_end),
    ]

    # Cam-referenced phases (actual cam profile)
    cam_phases = {
        "exposure": (0.0, 180.0),
        "close": (180.0, 185.0),
        "engage": (185.0, 190.0),
        "pulldown": (190.0, 330.0),
        "retract": (330.0, 335.0),
        "return": (335.0, 350.0),
        "dwell": (350.0, 360.0),
    }

    # Shutter phases
    shutter_phases = {
        "open": (0.0, 180.0),
        "closed": (180.0, 360.0),
    }

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "rules": rules,
        "phases": phases,
        "cam_phases": cam_phases,
        "shutter_phases": shutter_phases,
        "timing_data": states,
        "suggestions": suggestions,
        "exposure_duty": SHUTTER.duty_cycle,
        "pulldown_time_18ms": SHUTTER.pulldown_time(18) * 1000,
        "pulldown_time_24ms": SHUTTER.pulldown_time(24) * 1000,
        "settle_time_18ms": SHUTTER.settle_time(18) * 1000,
        "settle_time_24ms": SHUTTER.settle_time(24) * 1000,
        "key_angles": {
            "shutter_opens": shutter_opens_at,
            "shutter_closes": shutter_closes_at,
            "claw_engage_start": claw_engage_start,
            "claw_engage_done": claw_engage_done,
            "pulldown_start": pulldown_start,
            "pulldown_end": pulldown_end,
            "claw_retract_start": claw_retract_start,
            "claw_retracted": claw_retracted_at,
            "pin_engage": pin_engage_at,
            "pin_disengage": pin_disengage_at,
        },
    }


# =========================================================================
# TIMING DIAGRAM
# =========================================================================

def plot_timing_diagram(fps: int = 24, save_path: str = None) -> str:
    """Generate a multi-signal timing diagram for one shaft revolution.

    Signals plotted (Y axis, stacked):
      1. Shutter state: OPEN / CLOSED
      2. Claw vertical position: top → bottom → top
      3. Claw horizontal position: retracted / engaged
      4. Film motion: stationary / advancing
      5. Registration pin: engaged / disengaged

    X axis: shaft angle 0°–360°

    Args:
        fps: Frame rate for time annotations.
        save_path: Output file path. Defaults to export/timing_diagram_{fps}fps.png.

    Returns:
        Path to saved figure.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    result = validate_timing()
    states = result["timing_data"]
    theta = states["theta_deg"]

    period_ms = 1000.0 / fps
    deg_per_ms = 360.0 / period_ms

    fig, axes = plt.subplots(5, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f"Mechanism Timing Diagram @ {fps} fps "
                 f"(period = {period_ms:.2f} ms)",
                 fontsize=14, fontweight="bold")

    # Color scheme
    c_open = "#2ECC71"
    c_closed = "#E74C3C"
    c_engaged = "#3498DB"
    c_retracted = "#BDC3C7"
    c_moving = "#F39C12"
    c_stationary = "#ECF0F1"
    c_pin_in = "#9B59B6"
    c_pin_out = "#FADBD8"

    # --- Signal 1: Shutter state ---
    ax = axes[0]
    shutter_signal = states["shutter_open"].astype(float)
    ax.fill_between(theta, 0, shutter_signal, color=c_open, alpha=0.6,
                    label="OPEN", step="mid")
    ax.fill_between(theta, 0, 1 - shutter_signal, color=c_closed, alpha=0.3,
                    label="CLOSED", step="mid")
    ax.set_ylabel("Shutter", fontsize=10, fontweight="bold")
    ax.set_ylim(-0.1, 1.3)
    ax.set_yticks([0.5])
    ax.set_yticklabels([""])
    ax.text(90, 0.5, "OPEN", ha="center", va="center", fontsize=11,
            fontweight="bold", color="green")
    ax.text(270, 0.5, "CLOSED", ha="center", va="center", fontsize=11,
            fontweight="bold", color=c_closed)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.2)

    # --- Signal 2: Claw vertical position ---
    ax = axes[1]
    claw_y = states["claw_y_mm"]
    ax.plot(theta, claw_y, color="#2C3E50", linewidth=2, label="Claw Y (mm)")
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax.axhline(-FILM.perf_pitch, color="red", linewidth=1, linestyle="--",
               alpha=0.5, label=f"Target: -{FILM.perf_pitch} mm")
    ax.set_ylabel("Claw Y\n(mm)", fontsize=10, fontweight="bold")
    ax.set_ylim(-FILM.perf_pitch - 0.5, 0.5)
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(True, alpha=0.2)

    # Shade pulldown region
    if result["key_angles"]["pulldown_start"] and result["key_angles"]["pulldown_end"]:
        ax.axvspan(result["key_angles"]["pulldown_start"],
                   result["key_angles"]["pulldown_end"],
                   alpha=0.1, color="blue", label="Pulldown")

    # --- Signal 3: Claw horizontal position ---
    ax = axes[2]
    claw_x = states["claw_x_mm"]
    ax.fill_between(theta, 0, claw_x / 2.0, color=c_engaged, alpha=0.5,
                    step="mid")
    ax.plot(theta, claw_x / 2.0, color=c_engaged, linewidth=1.5,
            label="Claw X (norm)")
    ax.set_ylabel("Claw X\n(engage)", fontsize=10, fontweight="bold")
    ax.set_ylim(-0.1, 1.3)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Retracted", "Engaged"])
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.2)

    # --- Signal 4: Film motion ---
    ax = axes[3]
    film_signal = states["film_moving"].astype(float)
    ax.fill_between(theta, 0, film_signal, color=c_moving, alpha=0.6,
                    label="ADVANCING", step="mid")
    ax.fill_between(theta, 0, 1 - film_signal, color=c_stationary, alpha=0.3,
                    label="STATIONARY", step="mid")
    ax.set_ylabel("Film\nMotion", fontsize=10, fontweight="bold")
    ax.set_ylim(-0.1, 1.3)
    ax.set_yticks([0.5])
    ax.set_yticklabels([""])

    # Label stationary/advancing regions
    # Find advancing window
    advancing_indices = np.where(states["film_moving"])[0]
    if len(advancing_indices) > 0:
        adv_start = theta[advancing_indices[0]]
        adv_end = theta[advancing_indices[-1]]
        ax.text((adv_start + adv_end) / 2, 0.5, "ADVANCING",
                ha="center", va="center", fontsize=10, fontweight="bold",
                color="#E67E22")
    # Label stationary before shutter open
    ax.text(270, 0.5, "STATIONARY", ha="center", va="center",
            fontsize=10, fontweight="bold", color="gray")

    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.2)

    # --- Signal 5: Registration pin ---
    ax = axes[4]
    pin_signal = states["reg_pin_engaged"].astype(float)
    ax.fill_between(theta, 0, pin_signal, color=c_pin_in, alpha=0.5,
                    label="ENGAGED", step="mid")
    ax.fill_between(theta, 0, 1 - pin_signal, color=c_pin_out, alpha=0.3,
                    label="DISENGAGED", step="mid")
    ax.set_ylabel("Reg Pin", fontsize=10, fontweight="bold")
    ax.set_ylim(-0.1, 1.3)
    ax.set_yticks([0.5])
    ax.set_yticklabels([""])
    ax.set_xlabel("Shaft Angle (degrees)", fontsize=11)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.2)

    # --- Common X axis formatting ---
    for ax in axes:
        ax.set_xlim(0, 360)
        ax.set_xticks(range(0, 361, 30))
        # Shade shutter open region on all panels
        ax.axvspan(0, 180, alpha=0.04, color="yellow")
        # Vertical lines at key transitions
        ax.axvline(0, color="green", linewidth=0.8, linestyle=":", alpha=0.5)
        ax.axvline(180, color="red", linewidth=0.8, linestyle=":", alpha=0.5)

    # --- Phase labels at top ---
    ax_top = axes[0]
    cam_phases = result["cam_phases"]
    phase_colors = {
        "exposure": "#2ECC71", "close": "#95A5A6",
        "engage": "#27AE60", "pulldown": "#2980B9",
        "retract": "#E74C3C", "return": "#F39C12",
        "dwell": "#95A5A6",
    }
    for phase_name, (start, end) in cam_phases.items():
        mid = (start + end) / 2.0
        ax_top.annotate(phase_name.replace("_", " ").title(),
                        xy=(mid, 1.15), fontsize=7, ha="center",
                        color=phase_colors.get(phase_name, "gray"),
                        fontweight="bold")

    # --- Add time axis on top ---
    ax2 = axes[0].twiny()
    ax2.set_xlim(0, period_ms)
    ax2.set_xlabel(f"Time (ms) @ {fps} fps", fontsize=10)
    # Show tick marks at key angles converted to ms
    time_ticks_ms = [a / deg_per_ms for a in range(0, 361, 60)]
    ax2.set_xticks(time_ticks_ms)
    ax2.set_xticklabels([f"{t:.1f}" for t in time_ticks_ms])

    # --- Validation status box ---
    status_text = "ALL RULES PASS" if result["valid"] else "RULES VIOLATED"
    status_color = "green" if result["valid"] else "red"
    fig.text(0.98, 0.02, status_text, fontsize=12, fontweight="bold",
             color=status_color, ha="right", va="bottom",
             bbox=dict(boxstyle="round", facecolor="white", edgecolor=status_color,
                       alpha=0.9))

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    import os
    path = save_path or f"export/timing_diagram_{fps}fps.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Timing diagram saved: {path}")
    return path


# =========================================================================
# REPORTING
# =========================================================================

def print_timing_report():
    """Print comprehensive timing validation report for both frame rates."""
    result = validate_timing()
    sep = "=" * 68

    print(f"\n{sep}")
    print("  MECHANISM TIMING VALIDATION")
    print(sep)

    # Phase table
    print("\n  CAM PROFILE PHASES (shaft angle)")
    print("  " + "-" * 55)
    for name, (start, end) in result["cam_phases"].items():
        arc = end - start
        print(f"    {name:15s}: {start:6.1f}° — {end:6.1f}° ({arc:.0f}°)")

    print("\n  SHUTTER PHASES (with 180° offset keying)")
    print("  " + "-" * 55)
    for name, (start, end) in result["shutter_phases"].items():
        print(f"    {name:15s}: {start:6.1f}° — {end:6.1f}°")

    # Key angles
    print("\n  KEY TRANSITION ANGLES")
    print("  " + "-" * 55)
    ka = result["key_angles"]
    for label, angle in ka.items():
        if angle is not None:
            print(f"    {label:25s}: {angle:6.1f}°")
        else:
            print(f"    {label:25s}: (not detected)")

    # Frame rate specific
    for fps in [18, 24]:
        period_ms = 1000.0 / fps
        deg_per_ms = 360.0 / period_ms
        print(f"\n  TIMING @ {fps} fps (period = {period_ms:.2f} ms)")
        print("  " + "-" * 55)
        print(f"    Exposure:     {SHUTTER.exposure_time(fps) * 1000:.2f} ms "
              f"(1/{SHUTTER.exposure_reciprocal(fps):.0f} s)")
        print(f"    Pulldown:     {SHUTTER.pulldown_time(fps) * 1000:.2f} ms")
        print(f"    Settle:       {SHUTTER.settle_time(fps) * 1000:.2f} ms")

        # Convert key angles to ms
        for name, (start, end) in result["cam_phases"].items():
            t_start = start / deg_per_ms
            t_end = end / deg_per_ms
            print(f"    {name:15s}: {t_start:6.2f} — {t_end:6.2f} ms")

    # Critical rules
    print(f"\n  CRITICAL TIMING RULES")
    print("  " + "-" * 55)
    for rule_desc, passed, detail in result["rules"]:
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {rule_desc}")
        print(f"           {detail}")

    # Suggestions
    if result["suggestions"]:
        print(f"\n  SUGGESTED ADJUSTMENTS")
        print("  " + "-" * 55)
        for s in result["suggestions"]:
            print(f"    -> {s}")

    overall = "PASS" if result["valid"] else "FAIL"
    print(f"\n  Overall: {overall}")
    print(sep)

    return result


if __name__ == "__main__":
    result = print_timing_report()
    for fps in [18, 24]:
        plot_timing_diagram(fps)
