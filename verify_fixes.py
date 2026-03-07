#!/usr/bin/env python3
"""Standalone verification of the 5 bug fixes — no CadQuery required.

Tests all numerical/analytical changes without importing CadQuery.
"""
import sys
import math

# Patch CadQuery import so modules can load without OCP
import types
cq_mock = types.ModuleType("cadquery")
cq_mock.Workplane = type("Workplane", (), {})
cq_mock.exporters = types.ModuleType("cadquery.exporters")
cq_mock.Assembly = type("Assembly", (), {})
cq_mock.Location = type("Location", (), {"__init__": lambda self, *a: None})
sys.modules["cadquery"] = cq_mock
sys.modules["cadquery.exporters"] = cq_mock.exporters

# Now we can import
sys.path.insert(0, ".")

sep = "=" * 68
all_pass = True

def check(label, passed, detail=""):
    global all_pass
    status = "PASS" if passed else "FAIL"
    all_pass &= passed
    print(f"  [{status}] {label}")
    if detail:
        print(f"         {detail}")


print(f"\n{sep}")
print("  SUPER 8 CAMERA — FIX VERIFICATION")
print(sep)

# =========================================================================
# BUG 1: MOTOR OVER-SPEED
# =========================================================================
print(f"\n  BUG 1: MOTOR OVER-SPEED (gear ratio)")
print("  " + "-" * 55)

from super8cam.specs.master_specs import GEARBOX, MOTOR

check("Gear ratio is 6:1",
      GEARBOX.ratio == 6.0,
      f"ratio = {GEARBOX.ratio}")

check("Stage 1 is 3:1",
      GEARBOX.stage1_gear_teeth / GEARBOX.stage1_pinion_teeth == 3.0,
      f"{GEARBOX.stage1_gear_teeth}/{GEARBOX.stage1_pinion_teeth} = "
      f"{GEARBOX.stage1_gear_teeth / GEARBOX.stage1_pinion_teeth}")

check("Stage 2 is 2:1",
      GEARBOX.stage2_gear_teeth / GEARBOX.stage2_pinion_teeth == 2.0,
      f"{GEARBOX.stage2_gear_teeth}/{GEARBOX.stage2_pinion_teeth} = "
      f"{GEARBOX.stage2_gear_teeth / GEARBOX.stage2_pinion_teeth}")

motor_18 = GEARBOX.motor_rpm_18fps
motor_24 = GEARBOX.motor_rpm_24fps
check("Motor RPM @18fps within limit",
      motor_18 < MOTOR.no_load_rpm * 0.9,
      f"{motor_18:.0f} RPM < {MOTOR.no_load_rpm * 0.9:.0f} RPM (90% of no-load)")

check("Motor RPM @24fps within limit",
      motor_24 <= MOTOR.no_load_rpm * 0.9,
      f"{motor_24:.0f} RPM <= {MOTOR.no_load_rpm * 0.9:.0f} RPM (90% of no-load)")

# Torque check
output_torque = MOTOR.stall_torque_gcm * GEARBOX.ratio * GEARBOX.efficiency
check("Output torque sufficient",
      output_torque > 100.0,
      f"Stall torque at output: {output_torque:.1f} g-cm "
      f"({MOTOR.stall_torque_gcm} x {GEARBOX.ratio} x {GEARBOX.efficiency})")


# =========================================================================
# BUG 2: CAM TIMING
# =========================================================================
print(f"\n  BUG 2: CAM TIMING (phase synchronization)")
print("  " + "-" * 55)

import numpy as np
from super8cam.parts.cam_follower import cam_profile_full

profile = cam_profile_full(720)
theta = profile["theta_deg"]
x = profile["x_mm"]
y = profile["y_mm"]
d_theta = theta[1] - theta[0]

# Check claw is engaged (x > 1.0) at shutter open (10°)
idx_10 = int(10.0 / d_theta)
check("Claw engaged at shutter open (10°)",
      x[idx_10] > 1.5,
      f"claw_x at 10° = {x[idx_10]:.3f} mm (need > 1.5)")

# Check claw at top (y ≈ 0) at shutter open
check("Film at top (stationary) at shutter open (10°)",
      abs(y[idx_10]) < 0.05,
      f"claw_y at 10° = {y[idx_10]:.4f} mm (need < 0.05)")

# Check film stationary during exposure (10°-180°)
idx_180 = int(180.0 / d_theta)
max_y_during_exposure = float(np.max(np.abs(y[idx_10:idx_180])))
check("Film stationary during exposure (10°-180°)",
      max_y_during_exposure < 0.05,
      f"max |claw_y| during exposure = {max_y_during_exposure:.4f} mm")

# Check pulldown achieves full stroke (190°-340°)
idx_190 = int(190.0 / d_theta)
idx_340 = int(340.0 / d_theta)
max_pulldown = float(np.max(np.abs(y[idx_190:idx_340])))
from super8cam.specs.master_specs import FILM
check("Pulldown achieves full stroke",
      abs(max_pulldown - FILM.perf_pitch) < 0.01,
      f"max pulldown = {max_pulldown:.4f} mm (target {FILM.perf_pitch})")

# Check claw retracted during pulldown (should still be engaged)
min_x_pulldown = float(np.min(x[idx_190:idx_340]))
check("Claw engaged during pulldown",
      min_x_pulldown > 1.5,
      f"min claw_x during pulldown = {min_x_pulldown:.3f} mm")

# Check claw retracts after pulldown (retract is 340°-350°)
idx_350 = int(350.0 / d_theta)
check("Claw retracts by end of retract phase (350°)",
      x[idx_350] < 0.5,
      f"claw_x at 350° = {x[idx_350]:.3f} mm")

# Registration pin logic: claw retracted & film stationary → pin engaged
# At 5°-10° dwell, claw should be engaged (x~2), film stationary (y~0)
# Pin engages because film is stationary
idx_5 = int(5.0 / d_theta)
check("Claw at home position at dwell start (5°)",
      abs(y[idx_5]) < 0.1,
      f"claw_y at 5° = {y[idx_5]:.4f} mm")


# =========================================================================
# BUG 3: FLANGE DISTANCE STACK-UP
# =========================================================================
print(f"\n  BUG 3: FLANGE DISTANCE STACK-UP")
print("  " + "-" * 55)

from super8cam.parts.lens_mount import (
    MOUNT_TO_SHUTTER_FRONT, GATE_FRONT_TO_FILM_PLANE, STACK_TOTAL, STACK_ERROR,
)
from super8cam.parts.shutter_disc import DISC_THICK, GATE_CLEARANCE
from super8cam.specs.master_specs import CMOUNT

check("Mount-to-shutter distance computed",
      MOUNT_TO_SHUTTER_FRONT > 12.0,
      f"MOUNT_TO_SHUTTER_FRONT = {MOUNT_TO_SHUTTER_FRONT:.3f} mm")

check("Stack-up hits 17.526mm target",
      STACK_ERROR < 0.001,
      f"Total = {STACK_TOTAL:.4f} mm (error {STACK_ERROR:.4f} mm)")

# Now test the tolerance_stackup function
from super8cam.analysis.tolerance_stackup import flange_distance_stackup
fs = flange_distance_stackup()
check("Flange stackup nominal matches target",
      abs(fs["error_mm"]) < 0.001,
      f"Nominal = {fs['nominal_total_mm']:.4f} mm, "
      f"target = {fs['target_mm']:.3f} mm, "
      f"error = {fs['error_mm']:.4f} mm")

check("Flange stackup RSS in spec",
      fs["in_spec_rss"],
      f"RSS tol = ±{fs['rss_tol_mm']:.4f} mm (limit ±0.02)")


# =========================================================================
# BUG 5: REGISTRATION ACCURACY
# =========================================================================
print(f"\n  BUG 5: REGISTRATION ACCURACY")
print("  " + "-" * 55)

from super8cam.specs.master_specs import TOL
from super8cam.analysis.tolerance_stackup import registration_accuracy

check("Pin tolerance tightened to +0/-0.002",
      TOL.reg_pin_dia_minus == 0.002,
      f"reg_pin_dia_minus = {TOL.reg_pin_dia_minus}")

check("Pin hole tolerance H6",
      TOL.press_fit_hole == "H6",
      f"press_fit_hole = {TOL.press_fit_hole}")

check("Pin position tolerance tightened",
      TOL.reg_pin_position == 0.005,
      f"reg_pin_position = {TOL.reg_pin_position}")

ra = registration_accuracy()
check("Registration worst-case computed",
      ra["worst_case_error_mm"] > 0,
      f"Worst-case = ±{ra['worst_case_error_mm']:.4f} mm")

check("Registration RSS within Kodak spec (±0.025mm)",
      ra["in_spec_rss"],
      f"RSS = ±{ra['rss_error_mm']:.4f} mm (limit ±0.025)")


# =========================================================================
# BUG 4: ASSEMBLY INTERFERENCES (datum positions)
# =========================================================================
print(f"\n  BUG 4: ASSEMBLY DATUM POSITIONS")
print("  " + "-" * 55)

# Can't run full interference check without CadQuery, but verify datums
from super8cam.assemblies.full_camera import (
    SHAFT_Z, GEARBOX_X, GEARBOX_Y, GEARBOX_Z,
    MOTOR_X, MOTOR_Y, MOTOR_Z,
    CAM_X, CAM_Y, CAM_Z,
    CART_X, CART_Z, PCB_Z, VF_Z,
)

check("Shaft raised to clear gate",
      SHAFT_Z >= 16.0,
      f"SHAFT_Z = {SHAFT_Z} mm (was 12)")

check("Gearbox shifted for clearance",
      GEARBOX_X > 15.0 and GEARBOX_Z < 0.0,
      f"GEARBOX at X={GEARBOX_X}, Y={GEARBOX_Y}, Z={GEARBOX_Z}")

check("Cam offset from gate",
      CAM_X < -25.0,
      f"CAM_X = {CAM_X} mm")

from super8cam.specs.master_specs import CAMERA as CAM_DESIGN
check("PCB raised above body floor",
      PCB_Z > -CAM_DESIGN.body_height / 2.0 + 5.0,
      f"PCB_Z = {PCB_Z:.1f} mm")

# Verify shutter disc clears gate (shaft raised)
from super8cam.parts.shutter_disc import DISC_OD
disc_r = DISC_OD / 2.0
gate_half_h = CAM_DESIGN.gate_plate_h / 2.0
# Disc lowest point: SHAFT_Z - disc_r
disc_bottom = SHAFT_Z - disc_r
check("Shutter disc clears gate bottom edge",
      disc_bottom > -gate_half_h,
      f"Disc bottom at Z={disc_bottom:.1f} mm, gate bottom at Z={-gate_half_h:.1f} mm")


# =========================================================================
# OVERALL SUMMARY
# =========================================================================
print(f"\n{sep}")
if all_pass:
    print("  OVERALL: ALL CHECKS PASSED")
else:
    print("  OVERALL: SOME CHECKS FAILED — review above")
print(sep)

sys.exit(0 if all_pass else 1)
