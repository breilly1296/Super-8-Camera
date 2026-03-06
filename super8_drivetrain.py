#!/usr/bin/env python3
"""Super 8 Camera Drivetrain Calculator

Calculates the complete mechanical drivetrain for a Super 8 camera given
target frame rates, shutter geometry, and motor specifications.
"""

import math


# --- Motor Specification: Mabuchi FF-130 ---
MOTOR_RATED_RPM = 6600    # RPM at rated voltage
MOTOR_RATED_VOLTAGE = 3.0  # Volts
MOTOR_STALL_TORQUE = 4.4   # mN·m

# --- Camera Parameters ---
FRAME_RATES = [18, 24]              # fps
SHUTTER_OPENING_ANGLE = 180         # degrees
CLAW_PULLDOWN_TRAVEL = 4.23         # mm per frame

# Pulldown uses a fraction of the shutter-closed phase.
# Reserve a portion for dwell (film registration) before shutter opens.
# Typical claw mechanisms use ~60-70% of the closed phase for pulldown.
PULLDOWN_FRACTION_OF_CLOSED = 0.65


def calc_drivetrain(fps, shutter_angle_deg, pulldown_mm, motor_rpm,
                    pulldown_fraction=PULLDOWN_FRACTION_OF_CLOSED):
    """Calculate drivetrain parameters for a single frame rate.

    Returns a dict with all computed values and any timing violations.
    """
    # Main shaft turns once per frame
    main_shaft_rpm = fps * 60  # RPM

    # Gear reduction ratio
    gear_ratio = motor_rpm / main_shaft_rpm

    # Timing per frame
    frame_period = 1.0 / fps  # seconds

    # Shutter open / closed fractions
    shutter_open_fraction = shutter_angle_deg / 360.0
    shutter_closed_fraction = 1.0 - shutter_open_fraction

    exposure_time = frame_period * shutter_open_fraction      # seconds
    closed_time = frame_period * shutter_closed_fraction       # seconds

    # Pulldown must happen during the closed phase
    pulldown_time_budget = closed_time * pulldown_fraction     # seconds
    dwell_time = closed_time - pulldown_time_budget            # seconds

    # Claw linear velocity during pulldown
    claw_velocity_mm_s = pulldown_mm / pulldown_time_budget    # mm/s

    # Effective torque available after gear reduction (ideal, no losses)
    # Torque scales with gear ratio; speed scales inversely
    output_torque = MOTOR_STALL_TORQUE * gear_ratio            # mN·m (at stall)

    # Check for timing violations
    # Minimum pulldown time based on a practical peak claw velocity limit
    # (typical spring-loaded claw mechanisms max out around 300-400 mm/s)
    MAX_CLAW_VELOCITY = 400  # mm/s practical limit
    min_pulldown_time = pulldown_mm / MAX_CLAW_VELOCITY
    violation = None
    if pulldown_time_budget < min_pulldown_time:
        violation = (
            f"Pulldown budget {pulldown_time_budget*1000:.2f} ms < "
            f"minimum {min_pulldown_time*1000:.2f} ms "
            f"(claw would need {claw_velocity_mm_s:.0f} mm/s, limit {MAX_CLAW_VELOCITY} mm/s)"
        )

    return {
        "fps": fps,
        "main_shaft_rpm": main_shaft_rpm,
        "gear_ratio": gear_ratio,
        "frame_period_ms": frame_period * 1000,
        "exposure_time_ms": exposure_time * 1000,
        "closed_time_ms": closed_time * 1000,
        "pulldown_time_ms": pulldown_time_budget * 1000,
        "dwell_time_ms": dwell_time * 1000,
        "claw_velocity_mm_s": claw_velocity_mm_s,
        "output_torque_mNm": output_torque,
        "violation": violation,
    }


def print_summary(results):
    """Print a formatted summary table of drivetrain calculations."""
    sep = "=" * 62
    print(sep)
    print("  SUPER 8 CAMERA DRIVETRAIN CALCULATOR")
    print(sep)
    print()
    print(f"  Motor: Mabuchi FF-130  ({MOTOR_RATED_RPM} RPM @ {MOTOR_RATED_VOLTAGE}V, "
          f"stall torque {MOTOR_STALL_TORQUE} mN-m)")
    print(f"  Shutter opening angle: {SHUTTER_OPENING_ANGLE} deg")
    print(f"  Claw pulldown travel:  {CLAW_PULLDOWN_TRAVEL} mm/frame")
    print(f"  Pulldown fraction of closed phase: {PULLDOWN_FRACTION_OF_CLOSED*100:.0f}%")
    print()

    header = (
        f"  {'Parameter':<35} "
        + "  ".join(f"{'@' + str(r['fps']) + ' fps':>10}" for r in results)
    )
    print(header)
    print("  " + "-" * (35 + 12 * len(results)))

    rows = [
        ("Main shaft speed",        "main_shaft_rpm",       "RPM",   0),
        ("Gear ratio (motor:shaft)", "gear_ratio",           ":1",    1),
        ("Frame period",             "frame_period_ms",      "ms",    2),
        ("Exposure time (open)",     "exposure_time_ms",     "ms",    2),
        ("Shutter closed time",      "closed_time_ms",       "ms",    2),
        ("Pulldown time budget",     "pulldown_time_ms",     "ms",    2),
        ("Dwell time (registration)","dwell_time_ms",        "ms",    2),
        ("Claw velocity",           "claw_velocity_mm_s",    "mm/s",  1),
        ("Output torque (at stall)", "output_torque_mNm",    "mN-m",  1),
    ]

    for label, key, unit, decimals in rows:
        vals = "  ".join(
            f"{r[key]:>{10-len(unit)}.{decimals}f}{unit}" for r in results
        )
        print(f"  {label:<35} {vals}")

    print()

    # Timing violations
    violations = [(r["fps"], r["violation"]) for r in results if r["violation"]]
    if violations:
        print("  *** TIMING VIOLATIONS ***")
        for fps, msg in violations:
            print(f"  [{fps} fps] {msg}")
    else:
        print("  No timing violations detected -- all pulldowns feasible.")

    print()
    print(sep)


def main():
    results = [
        calc_drivetrain(
            fps=fps,
            shutter_angle_deg=SHUTTER_OPENING_ANGLE,
            pulldown_mm=CLAW_PULLDOWN_TRAVEL,
            motor_rpm=MOTOR_RATED_RPM,
        )
        for fps in FRAME_RATES
    ]
    print_summary(results)


if __name__ == "__main__":
    main()
