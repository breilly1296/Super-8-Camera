"""Top plate — covers the top of the camera body, carries viewfinder and accessory shoe.

Features:
  - Crowned plate (2mm convex crown via cylinder intersection)
  - Accessory shoe (cold shoe, ISO 518 standard: 18mm wide slot)
  - Strap lug on the right side
  - Viewfinder dovetail rail
  - 4× snap latches to attach to body halves

The viewfinder is offset 5mm left and sits on top.
"""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, FASTENERS, SCULPT
from super8cam.parts.interfaces import make_snap_latch, make_dovetail_rail

# =========================================================================
# PLATE DIMENSIONS
# =========================================================================
WALL = CAMERA.wall_thickness          # 2.5 mm
BODY_L = CAMERA.body_length           # 148 mm
BODY_D = CAMERA.body_depth            # 52 mm
BODY_H = CAMERA.body_height           # 88 mm
FILLET = CAMERA.body_fillet            # 4 mm

PLATE_L = BODY_L - 2.0               # mm — slightly inset from body edges
PLATE_D = BODY_D - 2.0               # mm
PLATE_THICK = WALL                    # 2.5 mm

# =========================================================================
# ACCESSORY (COLD) SHOE — ISO 518
# =========================================================================
SHOE_W = 18.0                          # mm — slot width (ISO standard)
SHOE_D = 18.0                          # mm — slot depth along body
SHOE_H = 2.0                           # mm — slot height
SHOE_X = 0.0                           # centered on plate
SHOE_Y = -PLATE_D / 4.0               # front quarter

# Spring contact recess in shoe floor
SPRING_W = 4.0                         # mm
SPRING_D = 12.0                        # mm
SPRING_DEPTH = 0.5                     # mm

# =========================================================================
# VIEWFINDER MOUNT
# =========================================================================
VF_OFFSET_LEFT = 5.0                   # mm — left of center
VF_TAB_SPACING = 30.0                  # mm — matching viewfinder tabs
VF_X = -VF_OFFSET_LEFT
M2 = FASTENERS["M2x5_shcs"]

# =========================================================================
# PLATE MOUNTING (M2.5 to body)
# =========================================================================
M25 = FASTENERS["M2_5x6_shcs"]
PLATE_MOUNT_POSITIONS = [
    (-PLATE_L / 2.0 + 8.0, -PLATE_D / 2.0 + 8.0),   # front-left
    (-PLATE_L / 2.0 + 8.0,  PLATE_D / 2.0 - 8.0),    # rear-left
    ( PLATE_L / 2.0 - 8.0, -PLATE_D / 2.0 + 8.0),    # front-right
    ( PLATE_L / 2.0 - 8.0,  PLATE_D / 2.0 - 8.0),    # rear-right
]

# Strap lug on right side
STRAP_LUG_X = PLATE_L / 2.0 - 5.0
STRAP_LUG_Y = 0.0
STRAP_HOLE_DIA = 3.0                   # mm
STRAP_LUG_W = 8.0
STRAP_LUG_H = 6.0


def build() -> cq.Workplane:
    """Build the top plate.

    Lies in the XY plane at the top of the body (Z = BODY_H/2).
    X = left-right, Y = front-back.
    """
    # --- Crowned base plate ---
    # Start with a plate that is PLATE_THICK + CROWN tall, then intersect
    # with a large cylinder along X to carve the crowned top surface.
    # Sagitta formula: R = (PLATE_D/2)^2 / (2*CROWN) + CROWN/2
    CROWN = SCULPT.top_crown  # 2.0 mm
    crown_r = (PLATE_D / 2.0) ** 2 / (2.0 * CROWN) + CROWN / 2.0

    plate = (
        cq.Workplane("XY")
        .box(PLATE_L, PLATE_D, PLATE_THICK + CROWN)
        .translate((0, 0, CROWN / 2.0))
    )

    # Large cylinder along X axis, positioned so its bottom tangent
    # is at Z = PLATE_THICK/2 + CROWN (top of the oversized plate),
    # carving the crown from the top surface.
    crown_cyl = (
        cq.Workplane("YZ")
        .cylinder(PLATE_L + 2.0, crown_r)
        .translate((0, 0, PLATE_THICK / 2.0 + CROWN - crown_r))
    )
    plate = plate.intersect(crown_cyl)

    try:
        plate = plate.edges("|Z").fillet(FILLET - 1.0)
    except Exception:
        pass

    # --- Accessory shoe slot ---
    shoe_slot = (
        cq.Workplane("XY")
        .box(SHOE_W, SHOE_D, SHOE_H)
        .translate((SHOE_X, SHOE_Y, PLATE_THICK / 2.0 - SHOE_H / 2.0))
    )
    plate = plate.cut(shoe_slot)

    # Spring contact recess in shoe floor
    spring_recess = (
        cq.Workplane("XY")
        .box(SPRING_W, SPRING_D, SPRING_DEPTH)
        .translate((SHOE_X, SHOE_Y,
                    PLATE_THICK / 2.0 - SHOE_H - SPRING_DEPTH / 2.0))
    )
    plate = plate.cut(spring_recess)

    # --- Viewfinder tube clearance cutout ---
    # Cut a through-hole where the viewfinder tube passes through the plate.
    # The viewfinder is at LENS_X - VF_OFFSET_LEFT in world X (= plate local X),
    # near the front edge of the plate, running along Y into the camera.
    VF_PASS_X = CAMERA.lens_mount_offset_x - VF_OFFSET_LEFT
    VF_TUBE_W = 10.0   # viewfinder tube width (from VF_SPEC)
    VF_TUBE_D = 8.0     # viewfinder tube depth
    VF_MARGIN = 5.0     # clearance margin
    vf_cutout = (
        cq.Workplane("XY")
        .box(VF_TUBE_W + VF_MARGIN, VF_TUBE_D + VF_MARGIN, PLATE_THICK + 2)
        .translate((VF_PASS_X,
                    -PLATE_D / 2.0 + (VF_TUBE_D + VF_MARGIN) / 2.0,
                    0))
    )
    plate = plate.cut(vf_cutout)

    # --- Viewfinder dovetail rail on top surface ---
    # Replaces M2 screw holes; viewfinder now slides onto dovetail.
    # Rail along Y axis at X = VF_X (-5mm), 40mm long, raised above surface.
    VF_RAIL_LENGTH = 40.0
    vf_rail = (
        make_dovetail_rail(VF_RAIL_LENGTH)
        .translate((VF_X, 0, PLATE_THICK / 2.0))
    )
    plate = plate.union(vf_rail)

    # --- 4× Snap latches replacing M2.5 screw holes ---
    # Latches oriented downward (-Z) to engage snap pockets in body halves.
    for px, py in PLATE_MOUNT_POSITIONS:
        latch = (
            make_snap_latch()
            .rotate((0, 0, 0), (1, 0, 0), 180)  # hook faces downward (-Z)
            .translate((px, py, -PLATE_THICK / 2.0))
        )
        plate = plate.union(latch)

    # --- Strap lug on right side ---
    lug = (
        cq.Workplane("XY")
        .box(STRAP_LUG_W, 4.0, STRAP_LUG_H)
        .translate((STRAP_LUG_X, STRAP_LUG_Y,
                    PLATE_THICK / 2.0 + STRAP_LUG_H / 2.0))
    )
    plate = plate.union(lug)

    # Strap hole through lug
    plate = (
        plate.faces(">Z").workplane()
        .center(STRAP_LUG_X, STRAP_LUG_Y)
        .hole(STRAP_HOLE_DIA, STRAP_LUG_H + PLATE_THICK)
    )

    return plate


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/top_plate.step")
    cq.exporters.export(solid, f"{output_dir}/top_plate.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Top plate exported to {output_dir}/")


if __name__ == "__main__":
    export()
