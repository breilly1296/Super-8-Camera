"""Cam and follower — eccentric cam on main shaft drives the claw pulldown."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, MATERIALS, MATERIAL_USAGE

MATERIAL = MATERIALS[MATERIAL_USAGE["cam"]]


def build_cam() -> cq.Workplane:
    """Build the cam lobe (egg-shaped profile on main shaft)."""
    # Base circle
    cam = (
        cq.Workplane("XY")
        .cylinder(CAMERA.cam_width, CAMERA.cam_od / 2)
    )

    # Shaft bore
    cam = cam.faces(">Z").workplane().hole(CAMERA.cam_id)

    return cam


def build_follower() -> cq.Workplane:
    """Build the cam follower roller."""
    roller = (
        cq.Workplane("XY")
        .cylinder(CAMERA.cam_width - 0.5, CAMERA.cam_follower_dia / 2)
    )
    return roller
