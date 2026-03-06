"""Thermal analysis — heat sources, temperature rise, and film safety.

Estimates:
  - Motor I²R power dissipation at running current
  - Voltage regulator dissipation for logic and motor driver
  - Total internal heat generation
  - Steady-state body temperature rise via natural convection:
        dT = P_total / (h × A_surface)
        h  ~ 10 W/m²·K (natural convection, still air)
  - Film zone temperature check (must stay below 40°C, flag at 35°C)
  - Gate aperture dimensional shift from thermal expansion
"""

import math
from super8cam.specs.master_specs import (
    MOTOR, CAMERA, BATTERY, MATERIALS, GEARBOX, PCB,
)


# =========================================================================
# Physical constants
# =========================================================================

# Natural convection coefficient for a small enclosure in still air
H_CONVECTION = 10.0  # W/m²·K

# Ambient temperature assumption
T_AMBIENT_C = 25.0   # degC

# Film safety limits
FILM_MAX_TEMP_C = 40.0     # absolute max for Kodak film
FILM_WARNING_TEMP_C = 35.0  # flag a warning above this

# Motor winding resistance (estimated from stall test)
# R = V_nom / I_stall = 6.0 / 2.2 = 2.73 ohm
MOTOR_WINDING_R_OHM = MOTOR.nominal_voltage / (MOTOR.stall_current_ma / 1000.0)

# Voltage regulators
# 5V logic rail from battery pack (LDO or buck)
VREG_LOGIC_VIN = BATTERY.pack_voltage_nom      # 6.0 V
VREG_LOGIC_VOUT = 5.0                          # V
VREG_LOGIC_ILOAD_MA = 80.0                     # mA — MCU + encoder + LED

# Motor driver assumed to be a low-Rdson MOSFET (negligible loss vs motor I²R)
# but include a small estimate for driver IC quiescent + switching losses
DRIVER_QUIESCENT_W = 0.02  # W


# =========================================================================
# Main analysis
# =========================================================================

def motor_heat_estimate(fps: int = 24) -> dict:
    """Estimate motor power dissipation and steady-state temperature rise.

    Args:
        fps: Frame rate (18 or 24).

    Returns dict with all thermal parameters and pass/fail status.
    """
    # --- Motor operating point ---
    motor_rpm = fps * 60.0 * GEARBOX.ratio
    # Linear interpolation between no-load and stall
    # At no-load RPM: current = no_load_current
    # At stall (0 RPM): current = stall_current
    # Running current at motor_rpm:
    load_fraction = 1.0 - (motor_rpm / MOTOR.no_load_rpm)
    load_fraction = max(0.0, min(1.0, load_fraction))

    # Light mechanical load — cam + shutter + claw — approx 15% of stall range
    effective_load = load_fraction * 0.15
    motor_current_ma = MOTOR.no_load_current_ma + effective_load * (
        MOTOR.stall_current_ma - MOTOR.no_load_current_ma)
    motor_current_a = motor_current_ma / 1000.0

    # --- Motor I²R loss ---
    motor_i2r_w = motor_current_a ** 2 * MOTOR_WINDING_R_OHM

    # --- Motor total power input ---
    voltage = BATTERY.pack_voltage_nom
    motor_power_in_w = voltage * motor_current_a

    # --- Motor efficiency ---
    # Mechanical output = input - I²R - friction losses
    # Simplified: friction losses ~ 20% of I²R
    motor_friction_w = motor_i2r_w * 0.20
    motor_heat_total_w = motor_i2r_w + motor_friction_w

    # --- Voltage regulator dissipation ---
    # LDO: P = (Vin - Vout) × Iload
    vreg_logic_w = (VREG_LOGIC_VIN - VREG_LOGIC_VOUT) * (VREG_LOGIC_ILOAD_MA / 1000.0)

    # --- Motor driver losses ---
    driver_loss_w = DRIVER_QUIESCENT_W

    # --- Total internal heat ---
    total_heat_w = motor_heat_total_w + vreg_logic_w + driver_loss_w

    # --- Camera body surface area ---
    l = CAMERA.body_length / 1000.0  # m
    h = CAMERA.body_height / 1000.0
    d = CAMERA.body_depth / 1000.0
    surface_area_m2 = 2.0 * (l * h + l * d + h * d)
    surface_area_cm2 = surface_area_m2 * 1e4

    # --- Steady-state temperature rise ---
    # dT = P / (h × A)
    delta_t = total_heat_w / (H_CONVECTION * surface_area_m2)

    # --- Film zone temperature ---
    film_zone_temp = T_AMBIENT_C + delta_t
    film_safe = film_zone_temp < FILM_MAX_TEMP_C
    film_warning = film_zone_temp >= FILM_WARNING_TEMP_C

    # --- Gate aperture thermal expansion ---
    # Brass gate expands in the film plane
    brass = MATERIALS["brass_c360"]
    alu = MATERIALS["alu_6061_t6"]

    # Gate aperture width change
    gate_expansion_w_um = brass.thermal_expansion * delta_t * CAMERA.gate_plate_w / 1000.0
    # Gate aperture height change
    gate_expansion_h_um = brass.thermal_expansion * delta_t * CAMERA.gate_plate_h / 1000.0

    # Body shell expansion (for reference)
    body_expansion_l_um = alu.thermal_expansion * delta_t * CAMERA.body_length / 1000.0

    # --- Heat breakdown table ---
    heat_sources = [
        ("Motor I²R losses", motor_i2r_w),
        ("Motor friction losses", motor_friction_w),
        ("Logic voltage regulator", vreg_logic_w),
        ("Motor driver quiescent", driver_loss_w),
    ]

    return {
        "fps": fps,
        # Motor
        "motor_rpm": motor_rpm,
        "motor_current_ma": motor_current_ma,
        "motor_winding_r_ohm": MOTOR_WINDING_R_OHM,
        "power_input_w": motor_power_in_w,
        # Heat sources
        "motor_i2r_w": motor_i2r_w,
        "motor_friction_w": motor_friction_w,
        "vreg_logic_w": vreg_logic_w,
        "driver_loss_w": driver_loss_w,
        "heat_dissipation_w": total_heat_w,
        "heat_sources": heat_sources,
        # Convection
        "surface_area_cm2": surface_area_cm2,
        "h_convection_w_m2k": H_CONVECTION,
        "temp_rise_degc": delta_t,
        # Film safety
        "ambient_temp_c": T_AMBIENT_C,
        "film_zone_temp_c": film_zone_temp,
        "film_max_temp_c": FILM_MAX_TEMP_C,
        "film_warning_temp_c": FILM_WARNING_TEMP_C,
        "film_safe": film_safe,
        "film_warning": film_warning,
        # Thermal expansion
        "body_material": alu.name,
        "thermal_expansion_ppm_k": alu.thermal_expansion,
        "gate_material": brass.name,
        "gate_expansion_um": gate_expansion_w_um,
        "gate_expansion_w_um": gate_expansion_w_um,
        "gate_expansion_h_um": gate_expansion_h_um,
        "body_expansion_l_um": body_expansion_l_um,
        "note": "Gate aperture shift due to thermal expansion",
    }


# =========================================================================
# Full report
# =========================================================================

def print_thermal_report():
    """Print a comprehensive thermal analysis report."""
    sep = "=" * 68
    print(sep)
    print("  THERMAL ANALYSIS REPORT")
    print(sep)

    for fps in [18, 24]:
        th = motor_heat_estimate(fps)

        print(f"\n  OPERATING POINT: {fps} fps")
        print("  " + "-" * 55)

        # Motor operating point
        print(f"    Motor speed:             {th['motor_rpm']:.0f} RPM")
        print(f"    Motor current:           {th['motor_current_ma']:.0f} mA")
        print(f"    Motor winding resistance:{th['motor_winding_r_ohm']:.2f} ohm")
        print(f"    Motor power input:       {th['power_input_w']:.3f} W")

        # Heat sources
        print(f"\n    HEAT SOURCES")
        print(f"    {'Source':<30s}  {'Power':>8s}")
        print("    " + "-" * 42)
        for name, power in th["heat_sources"]:
            print(f"    {name:<30s}  {power:>8.4f} W")
        print(f"    {'TOTAL':<30s}  {th['heat_dissipation_w']:>8.4f} W")

        # Temperature rise
        print(f"\n    TEMPERATURE")
        print(f"    Body surface area:       {th['surface_area_cm2']:.0f} cm²")
        print(f"    Convection coefficient:  {th['h_convection_w_m2k']:.0f} W/m²·K")
        print(f"    Ambient:                 {th['ambient_temp_c']:.0f} °C")
        print(f"    Temperature rise:        {th['temp_rise_degc']:.1f} °C")
        print(f"    Film zone temperature:   {th['film_zone_temp_c']:.1f} °C")

        # Film safety
        status = "SAFE" if th["film_safe"] else "EXCEEDED — REDESIGN NEEDED"
        if th["film_warning"] and th["film_safe"]:
            status = "WARNING — approaching limit"
        print(f"    Film temp limit:         {th['film_max_temp_c']:.0f} °C")
        print(f"    Film status:             {status}")

        if not th["film_safe"]:
            print(f"    *** FILM ZONE TEMP {th['film_zone_temp_c']:.1f} °C "
                  f"EXCEEDS {th['film_max_temp_c']:.0f} °C LIMIT ***")
        elif th["film_warning"]:
            print(f"    *** WARNING: Film zone temp {th['film_zone_temp_c']:.1f} °C "
                  f">= {th['film_warning_temp_c']:.0f} °C warning threshold ***")

        # Thermal expansion
        print(f"\n    THERMAL EXPANSION")
        print(f"    Gate ({th['gate_material']}):")
        print(f"      Width expansion:       {th['gate_expansion_w_um']:.3f} um")
        print(f"      Height expansion:      {th['gate_expansion_h_um']:.3f} um")
        print(f"    Body ({th['body_material']}):")
        print(f"      Length expansion:       {th['body_expansion_l_um']:.3f} um")

    print("\n  " + sep)


if __name__ == "__main__":
    print_thermal_report()
