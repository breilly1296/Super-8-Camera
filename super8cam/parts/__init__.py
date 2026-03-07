"""super8cam.parts — Individual CadQuery part models.

Every part imports dimensions from specs.master_specs.
Each module exposes a build() function returning a cq.Workplane solid.

Usage::

    from super8cam.parts import film_gate
    solid = film_gate.build()
"""

__all__ = [
    "film_gate",
    "pressure_plate",
    "claw_mechanism",
    "cam_follower",
    "film_channel",
    "registration_pin",
    "shutter_disc",
    "main_shaft",
    "motor_mount",
    "gearbox_housing",
    "gears",
    "cartridge_receiver",
    "cartridge_door",
    "pcb_bracket",
    "battery_door",
    "bottom_plate",
    "lens_mount",
    "viewfinder",
    "body_left",
    "body_right",
    "top_plate",
    "trigger",
    "interfaces",
]
