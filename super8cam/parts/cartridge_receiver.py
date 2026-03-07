"""Cartridge receiver — pocket that holds the Kodak Super 8 Type A cartridge.

The cartridge drops in from the right side (through a loading door). Two
register pins ensure the cartridge film exit aligns with the camera film gate
within +/-0.1mm. A takeup drive spindle engages the cartridge takeup spool
through a friction clutch.

Coordinate system (matches camera body frame):
  X = horizontal (+ right = loading door side)
  Y = vertical (+ up)
  Z = optical axis (+ toward lens)

The cartridge pocket is open on the +X side (loading door).
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CARTRIDGE, CAMERA, FASTENERS, MATERIALS, RECV_SPEC,
)

# =========================================================================
# POCKET DIMENSIONS
# =========================================================================
CLEARANCE = RECV_SPEC.pocket_clearance       # was 0.5
POCKET_L = CARTRIDGE.length + 2 * CLEARANCE    # 68.0 mm
POCKET_W = CARTRIDGE.width + 2 * CLEARANCE     # 63.0 mm
POCKET_D = CARTRIDGE.depth + CLEARANCE          # 21.5 mm
WALL = RECV_SPEC.pocket_wall                 # was 2.0

# Open on +X side for cartridge insertion through loading door
POCKET_OPEN_SIDE = "+X"

# =========================================================================
# REGISTRATION PINS
# =========================================================================
# Two 2mm diameter pins engage matching holes in the cartridge body.
# These ensure the film exit slot aligns with the camera film gate.
REG_PIN_DIA = RECV_SPEC.reg_pin_dia          # was 2.0
REG_PIN_HEIGHT = RECV_SPEC.reg_pin_height    # was 3.0
REG_PIN_FIT = RECV_SPEC.reg_pin_fit          # was 0.01

# Pin positions relative to pocket center (matching Kodak cartridge holes).
# The film exit slot is at CARTRIDGE.exit_slot_x from the left edge.
# Pins are positioned to constrain the cartridge in X and Y:
#   Pin 1: near the film exit slot (left of exit)
#   Pin 2: diagonally opposite (right side, far from exit)
REG_PIN_1_X = -(POCKET_L / 2.0 - CARTRIDGE.exit_slot_x - RECV_SPEC.reg_pin1_offset_x)
REG_PIN_1_Y = -(POCKET_W / 2.0 - RECV_SPEC.reg_pin1_offset_y)
REG_PIN_2_X = POCKET_L / 2.0 - RECV_SPEC.reg_pin2_offset_x
REG_PIN_2_Y = POCKET_W / 2.0 - RECV_SPEC.reg_pin2_offset_y

# =========================================================================
# TAKEUP DRIVE SPINDLE
# =========================================================================
# Cross-shaped tip engages the cartridge takeup spool socket.
# Driven from the main shaft via a friction belt/gear (doesn't need precise speed).
SPINDLE_DIA = RECV_SPEC.spindle_dia          # was 6.0
SPINDLE_TIP_DIA = RECV_SPEC.spindle_tip_dia  # was 4.0
SPINDLE_TIP_HEIGHT = RECV_SPEC.spindle_tip_height  # was 5.0
SPINDLE_CROSS_W = RECV_SPEC.spindle_cross_w  # was 1.5
SPINDLE_TOTAL_H = RECV_SPEC.spindle_total_h  # was 10.0

# Spindle position: aligned with cartridge takeup spool center
SPINDLE_X = POCKET_L / 2.0 - CARTRIDGE.length + CARTRIDGE.takeup_spool_x
SPINDLE_Y = POCKET_W / 2.0 - CARTRIDGE.width + CARTRIDGE.takeup_spool_x
# Correct: position relative to pocket center
_cart_center_x = 0.0  # cartridge centered in pocket
SPINDLE_POS_X = -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.takeup_spool_x
SPINDLE_POS_Y = 0.0  # in depth axis (Z), not Y

# =========================================================================
# FRICTION CLUTCH
# =========================================================================
# Spring-loaded disc on the spindle base prevents film over-tension.
CLUTCH_OD = RECV_SPEC.clutch_od              # was 10.0
CLUTCH_THICK = RECV_SPEC.clutch_thick        # was 1.5
CLUTCH_SPRING_FORCE = RECV_SPEC.clutch_spring_force  # was 0.5

# =========================================================================
# LEAF SPRING LATCH
# =========================================================================
LATCH_W = RECV_SPEC.latch_w                 # was 8.0
LATCH_L = RECV_SPEC.latch_l                 # was 15.0
LATCH_THICK = RECV_SPEC.latch_thick          # was 0.5
LATCH_FORCE = RECV_SPEC.latch_force          # was 1.0


def build() -> cq.Workplane:
    """Build the cartridge receiver pocket.

    Returns a solid representing the receiver walls. The inner pocket is
    the negative volume where the cartridge sits.
    """
    # Outer block (pocket walls)
    outer_l = POCKET_L + 2 * WALL
    outer_w = POCKET_W + 2 * WALL
    outer_d = POCKET_D + WALL  # closed on bottom, open on top

    receiver = (
        cq.Workplane("XY")
        .box(outer_l, outer_w, outer_d)
    )

    # Round outer edges
    receiver = receiver.edges("|Z").fillet(1.5)

    # Hollow out the pocket (open on top, +Z direction)
    pocket = (
        cq.Workplane("XY")
        .box(POCKET_L, POCKET_W, POCKET_D)
        .translate((0, 0, WALL / 2.0))
    )
    receiver = receiver.cut(pocket)

    # Open the loading door side (+X) — remove the +X wall
    door_cut = (
        cq.Workplane("XY")
        .box(WALL + 1.0, POCKET_W, POCKET_D)
        .translate((outer_l / 2.0 - WALL / 2.0, 0, WALL / 2.0))
    )
    receiver = receiver.cut(door_cut)

    # Film exit slot through -Y wall (toward film gate)
    exit_slot = (
        cq.Workplane("XY")
        .box(CARTRIDGE.exit_slot_w + 1.0, WALL + 2.0,
             CARTRIDGE.exit_slot_h + 0.5)
        .translate((
            -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.exit_slot_x,
            -outer_w / 2.0 + WALL / 2.0,
            0,
        ))
    )
    receiver = receiver.cut(exit_slot)

    # Film entry slot (return to takeup, same wall)
    entry_slot = (
        cq.Workplane("XY")
        .box(CARTRIDGE.entry_slot_w + 1.0, WALL + 2.0,
             CARTRIDGE.entry_slot_h + 0.5)
        .translate((
            -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.entry_slot_x,
            -outer_w / 2.0 + WALL / 2.0,
            0,
        ))
    )
    receiver = receiver.cut(entry_slot)

    # Registration pin holes in the pocket floor
    pin_positions = [
        (REG_PIN_1_X, REG_PIN_1_Y),
        (REG_PIN_2_X, REG_PIN_2_Y),
    ]
    receiver = (
        receiver.faces("<Z").workplane()
        .pushPoints(pin_positions)
        .hole(REG_PIN_DIA + 0.05, WALL)  # H7 holes through floor
    )

    # Takeup spindle bore through the pocket floor
    spindle_x = -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.takeup_spool_x
    receiver = (
        receiver.faces("<Z").workplane()
        .center(spindle_x, 0)
        .hole(SPINDLE_DIA + 0.2, WALL + 1.0)
    )

    return receiver


def build_register_pin() -> cq.Workplane:
    """Build a single registration pin (2mm dia, 3mm tall)."""
    pin = (
        cq.Workplane("XY")
        .cylinder(REG_PIN_HEIGHT, REG_PIN_DIA / 2.0)
    )
    # Chamfer the top for easy cartridge insertion
    pin = pin.faces(">Z").chamfer(0.2)
    return pin


def build_takeup_spindle() -> cq.Workplane:
    """Build the takeup drive spindle with cross-shaped engagement tip.

    The cross shape matches the Kodak cartridge's takeup spool socket.
    """
    # Base cylinder
    spindle = (
        cq.Workplane("XY")
        .cylinder(SPINDLE_TOTAL_H - SPINDLE_TIP_HEIGHT, SPINDLE_DIA / 2.0)
    )

    # Cross-shaped tip
    arm1 = (
        cq.Workplane("XY")
        .box(SPINDLE_TIP_DIA, SPINDLE_CROSS_W, SPINDLE_TIP_HEIGHT)
        .translate((0, 0, (SPINDLE_TOTAL_H - SPINDLE_TIP_HEIGHT) / 2.0
                    + SPINDLE_TIP_HEIGHT / 2.0))
    )
    arm2 = (
        cq.Workplane("XY")
        .box(SPINDLE_CROSS_W, SPINDLE_TIP_DIA, SPINDLE_TIP_HEIGHT)
        .translate((0, 0, (SPINDLE_TOTAL_H - SPINDLE_TIP_HEIGHT) / 2.0
                    + SPINDLE_TIP_HEIGHT / 2.0))
    )
    spindle = spindle.union(arm1).union(arm2)

    # Center bore for shaft (2mm)
    spindle = (
        spindle.faces("<Z").workplane()
        .hole(2.0, SPINDLE_TOTAL_H)
    )

    return spindle


def build_friction_clutch() -> cq.Workplane:
    """Build the friction clutch disc (spring-loaded slip clutch)."""
    clutch = (
        cq.Workplane("XY")
        .cylinder(CLUTCH_THICK, CLUTCH_OD / 2.0)
    )
    clutch = clutch.faces(">Z").workplane().hole(SPINDLE_DIA + 0.1, CLUTCH_THICK)

    # Radial friction grooves (4 grooves at 90° intervals)
    for angle in [0, 90, 180, 270]:
        rad = math.radians(angle)
        gx = (CLUTCH_OD / 4.0) * math.cos(rad)
        gy = (CLUTCH_OD / 4.0) * math.sin(rad)
        groove = (
            cq.Workplane("XY")
            .box(0.5, CLUTCH_OD / 2.0 - 1.0, CLUTCH_THICK + 0.1)
            .translate((gx, gy, 0))
        )
        # Rotate groove to radial orientation
        # (simplified: just cut small radial slots)

    return clutch


def build_latch_spring() -> cq.Workplane:
    """Build the leaf spring latch that holds the cartridge down."""
    spring = (
        cq.Workplane("XY")
        .box(LATCH_W, LATCH_L, LATCH_THICK)
    )
    # Bent end for engaging cartridge top
    hook = (
        cq.Workplane("XY")
        .box(LATCH_W, 2.0, 2.0)
        .translate((0, LATCH_L / 2.0 + 1.0, -1.0))
    )
    spring = spring.union(hook)

    # Mounting hole at fixed end
    spring = (
        spring.faces(">Z").workplane()
        .center(0, -LATCH_L / 2.0 + 2.0)
        .hole(2.2, LATCH_THICK)
    )
    return spring


def get_receiver_geometry() -> dict:
    """Return key geometry for assembly positioning."""
    return {
        "pocket_l": POCKET_L,
        "pocket_w": POCKET_W,
        "pocket_d": POCKET_D,
        "wall": WALL,
        "reg_pin_positions": [
            (REG_PIN_1_X, REG_PIN_1_Y),
            (REG_PIN_2_X, REG_PIN_2_Y),
        ],
        "spindle_x": -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.takeup_spool_x,
        "exit_slot_x": -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.exit_slot_x,
        "exit_slot_w": CARTRIDGE.exit_slot_w,
        "entry_slot_x": -POCKET_L / 2.0 + CLEARANCE + CARTRIDGE.entry_slot_x,
        "entry_slot_w": CARTRIDGE.entry_slot_w,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/cartridge_receiver.step")
    cq.exporters.export(solid, f"{output_dir}/cartridge_receiver.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Cartridge receiver exported to {output_dir}/")


if __name__ == "__main__":
    export()
