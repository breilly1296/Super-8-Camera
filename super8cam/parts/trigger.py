"""Trigger — ergonomic trigger button with pivot and return spring post."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA

TRIGGER_LENGTH = 20.0  # mm
TRIGGER_WIDTH = 10.0   # mm
TRIGGER_THICK = 4.0    # mm
PIVOT_HOLE_DIA = 2.0   # mm


def build() -> cq.Workplane:
    trigger = (
        cq.Workplane("XY")
        .box(TRIGGER_LENGTH, TRIGGER_WIDTH, TRIGGER_THICK)
        .edges("|Z").fillet(1.5)
    )

    # Rounded finger pad on top
    pad = (
        cq.Workplane("XY")
        .box(12.0, TRIGGER_WIDTH, 2.0)
        .edges().fillet(0.8)
        .translate((TRIGGER_LENGTH / 4, 0, TRIGGER_THICK / 2 + 1.0))
    )
    trigger = trigger.union(pad)

    # Pivot hole
    trigger = (
        trigger.faces(">Y").workplane()
        .center(-TRIGGER_LENGTH / 2 + 3, 0)
        .hole(PIVOT_HOLE_DIA)
    )

    # Spring post hole
    trigger = (
        trigger.faces("<Z").workplane()
        .center(-TRIGGER_LENGTH / 4, 0)
        .hole(1.5, 2.0)
    )

    return trigger
