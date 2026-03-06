"""Cartridge receiver — pocket inside the body that accepts a Kodak Type A cartridge."""

import cadquery as cq
from super8cam.specs.master_specs import CARTRIDGE, CAMERA

WALL = 1.5  # mm — receiver wall thickness
CLEARANCE = 0.5  # mm — all-around clearance for cartridge insertion


def build() -> cq.Workplane:
    """Build the cartridge receiver pocket (negative volume for boolean cut)."""
    pocket_l = CARTRIDGE.length + 2 * CLEARANCE
    pocket_w = CARTRIDGE.width + 2 * CLEARANCE
    pocket_d = CARTRIDGE.depth + CLEARANCE

    receiver = (
        cq.Workplane("XY")
        .box(pocket_l, pocket_w, pocket_d)
    )

    # Film exit slot (through-wall opening toward gate)
    slot = (
        cq.Workplane("XY")
        .box(CARTRIDGE.exit_slot_w + 1.0, WALL + 2, CARTRIDGE.exit_slot_h + 0.5)
        .translate((0, -pocket_w / 2, 0))
    )
    receiver = receiver.union(slot)

    return receiver
