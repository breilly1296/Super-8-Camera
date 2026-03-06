"""Pressure plate — spring-steel leaf that holds film flat against the gate.

A 301 stainless steel plate with two raised contact pads that align with
the gate's polished rails. Integral leaf springs provide ~0.5N total force
to press the film flat during exposure without excessive friction.

Spring deflection is calculated from cantilever beam bending formulas.
All dimensions reference master_specs and the film gate geometry.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import (
    FILM, CAMERA, FASTENERS, MATERIALS, MATERIAL_USAGE,
)
from super8cam.parts.film_gate import (
    GATE_W, GATE_H, GATE_THICK, CHANNEL_DEPTH, RAIL_W, RAIL_H,
    MOUNT_PATTERN_X, MOUNT_PATTERN_Y, get_film_plane_origin,
)

MATERIAL = MATERIALS[MATERIAL_USAGE["pressure_plate"]]

# Plate body
PLATE_W = 22.0           # mm — slightly smaller than gate
PLATE_H = 18.0           # mm
PLATE_THICK = 0.3        # mm — thin spring steel

# Raised contact pads — align with gate's pressure rails
PAD_W = 3.0              # mm — width (X direction, matches rail area)
PAD_L = 12.0             # mm — length (Y direction, along film travel)
PAD_H = 0.05             # mm — raised above plate surface

# Aperture window in plate (larger than film frame for clearance)
WINDOW_CLEARANCE = 0.5   # mm — each side beyond film frame
WINDOW_W = FILM.frame_w + 2 * WINDOW_CLEARANCE
WINDOW_H = FILM.frame_h + 2 * WINDOW_CLEARANCE

# Leaf spring geometry (cantilever beams from top and bottom edges)
SPRING_COUNT = 2         # one from top, one from bottom
SPRING_W = 4.0           # mm — beam width
SPRING_L = 6.0           # mm — free cantilever length
SPRING_THICK = PLATE_THICK  # same thickness as plate body

# Material properties for spring calculation
E_301SS = 193e3          # MPa (193 GPa) — Young's modulus for 301 SS
TARGET_FORCE_N = 0.5     # N — total force from both springs

# Mounting: M2 clearance holes matching gate bolt pattern
M2_CLEARANCE = FASTENERS["M2x5_shcs"].clearance_hole  # 2.2mm


def calculate_spring_deflection() -> dict:
    """Calculate the deflection needed for each leaf spring to achieve target force.

    Uses cantilever beam formula:
        delta = F * L^3 / (3 * E * I)
        I = b * h^3 / 12

    where:
        F = force per spring (total / SPRING_COUNT)
        L = free cantilever length
        E = Young's modulus
        b = beam width
        h = beam thickness (= PLATE_THICK)

    Returns dict with spring parameters and calculated values.
    """
    force_per_spring = TARGET_FORCE_N / SPRING_COUNT  # N

    # Second moment of area for rectangular cross-section
    b = SPRING_W   # mm
    h = SPRING_THICK  # mm
    I_mm4 = b * h**3 / 12.0  # mm^4

    # Convert E to N/mm^2 (MPa) — already in MPa
    E_mpa = E_301SS  # N/mm^2

    # Deflection for target force (mm)
    L = SPRING_L  # mm
    delta_mm = force_per_spring * L**3 / (3.0 * E_mpa * I_mm4)

    # Maximum bending stress at root (MPa)
    sigma_max = force_per_spring * L / (b * h**2 / 6.0)

    # Spring constant k = F/delta (N/mm)
    k = force_per_spring / delta_mm if delta_mm > 0 else float('inf')

    return {
        "force_per_spring_n": force_per_spring,
        "cantilever_length_mm": L,
        "beam_width_mm": b,
        "beam_thickness_mm": h,
        "I_mm4": I_mm4,
        "deflection_mm": delta_mm,
        "spring_rate_n_per_mm": k,
        "max_stress_mpa": sigma_max,
        "yield_strength_mpa": MATERIAL.yield_strength,
        "safety_factor": MATERIAL.yield_strength / sigma_max if sigma_max > 0 else float('inf'),
    }


def build() -> cq.Workplane:
    """Build the pressure plate with raised pads and integral leaf springs.

    Coordinate system matches the film gate:
      X = horizontal, Y = vertical (film travel), Z = optical axis.

    The plate sits behind the film (on the rear side of the gate).
    Contact pads face toward the film (positive Z direction).
    """
    # --- Main plate body ---
    plate = (
        cq.Workplane("XY")
        .box(PLATE_W, PLATE_H, PLATE_THICK)
    )

    # --- Aperture window ---
    # Cut-through so light reaches the film
    plate = (
        plate.faces(">Z").workplane()
        .rect(WINDOW_W, WINDOW_H)
        .cutThruAll()
    )

    # --- Raised contact pads ---
    # Two pads flanking the aperture, aligned with the gate's polished rails.
    # The pads sit on the film-facing side (+Z) of the plate.
    # X positions match the gate rail positions.
    rail_inner_x = FILM.frame_w / 2.0
    pad_center_x = rail_inner_x + PAD_W / 2.0

    for sign in [1, -1]:
        pad = (
            cq.Workplane("XY")
            .box(PAD_W, PAD_L, PAD_H)
            .translate((sign * pad_center_x, 0, (PLATE_THICK + PAD_H) / 2.0))
        )
        plate = plate.union(pad)

    # --- Leaf spring cantilevers ---
    # Two beams extending from the top and bottom edges of the plate.
    # These flex to provide the spring force that presses the plate
    # against the film and gate.
    for y_sign in [1, -1]:
        spring = (
            cq.Workplane("XY")
            .box(SPRING_W, SPRING_L, SPRING_THICK)
            .translate((
                0,
                y_sign * (PLATE_H / 2.0 + SPRING_L / 2.0),
                0,
            ))
        )
        plate = plate.union(spring)

    # --- Mounting holes ---
    # M2 clearance holes matching the gate's bolt pattern.
    # Only use the two holes that fit within the plate dimensions.
    mount_pts = [
        ( MOUNT_PATTERN_X / 2,  MOUNT_PATTERN_Y / 2),
        (-MOUNT_PATTERN_X / 2,  MOUNT_PATTERN_Y / 2),
        (-MOUNT_PATTERN_X / 2, -MOUNT_PATTERN_Y / 2),
        ( MOUNT_PATTERN_X / 2, -MOUNT_PATTERN_Y / 2),
    ]
    # Filter to points that fit within the plate
    usable_pts = [
        (x, y) for x, y in mount_pts
        if abs(x) < PLATE_W / 2.0 - 1.0 and abs(y) < PLATE_H / 2.0 - 1.0
    ]
    if usable_pts:
        plate = (
            plate.faces(">Z").workplane()
            .pushPoints(usable_pts)
            .hole(M2_CLEARANCE, PLATE_THICK)
        )

    return plate


def build_assembly() -> tuple:
    """Return (film_gate, pressure_plate) positioned correctly.

    The pressure plate sits behind the gate with a gap equal to the
    film thickness (0.155mm) plus the channel depth. The film rides
    between the gate channel floor and the pressure plate pads.

    Returns:
        (gate_solid, plate_solid) — both as cq.Workplane objects,
        with the plate translated to its assembled position.
    """
    from super8cam.parts.film_gate import build as build_gate

    gate = build_gate()
    plate = build()

    # Position the pressure plate behind the gate.
    # Gate rear face is at Z = -GATE_THICK/2.
    # Film channel floor is at Z = -(GATE_THICK/2) + CHANNEL_DEPTH.
    # Film sits on the channel floor, thickness = FILM.thickness (0.155mm).
    # Pressure plate pads contact the film from behind.
    # Plate pad surface should be at:
    #   Z = film_plane_z + FILM.thickness
    #   where film_plane_z = -(GATE_THICK/2) + CHANNEL_DEPTH
    #
    # The plate body center is at Z=0 in its own frame.
    # Pad top surface is at Z = (PLATE_THICK + PAD_H) / 2 + PAD_H/2
    #   = PLATE_THICK/2 + PAD_H
    # We want that surface at film_plane_z + FILM.thickness.

    film_plane_z = get_film_plane_origin()[2]
    pad_top_local = PLATE_THICK / 2.0 + PAD_H
    plate_z = film_plane_z + FILM.thickness - pad_top_local

    plate = plate.translate((0, 0, plate_z))

    return (gate, plate)


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/pressure_plate.step")
    cq.exporters.export(solid, f"{output_dir}/pressure_plate.stl",
                        tolerance=0.005, angularTolerance=0.05)

    # Print spring analysis
    spring = calculate_spring_deflection()
    print(f"  Pressure plate exported to {output_dir}/")
    print(f"  Spring analysis:")
    print(f"    Force per spring:  {spring['force_per_spring_n']:.3f} N")
    print(f"    Deflection needed: {spring['deflection_mm']:.4f} mm")
    print(f"    Spring rate:       {spring['spring_rate_n_per_mm']:.2f} N/mm")
    print(f"    Max stress:        {spring['max_stress_mpa']:.1f} MPa")
    print(f"    Yield strength:    {spring['yield_strength_mpa']:.0f} MPa")
    print(f"    Safety factor:     {spring['safety_factor']:.1f}")


if __name__ == "__main__":
    export()
