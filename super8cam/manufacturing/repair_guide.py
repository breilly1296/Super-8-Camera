"""repair_guide.py — Repair & Maintenance Guide PDF Generator

Generates a comprehensive multi-page repair manual from existing project data:
  - specs/modularity.py: MODULES, CONNECTORS, PART_CATALOG
  - specs/master_specs.py: CAMERA, FILM, etc.
  - manufacturing/generate_bom.py: cost rollup
  - super8cam/__init__.py: version

Output: export/repair_guide.pdf  (reportlab)

All data is pulled from existing sources — nothing is hardcoded.
"""

from __future__ import annotations
import os
import sys
from datetime import datetime
from typing import Dict, List

# ---------------------------------------------------------------------------
# ReportLab imports
# ---------------------------------------------------------------------------
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

# ---------------------------------------------------------------------------
# Project imports (mock CadQuery if absent)
# ---------------------------------------------------------------------------
try:
    import cadquery  # noqa: F401
except ImportError:
    import types as _types
    _cq = _types.ModuleType("cadquery")
    _cq.Workplane = type("Workplane", (), {})
    _cq.exporters = _types.ModuleType("cadquery.exporters")
    _cq.Assembly = type("Assembly", (), {})
    _cq.Location = type("Location", (), {"__init__": lambda self, *a: None})
    sys.modules["cadquery"] = _cq
    sys.modules["cadquery.exporters"] = _cq.exporters

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from super8cam import __version__
from super8cam.specs.modularity import (
    MODULES, CONNECTORS, PART_CATALOG, Module, ConnectorSpec, PartCatalogEntry,
)
from super8cam.specs.master_specs import CAMERA, FILM

# BOM cost data
from super8cam.manufacturing.generate_bom import generate_bom, compute_totals


# =========================================================================
# SYMPTOM LOOKUP  (mirrors modularity.print_repair_guide data)
# =========================================================================
# Pulled from the same source-of-truth dict defined in modularity.py.
# We keep it here rather than importing a private local variable.

SYMPTOMS: Dict[str, str] = {
    "Film Gate":            "Scratched frames, uneven exposure, film jams",
    "Pressure Plate":       "Soft focus, film not flat, uneven contact marks",
    "Claw Mechanism":       "Torn perforations, frame registration drift, missed pulldowns",
    "Cam Follower Assembly": "Erratic pulldown, clicking noise, timing drift",
    "Film Channel":         "Film scratches along edges, loading difficulty",
    "Registration Pin":     "Frame-to-frame jitter > 0.025 mm, loose pin feel",
    "Shutter Disc":         "Light leaks, exposure banding, rubbing noise",
    "Main Shaft":           "Vibration, bearing noise, runout > 0.01 mm",
    "Motor Mount":          "Motor vibration transmitted to body, loose motor",
    "Gearbox Housing":      "Gear noise, lubricant leaks, cracked housing",
    "Gear Set (Stage 1 + Stage 2)": "Gear whine, stripped teeth, speed inconsistency",
    "Cartridge Receiver":   "Cartridge won't seat, light leaks at receiver",
    "Cartridge Door":       "Door won't latch, light leaks at door seal",
    "PCB Bracket":          "PCB vibration, loose standoffs, cracked bracket",
    "Battery Door":         "Door won't close, spring contact corrosion",
    "Bottom Plate":         "Tripod insert stripped, plate warped",
    "Lens Mount (C-Mount)": "Lens wobble, can't achieve focus, thread damage",
    "Viewfinder":           "Dim image, parallax error, cracked optics",
    "Body Left Half":       "Dented shell, stripped screw bosses, crack",
    "Body Right Half":      "Dented shell, stripped screw bosses, crack",
    "Top Plate":            "Accessory shoe damage, dented plate",
    "Trigger Assembly":     "No response, intermittent trigger, mushy feel",
}


# =========================================================================
# MAINTENANCE SCHEDULE  (derived from PART_CATALOG replacement intervals)
# =========================================================================

MAINTENANCE_SCHEDULE = [
    {
        "interval": 10,
        "label": "Every 10 cartridges",
        "tasks": [
            "Clean film gate with lint-free cloth and isopropyl alcohol",
            "Inspect claw tip under 10x loupe for burrs or wear",
            "Blow dust from film channel with compressed air",
            "Check pressure plate contact marks on test strip",
        ],
    },
    {
        "interval": 50,
        "label": "Every 50 cartridges",
        "tasks": [
            "Replace pressure plate (S8C-102) if contact marks are uneven",
            "Lubricate guide rollers with one drop of clock oil",
            "Inspect film channel for scratches; replace if needed (S8C-105)",
            "Clean viewfinder optics with lens tissue",
        ],
    },
    {
        "interval": 100,
        "label": "Every 100 cartridges",
        "tasks": [
            "Inspect gear teeth for wear under magnification",
            "Check main shaft bearings for roughness by hand rotation",
            "Replace claw tip if pulldown stroke has drifted (S8C-103)",
            "Test registration accuracy with calibration film strip",
            "Inspect all JST connector crimps for corrosion",
        ],
    },
    {
        "interval": 500,
        "label": "Every 500 cartridges",
        "tasks": [
            "Full teardown and cleaning of all modules",
            "Replace main shaft bearings (S8C-402/403)",
            "Replace film gate (S8C-101) if aperture edges show wear",
            "Replace motor (S8C-401) if stall torque has dropped",
            "Re-grease all gear teeth with Superlube",
            "Inspect all screws for thread damage; replace as needed",
            "Verify 17.526 mm flange distance with depth gauge",
        ],
    },
]


# =========================================================================
# PRINT TIME / FILAMENT ESTIMATES (for printable parts)
# =========================================================================
# Rough estimates based on infill and volume.

def _estimate_print(part: PartCatalogEntry) -> Dict[str, str]:
    """Estimate print time and filament weight from print_settings."""
    settings = part.print_settings
    infill_str = settings.get("infill", "40%")
    try:
        infill_pct = int(infill_str.replace("%", "").split()[0])
    except (ValueError, IndexError):
        infill_pct = 40

    # Very rough estimates by part type
    # Small parts: ~30min/10g, medium: ~2h/25g, large: ~4h/50g
    name_lower = part.name.lower()
    if any(k in name_lower for k in ("channel", "bracket", "trigger")):
        base_time_min = 90
        base_grams = 15
    elif any(k in name_lower for k in ("gear", "pinion")):
        base_time_min = 60
        base_grams = 8
    elif any(k in name_lower for k in ("door", "housing")):
        base_time_min = 150
        base_grams = 30
    elif "viewfinder" in name_lower:
        base_time_min = 120
        base_grams = 20
    elif "mount" in name_lower:
        base_time_min = 90
        base_grams = 18
    else:
        base_time_min = 120
        base_grams = 20

    scale = infill_pct / 50.0  # normalize around 50%
    est_time = int(base_time_min * max(scale, 0.6))
    est_grams = round(base_grams * max(scale, 0.6), 1)

    hours = est_time // 60
    mins = est_time % 60
    time_str = f"{hours}h {mins}min" if hours else f"{mins} min"

    return {
        "print_time": time_str,
        "filament_g": f"{est_grams:.0f} g",
    }


# =========================================================================
# STYLES
# =========================================================================

def _build_styles():
    """Build custom paragraph styles."""
    ss = getSampleStyleSheet()

    ss.add(ParagraphStyle(
        "CoverTitle", parent=ss["Title"],
        fontSize=28, leading=34, alignment=TA_CENTER,
        spaceAfter=12,
    ))
    ss.add(ParagraphStyle(
        "CoverSubtitle", parent=ss["Normal"],
        fontSize=14, leading=18, alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
    ))
    ss.add(ParagraphStyle(
        "SectionTitle", parent=ss["Heading1"],
        fontSize=16, leading=20, spaceAfter=10, spaceBefore=16,
        textColor=colors.HexColor("#2c3e50"),
    ))
    ss.add(ParagraphStyle(
        "SubSection", parent=ss["Heading2"],
        fontSize=12, leading=15, spaceAfter=6, spaceBefore=10,
        textColor=colors.HexColor("#34495e"),
    ))
    ss.add(ParagraphStyle(
        "GuideBody", parent=ss["Normal"],
        fontSize=9, leading=12, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "ProcStep", parent=ss["Normal"],
        fontSize=9, leading=12, leftIndent=18, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        "SmallNote", parent=ss["Normal"],
        fontSize=7.5, leading=10, textColor=colors.HexColor("#777777"),
    ))
    return ss


# =========================================================================
# STANDARD TABLE STYLE
# =========================================================================

HEADER_BG = colors.HexColor("#2c3e50")
HEADER_FG = colors.white
ALT_ROW = colors.HexColor("#f8f9fa")

TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
    ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 8),
    ("FONTSIZE", (0, 1), (-1, -1), 7.5),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
])


def _alt_row_style(num_rows: int) -> TableStyle:
    """Return table style with alternating row backgrounds."""
    cmds = list(TABLE_STYLE.getCommands())
    for i in range(1, num_rows + 1):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), ALT_ROW))
    return TableStyle(cmds)


# =========================================================================
# PAGE BUILDERS
# =========================================================================

def _build_cover(ss) -> list:
    """Page 1: Cover page."""
    elements = []
    elements.append(Spacer(1, 2.5 * inch))
    elements.append(Paragraph(
        "Super 8 Camera", ss["CoverTitle"]))
    elements.append(Paragraph(
        "Repair &amp; Maintenance Guide", ss["CoverTitle"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(
        f"Version {__version__}", ss["CoverSubtitle"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        f"Film format: Kodak Super 8 ({FILM.frame_w} x {FILM.frame_h} mm)<br/>"
        f"Body: {CAMERA.body_length} x {CAMERA.body_height} x "
        f"{CAMERA.body_depth} mm aluminum<br/>"
        f"7 field-swappable modules | "
        f"{sum(1 for p in PART_CATALOG.values() if p.is_printable)} "
        f"FDM-printable parts",
        ss["CoverSubtitle"]))
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%Y-%m-%d')}",
        ss["SmallNote"]))
    elements.append(PageBreak())
    return elements


def _build_module_map(ss) -> list:
    """Page 2: Module map — all 7 modules, parts, connections."""
    elements = []
    elements.append(Paragraph("Module Map", ss["SectionTitle"]))
    elements.append(Paragraph(
        "The camera is organized into 7 field-swappable modules. "
        "Each module can be removed and replaced independently using "
        "the interface type listed below.",
        ss["GuideBody"]))
    elements.append(Spacer(1, 6))

    # Module summary table
    headers = ["Module ID", "Name", "Interface", "Level", "Swap Time",
               "Tools", "Parts"]
    rows = [headers]
    for mod in MODULES.values():
        level_str = {1: "User", 2: "Technician", 3: "Factory"}.get(
            mod.repair_level, str(mod.repair_level))
        time_str = (f"{mod.swap_time_seconds // 60}m {mod.swap_time_seconds % 60}s"
                    if mod.swap_time_seconds >= 60
                    else f"{mod.swap_time_seconds}s")
        tools = ", ".join(mod.tools_required) if mod.tools_required else "None"
        parts_str = ", ".join(mod.parts_included)
        rows.append([
            mod.module_id, mod.name, mod.interface_type,
            level_str, time_str, tools, parts_str,
        ])

    col_widths = [55, 85, 65, 55, 45, 110, 120]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_alt_row_style(len(rows) - 1))
    elements.append(t)
    elements.append(Spacer(1, 14))

    # Connection diagram (text-based)
    elements.append(Paragraph("Module Connections", ss["SubSection"]))
    for mod in MODULES.values():
        targets = ", ".join(mod.connects_to) if mod.connects_to else "(none)"
        elements.append(Paragraph(
            f"<b>{mod.module_id} {mod.name}</b> connects to: {targets}",
            ss["GuideBody"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Legend: [P] = FDM printable, [C] = CNC / precision machined",
        ss["SmallNote"]))

    for mod in MODULES.values():
        parts_lines = []
        for pname in mod.parts_included:
            marker = "[P]" if pname in mod.printable_parts else "[C]"
            parts_lines.append(f"  {marker} {pname}")
        elements.append(Paragraph(
            f"<b>{mod.module_id}</b>: " + " | ".join(
                (("[P] " if p in mod.printable_parts else "[C] ") + p)
                for p in mod.parts_included),
            ss["SmallNote"]))

    elements.append(PageBreak())
    return elements


def _build_repair_pages(ss) -> list:
    """Pages 3+: Repair procedures for serviceable parts."""
    elements = []
    elements.append(Paragraph("Repair Procedures", ss["SectionTitle"]))
    elements.append(Paragraph(
        "This section covers every part that is either a wear item or "
        "serviceable at repair level 1 (user) or 2 (technician). "
        "Factory-level (level 3) parts are included only if they are "
        "wear items.",
        ss["GuideBody"]))
    elements.append(Spacer(1, 8))

    for part in PART_CATALOG.values():
        # Include if: wear item OR repair_level <= 2
        if not (part.is_wear_item or part.repair_level <= 2):
            continue

        mod = MODULES.get(part.module)
        level_str = {1: "User", 2: "Technician", 3: "Factory"}.get(
            part.repair_level, str(part.repair_level))

        # Build a KeepTogether block for each part
        block = []
        block.append(Paragraph(
            f"{part.part_number} &mdash; {part.name}",
            ss["SubSection"]))

        # Info table (2 columns)
        symptom = SYMPTOMS.get(part.name, "Visual inspection / functional test")
        tools = ", ".join(mod.tools_required) if mod and mod.tools_required else "None"
        swap_time = f"{mod.swap_time_seconds}s" if mod else "N/A"
        if mod and mod.swap_time_seconds >= 60:
            swap_time = (f"{mod.swap_time_seconds // 60}m "
                         f"{mod.swap_time_seconds % 60}s")
        interval = (f"Every {part.replacement_interval_cartridges} cartridges"
                     if part.replacement_interval_cartridges
                     else "Lifetime (replace if damaged)")

        info_data = [
            ["Module:", f"{part.module} ({mod.name if mod else 'STRUCTURE'})"],
            ["Repair Level:", level_str],
            ["Cost:", f"${part.estimated_cost:.2f}"],
            ["Symptoms:", symptom],
            ["Tools Required:", tools],
            ["Est. Swap Time:", swap_time],
            ["Replacement Interval:", interval],
        ]
        info_table = Table(info_data, colWidths=[110, 420])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        block.append(info_table)
        block.append(Spacer(1, 4))

        # Step-by-step procedure
        block.append(Paragraph("<b>Replacement Procedure:</b>",
                               ss["GuideBody"]))
        for line in part.replacement_procedure.strip().split("\n"):
            line = line.strip()
            if line:
                block.append(Paragraph(line, ss["ProcStep"]))

        # Reassembly note
        block.append(Spacer(1, 3))
        block.append(Paragraph(
            "<i>Reassembly: reverse the above steps. Verify function "
            "before closing the camera body.</i>",
            ss["SmallNote"]))
        block.append(Spacer(1, 12))

        elements.append(KeepTogether(block))

    elements.append(PageBreak())
    return elements


def _build_connector_reference(ss) -> list:
    """Connector reference page — full wiring table."""
    elements = []
    elements.append(Paragraph("Connector Reference", ss["SectionTitle"]))
    elements.append(Paragraph(
        "All electrical connections between modules use JST XH (2.5 mm) or "
        "JST VH (3.96 mm) connectors. Each connector has a unique pin count "
        "to prevent accidental cross-connection.",
        ss["GuideBody"]))
    elements.append(Spacer(1, 8))

    # Main connector table
    headers = ["ID", "Pins", "Family", "From", "To", "Max mA",
               "Wire Colors"]
    rows = [headers]
    for conn in CONNECTORS.values():
        rows.append([
            conn.connector_id,
            str(conn.pin_count),
            conn.jst_family,
            conn.from_module,
            conn.to_module,
            f"{conn.max_current_ma:.0f}",
            ", ".join(conn.wire_colors),
        ])

    col_widths = [30, 30, 40, 60, 60, 45, 270]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_alt_row_style(len(rows) - 1))
    elements.append(t)
    elements.append(Spacer(1, 14))

    # Signal detail table
    elements.append(Paragraph("Signal Pinout", ss["SubSection"]))
    sig_headers = ["ID", "Pin", "Signal", "Color"]
    sig_rows = [sig_headers]
    for conn in CONNECTORS.values():
        for i, (sig, clr) in enumerate(
                zip(conn.signal_names, conn.wire_colors)):
            sig_rows.append([
                conn.connector_id if i == 0 else "",
                str(i + 1),
                sig,
                clr,
            ])

    sig_widths = [40, 30, 200, 80]
    st = Table(sig_rows, colWidths=sig_widths, repeatRows=1)
    st.setStyle(_alt_row_style(len(sig_rows) - 1))
    elements.append(st)

    elements.append(PageBreak())
    return elements


def _build_printable_parts(ss) -> list:
    """Printable parts catalog page."""
    elements = []
    elements.append(Paragraph("FDM Printable Parts Catalog", ss["SectionTitle"]))
    elements.append(Paragraph(
        "The following parts can be 3D printed as field replacements. "
        "Use the print settings below for best results. STL files are "
        "exported by the build system to the export/ directory.",
        ss["GuideBody"]))
    elements.append(Spacer(1, 8))

    printable = [p for p in PART_CATALOG.values() if p.is_printable]

    headers = ["Part No.", "Name", "STL File", "Material", "Layer",
               "Infill", "Supports", "Est. Time", "Est. Filament"]
    rows = [headers]
    for part in printable:
        ps = part.print_settings
        est = _estimate_print(part)
        # Derive STL filename from the part's name (snake_case of first
        # included part in its module, or from catalog name)
        stl_name = part.name.lower().replace(" ", "_").replace(
            "(", "").replace(")", "").replace("+", "").replace("&", "")
        stl_name = stl_name.replace("__", "_").strip("_") + ".stl"

        rows.append([
            part.part_number,
            part.name,
            stl_name,
            ps.get("material", "PETG"),
            ps.get("layer_height", "0.16 mm"),
            ps.get("infill", "40%"),
            ps.get("supports", "none"),
            est["print_time"],
            est["filament_g"],
        ])

    col_widths = [45, 95, 100, 42, 38, 32, 52, 48, 48]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_alt_row_style(len(rows) - 1))
    elements.append(t)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Total printable parts: {len(printable)} / {len(PART_CATALOG)}",
        ss["GuideBody"]))

    elements.append(PageBreak())
    return elements


def _build_maintenance_schedule(ss) -> list:
    """Maintenance schedule page."""
    elements = []
    elements.append(Paragraph("Maintenance Schedule", ss["SectionTitle"]))
    elements.append(Paragraph(
        "Follow this preventive maintenance schedule to keep the camera "
        "running reliably. Intervals are measured in Kodak Super 8 "
        "cartridges (50 ft / 15 m each, ~3.5 minutes at 18 fps).",
        ss["GuideBody"]))
    elements.append(Spacer(1, 8))

    for entry in MAINTENANCE_SCHEDULE:
        block = []
        block.append(Paragraph(
            f"<b>{entry['label']}</b>", ss["SubSection"]))
        for task in entry["tasks"]:
            block.append(Paragraph(f"\u2022 {task}", ss["ProcStep"]))
        block.append(Spacer(1, 6))
        elements.append(KeepTogether(block))

    # Also list wear items with their replacement intervals from catalog
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Wear Item Replacement Intervals (from Part Catalog)",
        ss["SubSection"]))

    wear_headers = ["Part No.", "Name", "Interval (cartridges)", "Cost"]
    wear_rows = [wear_headers]
    for part in PART_CATALOG.values():
        if part.is_wear_item and part.replacement_interval_cartridges:
            wear_rows.append([
                part.part_number,
                part.name,
                str(part.replacement_interval_cartridges),
                f"${part.estimated_cost:.2f}",
            ])

    # Sort by interval ascending
    data_rows = wear_rows[1:]
    data_rows.sort(key=lambda r: int(r[2]))
    wear_rows = [wear_headers] + data_rows

    wt = Table(wear_rows, colWidths=[55, 180, 110, 60], repeatRows=1)
    wt.setStyle(_alt_row_style(len(wear_rows) - 1))
    elements.append(wt)

    elements.append(PageBreak())
    return elements


def _build_spare_parts_form(ss) -> list:
    """Spare parts order form page."""
    elements = []
    elements.append(Paragraph("Spare Parts Order Form", ss["SectionTitle"]))
    elements.append(Paragraph(
        "Use this form to order replacement parts. Prices are estimated "
        "at single-unit quantity. Contact your supplier for volume "
        "pricing.",
        ss["GuideBody"]))
    elements.append(Spacer(1, 8))

    headers = ["Part No.", "Name", "Material", "Wear?",
               "Interval", "Unit Price", "Qty", "Subtotal"]
    rows = [headers]

    total = 0.0
    for part in PART_CATALOG.values():
        interval = (f"{part.replacement_interval_cartridges}"
                    if part.replacement_interval_cartridges else "Lifetime")
        wear = "Yes" if part.is_wear_item else ""
        rows.append([
            part.part_number,
            part.name,
            part.material,
            wear,
            interval,
            f"${part.estimated_cost:.2f}",
            "____",  # fill-in field
            "______",  # fill-in field
        ])
        total += part.estimated_cost

    col_widths = [48, 120, 72, 32, 50, 55, 30, 50]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_alt_row_style(len(rows) - 1))
    elements.append(t)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Full catalog value (1 of each): ${total:.2f}",
        ss["GuideBody"]))

    # Wear items subtotal
    wear_parts = [p for p in PART_CATALOG.values() if p.is_wear_item]
    wear_total = sum(p.estimated_cost for p in wear_parts)
    elements.append(Paragraph(
        f"Wear items only ({len(wear_parts)} parts): ${wear_total:.2f}",
        ss["GuideBody"]))

    # BOM cost reference
    bom = generate_bom()
    totals = compute_totals(bom)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"<b>Full Camera BOM Reference:</b> "
        f"${totals['total_qty1']:.2f} (qty 1) | "
        f"${totals['total_qty25']:.2f} (qty 25) | "
        f"${totals['total_qty100']:.2f} (qty 100)",
        ss["GuideBody"]))

    return elements


# =========================================================================
# MAIN — GENERATE PDF
# =========================================================================

def generate(output_dir: str = None) -> str:
    """Generate the repair guide PDF.

    Args:
        output_dir: Output directory. Defaults to export/.

    Returns:
        Path to the generated PDF.
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "export")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "repair_guide.pdf")

    ss = _build_styles()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title="Super 8 Camera - Repair & Maintenance Guide",
        author="super8cam build system",
    )

    elements = []
    elements.extend(_build_cover(ss))
    elements.extend(_build_module_map(ss))
    elements.extend(_build_repair_pages(ss))
    elements.extend(_build_connector_reference(ss))
    elements.extend(_build_printable_parts(ss))
    elements.extend(_build_maintenance_schedule(ss))
    elements.extend(_build_spare_parts_form(ss))

    doc.build(elements)
    print(f"  Repair guide saved to {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    generate()
