"""Shutter assembly — disc + shaft section + encoder flag."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, DERIVED
from super8cam.parts import shutter_disc, main_shaft


def build() -> cq.Assembly:
    assy = cq.Assembly(name="shutter_assembly")

    # Shutter disc positioned between lens and film gate
    assy.add(shutter_disc.build(), name="shutter_disc",
             loc=cq.Location((0, 0, 0)))

    # Shaft segment through shutter
    assy.add(main_shaft.build(), name="main_shaft",
             loc=cq.Location((0, 0, 0)))

    return assy
