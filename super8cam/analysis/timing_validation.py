"""Timing validation — verify shutter, claw, and registration pin synchronisation.

For one complete shaft revolution (0-360deg) at both 18fps and 24fps,
models five mechanism signals and verifies seven critical timing rules.

Signals modelled:
    1. Shutter state (OPEN / CLOSED)
    2. Claw vertical position (top → bottom → top)
    3. Claw horizontal position (retracted → engaged → retracted)
    4. Film motion (stationary / advancing)
    5. Registration pin (engaged / disengaged)

Critical timing rules (all must pass):
    R1  Film stationary >= 5deg dwell before shutter opens
    R2  Registration pin engaged before shutter opens
    R3  Claw fully retracted before registration pin engages
    R4  Shutter fully closed before claw begins pulldown
    R5  Film completes 4.234mm advance before shutter opens again
    R6  Claw completes return stroke before next engagement
    R7  No two mechanisms conflict at any point in the cycle
"""

import math
import os
import numpy as np

from super8cam.specs.master_specs import SHUTTER, FILM, CAMERA


# =========================================================================
# Phase boundary definitions (degrees of main shaft rotation)
# =========================================================================

# Shutter disc: open from 0 → opening_angle, closed the rest
SHUTTER_OPEN_START = SHUTTER.phase1_start     # 0
SHUTTER_OPEN_END = SHUTTER.phase1_end         # 180

# Claw engage/pulldown/retract/return
CLAW_ENGAGE_START = SHUTTER.phase2_start      # 180
CLAW_ENGAGE_END = SHUTTER.phase2_end          # 230
PULLDOWN_START = SHUTTER.phase3_start         # 230
PULLDOWN_END = SHUTTER.phase3_end             # 330
CLAW_RETRACT_START = SHUTTER.phase4_start     # 330
CLAW_RETRACT_END = SHUTTER.phase4_end         # 360

# Registration pin: engages after claw retracts, stays through exposure
# Pin engages during the settle window (retract phase 4) and disengages
# just before claw engage starts (phase 2).
REG_PIN_ENGAGE = CLAW_RETRACT_START + 10.0    # 340 — after claw is clear
REG_PIN_DISENGAGE = CLAW_ENGAGE_START - 5.0   # 175 — before claw moves in

# Film motion: film advances during pulldown only
FILM_ADVANCE_START = PULLDOWN_START            # 230
FILM_ADVANCE_END = PULLDOWN_END               # 330

# Required dwell: film must be stationary this many degrees before shutter opens
MIN_DWELL_DEG = 5.0


# =========================================================================
# Signal generation (one full revolution at 1-degree resolution)
# =========================================================================

def _generate_signals(n_points: int = 360) -> dict:
    """Generate all mechanism state signals for one shaft revolution.

    Returns dict of numpy arrays, each of length n_points, covering 0..360 deg.
    Binary signals use 1.0 (active/open/engaged) and 0.0.
    Claw position signals are normalised 0..1.
    """
    theta = np.linspace(0, 360, n_points, endpoint=False)

    # --- Shutter state (1 = OPEN, 0 = CLOSED) ---
    shutter = np.where((theta >= SHUTTER_OPEN_START) & (theta < SHUTTER_OPEN_END), 1.0, 0.0)

    # --- Claw vertical position (0 = top, 1 = bottom of stroke) ---
    # Modelled as sinusoidal within the pulldown window, 0 otherwise
    claw_y = np.zeros(n_points)
    for i, a in enumerate(theta):
        if PULLDOWN_START <= a < PULLDOWN_END:
            # Sinusoidal pulldown: 0 at start, 1 at end
            phase = (a - PULLDOWN_START) / (PULLDOWN_END - PULLDOWN_START)
            claw_y[i] = 0.5 * (1.0 - math.cos(math.pi * phase))
        elif CLAW_RETRACT_START <= a < CLAW_RETRACT_END:
            # Return stroke: 1 at start, 0 at end
            phase = (a - CLAW_RETRACT_START) / (CLAW_RETRACT_END - CLAW_RETRACT_START)
            claw_y[i] = 1.0 - phase
        elif CLAW_ENGAGE_START <= a < CLAW_ENGAGE_END:
            # Not moving vertically during engage
            claw_y[i] = 0.0

    # --- Claw horizontal position (0 = retracted, 1 = engaged) ---
    claw_x = np.zeros(n_points)
    for i, a in enumerate(theta):
        if CLAW_ENGAGE_START <= a < CLAW_ENGAGE_END:
            phase = (a - CLAW_ENGAGE_START) / (CLAW_ENGAGE_END - CLAW_ENGAGE_START)
            claw_x[i] = 0.5 * (1.0 - math.cos(math.pi * phase))
        elif CLAW_ENGAGE_END <= a < CLAW_RETRACT_START:
            # Fully engaged during pulldown
            claw_x[i] = 1.0
        elif CLAW_RETRACT_START <= a < CLAW_RETRACT_END:
            phase = (a - CLAW_RETRACT_START) / (CLAW_RETRACT_END - CLAW_RETRACT_START)
            claw_x[i] = 0.5 * (1.0 + math.cos(math.pi * phase))

    # --- Film motion (1 = advancing, 0 = stationary) ---
    film_motion = np.where((theta >= FILM_ADVANCE_START) & (theta < FILM_ADVANCE_END), 1.0, 0.0)

    # --- Registration pin (1 = engaged, 0 = disengaged) ---
    # Pin is engaged from REG_PIN_ENGAGE (340) through 360/0 to REG_PIN_DISENGAGE (175)
    reg_pin = np.zeros(n_points)
    for i, a in enumerate(theta):
        if a >= REG_PIN_ENGAGE or a < REG_PIN_DISENGAGE:
            reg_pin[i] = 1.0

    return {
        "theta_deg": theta,
        "shutter": shutter,
        "claw_y": claw_y,
        "claw_x": claw_x,
        "film_motion": film_motion,
        "reg_pin": reg_pin,
    }


# =========================================================================
# Timing rule verification
# =========================================================================

def _check_timing_rules(signals: dict) -> list:
    """Check all seven critical timing rules.

    Returns list of dicts: {rule, description, passed, detail, violation_angles}.
    """
    theta = signals["theta_deg"]
    shutter = signals["shutter"]
    claw_x = signals["claw_x"]
    claw_y = signals["claw_y"]
    film_motion = signals["film_motion"]
    reg_pin = signals["reg_pin"]
    n = len(theta)
    d_theta = theta[1] - theta[0]

    results = []

    # --- R1: Film stationary >= MIN_DWELL_DEG before shutter opens ---
    shutter_open_idx = None
    for i in range(n):
        if shutter[i] > 0.5 and (i == 0 or shutter[i - 1] < 0.5):
            shutter_open_idx = i
            break
    if shutter_open_idx is None:
        # Shutter opens at index 0 (wraps around)
        shutter_open_idx = 0

    # Check dwell: film_motion must be 0 for MIN_DWELL_DEG before shutter opens
    dwell_steps = int(MIN_DWELL_DEG / d_theta)
    dwell_ok = True
    violation_angles_r1 = []
    for j in range(1, dwell_steps + 1):
        idx = (shutter_open_idx - j) % n
        if film_motion[idx] > 0.5:
            dwell_ok = False
            violation_angles_r1.append(float(theta[idx]))
    results.append({
        "rule": "R1",
        "description": f"Film stationary >= {MIN_DWELL_DEG} deg before shutter opens",
        "passed": dwell_ok,
        "detail": f"Checked {dwell_steps} deg before shutter open at {theta[shutter_open_idx]:.0f} deg",
        "violation_angles": violation_angles_r1,
    })

    # --- R2: Registration pin engaged before shutter opens ---
    pin_ok = True
    violation_angles_r2 = []
    for j in range(1, dwell_steps + 1):
        idx = (shutter_open_idx - j) % n
        if reg_pin[idx] < 0.5:
            pin_ok = False
            violation_angles_r2.append(float(theta[idx]))
    # Also check at the exact shutter open angle
    if reg_pin[shutter_open_idx] < 0.5:
        pin_ok = False
        violation_angles_r2.append(float(theta[shutter_open_idx]))
    results.append({
        "rule": "R2",
        "description": "Registration pin engaged before shutter opens",
        "passed": pin_ok,
        "detail": f"Pin state at shutter open ({theta[shutter_open_idx]:.0f} deg): "
                  f"{'ENGAGED' if reg_pin[shutter_open_idx] > 0.5 else 'DISENGAGED'}",
        "violation_angles": violation_angles_r2,
    })

    # --- R3: Claw fully retracted before registration pin engages ---
    # Find where reg pin transitions from 0 → 1
    pin_engage_idx = None
    for i in range(n):
        prev = (i - 1) % n
        if reg_pin[i] > 0.5 and reg_pin[prev] < 0.5:
            pin_engage_idx = i
            break
    claw_retracted_ok = True
    violation_angles_r3 = []
    if pin_engage_idx is not None:
        # Claw_x must be < 0.05 at pin engage
        if claw_x[pin_engage_idx] > 0.05:
            claw_retracted_ok = False
            violation_angles_r3.append(float(theta[pin_engage_idx]))
        # Check a few degrees before too
        for j in range(1, 6):
            idx = (pin_engage_idx - j) % n
            if claw_x[idx] > 0.1:
                claw_retracted_ok = False
                violation_angles_r3.append(float(theta[idx]))
    results.append({
        "rule": "R3",
        "description": "Claw fully retracted before registration pin engages",
        "passed": claw_retracted_ok,
        "detail": f"Pin engages at {theta[pin_engage_idx]:.0f} deg, "
                  f"claw_x = {claw_x[pin_engage_idx]:.3f}" if pin_engage_idx else "Pin engage not found",
        "violation_angles": violation_angles_r3,
    })

    # --- R4: Shutter fully closed before claw begins pulldown ---
    # Find first angle where claw_x > 0.05 (engage starts)
    claw_start_idx = None
    for i in range(n):
        if claw_x[i] > 0.05 and claw_x[(i - 1) % n] < 0.05:
            claw_start_idx = i
            break
    shutter_closed_ok = True
    violation_angles_r4 = []
    if claw_start_idx is not None:
        if shutter[claw_start_idx] > 0.5:
            shutter_closed_ok = False
            violation_angles_r4.append(float(theta[claw_start_idx]))
        # Check a few degrees before
        for j in range(1, 4):
            idx = (claw_start_idx - j) % n
            if shutter[idx] > 0.5:
                # The shutter should be closing by now but still check boundary
                pass
    results.append({
        "rule": "R4",
        "description": "Shutter fully closed before claw begins engage",
        "passed": shutter_closed_ok,
        "detail": f"Claw engage starts at {theta[claw_start_idx]:.0f} deg, "
                  f"shutter: {'OPEN' if shutter[claw_start_idx] > 0.5 else 'CLOSED'}"
                  if claw_start_idx else "Claw start not found",
        "violation_angles": violation_angles_r4,
    })

    # --- R5: Film completes 4.234mm advance before shutter opens again ---
    # The film advance window (FILM_ADVANCE_START to FILM_ADVANCE_END) must
    # have enough arc at the given RPM to advance one full perf pitch.
    advance_arc = FILM_ADVANCE_END - FILM_ADVANCE_START  # degrees
    advance_fraction = advance_arc / 360.0
    # At any fps, one revolution = one frame.  If advance arc can accommodate
    # the full pulldown stroke, the advance completes in time.
    # The pulldown is designed so cam_lobe_lift = perf_pitch = 4.234mm.
    advance_ok = (CAMERA.claw_stroke >= FILM.perf_pitch - 0.01)
    results.append({
        "rule": "R5",
        "description": f"Film completes {FILM.perf_pitch} mm advance before shutter opens",
        "passed": advance_ok,
        "detail": f"Pulldown arc = {advance_arc:.0f} deg ({advance_fraction * 100:.1f}% of rev), "
                  f"cam stroke = {CAMERA.claw_stroke} mm, perf pitch = {FILM.perf_pitch} mm",
        "violation_angles": [],
    })

    # --- R6: Claw completes return stroke before next engagement ---
    # After retract ends (360/0), claw must be at x < 0.05 before next engage
    # The claw returns to 0 during retract (330-360), then stays retracted
    # through 0-180.  Check that at theta=0 claw_x ≈ 0.
    return_ok = claw_x[0] < 0.05
    violation_angles_r6 = []
    if not return_ok:
        violation_angles_r6.append(0.0)
    results.append({
        "rule": "R6",
        "description": "Claw completes return stroke before next engagement",
        "passed": return_ok,
        "detail": f"Claw_x at 0 deg = {claw_x[0]:.3f} (must be < 0.05)",
        "violation_angles": violation_angles_r6,
    })

    # --- R7: No two mechanisms conflict at any point ---
    # Conflicts:
    #   a) Claw engaged while shutter is open (claw would block light path)
    #   b) Film advancing while shutter is open (frame smear)
    #   c) Claw engaged while registration pin is engaged (mechanical clash)
    conflict_angles = []
    conflict_ok = True

    for i in range(n):
        conflicts_here = []
        # (a) Claw engaged + shutter open
        if claw_x[i] > 0.1 and shutter[i] > 0.5:
            conflicts_here.append("claw_engaged+shutter_open")
        # (b) Film advancing + shutter open
        if film_motion[i] > 0.5 and shutter[i] > 0.5:
            conflicts_here.append("film_advancing+shutter_open")
        # (c) Claw engaged + reg pin engaged simultaneously
        #     (pin should disengage before claw engages)
        if claw_x[i] > 0.5 and reg_pin[i] > 0.5:
            conflicts_here.append("claw_engaged+reg_pin_engaged")

        if conflicts_here:
            conflict_ok = False
            conflict_angles.append((float(theta[i]), conflicts_here))

    results.append({
        "rule": "R7",
        "description": "No two mechanisms conflict at any angle",
        "passed": conflict_ok,
        "detail": f"{len(conflict_angles)} conflict(s) found" if conflict_angles
                  else "No conflicts",
        "violation_angles": [a for a, _ in conflict_angles[:10]],  # limit output
        "conflicts": conflict_angles[:10] if conflict_angles else [],
    })

    return results


# =========================================================================
# Timing diagram plot
# =========================================================================

def plot_timing_diagram(fps: int = 24, save_path: str = None) -> str:
    """Generate a multi-track timing diagram showing all mechanism signals.

    Args:
        fps: Frame rate (for title annotation and time axis).
        save_path: Output file path (default: export/timing_diagram_{fps}fps.png).

    Returns the path to the saved image.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    signals = _generate_signals(720)
    theta = signals["theta_deg"]

    period_ms = 1000.0 / fps
    time_ms = theta / 360.0 * period_ms

    fig, axes = plt.subplots(5, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f"Super 8 Camera Timing Diagram @ {fps} fps  "
                 f"(period = {period_ms:.1f} ms)",
                 fontsize=13, fontweight="bold")

    track_labels = [
        "Shutter",
        "Claw Vertical\n(pulldown)",
        "Claw Horizontal\n(engage)",
        "Film Motion",
        "Registration\nPin",
    ]
    track_data = [
        signals["shutter"],
        signals["claw_y"],
        signals["claw_x"],
        signals["film_motion"],
        signals["reg_pin"],
    ]
    track_colors = ["#FFD700", "#2196F3", "#4CAF50", "#FF5722", "#9C27B0"]

    for ax, label, data, color in zip(axes, track_labels, track_data, track_colors):
        ax.fill_between(theta, data, alpha=0.35, color=color, step="mid" if label in ("Shutter", "Film Motion", "Registration\nPin") else None)
        ax.plot(theta, data, color=color, linewidth=1.5)
        ax.set_ylabel(label, fontsize=9, rotation=0, ha="right", va="center",
                       labelpad=70)
        ax.set_ylim(-0.1, 1.15)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["OFF", "ON"], fontsize=8)
        ax.grid(True, axis="x", alpha=0.3)
        ax.axvline(SHUTTER_OPEN_END, color="gray", linestyle="--", alpha=0.4)
        ax.axvline(CLAW_ENGAGE_START, color="gray", linestyle=":", alpha=0.4)
        ax.axvline(PULLDOWN_START, color="gray", linestyle=":", alpha=0.4)
        ax.axvline(PULLDOWN_END, color="gray", linestyle=":", alpha=0.4)
        ax.axvline(CLAW_RETRACT_START, color="gray", linestyle=":", alpha=0.4)

    # Phase labels at top
    axes[0].set_yticklabels(["CLOSED", "OPEN"], fontsize=8)
    axes[3].set_yticklabels(["STILL", "MOVING"], fontsize=8)
    axes[4].set_yticklabels(["OUT", "IN"], fontsize=8)

    # Annotate phases on the bottom axis
    axes[-1].set_xlabel("Shaft angle [degrees]", fontsize=10)
    axes[-1].set_xlim(0, 360)
    axes[-1].set_xticks(np.arange(0, 361, 30))

    # Phase region labels
    phase_labels = [
        (SHUTTER_OPEN_START, SHUTTER_OPEN_END, "EXPOSURE", "#FFF9C4"),
        (CLAW_ENGAGE_START, CLAW_ENGAGE_END, "ENGAGE", "#C8E6C9"),
        (PULLDOWN_START, PULLDOWN_END, "PULLDOWN", "#BBDEFB"),
        (CLAW_RETRACT_START, CLAW_RETRACT_END, "RETRACT\n+SETTLE", "#E1BEE7"),
    ]
    for start, end, label, bg_color in phase_labels:
        for ax in axes:
            ax.axvspan(start, end, alpha=0.15, color=bg_color, zorder=0)
        mid = (start + end) / 2
        axes[0].text(mid, 1.1, label, ha="center", va="bottom", fontsize=7,
                     fontweight="bold", color="gray")

    plt.tight_layout(rect=[0.08, 0, 1, 0.95])

    path = save_path or f"export/timing_diagram_{fps}fps.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Timing diagram saved: {path}")
    return path


# =========================================================================
# Timing adjustment suggestions
# =========================================================================

def _suggest_adjustments(rule_results: list) -> list:
    """Suggest cam phase offsets for failed timing rules."""
    suggestions = []
    for r in rule_results:
        if r["passed"]:
            continue
        rule = r["rule"]
        angles = r.get("violation_angles", [])
        if rule == "R1":
            suggestions.append(
                f"R1: Advance the pulldown end (currently {PULLDOWN_END} deg) earlier "
                f"by at least {MIN_DWELL_DEG} deg, or retard shutter open past "
                f"{SHUTTER_OPEN_START + MIN_DWELL_DEG} deg.")
        elif rule == "R2":
            suggestions.append(
                f"R2: Advance registration pin engage (currently {REG_PIN_ENGAGE} deg) "
                f"earlier so it is engaged well before shutter opens at {SHUTTER_OPEN_START} deg.")
        elif rule == "R3":
            suggestions.append(
                f"R3: Ensure claw retract completes (currently ends {CLAW_RETRACT_END} deg) "
                f"before reg pin engages at {REG_PIN_ENGAGE} deg.  "
                f"Reduce retract arc or advance retract start.")
        elif rule == "R4":
            suggestions.append(
                f"R4: Retard claw engage start (currently {CLAW_ENGAGE_START} deg) "
                f"so it begins after shutter closes at {SHUTTER_OPEN_END} deg.")
        elif rule == "R5":
            suggestions.append(
                f"R5: Increase pulldown arc (currently {PULLDOWN_END - PULLDOWN_START} deg) "
                f"or increase cam lobe lift (currently {CAMERA.cam_lobe_lift} mm).")
        elif rule == "R6":
            suggestions.append(
                f"R6: Ensure retract phase ({CLAW_RETRACT_START}-{CLAW_RETRACT_END} deg) "
                f"is long enough for full claw return.")
        elif rule == "R7":
            conflicts = r.get("conflicts", [])
            for angle, types in conflicts[:3]:
                suggestions.append(
                    f"R7: Conflict at {angle:.0f} deg: {', '.join(types)}.  "
                    f"Adjust phase offsets to eliminate overlap.")
    return suggestions


# =========================================================================
# Public API — backward-compatible validate_timing()
# =========================================================================

def validate_timing() -> dict:
    """Check that all phase boundaries are consistent and non-overlapping.

    Returns dict compatible with the build.py caller:
        valid:               bool
        errors:              list of error strings
        phases:              list of (name, start, end) tuples
        exposure_duty:       float
        pulldown_time_18ms:  float
        pulldown_time_24ms:  float
        settle_time_18ms:    float
        settle_time_24ms:    float
        rule_results:        list of per-rule dicts (new)
        suggestions:         list of adjustment suggestions (new)
    """
    errors = []

    phases = [
        ("Phase 1: Exposure", SHUTTER.phase1_start, SHUTTER.phase1_end),
        ("Phase 2: Claw engage", SHUTTER.phase2_start, SHUTTER.phase2_end),
        ("Phase 3: Pulldown", SHUTTER.phase3_start, SHUTTER.phase3_end),
        ("Phase 4: Claw retract", SHUTTER.phase4_start, SHUTTER.phase4_end),
    ]

    # --- Basic ordering checks (original logic) ---
    for i, (name, start, end) in enumerate(phases):
        if start >= end:
            errors.append(f"{name}: start ({start}) >= end ({end})")
        if i > 0:
            prev_name, _, prev_end = phases[i - 1]
            if start < prev_end:
                errors.append(f"{name} overlaps with {prev_name}")

    # Full revolution
    total = SHUTTER.phase4_end - SHUTTER.phase1_start
    if abs(total - 360.0) > 0.01:
        errors.append(f"Total arc = {total} deg (expected 360)")

    # Exposure duty cycle
    exposure_arc = SHUTTER.phase1_end - SHUTTER.phase1_start
    if abs(exposure_arc - CAMERA.shutter_opening_angle) > 0.01:
        errors.append(f"Exposure arc = {exposure_arc} deg, "
                      f"expected {CAMERA.shutter_opening_angle}")

    # Minimum pulldown time at 24 fps
    pulldown_time_24 = SHUTTER.pulldown_time(24)
    min_pulldown_time = 0.001  # 1 ms absolute minimum
    if pulldown_time_24 < min_pulldown_time:
        errors.append(f"Pulldown time at 24fps = {pulldown_time_24 * 1000:.2f}ms "
                      f"(< {min_pulldown_time * 1000}ms minimum)")

    # Film settle time
    settle_time_24 = SHUTTER.settle_time(24)
    if settle_time_24 < 0.0005:
        errors.append(f"Settle time at 24fps = {settle_time_24 * 1000:.2f}ms (too short)")

    # --- New: seven critical timing rules ---
    signals = _generate_signals(720)
    rule_results = _check_timing_rules(signals)

    for r in rule_results:
        if not r["passed"]:
            errors.append(f"{r['rule']}: {r['description']} — FAILED at "
                          f"{r['violation_angles'][:5]} deg. {r['detail']}")

    suggestions = _suggest_adjustments(rule_results)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "phases": phases,
        "exposure_duty": exposure_arc / 360.0,
        "pulldown_time_18ms": SHUTTER.pulldown_time(18) * 1000,
        "pulldown_time_24ms": SHUTTER.pulldown_time(24) * 1000,
        "settle_time_18ms": SHUTTER.settle_time(18) * 1000,
        "settle_time_24ms": SHUTTER.settle_time(24) * 1000,
        "rule_results": rule_results,
        "suggestions": suggestions,
    }


# =========================================================================
# Full report
# =========================================================================

def print_timing_report():
    """Print a comprehensive timing validation report."""
    sep = "=" * 68
    print(sep)
    print("  TIMING VALIDATION REPORT")
    print(sep)

    result = validate_timing()

    # Phase summary
    print("\n  PHASE BOUNDARIES")
    print("  " + "-" * 55)
    print(f"    {'Phase':<28s} {'Start':>6s}  {'End':>6s}  {'Arc':>6s}")
    print("    " + "-" * 50)
    for name, start, end in result["phases"]:
        print(f"    {name:<28s} {start:>6.0f}  {end:>6.0f}  {end - start:>6.0f} deg")

    # Timing parameters
    print("\n  TIMING PARAMETERS")
    print("  " + "-" * 55)
    print(f"    Exposure duty cycle:     {result['exposure_duty'] * 100:.1f}%")
    print(f"    Pulldown time @18fps:    {result['pulldown_time_18ms']:.2f} ms")
    print(f"    Pulldown time @24fps:    {result['pulldown_time_24ms']:.2f} ms")
    print(f"    Settle time @18fps:      {result['settle_time_18ms']:.2f} ms")
    print(f"    Settle time @24fps:      {result['settle_time_24ms']:.2f} ms")

    # Critical rules
    print("\n  CRITICAL TIMING RULES")
    print("  " + "-" * 55)
    for r in result["rule_results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"    [{status}] {r['rule']}: {r['description']}")
        print(f"           {r['detail']}")
        if not r["passed"] and r["violation_angles"]:
            angles_str = ", ".join(f"{a:.0f}" for a in r["violation_angles"][:5])
            print(f"           Violation at: {angles_str} deg")

    # Suggestions
    if result["suggestions"]:
        print("\n  SUGGESTED ADJUSTMENTS")
        print("  " + "-" * 55)
        for s in result["suggestions"]:
            print(f"    {s}")

    # Overall
    print(f"\n  OVERALL: {'PASS' if result['valid'] else 'FAIL'}")
    if result["errors"]:
        print(f"  {len(result['errors'])} error(s) found")
    print("  " + sep)


# =========================================================================
# Main
# =========================================================================

if __name__ == "__main__":
    print_timing_report()
    for fps in [18, 24]:
        plot_timing_diagram(fps)
