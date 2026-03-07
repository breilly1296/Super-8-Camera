"""Reusable interface geometry for modular camera assembly.

Provides parametric interface features matching the modularity spec
(specs/modularity.py) interface types: DOVETAIL, THUMBSCREW, SNAP_FIT, JST.

All functions return cq.Workplane solids ready for union/cut operations.
Dimensions follow DIN/ISO standards where applicable.
"""

import math
import cadquery as cq


# =========================================================================
# DOVETAIL INTERFACE (60-degree, ISO-style machine dovetail)
# =========================================================================
# Profile (XZ cross-section):
#   top_w = 4.0 mm (narrow face, the "tongue")
#   base_w = 6.0 mm (wide face, seated in body)
#   depth = 3.0 mm (Z direction)
#   angle = 60 degrees included angle on each side

DOVETAIL_TOP_W = 4.0      # mm — narrow (exposed) face
DOVETAIL_BASE_W = 6.0     # mm — wide (seated) face
DOVETAIL_DEPTH = 3.0      # mm — profile depth
DOVETAIL_CLEARANCE = 0.15  # mm — per side for slider fit

# Thumbscrew: M3 with knurled head
M3_TAP_DIA = 2.5           # mm — M3 tap drill
M3_CLEAR_DIA = 3.2         # mm — M3 clearance
M3_NUT_AF = 5.5            # mm — M3 hex nut across-flats
M3_NUT_DEPTH = 2.4         # mm — M3 nut height


def make_dovetail_rail(length: float) -> cq.Workplane:
    """Create a dovetail rail (male) extruded along Y.

    60-degree trapezoidal profile in XZ plane:
      - Top (Z+): DOVETAIL_TOP_W wide
      - Base (Z-): DOVETAIL_BASE_W wide
      - Height: DOVETAIL_DEPTH

    Parameters
    ----------
    length : float
        Rail length along Y axis (mm).

    Returns
    -------
    cq.Workplane
        Solid centered at origin, extending ±length/2 along Y.
    """
    half_top = DOVETAIL_TOP_W / 2.0
    half_base = DOVETAIL_BASE_W / 2.0
    d = DOVETAIL_DEPTH

    # Trapezoidal profile as XZ polygon (wider at bottom)
    profile = [
        (-half_base, 0),          # bottom-left
        ( half_base, 0),          # bottom-right
        ( half_top,  d),          # top-right
        (-half_top,  d),          # top-left
    ]

    rail = (
        cq.Workplane("XZ")
        .polyline(profile).close()
        .extrude(length)
        .translate((0, -length / 2.0, 0))
    )
    return rail


def make_dovetail_slider(length: float,
                         num_thumbscrews: int = 1) -> cq.Workplane:
    """Create a dovetail slider (female) that mates with make_dovetail_rail.

    Inverse trapezoidal channel with per-side clearance.
    Block envelope: 10mm wide x 8mm tall x length.
    Includes M3 through-holes and hex nut pockets for thumbscrew retention.

    Parameters
    ----------
    length : float
        Slider length along Y axis (mm).
    num_thumbscrews : int
        Number of M3 thumbscrew positions evenly spaced along Y.

    Returns
    -------
    cq.Workplane
        Solid centered at origin.
    """
    c = DOVETAIL_CLEARANCE
    half_top = (DOVETAIL_TOP_W + 2 * c) / 2.0    # 4.3/2 = 2.15
    half_base = (DOVETAIL_BASE_W + 2 * c) / 2.0  # 6.3/2 = 3.15
    d = DOVETAIL_DEPTH + c                         # 3.15 mm

    block_w = 10.0   # mm — slider body width (X)
    block_h = 8.0    # mm — slider body height (Z)

    # Solid block
    slider = (
        cq.Workplane("XY")
        .box(block_w, length, block_h)
    )

    # Dovetail channel (cut from bottom face)
    channel_profile = [
        (-half_base, 0),
        ( half_base, 0),
        ( half_top,  d),
        (-half_top,  d),
    ]
    channel = (
        cq.Workplane("XZ")
        .polyline(channel_profile).close()
        .extrude(length)
        .translate((0, -length / 2.0, -block_h / 2.0))
    )
    slider = slider.cut(channel)

    # M3 thumbscrew through-holes + hex nut pockets
    if num_thumbscrews > 0:
        spacing = length / (num_thumbscrews + 1)
        for i in range(num_thumbscrews):
            ty = -length / 2.0 + spacing * (i + 1)

            # Through-hole (Z direction, from top through to channel)
            through = (
                cq.Workplane("XY")
                .transformed(offset=(0, ty, 0))
                .circle(M3_CLEAR_DIA / 2.0)
                .extrude(block_h)
                .translate((0, 0, -block_h / 2.0))
            )
            slider = slider.cut(through)

            # Hex nut pocket on top face
            nut_pocket = (
                cq.Workplane("XY")
                .transformed(offset=(0, ty, block_h / 2.0 - M3_NUT_DEPTH))
                .polygon(6, M3_NUT_AF / math.cos(math.radians(30)))
                .extrude(M3_NUT_DEPTH + 0.1)
            )
            slider = slider.cut(nut_pocket)

    return slider


# =========================================================================
# SNAP-FIT INTERFACE (cantilever beam with hook)
# =========================================================================
# Designed per Bayer snap-fit design guidelines for 3D-printed PETG.

SNAP_BEAM_W = 2.0          # mm — beam width
SNAP_BEAM_T = 0.8          # mm — beam thickness
SNAP_BEAM_L = 8.0          # mm — beam length (cantilever)
SNAP_BASE_W = 2.0          # mm — base block width
SNAP_BASE_H = 2.0          # mm — base block height (along beam)
SNAP_BASE_D = 1.5          # mm — base block depth (perpendicular)
SNAP_HOOK_H = 0.5          # mm — hook height (catch depth)
SNAP_LEAD_ANGLE = 30.0     # degrees — lead-in chamfer at tip

SNAP_POCKET_W = 1.2        # mm — pocket channel width (beam + clearance)
SNAP_POCKET_L = 10.0       # mm — pocket length
SNAP_POCKET_UNDERCUT = 2.0  # mm — undercut depth for hook engagement
SNAP_POCKET_CLEARANCE = 0.2  # mm — per-side clearance


def make_snap_latch() -> cq.Workplane:
    """Create a cantilever snap-fit latch (male).

    Geometry: base block + thin cantilever beam + hook with lead-in.
    Beam extends along +Z from the base block.
    Hook protrudes in +X direction at the tip.

    Returns
    -------
    cq.Workplane
        Solid centered at base block origin.
    """
    # Base block
    latch = (
        cq.Workplane("XY")
        .box(SNAP_BASE_W, SNAP_BASE_D, SNAP_BASE_H)
        .translate((0, 0, SNAP_BASE_H / 2.0))
    )

    # Cantilever beam extending upward from base
    beam = (
        cq.Workplane("XY")
        .box(SNAP_BEAM_W, SNAP_BEAM_T, SNAP_BEAM_L)
        .translate((0, 0, SNAP_BASE_H + SNAP_BEAM_L / 2.0))
    )
    latch = latch.union(beam)

    # Hook at tip (rectangular protrusion)
    hook = (
        cq.Workplane("XY")
        .box(SNAP_HOOK_H, SNAP_BEAM_T, 1.0)
        .translate((SNAP_BEAM_W / 2.0 + SNAP_HOOK_H / 2.0, 0,
                    SNAP_BASE_H + SNAP_BEAM_L - 0.5))
    )
    latch = latch.union(hook)

    # Lead-in chamfer on hook tip (30-degree wedge)
    # Modeled as a box cut at an angle to create a ramp
    lead_h = SNAP_HOOK_H / math.tan(math.radians(SNAP_LEAD_ANGLE))
    lead_cut = (
        cq.Workplane("XY")
        .box(SNAP_HOOK_H + 0.1, SNAP_BEAM_T + 0.1, lead_h)
        .translate((SNAP_BEAM_W / 2.0 + SNAP_HOOK_H / 2.0, 0,
                    SNAP_BASE_H + SNAP_BEAM_L + lead_h / 2.0))
    )
    latch = latch.cut(lead_cut)

    return latch


def make_snap_pocket() -> cq.Workplane:
    """Create a snap-fit pocket (female) for boolean cut into body.

    A rectangular channel with an undercut cavity for the hook to engage.
    Use this with shell.cut(pocket) to create the receiving feature.

    Returns
    -------
    cq.Workplane
        Solid to be used as a boolean cut. Centered at origin,
        channel runs along +Z.
    """
    # Main channel for beam passage
    channel = (
        cq.Workplane("XY")
        .box(SNAP_POCKET_W + 2 * SNAP_POCKET_CLEARANCE,
             SNAP_BEAM_T + 2 * SNAP_POCKET_CLEARANCE,
             SNAP_POCKET_L)
        .translate((0, 0, SNAP_POCKET_L / 2.0))
    )

    # Undercut cavity for hook engagement
    undercut = (
        cq.Workplane("XY")
        .box(SNAP_POCKET_W + SNAP_POCKET_UNDERCUT,
             SNAP_BEAM_T + 2 * SNAP_POCKET_CLEARANCE,
             SNAP_HOOK_H + SNAP_POCKET_CLEARANCE)
        .translate((SNAP_POCKET_UNDERCUT / 2.0, 0,
                    SNAP_POCKET_L - SNAP_HOOK_H / 2.0))
    )
    pocket = channel.union(undercut)

    return pocket


# =========================================================================
# JST XH CONNECTOR SOCKET (visualization model)
# =========================================================================
# JST XH family: 2.50 mm pin pitch, header height 7.0 mm, depth 9.8 mm.

JST_XH_PITCH = 2.5         # mm — pin-to-pin
JST_XH_FLANGE = 6.0        # mm — housing width beyond pins (total extra)
JST_XH_HEIGHT = 7.0        # mm — housing height
JST_XH_DEPTH = 9.8         # mm — housing depth (mating direction)
JST_XH_PIN_W = 0.64        # mm — pin slot width
JST_XH_PIN_D = 0.64        # mm — pin slot depth


def make_jst_xh_socket(pin_count: int) -> cq.Workplane:
    """Create a JST XH connector socket visualization block.

    Dimensions: width = (pin_count-1) * 2.5 + 6.0 mm, 7mm tall, 9.8mm deep.
    Includes rectangular pin slots on the mating face.

    Parameters
    ----------
    pin_count : int
        Number of pins (2-8 typical for JST XH).

    Returns
    -------
    cq.Workplane
        Solid centered at origin. Mating face is -Y.
    """
    width = (pin_count - 1) * JST_XH_PITCH + JST_XH_FLANGE

    # Housing block
    socket = (
        cq.Workplane("XY")
        .box(width, JST_XH_DEPTH, JST_XH_HEIGHT)
    )

    # Pin slots on mating face (-Y)
    for i in range(pin_count):
        px = -((pin_count - 1) * JST_XH_PITCH) / 2.0 + i * JST_XH_PITCH
        pin_slot = (
            cq.Workplane("XY")
            .box(JST_XH_PIN_W, JST_XH_PIN_D + 0.1, JST_XH_HEIGHT - 2.0)
            .translate((px, -JST_XH_DEPTH / 2.0, 0))
        )
        socket = socket.cut(pin_slot)

    return socket
