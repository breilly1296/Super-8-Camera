#!/usr/bin/env python3
"""encoder_test.py — PID Controller Simulation & Encoder Signal Test Bench

Validates the firmware PID tuning by simulating:
  1. Synthetic encoder pulse train with realistic imperfections
  2. Software PID controller matching motor_control.c exactly
  3. Simple DC motor + inertia plant model

Test scenarios:
  A) 18 fps startup from rest, hold for 3 seconds
  B) 24 fps startup from rest, hold for 3 seconds
  C) Mid-run speed switch: 18 fps for 2s → 24 fps for 3s

Plots: actual vs target fps, PWM duty cycle, steady-state error.
Prints quantitative metrics for each scenario.

Usage:
    python encoder_test.py              # generate all plots
    python encoder_test.py --show       # try plt.show() (needs display)
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# =========================================================================
# Firmware-matching PID parameters (from motor_control.h)
# =========================================================================

PID_KP          = 1.8
PID_KI          = 0.9
PID_KD          = 0.05
PID_I_CLAMP     = 400.0
PID_INTERVAL_MS = 20       # PID runs at 50 Hz
PWM_DUTY_MIN    = 50
PWM_DUTY_MAX    = 999
RAMP_STEP       = 5
RAMP_INTERVAL_MS = 10
STALL_TIMEOUT_MS = 200

# =========================================================================
# Encoder noise model
# =========================================================================

JITTER_PCT      = 0.02     # +/- 2% timing jitter on each pulse
MISS_RATE       = 1 / 200  # 1 in 200 pulses randomly dropped
STARTUP_RAMP_S  = 0.5      # motor takes 0.5s from 0 to target fps


# =========================================================================
# Simple DC motor plant model
#
# Maps PWM duty (0-999) to shaft speed (fps) with first-order lag.
# Tau models motor + gearbox + film inertia.  K maps duty to steady-state
# speed.  This is intentionally simple — we're testing PID response, not
# building a full electromechanical sim.
# =========================================================================

class MotorPlant:
    """First-order model: tau * d(fps)/dt = K * duty - fps"""

    def __init__(self, K=0.03, tau=0.15, noise_std=0.3):
        """
        K:         gain — fps per unit duty at steady state
        tau:       time constant in seconds (inertia)
        noise_std: measurement noise on fps (encoder quantization etc.)
        """
        self.K = K
        self.tau = tau
        self.noise_std = noise_std
        self.fps = 0.0

    def step(self, duty, dt):
        """Advance the plant by dt seconds at the given duty cycle."""
        # Clamp duty
        duty = max(0, min(duty, PWM_DUTY_MAX))
        # First-order response: fps approaches K*duty with time constant tau
        target_fps = self.K * duty
        # Euler integration
        self.fps += (target_fps - self.fps) * (dt / self.tau)
        # Add noise
        noisy_fps = self.fps + np.random.normal(0, self.noise_std)
        return max(0.0, noisy_fps)

    def reset(self):
        self.fps = 0.0


# =========================================================================
# Encoder pulse generator (with jitter and dropouts)
# =========================================================================

class EncoderSim:
    """Simulates optical encoder output: 1 pulse per frame."""

    def __init__(self, jitter_pct=JITTER_PCT, miss_rate=MISS_RATE):
        self.jitter_pct = jitter_pct
        self.miss_rate = miss_rate
        self.last_pulse_time = 0.0
        self.time_since_last = 0.0

    def update(self, actual_fps, dt, current_time):
        """Returns (got_pulse, measured_period_us).

        Call every simulation tick. If the motor is producing pulses at
        actual_fps, this decides if a pulse fires this tick and returns
        the (noisy) period measurement.
        """
        if actual_fps < 0.5:
            # Motor essentially stopped — no pulses
            self.time_since_last += dt
            return False, 0

        ideal_period = 1.0 / actual_fps
        self.time_since_last += dt

        if self.time_since_last >= ideal_period:
            self.time_since_last -= ideal_period

            # Jitter: perturb the measured period
            jitter = 1.0 + np.random.uniform(-self.jitter_pct, self.jitter_pct)
            measured_period_us = ideal_period * jitter * 1e6  # to microseconds

            # Missed pulse?
            if np.random.random() < self.miss_rate:
                return False, 0

            self.last_pulse_time = current_time
            return True, measured_period_us

        return False, 0


# =========================================================================
# PID Controller — exact port of motor_control.c pid_compute()
# =========================================================================

class PIDController:
    """Mirrors the firmware PID implementation exactly."""

    def __init__(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.current_duty = PWM_DUTY_MIN

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.current_duty = PWM_DUTY_MIN

    def compute(self, target, actual):
        """Run one PID iteration. Returns new duty cycle."""
        error = target - actual

        # Proportional
        p_term = PID_KP * error

        # Integral with anti-windup clamp
        dt_s = PID_INTERVAL_MS / 1000.0
        self.integral += PID_KI * error * dt_s
        if self.integral > PID_I_CLAMP:
            self.integral = PID_I_CLAMP
        if self.integral < -PID_I_CLAMP:
            self.integral = -PID_I_CLAMP

        # Derivative (on error)
        d_term = PID_KD * (error - self.prev_error) / dt_s
        self.prev_error = error

        # Sum and clamp
        output = self.current_duty + p_term + self.integral + d_term
        if output < PWM_DUTY_MIN:
            output = PWM_DUTY_MIN
        if output > PWM_DUTY_MAX:
            output = PWM_DUTY_MAX

        self.current_duty = int(output)
        return self.current_duty


# =========================================================================
# Startup ramp (mirrors firmware STATE_RAMP_UP)
# =========================================================================

class StartupRamp:
    """Open-loop ramp before PID takes over."""

    def __init__(self):
        self.duty = 0
        self.active = True
        self.ms_counter = 0

    def reset(self):
        self.duty = 0
        self.active = True
        self.ms_counter = 0

    def step(self, dt_ms, got_encoder_pulse):
        """Returns (duty, still_ramping)."""
        if not self.active:
            return self.duty, False

        self.ms_counter += dt_ms
        if self.ms_counter >= RAMP_INTERVAL_MS:
            self.ms_counter = 0
            target_duty = int(PWM_DUTY_MAX * 0.40)
            if self.duty < target_duty:
                self.duty += RAMP_STEP
                if self.duty > target_duty:
                    self.duty = target_duty

        # Hand off to PID once we get encoder feedback
        if got_encoder_pulse and self.duty >= PWM_DUTY_MIN:
            self.active = False

        return self.duty, self.active


# =========================================================================
# Simulation runner
# =========================================================================

def run_scenario(name, duration_s, target_fps_func, sim_dt=0.001):
    """Run a complete scenario.

    Args:
        name:            scenario label
        duration_s:      total simulation time
        target_fps_func: callable(t) -> target fps at time t
        sim_dt:          simulation timestep (seconds)

    Returns dict of time-series arrays and metrics.
    """
    steps = int(duration_s / sim_dt)

    # State
    plant = MotorPlant()
    encoder = EncoderSim()
    pid = PIDController()
    ramp = StartupRamp()

    # Recording arrays
    t_arr = np.zeros(steps)
    target_arr = np.zeros(steps)
    actual_arr = np.zeros(steps)
    measured_arr = np.zeros(steps)
    duty_arr = np.zeros(steps)
    error_arr = np.zeros(steps)

    measured_fps = 0.0
    pid_timer_ms = 0.0
    last_enc_period_us = 0
    ramping = True
    current_duty = 0
    prev_target = 0
    enc_got_first_pulse = False

    for i in range(steps):
        t = i * sim_dt
        target = target_fps_func(t)

        # Detect target change (speed switch) — reset PID
        if abs(target - prev_target) > 1.0 and i > 0:
            pid.reset()
            pid.current_duty = current_duty  # keep current duty as starting point
        prev_target = target

        # Plant step
        actual_fps = plant.step(current_duty, sim_dt)

        # Encoder step
        got_pulse, period_us = encoder.update(actual_fps, sim_dt, t)
        if got_pulse:
            last_enc_period_us = period_us
            enc_got_first_pulse = True

        # Ramp or PID
        if ramping:
            current_duty, ramping = ramp.step(sim_dt * 1000, got_pulse)
            if not ramping:
                # Hand off to PID with current duty
                pid.current_duty = current_duty
        else:
            # PID runs at fixed interval
            pid_timer_ms += sim_dt * 1000
            if pid_timer_ms >= PID_INTERVAL_MS:
                pid_timer_ms -= PID_INTERVAL_MS
                # Compute measured fps from last encoder period
                if last_enc_period_us > 0:
                    measured_fps = 1e6 / last_enc_period_us
                else:
                    measured_fps = 0.0
                current_duty = pid.compute(target, measured_fps)

        # Record
        t_arr[i] = t
        target_arr[i] = target
        actual_arr[i] = actual_fps
        measured_arr[i] = measured_fps
        duty_arr[i] = current_duty
        error_arr[i] = target - actual_fps

    # ---- Compute metrics ----
    # Steady state: last 30% of the run (after all transients)
    ss_start = int(steps * 0.7)
    ss_error = error_arr[ss_start:]
    ss_actual = actual_arr[ss_start:]
    ss_target = target_arr[ss_start:]

    metrics = {
        "name": name,
        "mean_ss_error": np.mean(ss_error),
        "max_ss_error": np.max(np.abs(ss_error)),
        "std_ss_error": np.std(ss_error),
        "mean_ss_fps": np.mean(ss_actual),
        "target_ss_fps": np.mean(ss_target),
        "overshoot_pct": 0.0,
        "rise_time_s": 0.0,
        "settling_time_s": 0.0,
    }

    # Rise time: time to reach 90% of first target
    first_target = target_fps_func(0.0)
    threshold_90 = first_target * 0.90
    rise_indices = np.where(actual_arr >= threshold_90)[0]
    if len(rise_indices) > 0:
        metrics["rise_time_s"] = t_arr[rise_indices[0]]

    # Overshoot: max fps above target during the first 2 seconds
    early_end = min(int(2.0 / sim_dt), steps)
    early_actual = actual_arr[:early_end]
    early_target = target_arr[:early_end]
    overshoot_vals = early_actual - early_target
    if np.max(overshoot_vals) > 0:
        metrics["overshoot_pct"] = (np.max(overshoot_vals) / first_target) * 100

    # Settling time: time until error stays within ±2% of target
    settle_band = first_target * 0.02
    settled = np.abs(error_arr) < settle_band
    # Find last index where NOT settled, settling time is just after that
    not_settled = np.where(~settled)[0]
    if len(not_settled) > 0:
        metrics["settling_time_s"] = t_arr[not_settled[-1]] if not_settled[-1] < steps - 1 else duration_s

    return {
        "t": t_arr,
        "target": target_arr,
        "actual": actual_arr,
        "measured": measured_arr,
        "duty": duty_arr,
        "error": error_arr,
        "metrics": metrics,
    }


# =========================================================================
# Plotting
# =========================================================================

def plot_scenario(result, filename):
    """Generate a 3-panel plot for one scenario."""
    t = result["t"]
    m = result["metrics"]

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.patch.set_facecolor("#1a1a2e")
    fig.suptitle("PID Encoder Test: {}".format(m["name"]),
                 fontsize=14, color="white", fontweight="bold")

    for ax in axes:
        ax.set_facecolor("#0f0f23")
        ax.tick_params(colors="white")
        ax.grid(True, color="#333333", linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color("#444444")

    # ---- Panel 1: FPS ----
    ax1 = axes[0]
    ax1.plot(t, result["target"], "--", color="#FF6666", linewidth=1.5, label="Target fps")
    ax1.plot(t, result["actual"], color="#44BBFF", linewidth=1.0, alpha=0.4, label="Plant fps")
    ax1.plot(t, result["measured"], color="#00FF88", linewidth=0.8, alpha=0.7, label="Measured fps")
    ax1.set_ylabel("Frames/sec", color="white")
    ax1.set_ylim(0, max(np.max(result["target"]) * 1.4, 30))
    ax1.legend(loc="lower right", fontsize=9, facecolor="#1a1a2e",
               edgecolor="#444444", labelcolor="white")

    # Annotate metrics
    info = ("Rise: {:.3f}s | Settle: {:.3f}s\n"
            "Overshoot: {:.1f}% | SS error: {:.3f} fps").format(
        m["rise_time_s"], m["settling_time_s"],
        m["overshoot_pct"], m["mean_ss_error"])
    ax1.text(0.02, 0.95, info, transform=ax1.transAxes, fontsize=9,
             color="#CCCCCC", verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a2e",
                       edgecolor="#444444"))

    # ---- Panel 2: PWM Duty ----
    ax2 = axes[1]
    ax2.plot(t, result["duty"], color="#FFaa33", linewidth=1.0)
    ax2.set_ylabel("PWM Duty (0-999)", color="white")
    ax2.set_ylim(0, PWM_DUTY_MAX + 50)
    ax2.axhline(PWM_DUTY_MIN, color="#666666", linewidth=0.8, linestyle=":", label="Min duty")
    ax2.axhline(PWM_DUTY_MAX, color="#666666", linewidth=0.8, linestyle=":", label="Max duty")
    ax2.legend(loc="lower right", fontsize=8, facecolor="#1a1a2e",
               edgecolor="#444444", labelcolor="white")

    # ---- Panel 3: Error ----
    ax3 = axes[2]
    ax3.plot(t, result["error"], color="#FF4488", linewidth=0.8, alpha=0.7)
    ax3.axhline(0, color="#00FF88", linewidth=0.5)
    # +/- 2% band
    target_last = result["target"][-1]
    band = target_last * 0.02
    ax3.axhline(band, color="#666666", linewidth=0.8, linestyle="--", label="+/- 2%")
    ax3.axhline(-band, color="#666666", linewidth=0.8, linestyle="--")
    ax3.set_ylabel("Error (fps)", color="white")
    ax3.set_xlabel("Time (seconds)", color="white")
    ax3.set_ylim(-max(5, np.max(np.abs(result["error"])) * 1.1),
                  max(5, np.max(np.abs(result["error"])) * 1.1))
    ax3.legend(loc="upper right", fontsize=8, facecolor="#1a1a2e",
               edgecolor="#444444", labelcolor="white")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(filename, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  Saved: {}".format(filename))


def print_metrics(results_list):
    """Print a summary comparison table."""
    sep = "=" * 72
    print(sep)
    print("  PID TUNING VALIDATION — SUMMARY")
    print(sep)
    print()
    print("  Firmware PID:  Kp={}, Ki={}, Kd={}, interval={}ms".format(
        PID_KP, PID_KI, PID_KD, PID_INTERVAL_MS))
    print("  Encoder noise: jitter=+/-{}%, miss rate=1/{}".format(
        JITTER_PCT * 100, int(1 / MISS_RATE)))
    print()

    header = "  {:<30} {:>10} {:>10} {:>10} {:>10} {:>12}".format(
        "Scenario", "Rise (s)", "Settle(s)", "Ovshoot%", "SS err", "SS fps")
    print(header)
    print("  " + "-" * 82)

    for r in results_list:
        m = r["metrics"]
        print("  {:<30} {:>10.3f} {:>10.3f} {:>10.1f} {:>10.3f} {:>12.2f}".format(
            m["name"],
            m["rise_time_s"],
            m["settling_time_s"],
            m["overshoot_pct"],
            m["mean_ss_error"],
            m["mean_ss_fps"]))

    print()

    # Pass/fail checks
    all_pass = True
    for r in results_list:
        m = r["metrics"]
        issues = []
        if abs(m["mean_ss_error"]) > 1.0:
            issues.append("SS error > 1 fps")
        if m["overshoot_pct"] > 25:
            issues.append("overshoot > 25%")
        if m["rise_time_s"] > 1.5:
            issues.append("rise time > 1.5s")
        if m["settling_time_s"] > 3.0:
            issues.append("settling > 3s")

        if issues:
            print("  WARN {}: {}".format(m["name"], ", ".join(issues)))
            all_pass = False
        else:
            print("  PASS {}".format(m["name"]))

    print()
    if all_pass:
        print("  ALL SCENARIOS PASSED — PID tuning is acceptable for hardware.")
    else:
        print("  SOME SCENARIOS HAVE WARNINGS — consider retuning PID gains.")
    print()
    print("  " + sep)


# =========================================================================
# Main
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="PID Encoder Signal Test Bench")
    parser.add_argument("--show", action="store_true", help="Try interactive plt.show()")
    args = parser.parse_args()

    np.random.seed(42)  # reproducible noise

    # ---- Scenario A: 18 fps from rest ----
    result_18 = run_scenario(
        name="18 fps startup + hold",
        duration_s=4.0,
        target_fps_func=lambda t: 18.0,
    )

    # ---- Scenario B: 24 fps from rest ----
    result_24 = run_scenario(
        name="24 fps startup + hold",
        duration_s=4.0,
        target_fps_func=lambda t: 24.0,
    )

    # ---- Scenario C: speed switch 18 → 24 fps ----
    def speed_switch(t):
        return 18.0 if t < 2.0 else 24.0

    result_switch = run_scenario(
        name="18 fps -> 24 fps switch at t=2s",
        duration_s=5.0,
        target_fps_func=speed_switch,
    )

    # ---- Output ----
    all_results = [result_18, result_24, result_switch]

    plot_scenario(result_18, "pid_test_18fps.png")
    plot_scenario(result_24, "pid_test_24fps.png")
    plot_scenario(result_switch, "pid_test_switch.png")

    print()
    print_metrics(all_results)


if __name__ == "__main__":
    main()
