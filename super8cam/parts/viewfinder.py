"""Viewfinder — simple Galilean optical viewfinder tube."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA

TUBE_WALL = 1.0  # mm


def build() -> cq.Workplane:
    """Build the viewfinder tube (outer shell, two apertures)."""
    outer_r = max(CAMERA.viewfinder_eye_dia, CAMERA.viewfinder_obj_dia) / 2 + TUBE_WALL
    tube = (
        cq.Workplane("XY")
        .cylinder(CAMERA.viewfinder_length, outer_r)
    )

    # Eye aperture bore
    tube = (
        tube.faces(">Z").workplane()
        .hole(CAMERA.viewfinder_eye_dia, CAMERA.viewfinder_length / 2)
    )

    # Objective aperture bore from other end
    tube = (
        tube.faces("<Z").workplane()
        .hole(CAMERA.viewfinder_obj_dia, CAMERA.viewfinder_length / 2)
    )

    return tube
