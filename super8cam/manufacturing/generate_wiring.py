"""generate_wiring.py — Wiring Diagram Generator

Produces a single-page PDF (export/wiring_diagram.pdf) showing:
  - PCB outline with connector positions along one edge
  - Color-coded lines from each connector to its destination module
  - Connector table: ID, pin count, wire colors, signal names, module
  - Wire cut list: length, gauge, color for each wire in the harness

Uses matplotlib + PdfPages (same stack as generate_drawings.py).
"""

from __future__ import annotations
import os
import sys
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

# ---------------------------------------------------------------------------
# Imports (mock CadQuery if not installed)
# ---------------------------------------------------------------------------
try:
    import cadquery  # noqa: F401
except ImportError:
    import types
    cq_mock = types.ModuleType("cadquery")
    cq_mock.Workplane = type("Workplane", (), {})
    cq_mock.exporters = types.ModuleType("cadquery.exporters")
    cq_mock.Assembly = type("Assembly", (), {})
    cq_mock.Location = type("Location", (), {"__init__": lambda self, *a: None})
    sys.modules["cadquery"] = cq_mock
    sys.modules["cadquery.exporters"] = cq_mock.exporters

# Now safe to import project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from super8cam.specs.modularity import CONNECTORS, MODULES
from super8cam.assemblies.electronics import (
    WIRE_HARNESS, PCB_X, PCB_Y, PCB_Z, MODULE_POSITIONS,
    get_wire_cut_list,
)
from super8cam.specs.master_specs import PCB as PCB_SPEC

# =========================================================================
# COLOR MAP  (wire color name → matplotlib color)
# =========================================================================
WIRE_COLOR_MAP = {
    "red":    "#e74c3c",
    "black":  "#2c3e50",
    "orange": "#e67e22",
    "yellow": "#f1c40f",
    "brown":  "#795548",
    "white":  "#bdc3c7",
    "green":  "#27ae60",
    "blue":   "#2980b9",
    "violet": "#8e44ad",
    "grey":   "#95a5a6",
    "gray":   "#95a5a6",
}

# Module display colors (one per module, for route lines)
MODULE_COLOR_MAP = {
    "MOD-100": "#e74c3c",   # red — film transport
    "MOD-200": "#e67e22",   # orange — shutter
    "MOD-300": "#2980b9",   # blue — drivetrain
    "MOD-400": "#27ae60",   # green — cartridge
    "MOD-500": "#95a5a6",   # grey — electronics (self)
    "MOD-600": "#f1c40f",   # yellow — power
    "MOD-700": "#8e44ad",   # violet — optics
}


# =========================================================================
# DRAWING FUNCTIONS
# =========================================================================

def _draw_pcb_and_routes(ax):
    """Draw the PCB outline, connector positions, and wire routes (top view XY)."""
    ax.set_title("Wiring Harness — Top View (XY Plane)", fontsize=10,
                 fontweight="bold", pad=8)

    # Camera body outline (dashed)
    from super8cam.specs.master_specs import CAMERA
    bx = CAMERA.body_length / 2.0
    by = CAMERA.body_depth / 2.0
    body_rect = patches.FancyBboxPatch(
        (-bx, -by), 2 * bx, 2 * by,
        boxstyle="round,pad=2", linewidth=0.5, edgecolor="#bdc3c7",
        facecolor="#f8f9fa", linestyle="--", zorder=0)
    ax.add_patch(body_rect)
    ax.text(0, by + 3, "CAMERA BODY (148×52 mm)", fontsize=5,
            ha="center", color="#bdc3c7")

    # PCB outline (solid rectangle)
    pcb_w = PCB_SPEC.width    # 55 mm
    pcb_h = PCB_SPEC.height   # 35 mm
    pcb_rect = patches.Rectangle(
        (PCB_X - pcb_w / 2.0, PCB_Y - pcb_h / 2.0),
        pcb_w, pcb_h,
        linewidth=1.2, edgecolor="#2c3e50", facecolor="#ecf0f1", zorder=1)
    ax.add_patch(pcb_rect)
    ax.text(PCB_X, PCB_Y - 2, "PCB\n(MOD-500)", fontsize=6,
            ha="center", va="center", fontweight="bold", zorder=5)

    # Connector positions on PCB edge (spread along +Y edge)
    sorted_connectors = sorted(WIRE_HARNESS.keys())
    n = len(sorted_connectors)
    spacing = pcb_w / (n + 1)

    for idx, cid in enumerate(sorted_connectors):
        route = WIRE_HARNESS[cid]
        cx = PCB_X - pcb_w / 2.0 + spacing * (idx + 1)
        cy = PCB_Y + pcb_h / 2.0

        # Determine target module
        target = (route["to_module"] if route["from_module"] == "MOD-500"
                  else route["from_module"])
        target_pos = MODULE_POSITIONS.get(target, (0, 0, 0))
        tx, ty = target_pos[0], target_pos[1]

        line_color = MODULE_COLOR_MAP.get(target, "#555555")

        # Connector rectangle on PCB edge
        conn_w = 4.0
        conn_h = 3.0
        conn_rect = patches.Rectangle(
            (cx - conn_w / 2.0, cy - conn_h / 2.0),
            conn_w, conn_h,
            linewidth=0.6, edgecolor=line_color, facecolor=line_color,
            alpha=0.7, zorder=3)
        ax.add_patch(conn_rect)
        ax.text(cx, cy, cid, fontsize=4, ha="center", va="center",
                color="white", fontweight="bold", zorder=4)

        # L-shaped wire route (XY projection)
        ax.plot([cx, cx, tx], [cy, ty, ty],
                color=line_color, linewidth=1.0, alpha=0.8,
                linestyle="-", zorder=2)

        # Module label at destination
        mod_name = MODULES.get(target, None)
        label = mod_name.name if mod_name else target
        ax.plot(tx, ty, "s", color=line_color, markersize=6, zorder=3)
        ax.text(tx + 2, ty + 2, f"{cid}→{label}\n({route['pin_count']}P "
                f"{route['jst_family']})", fontsize=4, color=line_color,
                zorder=4)

    ax.set_xlim(-85, 85)
    ax.set_ylim(-40, 40)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm)", fontsize=6)
    ax.set_ylabel("Y (mm)", fontsize=6)
    ax.tick_params(labelsize=5)
    ax.grid(True, linewidth=0.2, alpha=0.4)


def _draw_connector_table(ax):
    """Draw the connector reference table."""
    ax.set_title("Connector Reference", fontsize=9, fontweight="bold", pad=4)
    ax.axis("off")

    headers = ["ID", "Pins", "Family", "From", "To", "Max mA", "Signals",
               "Wire Colors"]
    rows = []
    for cid in sorted(CONNECTORS.keys()):
        c = CONNECTORS[cid]
        rows.append([
            cid,
            str(c.pin_count),
            c.jst_family,
            c.from_module,
            c.to_module,
            f"{c.max_current_ma:.0f}",
            ", ".join(c.signal_names[:3]) + ("..." if c.pin_count > 3 else ""),
            ", ".join(c.wire_colors[:4]) + ("..." if c.pin_count > 4 else ""),
        ])

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(5)
    table.auto_set_column_width(list(range(len(headers))))
    table.scale(1.0, 1.3)

    # Style header
    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")

    # Color-code rows by target module
    for i, cid in enumerate(sorted(CONNECTORS.keys())):
        c = CONNECTORS[cid]
        target = c.to_module if c.from_module == "MOD-500" else c.from_module
        color = MODULE_COLOR_MAP.get(target, "#ffffff")
        for j in range(len(headers)):
            cell = table[i + 1, j]
            cell.set_facecolor(color + "18")  # very light tint


def _draw_wire_cut_list(ax):
    """Draw the wire cut list table."""
    ax.set_title("Wire Cut List", fontsize=9, fontweight="bold", pad=4)
    ax.axis("off")

    cuts = get_wire_cut_list()

    headers = ["Conn", "Pin", "Color", "Signal", "Length (mm)", "AWG"]
    rows = []
    for w in cuts:
        rows.append([
            w["connector_id"],
            str(w["pin"]),
            w["color"],
            w["signal"],
            f"{w['length_mm']:.0f}",
            str(w["gauge_awg"]),
        ])

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(4)
    table.auto_set_column_width(list(range(len(headers))))
    table.scale(1.0, 0.85)

    # Style header
    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")

    # Color swatch in the "Color" column
    for i, w in enumerate(cuts):
        cell = table[i + 1, 2]  # color column
        mpl_color = WIRE_COLOR_MAP.get(w["color"], "#cccccc")
        cell.set_facecolor(mpl_color + "40")


# =========================================================================
# TITLE BLOCK
# =========================================================================

def _draw_title_block(ax):
    """Draw the title block at the bottom of the page."""
    ax.axis("off")
    ax.text(0.5, 0.7, "SUPER 8 CAMERA — WIRING HARNESS DIAGRAM",
            fontsize=11, fontweight="bold", ha="center", va="center",
            transform=ax.transAxes)
    ax.text(0.5, 0.35,
            f"7 connectors  |  "
            f"{sum(c.pin_count for c in CONNECTORS.values())} conductors  |  "
            f"JST XH (2.5 mm) + VH (3.96 mm)",
            fontsize=7, ha="center", va="center", color="#555555",
            transform=ax.transAxes)

    total_wire = sum(
        w["total_length_mm"] * w["pin_count"] for w in WIRE_HARNESS.values()
    )
    ax.text(0.5, 0.10,
            f"Total wire: {total_wire:.0f} mm ({total_wire / 1000:.2f} m)  |  "
            f"Service loop: 30 mm/wire",
            fontsize=6, ha="center", va="center", color="#777777",
            transform=ax.transAxes)


# =========================================================================
# MAIN — GENERATE PDF
# =========================================================================

def generate(output_dir: str = None):
    """Generate the wiring diagram PDF.

    Args:
        output_dir: Directory for output file. Defaults to export/.
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "export")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "wiring_diagram.pdf")

    fig = plt.figure(figsize=(11, 17))  # tabloid portrait

    # Layout: 4 rows
    #   Row 1: Title block (short)
    #   Row 2: PCB + wire route diagram (tall)
    #   Row 3: Connector table
    #   Row 4: Wire cut list
    gs = fig.add_gridspec(4, 1, height_ratios=[0.8, 4, 2.5, 5],
                          hspace=0.35, top=0.96, bottom=0.02,
                          left=0.05, right=0.95)

    ax_title = fig.add_subplot(gs[0])
    ax_route = fig.add_subplot(gs[1])
    ax_table = fig.add_subplot(gs[2])
    ax_cuts  = fig.add_subplot(gs[3])

    _draw_title_block(ax_title)
    _draw_pcb_and_routes(ax_route)
    _draw_connector_table(ax_table)
    _draw_wire_cut_list(ax_cuts)

    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig, dpi=150)

    plt.close(fig)
    print(f"  Wiring diagram saved to {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    generate()
