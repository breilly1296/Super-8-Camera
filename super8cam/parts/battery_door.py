"""Battery door — hinged cover for the battery compartment on the camera bottom.

Features:
  - Sized to cover the battery pocket opening plus 2mm overlap all around
  - Piano hinge along one long edge (2× pin holes)
  - Coin-slot latch on the opposite edge
  - Spring contact placeholders on interior surface
  - Light-trap step around perimeter (1mm groove)

Material: 6061-T6 aluminum, black anodize.
"""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS, DOOR_SPEC
from super8cam.parts.interfaces import make_snap_latch

# =========================================================================
# DOOR DIMENSIONS
# =========================================================================
BATT_L = CAMERA.batt_pocket_l              # 58 mm — pocket length
BATT_W = CAMERA.batt_pocket_w              # 30 mm — pocket width
DOOR_THICK = CAMERA.batt_door_thick         # 2.0 mm

OVERLAP = DOOR_SPEC.batt_overlap                    # was 2.0
DOOR_L = BATT_L + 2 * OVERLAP + 4.0        # 66 mm
DOOR_W = BATT_W + 2 * OVERLAP + 4.0        # 38 mm
FILLET = DOOR_SPEC.batt_fillet                       # was 1.5

# =========================================================================
# LIGHT TRAP
# =========================================================================
TRAP_GROOVE_W = DOOR_SPEC.batt_trap_groove_w         # was 1.0
TRAP_GROOVE_DEPTH = DOOR_SPEC.batt_trap_groove_depth  # was 0.8
TRAP_INNER_L = DOOR_L - 2 * 3.0            # inner rectangle
TRAP_INNER_W = DOOR_W - 2 * 3.0

# =========================================================================
# HINGE
# =========================================================================
HINGE_PIN_DIA = DOOR_SPEC.batt_hinge_pin_dia         # was 1.5
HINGE_EAR_W = DOOR_SPEC.batt_hinge_ear_w             # was 4.0
HINGE_EAR_H = DOOR_SPEC.batt_hinge_ear_h             # was 3.0
# Two hinge ears on the rear edge
HINGE_SPACING = DOOR_L - 20.0              # mm — between hinge centers

# =========================================================================
# LATCH
# =========================================================================
LATCH_SLOT_W = DOOR_SPEC.batt_latch_slot_w            # was 10.0
LATCH_SLOT_H = DOOR_SPEC.batt_latch_slot_h            # was 2.0
LATCH_SLOT_DEPTH = DOOR_SPEC.batt_latch_slot_depth    # was 1.0

# =========================================================================
# SPRING CONTACTS (interior placeholders)
# =========================================================================
CONTACT_DIA = DOOR_SPEC.batt_contact_dia              # was 5.0
CONTACT_HEIGHT = DOOR_SPEC.batt_contact_height         # was 1.0
# 4 contacts for 4×AA batteries in 2×2 config
CONTACT_POSITIONS = [
    (-BATT_L / 4.0, -BATT_W / 4.0),        # cell 1
    (-BATT_L / 4.0,  BATT_W / 4.0),        # cell 2
    ( BATT_L / 4.0, -BATT_W / 4.0),        # cell 3
    ( BATT_L / 4.0,  BATT_W / 4.0),        # cell 4
]


def build() -> cq.Workplane:
    """Build the battery door.

    Door lies in XY plane. Exterior face is -Z, interior (contacts) is +Z.
    """
    # --- Main door panel ---
    door = (
        cq.Workplane("XY")
        .box(DOOR_L, DOOR_W, DOOR_THICK)
    )
    try:
        door = door.edges("|Z").fillet(FILLET)
    except Exception:
        pass

    # --- Light trap groove on interior face ---
    # A step around the perimeter so the door overlaps the body opening
    outer_step = (
        cq.Workplane("XY")
        .rect(DOOR_L - 2 * TRAP_GROOVE_W, DOOR_W - 2 * TRAP_GROOVE_W)
        .extrude(TRAP_GROOVE_DEPTH)
        .translate((0, 0, DOOR_THICK / 2.0 - TRAP_GROOVE_DEPTH))
    )
    inner_step = (
        cq.Workplane("XY")
        .rect(TRAP_INNER_L, TRAP_INNER_W)
        .extrude(TRAP_GROOVE_DEPTH + 0.1)
        .translate((0, 0, DOOR_THICK / 2.0 - TRAP_GROOVE_DEPTH - 0.05))
    )
    groove = outer_step.cut(inner_step)
    door = door.cut(groove)

    # --- 2× Snap latches on front edge (replacing coin-slot latch) ---
    # Latches at ±DOOR_L/4.0 on front edge, oriented to hook downward (-Z)
    # for engagement with bottom plate snap pockets.
    for sign in [-1, 1]:
        latch = (
            make_snap_latch()
            .rotate((0, 0, 0), (1, 0, 0), 180)  # hook faces downward (-Z)
            .translate((sign * DOOR_L / 4.0,
                        -DOOR_W / 2.0,
                        -DOOR_THICK / 2.0))
        )
        door = door.union(latch)

    # --- Hinge ears on rear edge ---
    for sign in [-1, 1]:
        hx = sign * HINGE_SPACING / 2.0
        ear = (
            cq.Workplane("XY")
            .box(HINGE_EAR_W, HINGE_EAR_H, DOOR_THICK)
            .translate((hx, DOOR_W / 2.0 + HINGE_EAR_H / 2.0, 0))
        )
        door = door.union(ear)

        # Hinge pin hole through ear
        pin_hole = (
            cq.Workplane("XZ")
            .transformed(offset=(hx, 0, DOOR_W / 2.0 + HINGE_EAR_H / 2.0))
            .circle(HINGE_PIN_DIA / 2.0)
            .extrude(HINGE_EAR_W + 1.0)
            .translate((-HINGE_EAR_W / 2.0 - 0.5, 0, 0))
        )
        door = door.cut(pin_hole)

    # --- Spring contact placeholders on interior ---
    for cx, cy in CONTACT_POSITIONS:
        contact = (
            cq.Workplane("XY")
            .cylinder(CONTACT_HEIGHT, CONTACT_DIA / 2.0)
            .translate((cx, cy, DOOR_THICK / 2.0 + CONTACT_HEIGHT / 2.0))
        )
        door = door.union(contact)

    return door


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/battery_door.step")
    cq.exporters.export(solid, f"{output_dir}/battery_door.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Battery door exported to {output_dir}/")


if __name__ == "__main__":
    export()
