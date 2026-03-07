"""Viewfinder — Galilean optical viewfinder for framing.

A simple reverse-telescope design (like a gunsight). No through-the-lens
viewing — this avoids the complexity of a beam splitter in the optical path.
Accepts parallax error at this MVP stage.

Layout:
  - Front element: plano-concave, f=-20mm, 8mm dia (diverging)
  - Rear element: plano-convex, f=+30mm, 8mm dia (eyepiece, converging)
  - Combined: ~0.5× magnification, ~42 deg horizontal FOV
    (matches a 6mm lens on Super 8 format)
  - Bright-line frame at the internal focal plane (5.79:4.01 aspect ratio)
  - Rectangular tube 10mm × 8mm × 40mm long
  - Two M2 mounting tabs on the bottom

Parallax: viewfinder offset ~20mm above and 5mm left of taking lens.
At typical shooting distances (>1m) this is negligible.
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import FILM, CAMERA, FASTENERS, VF_SPEC
from super8cam.parts.interfaces import make_dovetail_slider

# =========================================================================
# TUBE DIMENSIONS
# =========================================================================
TUBE_W = VF_SPEC.tube_w                # mm — width (horizontal)
TUBE_H = VF_SPEC.tube_h                # mm — height (vertical)
TUBE_LENGTH = VF_SPEC.tube_length      # mm — front to rear
TUBE_WALL = VF_SPEC.tube_wall          # mm — wall thickness

# =========================================================================
# OPTICAL ELEMENTS (modeled as discs for CadQuery)
# =========================================================================
LENS_DIA = VF_SPEC.lens_dia            # mm — both elements
LENS_THICK = VF_SPEC.lens_thick        # mm — disc thickness for modeling

FRONT_FOCAL_LENGTH = VF_SPEC.front_focal_length  # mm — plano-concave (diverging)
REAR_FOCAL_LENGTH = VF_SPEC.rear_focal_length    # mm — plano-convex (eyepiece)

# Element positions (from rear of tube, eye end)
REAR_ELEMENT_Z = VF_SPEC.rear_element_z                 # mm from eye end
FRONT_ELEMENT_Z = TUBE_LENGTH - VF_SPEC.rear_element_z  # mm from eye end

# =========================================================================
# BRIGHT-LINE FRAME
# =========================================================================
# Wire frame at the internal focal plane showing the image boundary.
# Aspect ratio matches Super 8 frame: 5.79:4.01
FRAME_ASPECT = FILM.frame_w / FILM.frame_h  # ~1.443
# Scale to fit within the tube bore
FRAME_H = TUBE_H - 2 * TUBE_WALL - 1.0     # mm — visible height (5.0mm)
FRAME_W = FRAME_H * FRAME_ASPECT            # mm — visible width (~7.2mm)
FRAME_WIRE_DIA = VF_SPEC.frame_wire_dia      # mm — wire thickness
# Position: roughly at the focal plane of the eyepiece
# For a Galilean telescope the virtual focal plane is in front of the eye lens
# We place the bright-line frame at ~60% of tube length from the rear
FRAME_Z = TUBE_LENGTH * 0.6                 # mm from eye end

# =========================================================================
# MOUNTING TABS
# =========================================================================
TAB_W = VF_SPEC.tab_w                  # mm — each tab width
TAB_H = VF_SPEC.tab_h                  # mm — extends below tube
TAB_THICK = VF_SPEC.tab_thick          # mm — thickness along optical axis
TAB_SPACING = VF_SPEC.tab_spacing      # mm — center-to-center along tube length
M2_CLEARANCE = FASTENERS["M2x5_shcs"].clearance_hole  # 2.2mm

# Viewfinder offset from taking lens
VF_OFFSET_UP = VF_SPEC.offset_up       # mm — above optical axis
VF_OFFSET_LEFT = VF_SPEC.offset_left   # mm — to the left


def build_tube() -> cq.Workplane:
    """Build the viewfinder tube shell (rectangular, with baffles)."""
    # Outer tube
    tube = (
        cq.Workplane("XY")
        .rect(TUBE_W, TUBE_H)
        .extrude(TUBE_LENGTH)
    )

    # Hollow interior
    inner_w = TUBE_W - 2 * TUBE_WALL
    inner_h = TUBE_H - 2 * TUBE_WALL
    inner = (
        cq.Workplane("XY")
        .rect(inner_w, inner_h)
        .extrude(TUBE_LENGTH)
    )
    tube = tube.cut(inner)

    # Front aperture (objective end, at Z=TUBE_LENGTH)
    tube = (
        tube.faces(">Z").workplane()
        .circle(LENS_DIA / 2.0 + 0.1)
        .cutBlind(-TUBE_WALL)
    )

    # Rear aperture (eye end, at Z=0)
    tube = (
        tube.faces("<Z").workplane()
        .circle(LENS_DIA / 2.0 + 0.1)
        .cutBlind(-TUBE_WALL)
    )

    return tube


def build_front_element() -> cq.Workplane:
    """Build the front lens element (plano-concave disc model)."""
    lens = (
        cq.Workplane("XY")
        .cylinder(LENS_THICK, LENS_DIA / 2.0)
    )
    # Concave surface approximation: shallow spherical cup on front face
    # Radius of curvature for plano-concave: R = (n-1) × f = ~0.5 × 20 = 10mm
    # We just model the concavity as a shallow pocket
    sag = VF_SPEC.front_sag  # mm — approximate sag of the concave surface
    lens = (
        lens.faces(">Z").workplane()
        .circle(LENS_DIA / 2.0 - 0.2)
        .cutBlind(-sag)
    )
    return lens


def build_rear_element() -> cq.Workplane:
    """Build the rear lens element (plano-convex disc model)."""
    lens = (
        cq.Workplane("XY")
        .cylinder(LENS_THICK, LENS_DIA / 2.0)
    )
    # Convex surface approximation: the rear face bulges out.
    # For CadQuery modeling we add a slight dome (union a spherical cap).
    # For simplicity, model as a plain disc — the dome is cosmetic.
    return lens


def build_bright_line_frame() -> cq.Workplane:
    """Build the bright-line frame insert (thin wire rectangle)."""
    # Outer frame
    outer = (
        cq.Workplane("XY")
        .rect(FRAME_W + FRAME_WIRE_DIA, FRAME_H + FRAME_WIRE_DIA)
        .extrude(FRAME_WIRE_DIA)
    )
    # Inner cutout (the viewing window)
    inner = (
        cq.Workplane("XY")
        .rect(FRAME_W - FRAME_WIRE_DIA, FRAME_H - FRAME_WIRE_DIA)
        .extrude(FRAME_WIRE_DIA)
    )
    frame = outer.cut(inner)
    return frame


def build_mounting_tabs() -> cq.Workplane:
    """Build dovetail slider base for mounting to top plate rail.

    Replaces the previous screw-hole tabs with a 35mm dovetail slider
    (1 thumbscrew) that mates with the top plate's dovetail rail.
    Slider is positioned below the tube (-Y direction), centered
    along Z (optical axis).
    """
    SLIDER_LENGTH = 35.0  # mm — slightly shorter than rail for slide clearance

    slider = (
        make_dovetail_slider(SLIDER_LENGTH, num_thumbscrews=1)
        .rotate((0, 0, 0), (1, 0, 0), 90)   # orient slider along Z (optical axis)
        .translate((0, -TUBE_H / 2.0, TUBE_LENGTH / 2.0))
    )
    return slider


def build() -> cq.Workplane:
    """Build the complete viewfinder assembly as a single solid.

    Coordinate system:
      X = horizontal (width)
      Y = vertical (height, up = +Y)
      Z = optical axis (eye at Z=0, front/scene at Z=TUBE_LENGTH)
    """
    # Tube shell
    vf = build_tube()

    # Mounting tabs on bottom
    tabs = build_mounting_tabs()
    vf = vf.union(tabs)

    return vf


def build_assembly() -> cq.Assembly:
    """Build viewfinder as a CadQuery Assembly with separate optical elements."""
    assy = cq.Assembly(name="viewfinder")

    # Tube
    assy.add(build_tube(), name="tube", loc=cq.Location((0, 0, 0)))

    # Mounting tabs
    assy.add(build_mounting_tabs(), name="mounting_tabs",
             loc=cq.Location((0, 0, 0)))

    # Front element (objective)
    assy.add(build_front_element(), name="front_element",
             loc=cq.Location((0, 0, FRONT_ELEMENT_Z)))

    # Rear element (eyepiece)
    assy.add(build_rear_element(), name="rear_element",
             loc=cq.Location((0, 0, REAR_ELEMENT_Z)))

    # Bright-line frame
    assy.add(build_bright_line_frame(), name="bright_line_frame",
             loc=cq.Location((0, 0, FRAME_Z)))

    return assy


def get_viewfinder_geometry() -> dict:
    """Return key geometry for positioning in the camera assembly."""
    return {
        "tube_w": TUBE_W,
        "tube_h": TUBE_H,
        "tube_length": TUBE_LENGTH,
        "lens_dia": LENS_DIA,
        "fov_horizontal_deg": VF_SPEC.fov_horizontal_deg,
        "magnification": VF_SPEC.magnification,
        "offset_up": VF_OFFSET_UP,
        "offset_left": VF_OFFSET_LEFT,
        "tab_spacing": TAB_SPACING,
        "frame_aspect": FRAME_ASPECT,
    }


def export(output_dir: str = "export"):
    """Export STEP and STL."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid, f"{output_dir}/viewfinder.step")
    cq.exporters.export(solid, f"{output_dir}/viewfinder.stl",
                        tolerance=0.01, angularTolerance=0.1)
    print(f"  Viewfinder exported to {output_dir}/")
    geom = get_viewfinder_geometry()
    print(f"  FOV: {geom['fov_horizontal_deg']}° horizontal, "
          f"{geom['magnification']}× magnification")


if __name__ == "__main__":
    export()
