"""Film gate — precision brass (C360) plate defining the film plane and image aperture.

This is the most critical precision part in the camera. The aperture edges
define image sharpness, the channel floor defines the film plane (focus
reference), and the registration pin hole sets frame-to-frame accuracy.

All dimensions imported from master_specs — no magic numbers.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, CMOUNT, TOL, FASTENERS, MATERIALS, MATERIAL_USAGE,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["film_gate"]]

# Gate body dimensions (from CAMERA spec)
GATE_W = CAMERA.gate_plate_w            # 24.0 mm
GATE_H = CAMERA.gate_plate_h            # 20.0 mm
GATE_THICK = CAMERA.gate_plate_thick    # 4.0 mm

# Film channel on rear face (film side)
CHANNEL_W = CAMERA.gate_channel_w       # 8.2 mm
CHANNEL_DEPTH = CAMERA.gate_channel_depth  # 0.20 mm

# Pressure plate contact rails
RAIL_W = CAMERA.gate_rail_w             # 1.5 mm
RAIL_H = CAMERA.gate_rail_h             # 0.15 mm

# Aperture taper (lens side is wider for wide-angle clearance)
APERTURE_TAPER = CAMERA.gate_aperture_taper    # 0.2 mm
APERTURE_CHAMFER = CAMERA.gate_aperture_chamfer  # 0.05 mm

# Perforation clearance slot
PERF_SLOT_W = CAMERA.gate_perf_slot_w   # 1.5 mm

# Claw access slot
CLAW_SLOT_W = CAMERA.gate_claw_slot_w   # 2.0 mm
CLAW_SLOT_H = CAMERA.gate_claw_slot_h   # 8.0 mm

# Registration pin hole
REG_PIN_HOLE_DIA = CAMERA.gate_reg_pin_hole_dia    # 0.82 mm
REG_PIN_PROTRUSION = CAMERA.gate_reg_pin_protrusion  # 0.5 mm

# Mounting: 4× M2 on bolt pattern
MOUNT_PATTERN_X = CAMERA.gate_mount_pattern_x   # 20.0 mm
MOUNT_PATTERN_Y = CAMERA.gate_mount_pattern_y   # 16.0 mm
M2_TAP_DIA = FASTENERS["M2x5_shcs"].tap_hole
M2_THREAD_DEPTH = CAMERA.gate_m2_thread_depth   # 3.0 mm

# Dowel pins
DOWEL_DIA = CAMERA.gate_dowel_dia       # 2.0 mm
DOWEL_DEPTH = CAMERA.gate_dowel_depth   # 3.0 mm


def build() -> cq.Workplane:
    """Build the complete film gate.

    Coordinate system:
      X = horizontal (camera left/right, + = camera-right)
      Y = vertical (film travel direction, + = up)
      Z = optical axis (+ = toward lens, - = toward film)

    The gate body is centered at the origin. The rear face (film side)
    is at Z = -GATE_THICK/2, the front face (lens side) at Z = +GATE_THICK/2.
    """
    half_t = GATE_THICK / 2.0

    # --- Base block ---
    gate = (
        cq.Workplane("XY")
        .box(GATE_W, GATE_H, GATE_THICK)
    )

    # --- Film channel on rear face (Z-) ---
    # A shallow recess the full height of the gate, centered on film path
    gate = (
        gate.faces("<Z").workplane()
        .rect(CHANNEL_W, GATE_H)
        .cutBlind(-CHANNEL_DEPTH)
    )

    # --- Pressure plate contact rails ---
    # Two polished rails flanking the aperture, raised above channel floor.
    # Each rail is RAIL_W wide, sitting just inside the channel edges,
    # adjacent to the aperture on each side.
    # Rail X positions: centered on the boundary between aperture edge and
    # channel edge, i.e. from aperture edge outward.
    rail_inner_x = FILM.frame_w / 2.0  # inner edge at aperture boundary
    rail_outer_x = rail_inner_x + RAIL_W
    rail_center_x = (rail_inner_x + rail_outer_x) / 2.0

    for sign in [1, -1]:
        rail = (
            cq.Workplane("XY")
            .box(RAIL_W, GATE_H, RAIL_H)
            .translate((
                sign * rail_center_x,
                0,
                -(half_t - CHANNEL_DEPTH - RAIL_H / 2.0)
            ))
        )
        gate = gate.union(rail)

    # --- Aperture through-hole ---
    # Rectangular hole for the image window. We cut it as a simple
    # rectangle first, then add the taper on the lens side.
    gate = (
        gate.faces(">Z").workplane()
        .rect(FILM.frame_w, FILM.frame_h)
        .cutThruAll()
    )

    # --- Aperture taper on lens side ---
    # The lens-side opening is APERTURE_TAPER wider (total) to avoid
    # clipping from wide-angle lenses. Model as a tapered pocket from
    # the front face inward ~1mm.
    taper_depth = 1.0  # mm — depth of the tapered relief
    taper_w = FILM.frame_w + APERTURE_TAPER
    taper_h = FILM.frame_h + APERTURE_TAPER
    gate = (
        gate.faces(">Z").workplane()
        .rect(taper_w, taper_h)
        .cutBlind(-taper_depth)
    )

    # --- Aperture chamfer on lens side ---
    # Select the aperture edges on the lens face and apply a small chamfer
    # to prevent reflections off sharp edges.
    # We approximate this by cutting a very shallow chamfered frame around
    # the tapered aperture opening.
    chamfer_w = taper_w + 2 * APERTURE_CHAMFER
    chamfer_h = taper_h + 2 * APERTURE_CHAMFER
    gate = (
        gate.faces(">Z").workplane()
        .rect(chamfer_w, chamfer_h)
        .cutBlind(-APERTURE_CHAMFER)
    )

    # --- Perforation clearance slot ---
    # Vertical slot to the left of the film channel where perforations run.
    # The claw tip enters through this slot. Full height of gate.
    # Position: just left of the film channel.
    # Film channel spans X = -CHANNEL_W/2 to +CHANNEL_W/2.
    # Perforations are on the camera-left side (negative X in our convention).
    perf_slot_center_x = -(CHANNEL_W / 2.0 + PERF_SLOT_W / 2.0)
    gate = (
        gate.faces("<Z").workplane()
        .center(perf_slot_center_x, 0)
        .rect(PERF_SLOT_W, GATE_H)
        .cutBlind(-CHANNEL_DEPTH)  # same depth as film channel
    )

    # --- Claw access slot ---
    # A through-slot behind the perforation area for the pulldown claw.
    # 2mm wide × 8mm tall, positioned in the perforation clearance zone.
    # Must not interfere with the registration pin hole.
    # The claw enters from the rear, so this is a through-cut.
    # Position it so the top of the slot is above aperture center
    # and the bottom clears the reg pin.
    # Reg pin is at Y = -4.234mm (one perf pitch below aperture center).
    # Place claw slot so its bottom edge is above the reg pin with clearance.
    claw_slot_center_x = perf_slot_center_x
    # Center the claw slot so it spans the pulldown travel zone.
    # The claw needs to travel 4.234mm downward starting from above
    # the registration pin position. Center the slot to cover this travel.
    claw_slot_center_y = -FILM.perf_pitch / 2.0 + CLAW_SLOT_H / 2.0 - FILM.perf_pitch / 2.0
    # Simpler: place the slot starting just above the reg pin and going up
    reg_pin_y = -FILM.reg_pin_below_frame_center
    claw_slot_bottom = reg_pin_y + 1.0  # 1mm clearance above reg pin
    claw_slot_center_y = claw_slot_bottom + CLAW_SLOT_H / 2.0

    gate = (
        gate.faces("<Z").workplane()
        .center(claw_slot_center_x, -claw_slot_center_y)  # workplane Y is flipped on rear
        .rect(CLAW_SLOT_W, CLAW_SLOT_H)
        .cutThruAll()
    )

    # --- Registration pin hole ---
    # 0.82mm diameter H7, located one perforation pitch below aperture center,
    # aligned with the perforation clearance slot.
    # Depth: through the gate but with a step — the pin protrudes REG_PIN_PROTRUSION
    # into the channel. We model it as a through-hole (pin is press-fit from rear).
    reg_pin_x = perf_slot_center_x
    gate = (
        gate.faces(">Z").workplane()
        .center(reg_pin_x, reg_pin_y)
        .hole(REG_PIN_HOLE_DIA, GATE_THICK)
    )

    # --- M2 threaded mounting holes ---
    # Four holes at corners of 20mm × 16mm bolt pattern
    mount_pts = [
        ( MOUNT_PATTERN_X / 2,  MOUNT_PATTERN_Y / 2),
        (-MOUNT_PATTERN_X / 2,  MOUNT_PATTERN_Y / 2),
        (-MOUNT_PATTERN_X / 2, -MOUNT_PATTERN_Y / 2),
        ( MOUNT_PATTERN_X / 2, -MOUNT_PATTERN_Y / 2),
    ]
    gate = (
        gate.faces("<Z").workplane()
        .pushPoints(mount_pts)
        .hole(M2_TAP_DIA, M2_THREAD_DEPTH)
    )

    # --- Dowel pin holes ---
    # Two 2mm H7 holes on a diagonal for repeatable alignment.
    # Place at top-right and bottom-left of the bolt pattern, inset slightly.
    dowel_inset = 2.0  # mm inward from mount holes
    dowel_pts = [
        ( MOUNT_PATTERN_X / 2 - dowel_inset,  MOUNT_PATTERN_Y / 2 - dowel_inset),
        (-MOUNT_PATTERN_X / 2 + dowel_inset, -MOUNT_PATTERN_Y / 2 + dowel_inset),
    ]
    gate = (
        gate.faces("<Z").workplane()
        .pushPoints(dowel_pts)
        .hole(DOWEL_DIA, DOWEL_DEPTH)
    )

    return gate


def get_film_plane_origin() -> tuple:
    """Return the 3D coordinate (x, y, z) of the film plane center.

    The film plane is the floor of the film channel on the rear face of the gate.
    Every other part in the camera references this point.

    Returns:
        (x, y, z) in mm — the center of the exposed frame on the film plane.
        x=0, y=0 (centered on aperture), z = rear face + channel depth.
    """
    # Rear face is at Z = -GATE_THICK/2.
    # Channel floor is CHANNEL_DEPTH inward from the rear face.
    film_plane_z = -(GATE_THICK / 2.0) + CHANNEL_DEPTH
    return (0.0, 0.0, film_plane_z)


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/film_gate.step")
    cq.exporters.export(solid, f"{output_dir}/film_gate.stl",
                        tolerance=0.005, angularTolerance=0.05)
    print(f"  Film gate exported to {output_dir}/")
    fp = get_film_plane_origin()
    print(f"  Film plane origin: ({fp[0]:.3f}, {fp[1]:.3f}, {fp[2]:.3f})")


if __name__ == "__main__":
    export()
