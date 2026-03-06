"""Drivetrain assembly — motor + gearbox + shaft."""

import cadquery as cq
from super8cam.specs.master_specs import GEARBOX, MOTOR
from super8cam.parts import motor_mount, gearbox_housing, gears, main_shaft


def build() -> cq.Assembly:
    assy = cq.Assembly(name="drivetrain")

    assy.add(motor_mount.build(), name="motor_mount",
             loc=cq.Location((0, 0, 0)))

    assy.add(gearbox_housing.build(), name="gearbox_housing",
             loc=cq.Location((0, MOTOR.body_length + 5, 0)))

    # Stage 1 pinion (on motor shaft)
    assy.add(gears.build_stage1_pinion(), name="stage1_pinion",
             loc=cq.Location((0, MOTOR.body_length + 2, 0)))

    # Stage 1 gear
    assy.add(gears.build_stage1_gear(), name="stage1_gear",
             loc=cq.Location((GEARBOX.stage1_center_distance, MOTOR.body_length + 2, 0)))

    # Stage 2 pinion (coaxial with stage1 gear)
    assy.add(gears.build_stage2_pinion(), name="stage2_pinion",
             loc=cq.Location((GEARBOX.stage1_center_distance, MOTOR.body_length + 2, 4)))

    # Stage 2 gear (output, on main shaft)
    cd2 = GEARBOX.stage1_center_distance + GEARBOX.stage2_center_distance
    assy.add(gears.build_stage2_gear(), name="stage2_gear",
             loc=cq.Location((cd2, MOTOR.body_length + 2, 4)))

    # Main shaft at output
    assy.add(main_shaft.build(), name="output_shaft",
             loc=cq.Location((cd2, MOTOR.body_length + 2, 0)))

    return assy
