"""Thermal analysis — complete heat budget and temperature rise estimation.

Computes all heat sources inside the camera body and estimates the
steady-state temperature rise using a simplified lumped-parameter model.

Heat sources:
  1. Motor I²R losses (winding resistance × running current²)
  2. Motor iron/friction losses (mechanical inefficiency)
  3. Voltage regulator dissipation (linear dropout: (Vin-Vout) × Iload)
  4. PCB electronics (quiescent + active draw)

Thermal model:
  ΔT = P_total / (h × A_surface)
  where h ≈ 10 W/m²·K (natural convection in still air)
  and A_surface = camera body exterior surface area

Film temperature limit: 35°C in the film zone (gate area).
The film gate is connected to the body via aluminum conduction, so
the gate temperature rises with the body but with a slight lag.
Brass (film gate) has lower thermal expansion than aluminum (body),
so the gate aperture shift is modest.

Flags if film zone exceeds 35°C (film base softening onset ~60°C,
but emulsion sensitivity drift begins above 35°C for color stocks).
"""

import math
from super8cam.specs.master_specs import (
    MOTOR, CAMERA, BATTERY, MATERIALS, GEARBOX, PCB, FILM, ANALYSIS,
)


# =========================================================================
# MOTOR ELECTRICAL MODEL
# =========================================================================

# Motor winding resistance estimated from stall current and voltage
# R = V / I_stall = 6.0V / 2.2A = 2.73Ω
MOTOR_WINDING_RESISTANCE_OHM = MOTOR.nominal_voltage / (
    MOTOR.stall_current_ma / 1000.0)  # ~2.73 Ω

# Motor friction torque (estimated from no-load current)
# P_friction_noload = V × I_noload = 6.0 × 0.120 = 0.72W
# This includes windage, bearing friction, brush friction
MOTOR_FRICTION_POWER_W = (MOTOR.nominal_voltage
                           * MOTOR.no_load_current_ma / 1000.0)


# =========================================================================
# VOLTAGE REGULATORS
# =========================================================================
# The PCB has two voltage regulators:
#   1. Motor driver: MOSFET H-bridge (PWM), very low dropout (~0.1V × I_motor)
#   2. Logic regulator: 3.3V LDO from battery (dropout = Vbat - 3.3V)

LOGIC_VOLTAGE_V = ANALYSIS.logic_voltage_v               # was 3.3
LOGIC_CURRENT_MA = ANALYSIS.logic_current_ma             # was 50.0
MOTOR_DRIVER_DROPOUT_V = ANALYSIS.motor_driver_dropout_v # was 0.2

# PCB components (LEDs, pull-ups, etc)
PCB_MISC_POWER_MW = ANALYSIS.pcb_misc_power_mw           # was 30.0


# =========================================================================
# AMBIENT CONDITIONS
# =========================================================================
AMBIENT_TEMP_C = ANALYSIS.ambient_temp_c                 # was 25.0
NATURAL_CONVECTION_H = ANALYSIS.natural_convection_h     # was 10.0
FORCED_CONVECTION_H = ANALYSIS.forced_convection_h       # was 25.0

# Film temperature limits
FILM_ZONE_LIMIT_C = ANALYSIS.film_zone_limit_c           # was 35.0
FILM_ABSOLUTE_LIMIT_C = ANALYSIS.film_absolute_limit_c   # was 50.0


# =========================================================================
# SURFACE AREA
# =========================================================================

def body_surface_area_m2() -> float:
    """Compute camera body exterior surface area in m²."""
    L = CAMERA.body_length  # 148 mm
    H = CAMERA.body_height  # 88 mm
    D = CAMERA.body_depth   # 52 mm

    # Rectangular box approximation (6 faces)
    area_mm2 = 2 * (L * H + L * D + H * D)
    return area_mm2 * 1e-6  # convert to m²


# =========================================================================
# HEAT SOURCE CALCULATIONS
# =========================================================================

def motor_heat(fps: int = 24) -> dict:
    """Compute motor heat dissipation at given frame rate.

    The motor operates at a specific RPM determined by the gear ratio and
    frame rate. The operating current is estimated from the motor's
    speed-torque characteristic (linear model).

    Returns dict with I²R losses, friction losses, total motor heat.
    """
    # Motor RPM at operating point
    shaft_rpm = fps * 60  # 1 rev per frame
    motor_rpm = shaft_rpm * GEARBOX.ratio

    # Motor current from linear speed-torque model:
    # I = I_noload + (I_stall - I_noload) × (1 - RPM/RPM_noload) × load_factor
    # The camera mechanism is a light load (~15% of rated torque).
    load_factor = ANALYSIS.motor_load_factor  # light mechanical load
    rpm_fraction = motor_rpm / MOTOR.no_load_rpm
    current_ma = (MOTOR.no_load_current_ma +
                  (MOTOR.stall_current_ma - MOTOR.no_load_current_ma)
                  * (1 - rpm_fraction) * load_factor)
    current_a = current_ma / 1000.0

    # I²R copper losses in winding
    i2r_loss_w = current_a ** 2 * MOTOR_WINDING_RESISTANCE_OHM

    # Mechanical friction losses (roughly proportional to speed)
    # Scale from no-load friction power
    friction_loss_w = MOTOR_FRICTION_POWER_W * (motor_rpm / MOTOR.no_load_rpm)

    # Total motor electrical input
    voltage = BATTERY.pack_voltage_nom
    power_in_w = voltage * current_a

    # Mechanical output
    mech_output_w = power_in_w - i2r_loss_w - friction_loss_w
    efficiency = mech_output_w / power_in_w if power_in_w > 0 else 0

    total_motor_heat_w = i2r_loss_w + friction_loss_w

    return {
        "fps": fps,
        "motor_rpm": motor_rpm,
        "motor_current_ma": current_ma,
        "motor_current_a": current_a,
        "winding_resistance_ohm": MOTOR_WINDING_RESISTANCE_OHM,
        "i2r_loss_w": i2r_loss_w,
        "friction_loss_w": friction_loss_w,
        "total_motor_heat_w": total_motor_heat_w,
        "power_input_w": power_in_w,
        "mech_output_w": max(0, mech_output_w),
        "efficiency_pct": efficiency * 100,
    }


def regulator_heat(fps: int = 24) -> dict:
    """Compute voltage regulator heat dissipation.

    Two regulators:
      1. Motor driver (PWM MOSFET): Rds_on × I_motor²
      2. Logic LDO (3.3V from battery): (Vbat - 3.3V) × I_logic
    """
    mh = motor_heat(fps)
    v_bat = BATTERY.pack_voltage_nom  # 6.0V

    # Motor driver: MOSFET switching losses + conduction
    # Approximate: dropout_V × motor_current
    driver_heat_w = MOTOR_DRIVER_DROPOUT_V * mh["motor_current_a"]

    # Logic LDO: linear dropout
    ldo_dropout_v = v_bat - LOGIC_VOLTAGE_V  # 6.0 - 3.3 = 2.7V
    ldo_current_a = LOGIC_CURRENT_MA / 1000.0
    ldo_heat_w = ldo_dropout_v * ldo_current_a

    # PCB misc
    pcb_misc_w = PCB_MISC_POWER_MW / 1000.0

    total_reg_heat_w = driver_heat_w + ldo_heat_w + pcb_misc_w

    return {
        "driver_heat_w": driver_heat_w,
        "driver_dropout_v": MOTOR_DRIVER_DROPOUT_V,
        "ldo_heat_w": ldo_heat_w,
        "ldo_dropout_v": ldo_dropout_v,
        "ldo_current_ma": LOGIC_CURRENT_MA,
        "pcb_misc_w": pcb_misc_w,
        "total_regulator_heat_w": total_reg_heat_w,
    }


# =========================================================================
# FULL THERMAL ANALYSIS
# =========================================================================

def motor_heat_estimate(fps: int = 24) -> dict:
    """Complete thermal analysis at given frame rate.

    Computes total heat budget, steady-state body temperature rise,
    film zone temperature, and gate thermal expansion.

    This is the main entry point — backward compatible with original API.
    """
    mh = motor_heat(fps)
    rh = regulator_heat(fps)

    # Total heat generated inside camera
    total_heat_w = mh["total_motor_heat_w"] + rh["total_regulator_heat_w"]

    # Surface area
    a_surface_m2 = body_surface_area_m2()
    a_surface_cm2 = a_surface_m2 * 1e4

    # Steady-state body temperature rise (natural convection)
    delta_t_natural = total_heat_w / (NATURAL_CONVECTION_H * a_surface_m2)

    # With light forced convection (walking/handheld)
    delta_t_forced = total_heat_w / (FORCED_CONVECTION_H * a_surface_m2)

    # Absolute temperatures
    body_temp_natural = AMBIENT_TEMP_C + delta_t_natural
    body_temp_forced = AMBIENT_TEMP_C + delta_t_forced

    # Film zone temperature
    # The film gate is thermally connected to the body via aluminum
    # conduction. The motor is the main heat source, located ~50mm from
    # the gate. The thermal resistance from motor to gate is higher than
    # motor to body exterior, so the gate temperature is between the
    # motor temperature and body exterior temperature.
    #
    # Simplified: gate temp ≈ body_exterior + 0.3 × (motor_temp - body_exterior)
    # Motor temperature rises more than body (concentrated heat source).
    # Motor thermal resistance to body: ~10 K/W (small contact area)
    motor_temp_rise = mh["total_motor_heat_w"] * ANALYSIS.motor_thermal_resistance  # K/W × W
    motor_temp = AMBIENT_TEMP_C + motor_temp_rise

    # Gate temperature: body exterior + fraction of motor-to-body gradient
    gate_fraction = ANALYSIS.gate_thermal_fraction  # thermal coupling factor (0=body temp, 1=motor temp)
    gate_temp_natural = (body_temp_natural +
                         gate_fraction * (motor_temp - body_temp_natural))
    gate_temp_forced = (body_temp_forced +
                        gate_fraction * (motor_temp - body_temp_forced))

    # Film zone temperature (worst case = natural convection)
    film_zone_temp = gate_temp_natural
    film_zone_ok = film_zone_temp < FILM_ZONE_LIMIT_C
    film_zone_absolute_ok = film_zone_temp < FILM_ABSOLUTE_LIMIT_C

    # Gate thermal expansion
    # Brass gate: aperture expands with temperature
    brass = MATERIALS["brass_c360"]
    alu = MATERIALS["alu_6061_t6"]
    gate_delta_t = gate_temp_natural - AMBIENT_TEMP_C

    # Aperture width change: ΔW = α × ΔT × W
    aperture_expansion_w_um = (brass.thermal_expansion * gate_delta_t
                                * FILM.frame_w)  # μm (ppm/K × K × mm = μm)
    aperture_expansion_h_um = (brass.thermal_expansion * gate_delta_t
                                * FILM.frame_h)

    # Body expansion (aluminum)
    body_expansion_um = (alu.thermal_expansion * delta_t_natural
                          * CAMERA.body_length)

    # Battery life impact: higher current = shorter runtime
    total_current_ma = mh["motor_current_ma"] + LOGIC_CURRENT_MA
    battery_life_min = (BATTERY.cell_capacity_mah / total_current_ma) * 60

    return {
        "fps": fps,
        # Motor
        "motor_current_ma": mh["motor_current_ma"],
        "motor_rpm": mh["motor_rpm"],
        "i2r_loss_w": mh["i2r_loss_w"],
        "friction_loss_w": mh["friction_loss_w"],
        "motor_heat_w": mh["total_motor_heat_w"],
        "motor_efficiency_pct": mh["efficiency_pct"],
        "power_input_w": mh["power_input_w"],
        # Regulators
        "driver_heat_w": rh["driver_heat_w"],
        "ldo_heat_w": rh["ldo_heat_w"],
        "pcb_misc_w": rh["pcb_misc_w"],
        "regulator_heat_w": rh["total_regulator_heat_w"],
        # Total
        "heat_dissipation_w": total_heat_w,
        "surface_area_cm2": a_surface_cm2,
        # Temperature rise
        "temp_rise_degc": delta_t_natural,
        "temp_rise_forced_degc": delta_t_forced,
        "body_temp_natural_c": body_temp_natural,
        "body_temp_forced_c": body_temp_forced,
        "motor_temp_c": motor_temp,
        "gate_temp_natural_c": gate_temp_natural,
        "gate_temp_forced_c": gate_temp_forced,
        # Film zone
        "film_zone_temp_c": film_zone_temp,
        "film_zone_limit_c": FILM_ZONE_LIMIT_C,
        "film_zone_ok": film_zone_ok,
        "film_zone_absolute_ok": film_zone_absolute_ok,
        # Thermal expansion
        "gate_expansion_w_um": aperture_expansion_w_um,
        "gate_expansion_h_um": aperture_expansion_h_um,
        "gate_expansion_um": aperture_expansion_w_um,  # backward compat
        "body_expansion_um": body_expansion_um,
        "body_material": alu.name,
        "thermal_expansion_ppm_k": alu.thermal_expansion,
        # Power budget
        "total_current_ma": total_current_ma,
        "battery_life_min": battery_life_min,
        "note": "Gate aperture shift due to thermal expansion",
    }


# =========================================================================
# REPORTING
# =========================================================================

def print_thermal_report():
    """Print comprehensive thermal analysis for both frame rates."""
    sep = "=" * 68

    print(f"\n{sep}")
    print("  THERMAL ANALYSIS")
    print(sep)

    print(f"\n  MOTOR ELECTRICAL MODEL")
    print(f"  {'-' * 55}")
    print(f"    Motor: {MOTOR.model}")
    print(f"    Winding resistance: {MOTOR_WINDING_RESISTANCE_OHM:.2f} Ω "
          f"(V_nom / I_stall)")
    print(f"    No-load friction power: {MOTOR_FRICTION_POWER_W:.2f} W")
    print(f"    Battery: {BATTERY.cell_count}×{BATTERY.cell_type} "
          f"({BATTERY.pack_voltage_nom}V)")

    print(f"\n  CAMERA BODY")
    print(f"  {'-' * 55}")
    a_m2 = body_surface_area_m2()
    print(f"    Envelope: {CAMERA.body_length}×{CAMERA.body_height}×"
          f"{CAMERA.body_depth} mm")
    print(f"    Surface area: {a_m2 * 1e4:.0f} cm² ({a_m2:.6f} m²)")
    print(f"    h (natural convection): {NATURAL_CONVECTION_H} W/m²·K")
    print(f"    h (forced, walking): {FORCED_CONVECTION_H} W/m²·K")
    print(f"    Ambient: {AMBIENT_TEMP_C}°C")

    for fps in [18, 24]:
        th = motor_heat_estimate(fps)

        print(f"\n  {'='*55}")
        print(f"  ANALYSIS @ {fps} fps")
        print(f"  {'='*55}")

        print(f"\n  HEAT SOURCES")
        print(f"  {'-' * 55}")
        print(f"    Motor RPM:          {th['motor_rpm']:.0f}")
        print(f"    Motor current:      {th['motor_current_ma']:.0f} mA")
        print(f"    Motor I²R loss:     {th['i2r_loss_w']:.4f} W "
              f"({th['motor_current_ma']/1000:.3f}A² × "
              f"{MOTOR_WINDING_RESISTANCE_OHM:.2f}Ω)")
        print(f"    Motor friction:     {th['friction_loss_w']:.4f} W")
        print(f"    Motor total heat:   {th['motor_heat_w']:.4f} W")
        print(f"    Motor efficiency:   {th['motor_efficiency_pct']:.1f}%")
        print(f"    Driver (MOSFET):    {th['driver_heat_w']:.4f} W")
        print(f"    Logic LDO:          {th['ldo_heat_w']:.4f} W "
              f"({BATTERY.pack_voltage_nom}-{LOGIC_VOLTAGE_V}V × "
              f"{LOGIC_CURRENT_MA:.0f}mA)")
        print(f"    PCB misc:           {th['pcb_misc_w']:.4f} W")
        print(f"    Regulator total:    {th['regulator_heat_w']:.4f} W")
        print(f"    ────────────────────────────────")
        print(f"    TOTAL HEAT:         {th['heat_dissipation_w']:.4f} W")

        print(f"\n  TEMPERATURE RISE")
        print(f"  {'-' * 55}")
        print(f"    Body (natural):     {th['temp_rise_degc']:.1f}°C rise → "
              f"{th['body_temp_natural_c']:.1f}°C")
        print(f"    Body (forced):      {th['temp_rise_forced_degc']:.1f}°C rise → "
              f"{th['body_temp_forced_c']:.1f}°C")
        print(f"    Motor housing:      {th['motor_temp_c'] - AMBIENT_TEMP_C:.1f}°C rise → "
              f"{th['motor_temp_c']:.1f}°C")
        print(f"    Gate (natural):     {th['gate_temp_natural_c'] - AMBIENT_TEMP_C:.1f}°C rise → "
              f"{th['gate_temp_natural_c']:.1f}°C")

        print(f"\n  FILM ZONE CHECK")
        print(f"  {'-' * 55}")
        film_status = "PASS" if th["film_zone_ok"] else "FAIL"
        print(f"    Film zone temp:     {th['film_zone_temp_c']:.1f}°C "
              f"(limit {FILM_ZONE_LIMIT_C}°C) [{film_status}]")
        if not th["film_zone_ok"]:
            excess = th["film_zone_temp_c"] - FILM_ZONE_LIMIT_C
            print(f"    *** WARNING: Film zone {excess:.1f}°C above limit! ***")
            print(f"    *** Color film emulsion sensitivity may drift. ***")
            if not th["film_zone_absolute_ok"]:
                print(f"    *** CRITICAL: Film base softening risk above "
                      f"{FILM_ABSOLUTE_LIMIT_C}°C! ***")

        print(f"\n  THERMAL EXPANSION")
        print(f"  {'-' * 55}")
        print(f"    Gate aperture ΔW:   {th['gate_expansion_w_um']:.2f} μm "
              f"(brass, {FILM.frame_w}mm × "
              f"{MATERIALS['brass_c360'].thermal_expansion} ppm/K)")
        print(f"    Gate aperture ΔH:   {th['gate_expansion_h_um']:.2f} μm")
        print(f"    Body length change: {th['body_expansion_um']:.1f} μm "
              f"(alu 6061, {CAMERA.body_length}mm)")

        print(f"\n  POWER BUDGET")
        print(f"  {'-' * 55}")
        print(f"    Total current:      {th['total_current_ma']:.0f} mA")
        print(f"    Battery life:       {th['battery_life_min']:.0f} min "
              f"({th['battery_life_min']/60:.1f} hr)")

    print(f"\n{sep}")
    # Overall assessment
    th24 = motor_heat_estimate(24)
    if th24["film_zone_ok"]:
        print("  OVERALL: THERMAL DESIGN ACCEPTABLE")
        print(f"  Film zone stays below {FILM_ZONE_LIMIT_C}°C at all frame rates.")
    else:
        print("  OVERALL: THERMAL DESIGN NEEDS ATTENTION")
        print(f"  Film zone exceeds {FILM_ZONE_LIMIT_C}°C at 24fps.")
        print("  Consider: thermal pad between motor and body, venting, or")
        print("  thermal barrier between motor zone and film gate zone.")
    print(sep)

    return motor_heat_estimate(24)  # return 24fps data for build.py


if __name__ == "__main__":
    print_thermal_report()
