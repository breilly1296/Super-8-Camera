"""Film channel — guide rails and rollers for the film path from cartridge to gate.

The film path:
  Cartridge exit → guide roller → ~5mm channel → FILM GATE → ~5mm channel
  → guide roller → cartridge entry (takeup side)

The channel is 8.2mm wide (matching the film gate), 0.2mm deep, with polished
surfaces to minimize friction and scratching.

Small slack loops (2-3mm) between the cartridge and each guide roller absorb
the intermittent claw motion — the claw pulls film in jerks but the cartridge
feeds/takes up continuously. Without these loops the film would tear.

Guide rollers at entry and exit prevent the film from touching sharp edges
and ensure smooth feeding under all conditions.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, FASTENERS, MATERIALS,
)
from super8cam.parts.film_gate import GATE_H, CHANNEL_W, CHANNEL_DEPTH

# =========================================================================
# CHANNEL DIMENSIONS
# =========================================================================
CHANNEL_LENGTH_EACH = 5.0       # mm — channel length on each side of gate
CHANNEL_TOTAL = GATE_H + 2 * CHANNEL_LENGTH_EACH  # 30mm total guided path
CHANNEL_WIDTH = CHANNEL_W       # 8.2mm — matches gate
CHANNEL_DEPTH_MM = CHANNEL_DEPTH  # 0.2mm

RAIL_THICKNESS = 1.5            # mm — width of each guide rail
RAIL_HEIGHT = 2.0               # mm — stands off from mounting surface

# =========================================================================
# GUIDE ROLLERS
# =========================================================================
ROLLER_DIA = 3.0                # mm — small diameter for tight path
ROLLER_WIDTH = 8.5              # mm — slightly wider than film (8.0mm)
ROLLER_SHAFT_DIA = 1.5          # mm — stainless steel shaft
ROLLER_SHAFT_LENGTH = 12.0      # mm — extends into brackets on each side

# Roller positions: just beyond the guide channel ends
# Film travels in the Y direction (vertical), gate centered at Y=0
ROLLER_ENTRY_Y = -(GATE_H / 2.0 + CHANNEL_LENGTH_EACH + ROLLER_DIA / 2.0)
ROLLER_EXIT_Y = (GATE_H / 2.0 + CHANNEL_LENGTH_EACH + ROLLER_DIA / 2.0)

# Roller brackets
BRACKET_THICK = 1.5             # mm
BRACKET_H = 6.0                 # mm — height of bracket ears
BRACKET_W = ROLLER_WIDTH + 2 * BRACKET_THICK  # total width

# =========================================================================
# FILM LOOP GEOMETRY
# =========================================================================
# Slack loops between cartridge and rollers absorb intermittent motion.
# The loop is a gentle U-shape with ~2-3mm of extra film.
LOOP_SLACK_MM = 2.5             # mm — extra film length in each loop
LOOP_DEPTH_MM = 3.0             # mm — how far the loop extends outward
MIN_BEND_RADIUS = 5.0           # mm — minimum to avoid film damage

# M2 mounting holes for channel rails
M2_CLEARANCE = FASTENERS["M2x5_shcs"].clearance_hole  # 2.2mm
RAIL_MOUNT_SPACING = 20.0      # mm — spacing along Y


def build_guide_rails() -> cq.Workplane:
    """Build a pair of guide rails flanking the film path.

    The rails create a shallow channel (8.2mm wide × 0.2mm deep) that
    constrains the film laterally as it approaches and leaves the gate.

    Coordinate system: Y = film travel direction, X = across film width.
    """
    rail_length = CHANNEL_TOTAL

    # Channel base plate (the floor between the rails)
    base = (
        cq.Workplane("XY")
        .box(CHANNEL_WIDTH + 2 * RAIL_THICKNESS, rail_length, RAIL_HEIGHT)
    )

    # Cut the channel recess (film sits in this shallow groove)
    channel_cut = (
        cq.Workplane("XY")
        .box(CHANNEL_WIDTH, rail_length, CHANNEL_DEPTH_MM)
        .translate((0, 0, RAIL_HEIGHT / 2.0 - CHANNEL_DEPTH_MM / 2.0))
    )
    base = base.cut(channel_cut)

    # M2 mounting holes at each end
    mount_pts = [
        (-(CHANNEL_WIDTH / 2.0 + RAIL_THICKNESS / 2.0), -RAIL_MOUNT_SPACING / 2.0),
        (-(CHANNEL_WIDTH / 2.0 + RAIL_THICKNESS / 2.0), RAIL_MOUNT_SPACING / 2.0),
        ((CHANNEL_WIDTH / 2.0 + RAIL_THICKNESS / 2.0), -RAIL_MOUNT_SPACING / 2.0),
        ((CHANNEL_WIDTH / 2.0 + RAIL_THICKNESS / 2.0), RAIL_MOUNT_SPACING / 2.0),
    ]
    base = (
        base.faces(">Z").workplane()
        .pushPoints(mount_pts)
        .hole(M2_CLEARANCE, RAIL_HEIGHT)
    )

    return base


def build_guide_roller() -> cq.Workplane:
    """Build a single guide roller (smooth cylinder on shaft).

    Material: Delrin 150 (self-lubricating, won't scratch film).
    """
    # Roller body
    roller = (
        cq.Workplane("XY")
        .cylinder(ROLLER_WIDTH, ROLLER_DIA / 2.0)
    )

    # Central bore for shaft
    roller = (
        roller.faces(">Z").workplane()
        .hole(ROLLER_SHAFT_DIA + 0.05, ROLLER_WIDTH)  # clearance fit
    )

    # Slight crown (0.05mm) to center the film — approximate as taper
    # (Film tends to track toward the high point of a crowned roller)
    # For CadQuery simplicity, skip the micro-crown; functional in practice.

    return roller


def build_roller_shaft() -> cq.Workplane:
    """Build the roller shaft (stainless steel pin)."""
    shaft = (
        cq.Workplane("XY")
        .cylinder(ROLLER_SHAFT_LENGTH, ROLLER_SHAFT_DIA / 2.0)
    )
    return shaft


def build_roller_bracket() -> cq.Workplane:
    """Build the roller bracket (two ears with shaft holes).

    The bracket holds the roller shaft and mounts to the camera body.
    """
    # Two ears connected by a base
    ear_spacing = ROLLER_WIDTH + 1.0  # gap between ears
    base_w = ear_spacing + 2 * BRACKET_THICK

    bracket = (
        cq.Workplane("XY")
        .box(base_w, BRACKET_H, BRACKET_THICK)
    )

    # Left ear
    left_ear = (
        cq.Workplane("XY")
        .box(BRACKET_THICK, BRACKET_H, BRACKET_H)
        .translate((-ear_spacing / 2.0 - BRACKET_THICK / 2.0, 0,
                    BRACKET_H / 2.0 - BRACKET_THICK / 2.0))
    )

    # Right ear
    right_ear = (
        cq.Workplane("XY")
        .box(BRACKET_THICK, BRACKET_H, BRACKET_H)
        .translate((ear_spacing / 2.0 + BRACKET_THICK / 2.0, 0,
                    BRACKET_H / 2.0 - BRACKET_THICK / 2.0))
    )

    bracket = bracket.union(left_ear).union(right_ear)

    # Shaft holes through the ears
    for sign in [-1, 1]:
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=(
                sign * (ear_spacing / 2.0 + BRACKET_THICK / 2.0),
                0,
                BRACKET_H / 2.0 - BRACKET_THICK / 2.0 + BRACKET_H / 2.0 - 1.5
            ))
            .circle(ROLLER_SHAFT_DIA / 2.0 + 0.025)  # H7 fit
            .extrude(BRACKET_THICK + 0.2)
        )
        bracket = bracket.cut(hole)

    # M2 mounting hole in base
    bracket = (
        bracket.faces("<Z").workplane()
        .hole(M2_CLEARANCE, BRACKET_THICK)
    )

    return bracket


def build() -> cq.Workplane:
    """Build the complete film channel (rails only, rollers separate)."""
    return build_guide_rails()


def build_roller_assembly() -> cq.Assembly:
    """Build a single roller + shaft + bracket as an assembly."""
    assy = cq.Assembly(name="guide_roller_assy")
    assy.add(build_guide_roller(), name="roller",
             loc=cq.Location((0, 0, 0)))
    assy.add(build_roller_shaft(), name="shaft",
             loc=cq.Location((0, 0, 0)))
    assy.add(build_roller_bracket(), name="bracket",
             loc=cq.Location((0, 0, -ROLLER_DIA / 2.0 - BRACKET_THICK / 2.0)))
    return assy


def get_film_path_geometry() -> dict:
    """Return key geometry for the film path layout."""
    return {
        "channel_width": CHANNEL_WIDTH,
        "channel_depth": CHANNEL_DEPTH_MM,
        "channel_total_length": CHANNEL_TOTAL,
        "roller_dia": ROLLER_DIA,
        "roller_width": ROLLER_WIDTH,
        "roller_entry_y": ROLLER_ENTRY_Y,
        "roller_exit_y": ROLLER_EXIT_Y,
        "loop_slack": LOOP_SLACK_MM,
        "loop_depth": LOOP_DEPTH_MM,
        "min_bend_radius": MIN_BEND_RADIUS,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/film_channel.step")
    cq.exporters.export(solid, f"{output_dir}/film_channel.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Film channel exported to {output_dir}/")

    roller = build_guide_roller()
    cq.exporters.export(roller, f"{output_dir}/guide_roller.step")
    print(f"  Guide roller exported to {output_dir}/")


if __name__ == "__main__":
    export()
