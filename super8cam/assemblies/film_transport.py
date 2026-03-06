"""Film transport assembly — gate + pressure plate + claw + cam + film channel."""

import cadquery as cq
from super8cam.specs.master_specs import FILM, CAMERA, DERIVED
from super8cam.parts import (
    film_gate, pressure_plate, claw_mechanism, cam_follower,
    film_channel, registration_pin,
)


def build() -> cq.Assembly:
    assy = cq.Assembly(name="film_transport")

    # Film gate at origin (film plane)
    assy.add(film_gate.build(), name="film_gate",
             loc=cq.Location((0, 0, 0)))

    # Pressure plate behind gate
    assy.add(pressure_plate.build(), name="pressure_plate",
             loc=cq.Location((0, 0, -CAMERA.gate_plate_thick - 0.5)))

    # Film channel rails
    assy.add(film_channel.build(), name="film_channel",
             loc=cq.Location((0, 0, CAMERA.gate_plate_thick / 2 + 1.0)))

    # Claw mechanism below gate
    assy.add(claw_mechanism.build(), name="claw",
             loc=cq.Location((-FILM.width / 2 - CAMERA.claw_retract_dist,
                               -FILM.reg_pin_below_frame_center, 0)))

    # Cam on main shaft (offset laterally)
    assy.add(cam_follower.build_cam(), name="cam",
             loc=cq.Location((-FILM.width / 2 - 8, 0, 0)))

    # Registration pin
    assy.add(registration_pin.build(), name="reg_pin",
             loc=cq.Location((0, -FILM.reg_pin_below_frame_center,
                               CAMERA.gate_plate_thick / 2)))

    return assy
