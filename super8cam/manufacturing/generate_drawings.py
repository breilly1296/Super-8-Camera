"""generate_drawings.py — Engineering Drawing Generator

Generates 2D engineering drawings with matplotlib for every CNC-machined part.

Each drawing includes:
  - Three orthographic views (front, top, right side) with hidden lines
  - Key dimensions with tolerance callouts
  - GD&T feature control frames (position, flatness, cylindricity, etc.)
  - Material specification and surface finish callouts
  - Title block with part number, revision, scale, date
  - Export as PDF to export/drawings/

Drawing conventions:
  - Solid lines (black):   visible edges
  - Dashed lines (gray):   hidden edges
  - Thin lines (blue):     dimension lines and leaders
  - Red:                    GD&T symbols and callouts
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

from super8cam.specs.master_specs import (
    FILM, CAMERA, CMOUNT, TOL, MOTOR, GEARBOX, BATTERY, PCB, BEARINGS,
    FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE,
)
from super8cam.manufacturing.gdt_standards import (
    GATE_GDT, SHAFT_GDT, HOUSING_GDT, SHUTTER_GDT, CAM_GDT,
    TORQUE_SPECS, feature_control_frame, surface_finish_callout,
    ra_to_ngrade, get_limits,
)


# =========================================================================
# DRAWING PRIMITIVES
# =========================================================================

VISIBLE_STYLE = dict(color="black", linewidth=0.8)
HIDDEN_STYLE  = dict(color="gray", linewidth=0.4, linestyle="--")
DIM_STYLE     = dict(color="#2980b9", linewidth=0.3)
GDT_STYLE     = dict(color="#c0392b", fontsize=6, fontweight="bold")
DIM_TEXT_SIZE  = 6.5
NOTE_TEXT_SIZE = 5.5


def _dim_line(ax, x1, y1, x2, y2, label: str, offset: float = 0.0,
              side: str = "above"):
    """Draw a dimension line with arrowheads and centered text.

    Args:
        ax: matplotlib axes
        x1, y1: start point
        x2, y2: end point
        label: dimension text (e.g. "25.00 ±0.05")
        offset: perpendicular offset for the dimension line
        side: "above" or "below" for text placement
    """
    import math

    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.01:
        return

    # Unit perpendicular vector
    nx = -dy / length
    ny = dx / length

    # Offset points
    ox1 = x1 + nx * offset
    oy1 = y1 + ny * offset
    ox2 = x2 + nx * offset
    oy2 = y2 + ny * offset

    # Extension lines
    ax.plot([x1, ox1], [y1, oy1], **DIM_STYLE)
    ax.plot([x2, ox2], [y2, oy2], **DIM_STYLE)

    # Dimension line with arrows
    ax.annotate("", xy=(ox2, oy2), xytext=(ox1, oy1),
                arrowprops=dict(arrowstyle="<->", color=DIM_STYLE["color"],
                                linewidth=DIM_STYLE["linewidth"]))

    # Text
    mx = (ox1 + ox2) / 2
    my = (oy1 + oy2) / 2
    text_offset = 0.8 if side == "above" else -0.8
    ax.text(mx + nx * text_offset, my + ny * text_offset, label,
            fontsize=DIM_TEXT_SIZE, color=DIM_STYLE["color"],
            ha="center", va="center", rotation=0,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="none", alpha=0.9))


def _gdt_callout(ax, x, y, text: str):
    """Place a GD&T feature control frame callout."""
    ax.text(x, y, text, **GDT_STYLE,
            bbox=dict(boxstyle="square,pad=0.2", facecolor="#fef9e7",
                      edgecolor="#c0392b", linewidth=0.5))


def _note(ax, x, y, text: str):
    """Place a note annotation."""
    ax.text(x, y, text, fontsize=NOTE_TEXT_SIZE, color="#7f8c8d",
            style="italic")


def _title_block(ax, part_name: str, part_number: str, material: str,
                 finish: str, scale: str = "2:1", rev: str = "A"):
    """Draw a title block in the lower-right corner."""
    # Title block border
    tb = patches.FancyBboxPatch(
        (0.55, 0.01), 0.44, 0.12,
        boxstyle="round,pad=0.005", linewidth=0.8,
        edgecolor="black", facecolor="#f8f9fa")
    ax.add_patch(tb)

    ax.text(0.57, 0.115, "SUPER 8 CAMERA PROJECT", fontsize=6,
            fontweight="bold")
    ax.text(0.57, 0.095, part_name, fontsize=8, fontweight="bold")
    ax.text(0.57, 0.075, f"Part No: {part_number}", fontsize=6)
    ax.text(0.57, 0.058, f"Material: {material}", fontsize=5.5)
    ax.text(0.57, 0.043, f"Finish: {finish}", fontsize=5.5)
    ax.text(0.57, 0.028, f"Scale: {scale}    Rev: {rev}", fontsize=5.5)
    ax.text(0.82, 0.028, "Units: mm", fontsize=5.5)
    ax.text(0.82, 0.043, "Tol: ±0.05 (unless noted)", fontsize=5)


# =========================================================================
# PART DRAWING DEFINITIONS
#
# Each function draws the three orthographic views and dimensions
# for one part onto a single matplotlib figure.
# =========================================================================

def _draw_film_gate(fig) -> dict:
    """Film gate — the most critical precision part."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-2, 42)
    ax.set_ylim(-2, 32)
    ax.set_aspect("equal")
    ax.axis("off")

    W = CAMERA.gate_plate_w      # 25
    H = CAMERA.gate_plate_h      # 18
    T = CAMERA.gate_plate_thick   # 3
    AW = FILM.frame_w             # 5.79
    AH = FILM.frame_h             # 4.01
    CW = CAMERA.gate_channel_w    # 8
    CD = CAMERA.gate_channel_depth  # 0.1
    RPD = CAMERA.reg_pin_dia      # 0.813

    # ---- FRONT VIEW (center) ----
    ox, oy = 5, 8
    # Plate outline
    rect = patches.Rectangle((ox, oy), W, H, linewidth=0.8,
                              edgecolor="black", facecolor="#f5f5f0")
    ax.add_patch(rect)

    # Film channel (recessed groove)
    cx = ox + (W - CW) / 2
    chan = patches.Rectangle((cx, oy), CW, H, linewidth=0.4,
                              edgecolor="gray", facecolor="#eee8d5",
                              linestyle="--")
    ax.add_patch(chan)

    # Aperture (center of plate)
    apx = ox + (W - AW) / 2
    apy = oy + (H - AH) / 2
    ap = patches.Rectangle((apx, apy), AW, AH, linewidth=0.8,
                            edgecolor="black", facecolor="white")
    ax.add_patch(ap)

    # Registration pin hole (below aperture)
    rpx = ox + W / 2
    rpy = apy - FILM.reg_pin_below_frame_center + AH / 2
    circle = plt.Circle((rpx, rpy), RPD / 2 * 3, linewidth=0.6,
                         edgecolor="black", facecolor="white")
    ax.add_artist(circle)

    # Mounting holes (2× M2)
    for dx in [-8, 8]:
        mh = plt.Circle((ox + W / 2 + dx, oy + H / 2), 1.1,
                         linewidth=0.4, edgecolor="gray",
                         facecolor="white", linestyle="--")
        ax.add_artist(mh)

    # ---- Dimensions ----
    _dim_line(ax, ox, oy - 1, ox + W, oy - 1,
              f"{W:.1f} ±{TOL.cnc_general}", offset=-1.5)
    _dim_line(ax, ox - 1, oy, ox - 1, oy + H,
              f"{H:.1f} ±{TOL.cnc_general}", offset=-1.5)
    _dim_line(ax, apx, apy + AH + 0.5, apx + AW, apy + AH + 0.5,
              f"{AW:.2f} ±{TOL.gate_aperture}", offset=1.5)
    _dim_line(ax, apx + AW + 0.5, apy, apx + AW + 0.5, apy + AH,
              f"{AH:.2f} ±{TOL.gate_aperture}", offset=1.5)

    # ---- TOP VIEW (above front) ----
    tox, toy = 5, 28
    top = patches.Rectangle((tox, toy), W, T, linewidth=0.8,
                              edgecolor="black", facecolor="#f5f5f0")
    ax.add_patch(top)
    # Channel groove (hidden)
    tcx = tox + (W - CW) / 2
    tc = patches.Rectangle((tcx, toy), CW, CD, linewidth=0.4,
                            edgecolor="gray", facecolor="#eee8d5",
                            linestyle="--")
    ax.add_patch(tc)
    _dim_line(ax, tox, toy + T + 0.5, tox + W, toy + T + 0.5,
              f"{W:.1f}", offset=0.8)
    _dim_line(ax, tox + W + 0.5, toy, tox + W + 0.5, toy + T,
              f"{T:.1f} ±{TOL.cnc_fine}", offset=0.8)

    # ---- RIGHT SIDE VIEW ----
    sox, soy = 34, 8
    side = patches.Rectangle((sox, soy), T, H, linewidth=0.8,
                               edgecolor="black", facecolor="#f5f5f0")
    ax.add_patch(side)
    # Channel depth callout
    _dim_line(ax, sox, soy + H + 0.5, sox + T, soy + H + 0.5,
              f"{T:.1f}", offset=0.8)

    # ---- GD&T callouts ----
    _gdt_callout(ax, 1, 22, GATE_GDT["aperture_position"])
    _gdt_callout(ax, 1, 20, GATE_GDT["channel_flatness"])
    _gdt_callout(ax, 1, 18, GATE_GDT["channel_surface"])

    # ---- Notes ----
    _note(ax, 1, 4, "DATUM A: Mounting hole pattern")
    _note(ax, 1, 2.5, f"Reg pin hole: Ø{RPD} +0/-{TOL.reg_pin_dia_minus}")
    _note(ax, 1, 1, f"All film-contact surfaces: Ra {TOL.gate_surface_ra} µm")

    # ---- Title block ----
    mat = MATERIALS[MATERIAL_USAGE["film_gate"]]
    _title_block(ax, "Film Gate", "S8C-107", mat.designation,
                 mat.finish, scale="4:1")

    ax.set_title("FILM GATE — Engineering Drawing", fontsize=10, pad=15)

    return {
        "part_name": "Film Gate",
        "part_number": "S8C-107",
        "views": ["front", "top", "right"],
    }


def _draw_main_shaft(fig) -> dict:
    """Main shaft with bearing seats, keyway, cam section."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-2, 50)
    ax.set_ylim(-8, 15)
    ax.set_aspect("equal")
    ax.axis("off")

    D = CAMERA.shaft_dia          # 4.0
    L = CAMERA.shaft_length       # 38.0
    R = D / 2

    # Shaft sections (from left): gear(3), brg1(4), cam(4), brg2(4), shutter(4), encoder(3)
    sections = [
        ("Gear", 3.0, D),
        ("Brg 1", 4.0, D),
        ("Cam", 4.0, D),
        ("Brg 2", 4.0, D),
        ("Shutter", 4.0, D),
        ("Encoder", 3.0, D - 0.5),  # slightly reduced
    ]

    # ---- FRONT VIEW (side profile) ----
    ox = 2
    x = ox
    for name, length, dia in sections:
        y_off = -dia / 2
        rect = patches.Rectangle((x, y_off), length, dia,
                                  linewidth=0.8, edgecolor="black",
                                  facecolor="#e8e8e8")
        ax.add_patch(rect)

        # Section label
        ax.text(x + length / 2, -dia / 2 - 1.5, name,
                fontsize=5, ha="center", color="gray")
        x += length

    # Keyway on shutter section
    kw_x = ox + 3 + 4 + 4 + 4
    kw = patches.Rectangle(
        (kw_x + 1, R - CAMERA.shutter_keyway_depth),
        2, CAMERA.shutter_keyway_depth,
        linewidth=0.4, edgecolor="black", facecolor="white")
    ax.add_patch(kw)

    # ---- Dimensions ----
    _dim_line(ax, ox, -R - 3, ox + L, -R - 3,
              f"{L:.1f} ±{TOL.cnc_general}", offset=-1)

    # Bearing seat diameters
    bx1 = ox + 3
    _dim_line(ax, bx1 + 4 + 0.5, -R, bx1 + 4 + 0.5, R,
              f"Ø{D:.1f} {TOL.bearing_shaft}", offset=2)

    # ---- GD&T ----
    _gdt_callout(ax, 2, 6, SHAFT_GDT["bearing_seat_cylindricity"])
    _gdt_callout(ax, 2, 4.5, SHAFT_GDT["seat_concentricity"])
    _gdt_callout(ax, 2, 3, SHAFT_GDT["bearing_seat_surface"])

    # ---- TOP VIEW ----
    tox, toy = 2, 9
    for name, length, dia in sections:
        rect = patches.Rectangle((tox, toy), length, D,
                                  linewidth=0.8, edgecolor="black",
                                  facecolor="#e8e8e8")
        ax.add_patch(rect)
        tox += length

    # ---- Right end view (circle) ----
    cv_x, cv_y = 45, 0
    circle = plt.Circle((cv_x, cv_y), R, linewidth=0.8,
                         edgecolor="black", facecolor="#e8e8e8")
    ax.add_artist(circle)
    ax.text(cv_x, cv_y + R + 1, f"Ø{D:.1f}", fontsize=DIM_TEXT_SIZE,
            ha="center", color=DIM_STYLE["color"])

    # ---- Notes ----
    _note(ax, 2, -7, f"Material: {MATERIALS[MATERIAL_USAGE['main_shaft']].designation}")
    _note(ax, 20, -7, f"Bearing seats: Ra {TOL.bearing_seat_ra} µm ground")

    _title_block(ax, "Main Shaft", "S8C-110",
                 MATERIALS[MATERIAL_USAGE["main_shaft"]].designation,
                 "Black oxide", scale="3:1")

    ax.set_title("MAIN SHAFT — Engineering Drawing", fontsize=10, pad=15)
    return {"part_name": "Main Shaft", "part_number": "S8C-110"}


def _draw_shutter_disc(fig) -> dict:
    """Shutter disc — half-disc with keyway and encoder flag."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-22, 22)
    ax.set_ylim(-22, 22)
    ax.set_aspect("equal")
    ax.axis("off")

    OD = CAMERA.shutter_od / 2     # radius = 15
    BD = CAMERA.shutter_shaft_hole / 2  # bore radius = 2

    # ---- FRONT VIEW (face) ----
    import numpy as np

    # Full disc outline (thin/hidden for closed sector)
    theta_full = np.linspace(0, 2 * np.pi, 100)
    ax.plot(OD * np.cos(theta_full), OD * np.sin(theta_full),
            **HIDDEN_STYLE)

    # Open sector (solid, the opening)
    theta_open = np.linspace(0, np.pi, 50)  # 180° opening
    ax.fill_between(OD * np.cos(theta_open), OD * np.sin(theta_open),
                     0, alpha=0.05, color="blue")

    # Solid sector
    theta_closed = np.linspace(np.pi, 2 * np.pi, 50)
    ax.fill_between(OD * np.cos(theta_closed), OD * np.sin(theta_closed),
                     0, alpha=0.15, color="gray")
    ax.plot(OD * np.cos(theta_closed), OD * np.sin(theta_closed),
            **VISIBLE_STYLE)
    ax.plot([-OD, OD], [0, 0], **VISIBLE_STYLE)

    # Center bore
    bore = plt.Circle((0, 0), BD, linewidth=0.8, edgecolor="black",
                       facecolor="white")
    ax.add_artist(bore)

    # Keyway
    kw = patches.Rectangle(
        (-CAMERA.shutter_keyway_w / 2, BD - CAMERA.shutter_keyway_depth),
        CAMERA.shutter_keyway_w, CAMERA.shutter_keyway_depth,
        linewidth=0.4, edgecolor="black", facecolor="white")
    ax.add_patch(kw)

    # ---- Dimensions ----
    _dim_line(ax, -OD, -OD - 2, OD, -OD - 2,
              f"Ø{CAMERA.shutter_od:.1f} ±0.1", offset=-1)
    ax.text(0, 0 + BD + 1.5, f"Ø{CAMERA.shutter_shaft_hole:.1f} "
            f"{TOL.press_fit_hole}",
            fontsize=DIM_TEXT_SIZE, ha="center",
            color=DIM_STYLE["color"])

    # Opening angle
    ax.annotate(f"{CAMERA.shutter_opening_angle:.0f}°",
                xy=(OD * 0.4, OD * 0.3), fontsize=DIM_TEXT_SIZE,
                color=DIM_STYLE["color"])

    # ---- GD&T ----
    _gdt_callout(ax, -20, 18, SHUTTER_GDT["flatness"])
    _gdt_callout(ax, -20, 16, SHUTTER_GDT["bore_concentricity"])

    # ---- Notes ----
    _note(ax, -20, -18, f"Material: {MATERIALS[MATERIAL_USAGE['shutter_disc']].designation}")
    _note(ax, -20, -19.5, f"Thickness: {CAMERA.shutter_thickness} ±0.05 mm")
    _note(ax, -20, -21, "Balance: < 0.1 g·mm imbalance")

    _title_block(ax, "Shutter Disc", "S8C-111",
                 MATERIALS[MATERIAL_USAGE["shutter_disc"]].designation,
                 "Black anodize", scale="2:1")

    ax.set_title("SHUTTER DISC — Engineering Drawing", fontsize=10, pad=15)
    return {"part_name": "Shutter Disc", "part_number": "S8C-111"}


def _draw_body_shell(fig) -> dict:
    """Body shell (left half) — largest part."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-5, 85)
    ax.set_ylim(-5, 55)
    ax.set_aspect("equal")
    ax.axis("off")

    L = CAMERA.body_length        # 148 → scale to ~74
    H = CAMERA.body_height        # 88 → scale to ~44
    D = CAMERA.body_depth         # 52 → scale to ~26
    W = CAMERA.wall_thickness     # 2.5
    S = 0.5  # drawing scale

    # ---- FRONT VIEW ----
    ox, oy = 2, 5
    sl, sh = L * S, H * S
    sw = W * S

    # Outer shell
    outer = patches.FancyBboxPatch(
        (ox, oy), sl, sh,
        boxstyle=f"round,pad={CAMERA.body_fillet * S}",
        linewidth=0.8, edgecolor="black", facecolor="#d5d8dc")
    ax.add_patch(outer)

    # Inner cavity (hidden)
    inner = patches.FancyBboxPatch(
        (ox + sw, oy + sw), sl - 2 * sw, sh - 2 * sw,
        boxstyle=f"round,pad={2 * S}",
        linewidth=0.4, edgecolor="gray", facecolor="#ecf0f1",
        linestyle="--")
    ax.add_patch(inner)

    # Lens boss (circle on front face)
    lens_x = ox + sl * 0.3
    lens_y = oy + sh * 0.55
    lens_r = CMOUNT.thread_od / 2 * S
    lens = plt.Circle((lens_x, lens_y), lens_r, linewidth=0.6,
                       edgecolor="black", facecolor="white")
    ax.add_artist(lens)

    # Battery pocket (dashed)
    bp_w = CAMERA.batt_pocket_l * S
    bp_h = CAMERA.batt_pocket_w * S
    bp_x = ox + sl * 0.6
    bp_y = oy + 2 * S
    bp = patches.Rectangle((bp_x, bp_y), bp_w, bp_h,
                            linewidth=0.4, edgecolor="gray",
                            facecolor="white", linestyle="--")
    ax.add_patch(bp)

    # ---- Dimensions ----
    _dim_line(ax, ox, oy - 2, ox + sl, oy - 2,
              f"{L:.0f} ±{TOL.cnc_general}", offset=-1.5)
    _dim_line(ax, ox - 2, oy, ox - 2, oy + sh,
              f"{H:.0f} ±{TOL.cnc_general}", offset=-1.5)

    # Wall thickness
    ax.annotate(f"wall {W:.1f}",
                xy=(ox + sw / 2, oy + sh / 2),
                fontsize=5, color=DIM_STYLE["color"],
                rotation=90, ha="center")

    # ---- TOP VIEW ----
    tox = 2
    toy = oy + sh + 4
    sd = D * S
    top = patches.FancyBboxPatch(
        (tox, toy), sl, sd,
        boxstyle=f"round,pad={CAMERA.body_fillet * S}",
        linewidth=0.8, edgecolor="black", facecolor="#d5d8dc")
    ax.add_patch(top)
    _dim_line(ax, tox + sl + 1, toy, tox + sl + 1, toy + sd,
              f"{D:.0f}", offset=1.5)

    # ---- Notes ----
    _note(ax, 2, 2, f"Material: {MATERIALS[MATERIAL_USAGE['body_shell']].designation}")
    _note(ax, 2, 0.5, f"Finish: {MATERIALS[MATERIAL_USAGE['body_shell']].finish}")
    _note(ax, 30, 2, f"Surface: Ra {TOL.body_exterior_ra} µm (exterior)")

    _title_block(ax, "Body Shell — Left Half", "S8C-101",
                 MATERIALS[MATERIAL_USAGE["body_shell"]].designation,
                 MATERIALS[MATERIAL_USAGE["body_shell"]].finish,
                 scale="1:2")

    ax.set_title("BODY SHELL (LEFT) — Engineering Drawing",
                 fontsize=10, pad=15)
    return {"part_name": "Body Shell Left", "part_number": "S8C-101"}


def _draw_cam(fig) -> dict:
    """Pulldown cam with eccentric profile."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-12, 12)
    ax.set_ylim(-12, 15)
    ax.set_aspect("equal")
    ax.axis("off")

    import numpy as np

    OD = CAMERA.cam_od / 2       # 6 mm radius
    BD = CAMERA.cam_id / 2       # 2 mm bore radius
    W = CAMERA.cam_width          # 3 mm

    # ---- FRONT VIEW (face) ----
    theta = np.linspace(0, 2 * np.pi, 100)

    # Simplified cam profile with eccentric lobe
    r_profile = OD + 1.5 * np.sin(theta)
    ax.plot(r_profile * np.cos(theta), r_profile * np.sin(theta),
            **VISIBLE_STYLE)

    # Center bore
    bore = plt.Circle((0, 0), BD, linewidth=0.8, edgecolor="black",
                       facecolor="white")
    ax.add_artist(bore)

    # Keyway
    kw = patches.Rectangle((-0.5, BD - 0.5), 1.0, 0.5,
                            linewidth=0.4, edgecolor="black",
                            facecolor="white")
    ax.add_patch(kw)

    # ---- Dimensions ----
    ax.text(0, -OD - 3, f"Ø{CAMERA.cam_od:.1f} OD (max lobe)",
            fontsize=DIM_TEXT_SIZE, ha="center", color=DIM_STYLE["color"])
    ax.text(0, BD + 2, f"Ø{CAMERA.cam_id:.1f} bore",
            fontsize=DIM_TEXT_SIZE, ha="center", color=DIM_STYLE["color"])

    # ---- GD&T ----
    _gdt_callout(ax, -11, 12, CAM_GDT["profile_position"])
    _gdt_callout(ax, -11, 10.5, CAM_GDT["bore_concentricity"])

    # ---- Notes ----
    _note(ax, -11, -10, f"Material: {MATERIALS[MATERIAL_USAGE['cam']].designation}")
    _note(ax, -11, -11.5, f"Width: {W:.1f} mm, Lift: {CAMERA.cam_lobe_lift:.3f} mm")
    _note(ax, -11, -13, "Harden to HRC 28-32")

    _title_block(ax, "Pulldown Cam", "S8C-112",
                 MATERIALS[MATERIAL_USAGE["cam"]].designation,
                 "Black oxide, hardened", scale="5:1")

    ax.set_title("PULLDOWN CAM — Engineering Drawing", fontsize=10, pad=15)
    return {"part_name": "Pulldown Cam", "part_number": "S8C-112"}


def _draw_lens_mount(fig) -> dict:
    """C-mount lens mount boss."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-20, 25)
    ax.set_ylim(-20, 20)
    ax.set_aspect("equal")
    ax.axis("off")

    OD = CAMERA.lens_boss_od / 2      # 16
    TD = CMOUNT.thread_od / 2          # 12.7
    P = CAMERA.lens_boss_protrusion    # 4
    TH = CMOUNT.thread_depth           # 3.8

    # ---- FRONT VIEW (face) ----
    outer = plt.Circle((0, 0), OD, linewidth=0.8, edgecolor="black",
                        facecolor="#d5d8dc")
    ax.add_artist(outer)
    thread = plt.Circle((0, 0), TD, linewidth=0.6, edgecolor="black",
                         facecolor="white", linestyle="--")
    ax.add_artist(thread)

    # ---- Dimensions ----
    ax.text(0, -OD - 2, f"Ø{CAMERA.lens_boss_od:.1f} boss OD",
            fontsize=DIM_TEXT_SIZE, ha="center", color=DIM_STYLE["color"])
    ax.text(0, -TD - 0.5, f"Ø{CMOUNT.thread_od:.1f} thread ({CMOUNT.thread_tpi} TPI)",
            fontsize=DIM_TEXT_SIZE - 0.5, ha="center", color=DIM_STYLE["color"])

    # ---- SIDE VIEW ----
    sox, soy = 20, -5
    side = patches.Rectangle((sox, soy), P, OD * 2 * 0.6,
                               linewidth=0.8, edgecolor="black",
                               facecolor="#d5d8dc")
    ax.add_patch(side)
    _dim_line(ax, sox, soy - 1.5, sox + P, soy - 1.5,
              f"{P:.1f}", offset=-1)
    _note(ax, sox, soy - 4, f"Thread depth: {TH:.1f} mm")

    # ---- Notes ----
    _note(ax, -19, 16, f"Flange focal dist: {CMOUNT.flange_focal_dist} ±0.02 mm")
    _note(ax, -19, 14, f"Thread: C-mount, 1\"-32 TPI")
    _note(ax, -19, 12, f"Material: {MATERIALS[MATERIAL_USAGE['body_shell']].designation}")

    _title_block(ax, "Lens Mount Boss", "S8C-109",
                 MATERIALS[MATERIAL_USAGE["body_shell"]].designation,
                 "Black anodize", scale="2:1")

    ax.set_title("LENS MOUNT BOSS — Engineering Drawing",
                 fontsize=10, pad=15)
    return {"part_name": "Lens Mount Boss", "part_number": "S8C-109"}


def _draw_pressure_plate(fig) -> dict:
    """Pressure plate — spring steel."""
    ax = fig.add_subplot(111)
    ax.set_xlim(-2, 30)
    ax.set_ylim(-2, 22)
    ax.set_aspect("equal")
    ax.axis("off")

    W = CAMERA.pressure_plate_w    # 20
    H = CAMERA.pressure_plate_h    # 14
    T = CAMERA.pressure_plate_thick  # 1.0

    # ---- FRONT VIEW ----
    ox, oy = 2, 4
    rect = patches.Rectangle((ox, oy), W, H, linewidth=0.8,
                               edgecolor="black", facecolor="#c0c0c0")
    ax.add_patch(rect)

    # Film contact area (raised lip)
    lip_inset = 3
    lip = patches.Rectangle((ox + lip_inset, oy + lip_inset),
                              W - 2 * lip_inset, H - 2 * lip_inset,
                              linewidth=0.4, edgecolor="gray",
                              facecolor="none", linestyle="--")
    ax.add_patch(lip)

    # ---- Dimensions ----
    _dim_line(ax, ox, oy - 1, ox + W, oy - 1,
              f"{W:.1f} ±{TOL.cnc_general}", offset=-1)
    _dim_line(ax, ox - 1, oy, ox - 1, oy + H,
              f"{H:.1f} ±{TOL.cnc_general}", offset=-1)

    # ---- TOP VIEW ----
    tox, toy = 2, 20
    top = patches.Rectangle((tox, toy), W, T, linewidth=0.8,
                              edgecolor="black", facecolor="#c0c0c0")
    ax.add_patch(top)
    ax.text(tox + W + 1, toy + T / 2, f"{T:.1f} mm",
            fontsize=DIM_TEXT_SIZE, color=DIM_STYLE["color"])

    # ---- Notes ----
    _note(ax, 2, 1.5, f"Material: {MATERIALS[MATERIAL_USAGE['pressure_plate']].designation}")
    _note(ax, 2, 0, f"Spring force: {CAMERA.pressure_plate_force_n} N per spring")

    _title_block(ax, "Pressure Plate", "S8C-108",
                 MATERIALS[MATERIAL_USAGE["pressure_plate"]].designation,
                 "Passivated", scale="3:1")

    ax.set_title("PRESSURE PLATE — Engineering Drawing",
                 fontsize=10, pad=15)
    return {"part_name": "Pressure Plate", "part_number": "S8C-108"}


# =========================================================================
# DRAWING REGISTRY
# =========================================================================

DRAWING_FUNCTIONS: Dict[str, callable] = {
    "film_gate":       _draw_film_gate,
    "main_shaft":      _draw_main_shaft,
    "shutter_disc":    _draw_shutter_disc,
    "body_shell_left": _draw_body_shell,
    "pulldown_cam":    _draw_cam,
    "lens_mount":      _draw_lens_mount,
    "pressure_plate":  _draw_pressure_plate,
}


# =========================================================================
# PUBLIC API
# =========================================================================

def generate_drawing(part_key: str, output_dir: str = "export/drawings") -> str:
    """Generate a single engineering drawing as PDF.

    Args:
        part_key: Key into DRAWING_FUNCTIONS
        output_dir: Directory for PDF output

    Returns:
        Path to the generated PDF file.
    """
    if part_key not in DRAWING_FUNCTIONS:
        raise ValueError(f"Unknown part: {part_key}.  "
                         f"Available: {list(DRAWING_FUNCTIONS.keys())}")

    os.makedirs(output_dir, exist_ok=True)

    fig = plt.figure(figsize=(11, 8.5))
    info = DRAWING_FUNCTIONS[part_key](fig)

    filepath = os.path.join(output_dir, f"{part_key}.pdf")
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"  Drawing: {filepath} — {info.get('part_name', part_key)}")
    return filepath


def generate_all(output_dir: str = "export/drawings") -> List[str]:
    """Generate engineering drawings for all registered parts.

    Returns:
        List of generated PDF file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []

    for part_key in DRAWING_FUNCTIONS:
        path = generate_drawing(part_key, output_dir)
        paths.append(path)

    print(f"\n  Generated {len(paths)} engineering drawings in {output_dir}/")
    return paths


def generate_drawing_package(output_dir: str = "export/drawings") -> str:
    """Generate all drawings and combine into a single multi-page PDF.

    Returns:
        Path to the combined PDF.
    """
    os.makedirs(output_dir, exist_ok=True)
    combined_path = os.path.join(output_dir, "S8C_drawing_package.pdf")

    with PdfPages(combined_path) as pdf:
        # Cover page
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        ax.text(0.5, 0.7, "SUPER 8 CAMERA", ha="center",
                fontsize=28, fontweight="bold")
        ax.text(0.5, 0.60, "ENGINEERING DRAWING PACKAGE",
                ha="center", fontsize=18, color="#2c3e50")
        ax.text(0.5, 0.52, "Document: S8C-DWG-001  Rev A",
                ha="center", fontsize=11, color="gray")

        ax.text(0.5, 0.40, f"Contains {len(DRAWING_FUNCTIONS)} drawings:",
                ha="center", fontsize=11)
        y = 0.35
        for key, func in DRAWING_FUNCTIONS.items():
            ax.text(0.5, y, f"  {key.replace('_', ' ').title()}",
                    ha="center", fontsize=10)
            y -= 0.03

        pdf.savefig(fig)
        plt.close(fig)

        # Individual drawings
        for part_key, draw_func in DRAWING_FUNCTIONS.items():
            fig = plt.figure(figsize=(11, 8.5))
            draw_func(fig)
            pdf.savefig(fig, dpi=150, bbox_inches="tight")
            plt.close(fig)

    print(f"  Drawing package: {combined_path} "
          f"({len(DRAWING_FUNCTIONS) + 1} pages)")
    return combined_path


# Backward-compatible API
def generate_gate_drawing() -> dict:
    """Generate film gate drawing specification (legacy API)."""
    return {
        "part": "Film Gate",
        "material": MATERIALS[MATERIAL_USAGE["film_gate"]].designation,
        "dims": {
            "plate_w": (CAMERA.gate_plate_w, TOL.cnc_general),
            "plate_h": (CAMERA.gate_plate_h, TOL.cnc_general),
            "plate_thick": (CAMERA.gate_plate_thick, TOL.cnc_fine),
            "aperture_w": (FILM.frame_w, TOL.gate_aperture),
            "aperture_h": (FILM.frame_h, TOL.gate_aperture),
            "channel_depth": (CAMERA.gate_channel_depth, TOL.gate_channel_depth),
            "channel_w": (CAMERA.gate_channel_w, TOL.cnc_general),
            "reg_pin_hole": (CAMERA.reg_pin_dia, 0.005),
            "reg_pin_pos": (FILM.reg_pin_below_frame_center, TOL.reg_pin_position),
        },
        "surface_finish_ra_um": TOL.gate_surface_ra,
        "gdt": GATE_GDT,
        "fasteners": FASTENER_USAGE["film_gate_mount"],
    }


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    generate_all()
    generate_drawing_package()
