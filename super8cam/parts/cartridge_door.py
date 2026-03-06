"""Cartridge door — hinged loading door on the right side of the body."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA


def build() -> cq.Workplane:
    door = (
        cq.Workplane("XY")
        .box(CAMERA.cart_door_w + 2, CAMERA.cart_door_h + 2,
             CAMERA.cart_door_thick)
        .edges("|Z").fillet(2.0)
    )

    # Light trap groove around inner edge
    groove_w = 1.0
    groove_d = 0.8
    inner_rect = (
        cq.Workplane("XY")
        .rect(CAMERA.cart_door_w - 2, CAMERA.cart_door_h - 2)
        .extrude(groove_d)
        .translate((0, 0, -CAMERA.cart_door_thick / 2))
    )
    outer_rect = (
        cq.Workplane("XY")
        .rect(CAMERA.cart_door_w, CAMERA.cart_door_h)
        .extrude(groove_d)
        .translate((0, 0, -CAMERA.cart_door_thick / 2))
    )
    groove = outer_rect.cut(inner_rect)
    door = door.cut(groove)

    # Hinge pin holes
    pin_dia = 2.0
    door = (
        door.faces("<X").workplane()
        .pushPoints([(0, -CAMERA.cart_door_h / 2 + 5),
                     (0, CAMERA.cart_door_h / 2 - 5)])
        .hole(pin_dia)
    )

    return door
