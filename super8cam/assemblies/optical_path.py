"""Optical path assembly — lens mount + shutter + film gate alignment."""

import cadquery as cq
from super8cam.specs.master_specs import CMOUNT, CAMERA, DERIVED
from super8cam.parts import lens_mount, viewfinder


def build() -> cq.Assembly:
    assy = cq.Assembly(name="optical_path")

    # Lens mount at front face
    assy.add(lens_mount.build(), name="lens_mount",
             loc=cq.Location((CAMERA.lens_mount_offset_x, 0, 0)))

    # Viewfinder above and to the right of lens
    assy.add(viewfinder.build(), name="viewfinder",
             loc=cq.Location((CAMERA.lens_mount_offset_x + 20,
                               0, CAMERA.body_height / 2 - 10)))

    return assy
