"""Thermal analysis — motor heat dissipation and body temperature rise."""

from super8cam.specs.master_specs import MOTOR, CAMERA, BATTERY, MATERIALS, GEARBOX


def motor_heat_estimate(fps: int = 24):
    """Estimate motor power dissipation and steady-state temperature rise."""
    # Motor current at operating point (interpolated between no-load and stall)
    motor_rpm = fps * 60 * GEARBOX.ratio
    load_fraction = 1 - (motor_rpm / MOTOR.no_load_rpm)
    current_ma = MOTOR.no_load_current_ma + load_fraction * (
        MOTOR.stall_current_ma - MOTOR.no_load_current_ma) * 0.15  # light load

    voltage = BATTERY.pack_voltage_nom
    power_in_w = voltage * current_ma / 1000
    # Estimate efficiency at ~60% for small DC motor under light load
    efficiency = 0.60
    heat_w = power_in_w * (1 - efficiency)

    # Simplified body temperature rise: Q = h * A * dT
    # h ~ 10 W/m^2/K (natural convection), A ~ body surface area
    surface_area_m2 = 2 * (CAMERA.body_length * CAMERA.body_height +
                            CAMERA.body_length * CAMERA.body_depth +
                            CAMERA.body_height * CAMERA.body_depth) * 1e-6
    h_conv = 10.0  # W/m^2/K
    delta_t = heat_w / (h_conv * surface_area_m2)

    alu = MATERIALS["alu_6061_t6"]

    return {
        "fps": fps,
        "motor_current_ma": current_ma,
        "power_input_w": power_in_w,
        "heat_dissipation_w": heat_w,
        "surface_area_cm2": surface_area_m2 * 1e4,
        "temp_rise_degc": delta_t,
        "body_material": alu.name,
        "thermal_expansion_ppm_k": alu.thermal_expansion,
        "gate_expansion_um": (MATERIALS["brass_c360"].thermal_expansion *
                               delta_t * CAMERA.gate_plate_w / 1000),
        "note": "Gate aperture shift due to thermal expansion",
    }
