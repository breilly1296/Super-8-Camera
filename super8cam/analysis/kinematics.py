"""Kinematics analysis — claw motion profile, pulldown velocity, acceleration."""

import numpy as np
from super8cam.specs.master_specs import FILM, CAMERA, SHUTTER, GEARBOX


def pulldown_profile(fps: int, steps: int = 1000):
    """Compute claw position, velocity, and acceleration during pulldown.

    Returns dict of arrays: angle_deg, position_mm, velocity_mm_s, accel_mm_s2
    """
    period_s = 1.0 / fps
    pulldown_arc_deg = SHUTTER.pulldown_arc
    pulldown_time = SHUTTER.pulldown_time(fps)
    dt = pulldown_time / steps

    angles = np.linspace(SHUTTER.phase3_start, SHUTTER.phase3_end, steps)
    t = np.linspace(0, pulldown_time, steps)

    # Sinusoidal pulldown: position = pitch/2 * (1 - cos(pi * t / T))
    T = pulldown_time
    position = FILM.perf_pitch / 2 * (1 - np.cos(np.pi * t / T))
    velocity = FILM.perf_pitch / 2 * np.pi / T * np.sin(np.pi * t / T)
    accel = FILM.perf_pitch / 2 * (np.pi / T) ** 2 * np.cos(np.pi * t / T)

    return {
        "angle_deg": angles,
        "time_s": t,
        "position_mm": position,
        "velocity_mm_s": velocity,
        "accel_mm_s2": accel,
        "peak_velocity_mm_s": np.max(np.abs(velocity)),
        "peak_accel_mm_s2": np.max(np.abs(accel)),
    }


def shaft_torque_estimate(fps: int) -> float:
    """Estimate required torque at main shaft (N-mm) for film pulldown."""
    profile = pulldown_profile(fps)
    # F = m * a, where m ~ mass of 1 frame of film
    film_mass_per_frame_g = (FILM.width * FILM.perf_pitch * FILM.thickness *
                              1.4e-3)  # ~1.4 g/cm^3 PET
    film_mass_kg = film_mass_per_frame_g / 1000
    peak_force_n = film_mass_kg * profile["peak_accel_mm_s2"] / 1000
    # Torque at claw arm tip
    torque_nmm = peak_force_n * CAMERA.claw_arm_length
    return torque_nmm


def motor_speed_check():
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


# Avoid circular import — import MOTOR at module level
from super8cam.specs.master_specs import MOTOR
