"""Film channel — guide rails that constrain film path through the gate area."""

import cadquery as cq
from super8cam.specs.master_specs import FILM, CAMERA

RAIL_THICKNESS = 1.5  # mm
RAIL_HEIGHT = 2.0     # mm — stands off from gate plate


def build() -> cq.Workplane:
    """Build a pair of guide rails flanking the film path."""
    rail_length = CAMERA.film_channel_length

    # Left rail
    left = (
        cq.Workplane("XY")
        .box(RAIL_THICKNESS, rail_length, RAIL_HEIGHT)
        .translate((-CAMERA.film_channel_width / 2 - RAIL_THICKNESS / 2, 0, 0))
    )

    # Right rail
    right = (
        cq.Workplane("XY")
        .box(RAIL_THICKNESS, rail_length, RAIL_HEIGHT)
        .translate((CAMERA.film_channel_width / 2 + RAIL_THICKNESS / 2, 0, 0))
    )

    return left.union(right)
