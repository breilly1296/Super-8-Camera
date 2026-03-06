"""Lens mount — C-mount threaded boss on the camera front face."""

import cadquery as cq
from super8cam.specs.master_specs import CMOUNT, CAMERA


def build() -> cq.Workplane:
    """Build the lens mount boss (simplified — thread modeled as plain bore)."""
    boss = (
        cq.Workplane("XY")
        .cylinder(CAMERA.lens_boss_protrusion + CAMERA.wall_thickness,
                  CAMERA.lens_boss_od / 2)
    )

    # C-mount thread bore (modeled as plain bore at major diameter)
    bore_depth = CMOUNT.thread_depth + CAMERA.wall_thickness
    boss = (
        boss.faces(">Z").workplane()
        .hole(CMOUNT.thread_major_dia, bore_depth)
    )

    return boss
