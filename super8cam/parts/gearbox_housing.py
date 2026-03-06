"""Gearbox housing — enclosure for the 2-stage gear train."""

import cadquery as cq
from super8cam.specs.master_specs import GEARBOX, CAMERA, BEARINGS

WALL = 2.0  # mm
HOUSING_DEPTH = GEARBOX.gear_face_width + 2 * WALL + 2.0  # axial depth


def build() -> cq.Workplane:
    """Build the gearbox housing (rectangular box with bearing bores)."""
    # Envelope that contains both gear stages
    total_span = GEARBOX.stage1_center_distance + GEARBOX.stage2_center_distance
    housing_w = total_span + GEARBOX.stage2_gear_pcd + 2 * WALL + 4
    housing_h = max(GEARBOX.stage1_gear_pcd, GEARBOX.stage2_gear_pcd) + 2 * WALL + 4

    housing = (
        cq.Workplane("XY")
        .box(housing_w, housing_h, HOUSING_DEPTH)
        .edges("|Z").fillet(1.5)
    )

    # Hollow out interior
    inner = (
        cq.Workplane("XY")
        .box(housing_w - 2 * WALL, housing_h - 2 * WALL, HOUSING_DEPTH - WALL)
        .translate((0, 0, WALL / 2))
    )
    housing = housing.cut(inner)

    # Bearing bores on the output shaft side
    brg = BEARINGS["main_shaft"]
    housing = (
        housing.faces(">Z").workplane()
        .hole(brg.od, brg.width + 0.5)
    )

    return housing
