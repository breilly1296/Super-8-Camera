"""Cartridge door — hinged loading door on the right side of the camera body.

Features:
  - Piano hinge along the rear edge (2× hinge pin holes)
  - Spring-loaded button latch on the front edge
  - 1mm wide light-trap groove around entire inner perimeter
    (a stepped overlap where door overlaps body by 2mm, blocking light paths)
  - Must seal completely — any light leak ruins film

Material: 6061-T6 aluminum, black anodize Type II.
Interior face: matte black paint for anti-reflection.
"""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS, DOOR_SPEC
from super8cam.parts.interfaces import make_snap_latch

# =========================================================================
# DOOR DIMENSIONS
# =========================================================================
CART_DOOR_W = CAMERA.cart_door_w       # 60 mm — opening width
CART_DOOR_H = CAMERA.cart_door_h       # 50 mm — opening height
DOOR_THICK = CAMERA.cart_door_thick    # 2.5 mm

OVERLAP = DOOR_SPEC.cart_overlap                     # was 2.0
DOOR_W = CART_DOOR_W + 2 * OVERLAP     # 64 mm total
DOOR_H = CART_DOOR_H + 2 * OVERLAP     # 54 mm total
FILLET = DOOR_SPEC.cart_fillet                        # was 2.0

# =========================================================================
# LIGHT TRAP GROOVE
# =========================================================================
# The light trap is a 1mm wide, 1.5mm deep step around the entire inner
# perimeter. The door's inner face has a raised rim that seats into a
# matching groove in the body. This creates a labyrinth seal.
TRAP_W = DOOR_SPEC.cart_trap_w                       # was 1.0
TRAP_DEPTH = DOOR_SPEC.cart_trap_depth               # was 1.5
TRAP_RIM_H = DOOR_SPEC.cart_trap_rim_h               # was 1.5

# =========================================================================
# HINGE (piano hinge along rear edge)
# =========================================================================
HINGE_PIN_DIA = DOOR_SPEC.cart_hinge_pin_dia         # was 2.0
HINGE_KNUCKLE_DIA = DOOR_SPEC.cart_hinge_knuckle_dia # was 4.0
HINGE_KNUCKLE_W = DOOR_SPEC.cart_hinge_knuckle_w     # was 5.0
# Two knuckles near top and bottom of door
HINGE_SPACING = DOOR_H - 15.0         # mm between centers
HINGE_Y = DOOR_W / 2.0                # on the rear edge (+Y in door frame)

# =========================================================================
# LATCH
# =========================================================================
# Spring-loaded button on front edge. A small cylinder with internal spring.
LATCH_BUTTON_DIA = DOOR_SPEC.cart_latch_button_dia   # was 6.0
LATCH_BUTTON_LENGTH = DOOR_SPEC.cart_latch_button_length  # was 4.0
LATCH_POCKET_DEPTH = DOOR_SPEC.cart_latch_pocket_depth    # was 8.0
LATCH_Y = -DOOR_W / 2.0              # on front edge (-Y in door frame)

# =========================================================================
# INTERIOR FEATURES
# =========================================================================
# Foam pad recess (light seal backup — self-adhesive foam strip)
FOAM_W = DOOR_SPEC.cart_foam_w                       # was 3.0
FOAM_DEPTH = DOOR_SPEC.cart_foam_depth               # was 1.0
# Foam runs around the full perimeter just inside the light trap


def build() -> cq.Workplane:
    """Build the cartridge loading door.

    Door lies in the XZ plane (width along X, height along Z).
    Exterior face is +Y, interior is -Y.
    Hinge edge is at +X (rear), latch at -X (front).
    """
    # --- Main door panel ---
    door = (
        cq.Workplane("XY")
        .box(DOOR_H, DOOR_W, DOOR_THICK)
    )
    try:
        door = door.edges("|Z").fillet(FILLET)
    except Exception:
        pass

    # --- Light trap: raised rim on interior face ---
    # The rim sits into a matching groove in the body opening.
    outer_rim = (
        cq.Workplane("XY")
        .rect(DOOR_H - 2 * OVERLAP + TRAP_W,
              DOOR_W - 2 * OVERLAP + TRAP_W)
        .extrude(TRAP_RIM_H)
        .translate((0, 0, DOOR_THICK / 2.0))
    )
    inner_rim_cut = (
        cq.Workplane("XY")
        .rect(DOOR_H - 2 * OVERLAP - TRAP_W,
              DOOR_W - 2 * OVERLAP - TRAP_W)
        .extrude(TRAP_RIM_H + 0.1)
        .translate((0, 0, DOOR_THICK / 2.0 - 0.05))
    )
    rim = outer_rim.cut(inner_rim_cut)
    door = door.union(rim)

    # --- Foam channel recess on interior ---
    outer_foam = (
        cq.Workplane("XY")
        .rect(DOOR_H - 2 * (OVERLAP - FOAM_W / 2.0),
              DOOR_W - 2 * (OVERLAP - FOAM_W / 2.0))
        .extrude(FOAM_DEPTH)
        .translate((0, 0, DOOR_THICK / 2.0 + TRAP_RIM_H - FOAM_DEPTH))
    )
    inner_foam = (
        cq.Workplane("XY")
        .rect(DOOR_H - 2 * (OVERLAP + FOAM_W / 2.0),
              DOOR_W - 2 * (OVERLAP + FOAM_W / 2.0))
        .extrude(FOAM_DEPTH + 0.1)
        .translate((0, 0, DOOR_THICK / 2.0 + TRAP_RIM_H - FOAM_DEPTH - 0.05))
    )
    foam = outer_foam.cut(inner_foam)
    door = door.cut(foam)

    # --- Hinge knuckles on rear edge (+X side) ---
    for sign in [-1, 1]:
        hz = sign * HINGE_SPACING / 2.0
        knuckle = (
            cq.Workplane("YZ")
            .transformed(offset=(0, hz, DOOR_W / 2.0))
            .circle(HINGE_KNUCKLE_DIA / 2.0)
            .extrude(HINGE_KNUCKLE_W)
            .translate((-HINGE_KNUCKLE_W / 2.0, 0, 0))
        )
        door = door.union(knuckle)

        # Hinge pin hole
        pin_hole = (
            cq.Workplane("YZ")
            .transformed(offset=(0, hz, DOOR_W / 2.0))
            .circle(HINGE_PIN_DIA / 2.0)
            .extrude(HINGE_KNUCKLE_W + 2.0)
            .translate((-(HINGE_KNUCKLE_W / 2.0 + 1.0), 0, 0))
        )
        door = door.cut(pin_hole)

    # --- Latch button pocket on front edge (-Y side) ---
    latch_bore = (
        cq.Workplane("XZ")
        .transformed(offset=(0, 0, -DOOR_W / 2.0))
        .circle(LATCH_BUTTON_DIA / 2.0)
        .extrude(LATCH_POCKET_DEPTH)
        .translate((0, DOOR_W / 2.0 - LATCH_POCKET_DEPTH, 0))
    )
    door = door.cut(latch_bore)

    # Latch button (simplified cylinder, partially protruding)
    button = (
        cq.Workplane("XZ")
        .transformed(offset=(0, 0, -DOOR_W / 2.0))
        .circle(LATCH_BUTTON_DIA / 2.0 - 0.3)
        .extrude(LATCH_BUTTON_LENGTH)
        .translate((0, -LATCH_BUTTON_LENGTH, 0))
    )
    door = door.union(button)

    # --- 2× Snap latches for redundant light-tight retention ---
    # Positioned at ±DOOR_H/4.0, on front edge (-Y side), alongside
    # the existing spring-button latch for additional seal force.
    for sign in [-1, 1]:
        latch = (
            make_snap_latch()
            .rotate((0, 0, 0), (0, 0, 1), 90)  # orient for door engagement
            .translate((sign * DOOR_H / 4.0,
                        -DOOR_W / 2.0,
                        0))
        )
        door = door.union(latch)

    return door


def get_door_geometry() -> dict:
    """Return door geometry for assembly."""
    return {
        "door_w": DOOR_W,
        "door_h": DOOR_H,
        "door_thick": DOOR_THICK,
        "overlap": OVERLAP,
        "hinge_spacing": HINGE_SPACING,
        "hinge_pin_dia": HINGE_PIN_DIA,
        "trap_rim_height": TRAP_RIM_H,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/cartridge_door.step")
    cq.exporters.export(solid, f"{output_dir}/cartridge_door.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Cartridge door exported to {output_dir}/")


if __name__ == "__main__":
    export()
