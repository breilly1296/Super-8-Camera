"""Film transport assembly — gate bracket + gate + pressure plate + claw + cam + film channel.

The gate bracket is a dovetail-mounted carrier that slides onto the body's
interior dovetail rails.  It holds the film gate, pressure plate, and claw
mechanism as a single field-swappable module (MOD-100).
"""

import cadquery as cq
from super8cam.specs.master_specs import FILM, CAMERA
from super8cam.parts import (
    film_gate, pressure_plate, claw_mechanism, cam_follower,
    film_channel, registration_pin,
)
from super8cam.parts.interfaces import make_dovetail_slider


# =========================================================================
# GATE BRACKET DIMENSIONS
# =========================================================================
BRACKET_Y = 30.0       # mm — front-to-back (matches dovetail rail length)
BRACKET_Z = 28.0       # mm — height (enough to span film gate)
BRACKET_X = 6.0        # mm — thickness (lateral)

# Spring clip fingers on inner face to grip film gate edges
CLIP_THICK = 0.8       # mm
CLIP_WIDTH = 3.0       # mm
CLIP_HEIGHT = 8.0      # mm — cantilever length
CLIP_HOOK = 0.5        # mm — inward hook depth
CLIP_SPACING = 20.0    # mm — distance between clip pair (straddles gate)


def build_gate_bracket() -> cq.Workplane:
    """Build the dovetail-mounted gate bracket.

    Bracket body: 30 x 28 x 6 mm box with a dovetail slider on the
    bottom X face (28mm long, 1 thumbscrew) and 2x spring clip fingers
    on the inner face to grip the film gate edges.

    Returns
    -------
    cq.Workplane
        Solid centered at origin.
    """
    # Main bracket body
    bracket = (
        cq.Workplane("XY")
        .box(BRACKET_X, BRACKET_Y, BRACKET_Z)
    )

    # Dovetail slider on bottom face (the X face that mates with body rail)
    slider = (
        make_dovetail_slider(BRACKET_Z, num_thumbscrews=1)
        .rotate((0, 0, 0), (0, 1, 0), 90)  # orient slider along bracket height
        .translate((-BRACKET_X / 2.0, 0, 0))
    )
    bracket = bracket.union(slider)

    # 2× Spring clip fingers on inner face (+X side) to grip film gate
    for sign in [-1, 1]:
        cz = sign * CLIP_SPACING / 2.0

        # Cantilever beam
        clip_beam = (
            cq.Workplane("XY")
            .box(CLIP_THICK, CLIP_WIDTH, CLIP_HEIGHT)
            .translate((BRACKET_X / 2.0 + CLIP_THICK / 2.0, 0, cz))
        )
        bracket = bracket.union(clip_beam)

        # Inward hook at tip
        hook = (
            cq.Workplane("XY")
            .box(CLIP_HOOK, CLIP_WIDTH, 1.0)
            .translate((BRACKET_X / 2.0 + CLIP_THICK - CLIP_HOOK / 2.0, 0,
                        cz + sign * (CLIP_HEIGHT / 2.0 - 0.5)))
        )
        bracket = bracket.union(hook)

    return bracket


def build() -> cq.Assembly:
    """Build the film transport assembly with gate bracket.

    The gate bracket is the first component at origin. All other parts
    are positioned relative to the film plane.
    """
    assy = cq.Assembly(name="film_transport")

    # Gate bracket at origin
    assy.add(build_gate_bracket(), name="gate_bracket",
             loc=cq.Location((0, 0, 0)))

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


def export_bracket(output_dir: str = "export"):
    """Export the gate bracket as standalone STL for 3D printing."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build_gate_bracket()
    cq.exporters.export(solid, f"{output_dir}/gate_bracket.step")
    cq.exporters.export(solid, f"{output_dir}/gate_bracket.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Gate bracket exported to {output_dir}/")
