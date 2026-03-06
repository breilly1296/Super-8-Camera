#!/usr/bin/env python3
"""Super 8 Camera Battery Life Calculator

Models total system power draw, estimates runtime and cartridges per
battery set, and plots a voltage-sag derating curve showing how motor
speed degrades over the discharge cycle.

Power source: 4x AA cells in series (6V nominal).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Battery specifications
# ---------------------------------------------------------------------------
NUM_CELLS = 4

BATTERY_TYPES = {
    "Alkaline": {
        "capacity_mAh": 2800,       # at moderate drain (~200 mA)
        "v_fresh": 1.60,            # V per cell, fresh off shelf
        "v_nominal": 1.50,          # V per cell, nominal
        "v_cutoff": 1.00,           # V per cell, effective empty
        # Piecewise-linear discharge profile: (fraction_used, voltage_per_cell)
        # Approximates a typical alkaline AA curve at ~200 mA drain
        "discharge_curve": [
            (0.00, 1.60),
            (0.05, 1.50),
            (0.15, 1.45),
            (0.40, 1.30),
            (0.60, 1.20),
            (0.80, 1.10),
            (0.90, 1.05),
            (1.00, 1.00),
        ],
    },
    "NiMH": {
        "capacity_mAh": 2000,
        "v_fresh": 1.40,
        "v_nominal": 1.20,
        "v_cutoff": 1.00,
        # NiMH has a flatter discharge plateau
        "discharge_curve": [
            (0.00, 1.40),
            (0.05, 1.30),
            (0.10, 1.25),
            (0.70, 1.22),
            (0.85, 1.20),
            (0.90, 1.15),
            (0.95, 1.10),
            (1.00, 1.00),
        ],
    },
}


# ---------------------------------------------------------------------------
# Component current draws (mA)
# ---------------------------------------------------------------------------
COMPONENTS = {
    "DC motor (FF-130, loaded)":  200.0,
    "STM32L0 MCU (active)":        5.0,
    "Motor driver IC (quiescent)":  2.0,
    "Metering photodiode circuit":  1.0,
    "Voltage regulators (2x)":      0.1,   # 50 uA each
    "Viewfinder LED":              10.0,
}


# ---------------------------------------------------------------------------
# Camera parameters
# ---------------------------------------------------------------------------
FRAME_RATES = [18, 24]

# Cartridge run times (50 ft Super 8 cartridge)
CARTRIDGE_TIME = {18: 3.333, 24: 2.500}  # minutes

# Mabuchi FF-130 motor characteristics
MOTOR_RATED_RPM = 6600   # at rated voltage
MOTOR_RATED_V = 3.0      # rated voltage
MOTOR_NO_LOAD_RPM = 9600 # free-running RPM at rated voltage

# The motor driver uses PWM to regulate the motor to the target shaft RPM.
# Under load the motor needs a certain voltage to sustain the required RPM.
# The driver can deliver at most (V_pack - driver_drop) to the motor.
# When pack voltage sags below what the driver needs, it can no longer
# maintain the target RPM and the motor (and frame rate) slows down.
DRIVER_DROP_V = 0.3       # H-bridge / driver saturation drop (V)
MCU_REG_HEADROOM_V = 0.5  # LDO headroom for 3.3V MCU regulator

# Target motor voltages at each fps (derived from drivetrain gear ratios):
#   main_shaft_rpm = fps * 60
#   gear_ratio = MOTOR_RATED_RPM / main_shaft_rpm  (from drivetrain calc)
#   motor_rpm_needed = main_shaft_rpm * gear_ratio = fps * 60 * gear_ratio
#   But with load, motor draws current and speed drops from back-EMF.
#   V_motor = V_rated * (RPM_target / RPM_no_load_at_rated)  approximately
# For a loaded FF-130 at the required RPMs:
#   18 fps: shaft=1080 RPM, gear=6.11:1, motor=6600 RPM -> V~2.06V
#   24 fps: shaft=1440 RPM, gear=4.58:1, motor=6600 RPM -> V~2.06V
# Both need ~2.1V at the motor terminals (same motor RPM, different gearing).
# Under load the motor draws more current, increasing I*R losses in the
# windings, so we need somewhat more voltage.  Estimate ~2.5V under load.
MOTOR_V_NEEDED_LOADED = 2.5  # V needed at motor terminals under load


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------

def total_system_current_mA():
    """Sum of all component draws at nominal voltage."""
    return sum(COMPONENTS.values())


def system_current_at_voltage(v_pack, v_nominal):
    """Estimate real system current accounting for constant-power motor load.

    The motor driver maintains target RPM via PWM.  As voltage drops, the
    driver increases duty cycle, drawing more current to deliver the same
    mechanical power.  P = V * I = const, so I increases as V decreases.

    Other components (MCU, LED, etc.) draw roughly constant current.
    """
    motor_nominal_mA = COMPONENTS["DC motor (FF-130, loaded)"]
    other_mA = sum(v for k, v in COMPONENTS.items()
                   if k != "DC motor (FF-130, loaded)")

    # Motor current scales inversely with voltage (constant power)
    # Clamp ratio to avoid unrealistic values at very low voltage
    v_ratio = max(v_pack / v_nominal, 0.5)
    motor_current = motor_nominal_mA / v_ratio

    return motor_current + other_mA


def runtime_minutes(capacity_mAh, current_mA):
    """Ideal runtime in minutes from capacity and current."""
    return (capacity_mAh / current_mA) * 60


def cartridges_per_set(runtime_min, fps):
    """Number of 50-ft cartridges that fit in the runtime."""
    return runtime_min / CARTRIDGE_TIME[fps]


def interpolate_discharge(curve, n_points=200):
    """Interpolate a discharge curve to n evenly-spaced points.

    Returns (fraction_used, voltage_per_cell) arrays.
    """
    fracs = [p[0] for p in curve]
    volts = [p[1] for p in curve]
    frac_interp = np.linspace(0, 1, n_points)
    volt_interp = np.interp(frac_interp, fracs, volts)
    return frac_interp, volt_interp


def motor_speed_fraction(pack_voltage):
    """Motor speed as fraction of target RPM given pack voltage.

    The motor driver regulates via PWM to maintain target RPM as long as the
    pack voltage is high enough.  Once V_pack drops below the minimum needed
    (motor voltage + driver drop), the driver saturates at 100% duty and motor
    speed becomes proportional to available voltage.

    Returns 1.0 when pack can sustain target, <1.0 when it cannot.
    """
    v_available = max(pack_voltage - DRIVER_DROP_V, 0)
    v_needed = MOTOR_V_NEEDED_LOADED

    if v_available >= v_needed:
        return 1.0
    else:
        return v_available / v_needed


def derating_curve(btype, fps, n_points=200):
    """Compute voltage-sag derating over battery life.

    Returns dict with arrays for plotting and the cartridge-count axis.
    """
    info = BATTERY_TYPES[btype]
    frac, v_cell = interpolate_discharge(info["discharge_curve"], n_points)
    v_pack = v_cell * NUM_CELLS
    v_nom = info["v_nominal"] * NUM_CELLS

    # Compute current at each point in the discharge and integrate for runtime.
    # Each step consumes a fraction (1/n_points) of total capacity.
    nominal_current = total_system_current_mA()
    capacity_mAh = info["capacity_mAh"]
    slice_mAh = capacity_mAh / n_points  # charge consumed per slice

    currents = np.array([system_current_at_voltage(v, v_nom) for v in v_pack])
    slice_hours = slice_mAh / currents  # hours per slice
    time_min = np.cumsum(slice_hours) * 60
    total_runtime_min = time_min[-1]
    carts = time_min / CARTRIDGE_TIME[fps]

    speed_frac = np.array([motor_speed_fraction(v) for v in v_pack])
    effective_fps = fps * speed_frac

    # Usable cartridges: motor can still hit target RPM (speed_frac == 1.0)
    regulated_mask = speed_frac >= 1.0
    regulated_carts = carts[regulated_mask][-1] if np.any(regulated_mask) else 0

    # Degraded but usable: speed >= 90% of target
    usable_mask = speed_frac >= 0.90
    usable_carts = carts[usable_mask][-1] if np.any(usable_mask) else 0

    # MCU minimum voltage (3.3V LDO needs headroom)
    mcu_min_pack_v = 3.3 + MCU_REG_HEADROOM_V  # 3.8V
    mcu_alive_mask = v_pack >= mcu_min_pack_v
    mcu_alive_carts = carts[mcu_alive_mask][-1] if np.any(mcu_alive_mask) else 0

    return {
        "frac": frac,
        "v_pack": v_pack,
        "time_min": time_min,
        "cartridges": carts,
        "speed_frac": speed_frac,
        "effective_fps": effective_fps,
        "regulated_cartridges": regulated_carts,
        "usable_cartridges": usable_carts,
        "mcu_alive_cartridges": mcu_alive_carts,
        "total_runtime_min": total_runtime_min,
        "total_cartridges": carts[-1],
    }


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

def print_report():
    sep = "=" * 68
    print(sep)
    print("  SUPER 8 CAMERA BATTERY LIFE CALCULATOR")
    print(sep)

    # Component breakdown
    print()
    print("  Component current draw:")
    total = 0
    for name, ma in COMPONENTS.items():
        print(f"    {name:<34} {ma:>7.1f} mA")
        total += ma
    print(f"    {'':─<34} {'':─>7}───")
    print(f"    {'TOTAL SYSTEM CURRENT':<34} {total:>7.1f} mA")

    print()
    print(f"  Power source: {NUM_CELLS}x AA cells in series")
    print()

    # Per-battery-type, per-fps results
    for btype, info in BATTERY_TYPES.items():
        v_nom = info["v_nominal"] * NUM_CELLS
        print(f"  ┌── {btype} ({info['capacity_mAh']} mAh, "
              f"{v_nom:.1f}V nominal) ──")

        for fps in FRAME_RATES:
            dr = derating_curve(btype, fps)

            print(f"  │")
            print(f"  │  @ {fps} fps  "
                  f"(cartridge = {CARTRIDGE_TIME[fps]:.1f} min):")
            print(f"  │    Runtime (integrated):      "
                  f"{dr['total_runtime_min']:>6.1f} min")
            print(f"  │    Cartridges (total energy):  "
                  f"{dr['total_cartridges']:>5.1f}")
            print(f"  │    Cartridges (regulated):     "
                  f"{dr['regulated_cartridges']:>5.1f}  "
                  f"(motor holds target RPM)")
            print(f"  │    Cartridges (>90% speed):    "
                  f"{dr['usable_cartridges']:>5.1f}  "
                  f"(degraded but usable)")
            print(f"  │    Cartridges (MCU alive):     "
                  f"{dr['mcu_alive_cartridges']:>5.1f}  "
                  f"(V_pack >= 3.8V)")

        print(f"  └{'':─<50}")
        print()

    print(sep)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_derating(filename="super8_battery_life.png"):
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    fig.suptitle("Super 8 Camera – Battery Voltage & Motor Speed vs Cartridges Shot",
                 fontsize=13, fontweight="bold")

    colors = {"Alkaline": "#e67e22", "NiMH": "#27ae60"}
    styles = {18: "-", 24: "--"}

    # --- Top plot: pack voltage vs cartridges ---
    ax1 = axes[0]
    for btype in BATTERY_TYPES:
        for fps in FRAME_RATES:
            dr = derating_curve(btype, fps)
            lbl = f"{btype} @ {fps} fps"
            ax1.plot(dr["cartridges"], dr["v_pack"],
                     color=colors[btype], linestyle=styles[fps],
                     linewidth=1.5, label=lbl)

    # Cutoff lines
    for btype, info in BATTERY_TYPES.items():
        v_cut = info["v_cutoff"] * NUM_CELLS
        ax1.axhline(v_cut, color=colors[btype], linestyle=":",
                    linewidth=0.8, alpha=0.6)

    # Motor driver saturation voltage & MCU minimum
    v_motor_min = MOTOR_V_NEEDED_LOADED + DRIVER_DROP_V
    ax1.axhline(v_motor_min, color="#8e44ad", linestyle="-.", linewidth=1.0,
                alpha=0.8, label=f"Motor min ({v_motor_min:.1f}V)")
    mcu_min = 3.3 + MCU_REG_HEADROOM_V
    ax1.axhline(mcu_min, color="#c0392b", linestyle="-.", linewidth=1.0,
                alpha=0.8, label=f"MCU min ({mcu_min:.1f}V)")

    ax1.set_ylabel("Pack voltage (V)")
    ax1.set_title("Battery discharge over cartridges shot", fontsize=10)
    ax1.legend(fontsize=8, loc="lower left")
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(3.0, 7.0)

    # --- Bottom plot: motor speed fraction vs cartridges ---
    ax2 = axes[1]
    for btype in BATTERY_TYPES:
        for fps in FRAME_RATES:
            dr = derating_curve(btype, fps)
            lbl = f"{btype} @ {fps} fps"
            ax2.plot(dr["cartridges"], dr["speed_frac"] * 100,
                     color=colors[btype], linestyle=styles[fps],
                     linewidth=1.5, label=lbl)

    # Threshold lines
    ax2.axhline(100, color="#2980b9", linestyle=":", linewidth=0.8,
                alpha=0.7, label="Target RPM (regulated)")
    ax2.axhline(90, color="#c0392b", linestyle="-.", linewidth=1.0,
                label="90% min usable speed")

    # Shade degraded zone
    ax2.axhspan(0, 90, color="#fee2e2", alpha=0.2, zorder=0)

    ax2.set_ylabel("Motor speed (% of target)")
    ax2.set_xlabel("Cartridges shot (50 ft each)")
    ax2.set_title("Motor speed derating from voltage sag", fontsize=10)
    ax2.legend(fontsize=8, loc="lower left")
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(40, 110)

    plt.tight_layout()
    fig.savefig(filename, dpi=150)
    print(f"\n  Plot saved to {filename}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print_report()
    plot_derating()


if __name__ == "__main__":
    main()
