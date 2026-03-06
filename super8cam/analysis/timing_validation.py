"""Timing validation — verify that all mechanism phases fit within one revolution."""

from super8cam.specs.master_specs import SHUTTER, FILM, CAMERA


def validate_timing():
    """Check that all phase boundaries are consistent and non-overlapping."""
    errors = []

    phases = [
        ("Phase 1: Exposure", SHUTTER.phase1_start, SHUTTER.phase1_end),
        ("Phase 2: Claw engage", SHUTTER.phase2_start, SHUTTER.phase2_end),
        ("Phase 3: Pulldown", SHUTTER.phase3_start, SHUTTER.phase3_end),
        ("Phase 4: Claw retract", SHUTTER.phase4_start, SHUTTER.phase4_end),
    ]

    # Check ordering
    for i, (name, start, end) in enumerate(phases):
        if start >= end:
            errors.append(f"{name}: start ({start}) >= end ({end})")
        if i > 0:
            prev_name, _, prev_end = phases[i - 1]
            if start < prev_end:
                errors.append(f"{name} overlaps with {prev_name}")

    # Check full revolution
    total = SHUTTER.phase4_end - SHUTTER.phase1_start
    if abs(total - 360.0) > 0.01:
        errors.append(f"Total arc = {total} deg (expected 360)")

    # Exposure duty cycle
    exposure_arc = SHUTTER.phase1_end - SHUTTER.phase1_start
    if abs(exposure_arc - CAMERA.shutter_opening_angle) > 0.01:
        errors.append(f"Exposure arc = {exposure_arc} deg, "
                      f"expected {CAMERA.shutter_opening_angle}")

    # Minimum pulldown time check at 24 fps
    pulldown_time_24 = SHUTTER.pulldown_time(24)
    min_pulldown_time = 0.001  # 1 ms absolute minimum
    if pulldown_time_24 < min_pulldown_time:
        errors.append(f"Pulldown time at 24fps = {pulldown_time_24*1000:.2f}ms "
                      f"(< {min_pulldown_time*1000}ms minimum)")

    # Film settle time check
    settle_time_24 = SHUTTER.settle_time(24)
    if settle_time_24 < 0.0005:  # 0.5 ms minimum
        errors.append(f"Settle time at 24fps = {settle_time_24*1000:.2f}ms (too short)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "phases": phases,
        "exposure_duty": exposure_arc / 360.0,
        "pulldown_time_18ms": SHUTTER.pulldown_time(18) * 1000,
        "pulldown_time_24ms": SHUTTER.pulldown_time(24) * 1000,
        "settle_time_18ms": SHUTTER.settle_time(18) * 1000,
        "settle_time_24ms": SHUTTER.settle_time(24) * 1000,
    }
