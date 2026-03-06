"""Full camera assembly — all sub-assemblies positioned in the body."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA
from super8cam.assemblies import (
    film_transport, shutter_assembly, drivetrain,
    optical_path, power_system, electronics,
)
from super8cam.parts import (
    body_left, body_right, top_plate, cartridge_door, trigger,
)


def build() -> cq.Assembly:
    assy = cq.Assembly(name="super8_camera")

    # Body shell halves
    assy.add(body_left.build(), name="body_left",
             loc=cq.Location((-CAMERA.body_length / 4, 0, 0)))
    assy.add(body_right.build(), name="body_right",
             loc=cq.Location((CAMERA.body_length / 4, 0, 0)))

    # Top plate
    assy.add(top_plate.build(), name="top_plate",
             loc=cq.Location((0, 0, CAMERA.body_height / 2)))

    # Cartridge door
    assy.add(cartridge_door.build(), name="cartridge_door",
             loc=cq.Location((CAMERA.body_length / 2 + CAMERA.cart_door_thick / 2,
                               0, 5)))

    # Internal sub-assemblies
    assy.add(film_transport.build(), name="film_transport",
             loc=cq.Location((CAMERA.lens_mount_offset_x, 0, 0)))
    assy.add(shutter_assembly.build(), name="shutter_assy",
             loc=cq.Location((CAMERA.lens_mount_offset_x, -5, 0)))
    assy.add(drivetrain.build(), name="drivetrain",
             loc=cq.Location((30, 10, -15)))
    assy.add(optical_path.build(), name="optical_path",
             loc=cq.Location((0, -CAMERA.body_depth / 2, 0)))
    assy.add(power_system.build(), name="power_system")
    assy.add(electronics.build(), name="electronics")

    # Trigger
    assy.add(trigger.build(), name="trigger",
             loc=cq.Location((-10, -CAMERA.body_depth / 2 + 5,
                               -CAMERA.body_height / 4)))

    return assy
