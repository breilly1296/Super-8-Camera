#!/usr/bin/env python3
"""Parametric Super 8 Film Gate — CadQuery Model

Generates a film gate with:
  - Precise Super 8 aperture (5.79 x 4.01 mm)
  - Film channel recessed into the gate face
  - Registration pin hole per Kodak spec
  - Raised pressure-plate lip around the aperture
  - Two M2 mounting holes at diagonal corners

All dimensions are parameters at the top for easy tweaking.
Exports STEP and STL files.
"""

import cadquery as cq

# ---------------------------------------------------------------------------
# Parameters — adjust these to modify the gate design
# ---------------------------------------------------------------------------

# Overall plate
PLATE_WIDTH = 25.0       # mm (X)
PLATE_HEIGHT = 18.0      # mm (Y)
PLATE_THICKNESS = 3.0    # mm (Z)

# Super 8 frame aperture (Kodak standard)
APERTURE_W = 5.79        # mm  (horizontal, across film)
APERTURE_H = 4.01        # mm  (vertical, along film travel)

# Film channel — recessed track the film rides in
CHANNEL_WIDTH = 8.0      # mm  (centered on aperture)
CHANNEL_DEPTH = 0.1      # mm  (into the film-side face)

# Registration pin hole
REG_PIN_DIA = 0.8        # mm
# Kodak spec: pin center is one frame pitch below aperture center
REG_PIN_OFFSET_Y = 4.234 # mm below aperture center

# Pressure-plate lip — raised rim around aperture for film contact
LIP_WIDTH = 0.8          # mm  (rim width around aperture)
LIP_HEIGHT = 0.05        # mm  (raised above film-side surface)

# M2 mounting holes (diagonal corners)
M2_DIA = 2.2             # mm  (clearance hole for M2)
M2_INSET_X = 3.0         # mm from plate edge to hole center (X)
M2_INSET_Y = 3.0         # mm from plate edge to hole center (Y)

# Fillet radius on plate edges
PLATE_FILLET = 1.0        # mm

# Aperture corner radius (slight radius to reduce stress risers)
APERTURE_FILLET = 0.15    # mm


# ---------------------------------------------------------------------------
# Build the gate
# ---------------------------------------------------------------------------

def build_film_gate():
    # --- Base plate ---
    gate = (
        cq.Workplane("XY")
        .box(PLATE_WIDTH, PLATE_HEIGHT, PLATE_THICKNESS)
        .edges("|Z")
        .fillet(PLATE_FILLET)
    )

    # --- Film channel (recessed into +Z face, the film-contact side) ---
    # The channel runs the full height of the plate, centered on X.
    gate = (
        gate
        .faces(">Z")
        .workplane()
        .rect(CHANNEL_WIDTH, PLATE_HEIGHT)
        .cutBlind(-CHANNEL_DEPTH)
    )

    # --- Pressure-plate lip (raised rim around aperture on film side) ---
    # Built on top of the channel floor.  Outer rect = aperture + lip,
    # inner rect = aperture.  Height = lip_height above channel floor,
    # which means it protrudes lip_height - channel_depth relative to the
    # original face (it sits within the channel).
    lip_outer_w = APERTURE_W + 2 * LIP_WIDTH
    lip_outer_h = APERTURE_H + 2 * LIP_WIDTH

    lip = (
        cq.Workplane("XY")
        .box(lip_outer_w, lip_outer_h, LIP_HEIGHT)
        # Position: top of lip flush with channel floor + lip_height
        # Channel floor Z = PLATE_THICKNESS/2 - CHANNEL_DEPTH
        # Lip bottom at channel floor, lip top at channel floor + LIP_HEIGHT
        .translate((
            0,
            0,
            PLATE_THICKNESS / 2 - CHANNEL_DEPTH + LIP_HEIGHT / 2
        ))
    )
    gate = gate.union(lip)

    # --- Aperture (through-hole) ---
    gate = (
        gate
        .faces(">Z")
        .workplane()
        .rect(APERTURE_W, APERTURE_H)
        .cutThruAll()
    )

    # Fillet the aperture edges to reduce stress and improve film glide
    # Select edges of the aperture hole (internal vertical edges)
    gate = (
        gate
        .edges(
            cq.selectors.BoxSelector(
                (-APERTURE_W / 2 - 0.1, -APERTURE_H / 2 - 0.1, -PLATE_THICKNESS),
                ( APERTURE_W / 2 + 0.1,  APERTURE_H / 2 + 0.1,  PLATE_THICKNESS),
            )
        )
        .fillet(APERTURE_FILLET)
    )

    # --- Registration pin hole ---
    # Centered on X, offset below aperture center (−Y direction)
    gate = (
        gate
        .faces(">Z")
        .workplane()
        .center(0, -REG_PIN_OFFSET_Y)
        .hole(REG_PIN_DIA)
    )

    # --- M2 mounting holes (diagonal: top-left and bottom-right) ---
    hole_x = PLATE_WIDTH / 2 - M2_INSET_X
    hole_y = PLATE_HEIGHT / 2 - M2_INSET_Y

    mounting_positions = [
        (-hole_x,  hole_y),   # top-left
        ( hole_x, -hole_y),   # bottom-right
    ]

    gate = (
        gate
        .faces(">Z")
        .workplane()
        .pushPoints(mounting_positions)
        .hole(M2_DIA)
    )

    return gate


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_gate(gate, step_path="film_gate.step", stl_path="film_gate.stl"):
    cq.exporters.export(gate, step_path)
    print(f"  Exported STEP: {step_path}")

    cq.exporters.export(gate, stl_path, tolerance=0.01, angularTolerance=0.1)
    print(f"  Exported STL:  {stl_path}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    sep = "=" * 60
    print(sep)
    print("  SUPER 8 FILM GATE — PARAMETRIC MODEL")
    print(sep)
    print()
    print(f"  Plate:           {PLATE_WIDTH} x {PLATE_HEIGHT} x "
          f"{PLATE_THICKNESS} mm")
    print(f"  Aperture:        {APERTURE_W} x {APERTURE_H} mm "
          f"(r={APERTURE_FILLET} mm corners)")
    print(f"  Film channel:    {CHANNEL_WIDTH} mm wide x "
          f"{CHANNEL_DEPTH} mm deep")
    print(f"  Pressure lip:    {LIP_WIDTH} mm rim, "
          f"{LIP_HEIGHT} mm raised")
    print(f"  Reg pin hole:    dia {REG_PIN_DIA} mm, "
          f"{REG_PIN_OFFSET_Y} mm below aperture center")
    print(f"  Mounting holes:  M2 clearance ({M2_DIA} mm) at "
          f"diagonal corners")
    print(f"  Plate fillet:    {PLATE_FILLET} mm")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print_summary()
    gate = build_film_gate()
    export_gate(gate)
    print()
    print("  " + "=" * 60)


if __name__ == "__main__":
    main()
