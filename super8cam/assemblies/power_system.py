"""Power system assembly — battery compartment + door."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, BATTERY
from super8cam.parts import battery_door, bottom_plate


def build() -> cq.Assembly:
    assy = cq.Assembly(name="power_system")

    assy.add(bottom_plate.build(), name="bottom_plate",
             loc=cq.Location((0, 0, -CAMERA.body_height / 2)))

    assy.add(battery_door.build(), name="battery_door",
             loc=cq.Location((CAMERA.body_length / 4, 0,
                               -CAMERA.body_height / 2 - CAMERA.batt_door_thick)))

    return assy
