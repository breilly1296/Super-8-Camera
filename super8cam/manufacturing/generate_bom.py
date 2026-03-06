"""generate_bom.py — Complete Bill of Materials generator.

Generates a full BOM as both CSV and formatted PDF with columns:
  - Item number, part name, part number, material, quantity
  - Make or buy, estimated unit cost at qty 1/25/100
  - Supplier/source, lead time, total cost per camera

Part numbering scheme:
  S8C-1xx  Mechanical parts (machined in-house)
  S8C-2xx  Electronics
  S8C-3xx  Fasteners
  S8C-4xx  Purchased parts (bearings, motor, etc.)
"""

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from super8cam.specs.master_specs import (
    FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE,
    BEARINGS, MOTOR, PCB, BATTERY, CAMERA, GEARBOX,
)
from super8cam.manufacturing.generate_drawings import PART_NUMBERS

EXPORT_DIR = "export"


# =========================================================================
# BOM item definition
# =========================================================================

@dataclass
class BOMItem:
    """One line item in the Bill of Materials."""
    item_number: int
    part_name: str
    part_number: str
    material: str
    qty: int
    make_or_buy: str        # "Make" or "Buy"
    cost_qty1: float        # unit cost at qty 1
    cost_qty25: float       # unit cost at qty 25
    cost_qty100: float      # unit cost at qty 100
    supplier: str
    lead_time: str
    category: str           # "Mechanical", "Electronics", "Fastener", "Purchased"
    notes: str = ""


# =========================================================================
# Cost models
# =========================================================================

# CNC machining cost estimates by material (per part, qty 1)
_CNC_COST_QTY1 = {
    "brass_c360":  45.00,   # precision gate work
    "alu_6061_t6": 25.00,   # general CNC aluminum
    "steel_4140":  35.00,   # harder to machine
    "steel_302":   20.00,   # simple flat part (spring)
    "delrin_150":  12.00,   # easy to machine
}

# Quantity discount factors (relative to qty 1)
_QTY_DISCOUNT = {
    1:   1.00,
    25:  0.55,   # 45% discount at 25 units
    100: 0.35,   # 65% discount at 100 units
}

# Complexity multipliers for specific parts
_COMPLEXITY = {
    "film_gate":       2.0,    # precision work, polishing
    "main_shaft":      1.5,    # grinding, heat treat
    "registration_pin": 1.8,   # precision turning
    "claw_mechanism":  1.5,    # small features
    "shutter_disc":    1.2,    # disc + keyway
    "gearbox_housing": 1.3,    # multiple bores
    "body_left":       1.8,    # large, many features
    "body_right":      1.8,
    "lens_mount":      1.4,    # thread cutting
}

# Purchased component costs (qty 1 / qty 25 / qty 100)
_PURCHASED_COSTS = {
    "694ZZ":     (2.50, 1.80, 1.20),
    "683ZZ":     (2.00, 1.50, 1.00),
    "FF-130SH":  (5.00, 3.50, 2.50),
    "PCB":       (35.00, 15.00, 8.00),
    "AA_cells":  (4.00, 3.00, 2.00),    # pack of 4
    "spring":    (1.50, 0.80, 0.50),
    "encoder":   (3.00, 2.00, 1.50),
    "lens":      (45.00, 35.00, 28.00),
    "light_seal": (2.00, 1.00, 0.60),
    "wiring":    (3.00, 2.00, 1.50),
    "connector": (1.50, 1.00, 0.70),
}

# Fastener costs per unit
_FASTENER_COSTS = {
    "M2x5_shcs":     (0.08, 0.04, 0.02),
    "M2x8_shcs":     (0.08, 0.04, 0.02),
    "M2_5x6_shcs":   (0.10, 0.05, 0.03),
    "M3x8_shcs":     (0.12, 0.06, 0.04),
    "quarter20x6":   (0.50, 0.30, 0.20),
}


# =========================================================================
# BOM generation
# =========================================================================

def _machined_part_cost(part_name: str, mat_key: str) -> Tuple[float, float, float]:
    """Return (cost_qty1, cost_qty25, cost_qty100) for a machined part."""
    base = _CNC_COST_QTY1.get(mat_key, 25.00)
    cmplx = _COMPLEXITY.get(part_name, 1.0)
    c1 = base * cmplx
    c25 = c1 * _QTY_DISCOUNT[25]
    c100 = c1 * _QTY_DISCOUNT[100]
    return (round(c1, 2), round(c25, 2), round(c100, 2))


def generate_bom() -> List[BOMItem]:
    """Build the complete BOM.  Returns list of BOMItem."""
    items = []
    item_num = 1

    # ---- S8C-1xx: Machined mechanical parts ----
    machined_parts = [
        ("film_gate",          "brass_c360",  "CNC shop",     "3-4 weeks"),
        ("pressure_plate",     "steel_302",   "CNC shop",     "2-3 weeks"),
        ("film_channel",       "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("registration_pin",   "steel_4140",  "CNC shop",     "2-3 weeks"),
        ("claw_mechanism",     "steel_4140",  "CNC shop",     "3-4 weeks"),
        ("cam_follower",       "steel_4140",  "CNC shop",     "3-4 weeks"),
        ("main_shaft",         "steel_4140",  "CNC shop",     "2-3 weeks"),
        ("shutter_disc",       "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("gearbox_housing",    "alu_6061_t6", "CNC shop",     "3-4 weeks"),
        ("body_left",          "alu_6061_t6", "CNC shop",     "4-5 weeks"),
        ("body_right",         "alu_6061_t6", "CNC shop",     "4-5 weeks"),
        ("top_plate",          "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("bottom_plate",       "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("battery_door",       "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("cartridge_door",     "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("trigger",            "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("lens_mount",         "alu_6061_t6", "CNC shop",     "3-4 weeks"),
        ("viewfinder",         "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("motor_mount",        "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("pcb_bracket",        "alu_6061_t6", "CNC shop",     "2-3 weeks"),
        ("cartridge_receiver", "alu_6061_t6", "CNC shop",     "3-4 weeks"),
        ("stage1_pinion",      "delrin_150",  "CNC shop",     "2-3 weeks"),
        ("stage1_gear",        "delrin_150",  "CNC shop",     "2-3 weeks"),
        ("stage2_pinion",      "delrin_150",  "CNC shop",     "2-3 weeks"),
        ("stage2_gear",        "delrin_150",  "CNC shop",     "2-3 weeks"),
    ]

    for name, mat_key, supplier, lead in machined_parts:
        pn = PART_NUMBERS.get(name, f"S8C-1{item_num:02d}")
        mat = MATERIALS[mat_key]
        c1, c25, c100 = _machined_part_cost(name, mat_key)
        items.append(BOMItem(
            item_number=item_num,
            part_name=name.replace("_", " ").title(),
            part_number=pn,
            material=mat.designation,
            qty=1,
            make_or_buy="Make",
            cost_qty1=c1, cost_qty25=c25, cost_qty100=c100,
            supplier=supplier,
            lead_time=lead,
            category="Mechanical",
        ))
        item_num += 1

    # ---- S8C-2xx: Electronics ----
    electronics = [
        ("Control PCB (4-layer ENIG)", "S8C-200", "FR4/ENIG", 1,
         "Make", 35.00, 15.00, 8.00, "JLCPCB / PCBWay", "2-3 weeks"),
        ("STM32L031K6 MCU", "S8C-201", "IC", 1,
         "Buy", 3.50, 2.80, 2.20, "DigiKey / Mouser", "1-2 weeks"),
        ("Motor Driver (DRV8833)", "S8C-202", "IC", 1,
         "Buy", 2.50, 1.80, 1.40, "DigiKey / Mouser", "1-2 weeks"),
        ("Photodiode (BPW21R)", "S8C-203", "Si photodiode", 1,
         "Buy", 4.00, 3.00, 2.50, "DigiKey / Mouser", "1-2 weeks"),
        ("Voltage Regulator (LDO 3.3V)", "S8C-204", "IC", 1,
         "Buy", 0.80, 0.50, 0.35, "DigiKey / Mouser", "1-2 weeks"),
        ("Passive Components Kit", "S8C-205", "Mixed", 1,
         "Buy", 5.00, 3.00, 2.00, "DigiKey / Mouser", "1-2 weeks"),
        ("Optical Encoder Sensor", "S8C-206", "Slotted optical", 1,
         "Buy", 3.00, 2.00, 1.50, "DigiKey / Mouser", "1-2 weeks"),
        ("Galvanometer Movement", "S8C-207", "Meter movement", 1,
         "Buy", 8.00, 6.00, 4.50, "Surplus / eBay", "2-4 weeks"),
        ("Wiring Harness", "S8C-208", "Wire + connectors", 1,
         "Make", 3.00, 2.00, 1.50, "In-house", "1 week"),
    ]

    for name, pn, mat, qty, mob, c1, c25, c100, supp, lead in electronics:
        items.append(BOMItem(
            item_number=item_num,
            part_name=name,
            part_number=pn,
            material=mat,
            qty=qty,
            make_or_buy=mob,
            cost_qty1=c1, cost_qty25=c25, cost_qty100=c100,
            supplier=supp,
            lead_time=lead,
            category="Electronics",
        ))
        item_num += 1

    # ---- S8C-3xx: Fasteners ----
    fnum = 300
    for usage, (fkey, qty) in FASTENER_USAGE.items():
        f = FASTENERS[fkey]
        c1, c25, c100 = _FASTENER_COSTS.get(fkey, (0.10, 0.05, 0.03))
        items.append(BOMItem(
            item_number=item_num,
            part_name=f"{f.thread} x {f.length}mm {f.head_type}",
            part_number=f"S8C-{fnum}",
            material="Steel / Stainless",
            qty=qty,
            make_or_buy="Buy",
            cost_qty1=c1 * qty, cost_qty25=c25 * qty, cost_qty100=c100 * qty,
            supplier="McMaster-Carr / Bolt Depot",
            lead_time="1-2 weeks",
            category="Fastener",
            notes=f"Usage: {usage}, torque: {f.torque_nm} N-m",
        ))
        fnum += 1
        item_num += 1

    # ---- S8C-4xx: Purchased parts ----
    # Bearings
    pnum = 400
    for usage, brg in BEARINGS.items():
        c1, c25, c100 = _PURCHASED_COSTS.get(brg.designation, (2.50, 1.80, 1.20))
        items.append(BOMItem(
            item_number=item_num,
            part_name=f"Bearing {brg.designation} ({usage})",
            part_number=f"S8C-{pnum}",
            material=f"{brg.bore}x{brg.od}x{brg.width}mm {brg.seal}",
            qty=1,
            make_or_buy="Buy",
            cost_qty1=c1, cost_qty25=c25, cost_qty100=c100,
            supplier="SKF / NMB / Amazon",
            lead_time="1-2 weeks",
            category="Purchased",
        ))
        pnum += 1
        item_num += 1

    # Motor
    items.append(BOMItem(
        item_number=item_num,
        part_name=f"DC Motor {MOTOR.model}",
        part_number=f"S8C-{pnum}",
        material=f"{MOTOR.nominal_voltage}V DC motor",
        qty=1,
        make_or_buy="Buy",
        cost_qty1=5.00, cost_qty25=3.50, cost_qty100=2.50,
        supplier="Mabuchi / AliExpress",
        lead_time="2-3 weeks",
        category="Purchased",
    ))
    pnum += 1
    item_num += 1

    # Battery holder
    items.append(BOMItem(
        item_number=item_num,
        part_name=f"Battery Holder ({BATTERY.cell_count}x{BATTERY.cell_type})",
        part_number=f"S8C-{pnum}",
        material="Plastic + spring contacts",
        qty=1,
        make_or_buy="Buy",
        cost_qty1=2.00, cost_qty25=1.50, cost_qty100=1.00,
        supplier="DigiKey / Mouser",
        lead_time="1-2 weeks",
        category="Purchased",
    ))
    pnum += 1
    item_num += 1

    # Batteries
    items.append(BOMItem(
        item_number=item_num,
        part_name=f"AA Alkaline Cells (pack of {BATTERY.cell_count})",
        part_number=f"S8C-{pnum}",
        material="Alkaline",
        qty=1,
        make_or_buy="Buy",
        cost_qty1=4.00, cost_qty25=3.00, cost_qty100=2.00,
        supplier="Any",
        lead_time="Stock",
        category="Purchased",
    ))
    pnum += 1
    item_num += 1

    # C-mount lens (not included in camera cost but listed)
    items.append(BOMItem(
        item_number=item_num,
        part_name="C-Mount Lens (user-supplied)",
        part_number=f"S8C-{pnum}",
        material="Optical glass",
        qty=1,
        make_or_buy="Buy",
        cost_qty1=45.00, cost_qty25=35.00, cost_qty100=28.00,
        supplier="Various (Computar, Fujinon)",
        lead_time="1-2 weeks",
        category="Purchased",
        notes="Optional — user may supply own lens",
    ))
    pnum += 1
    item_num += 1

    # Light seal foam
    items.append(BOMItem(
        item_number=item_num,
        part_name="Light Seal Foam Strip",
        part_number=f"S8C-{pnum}",
        material="Closed-cell foam, adhesive-backed",
        qty=1,
        make_or_buy="Buy",
        cost_qty1=2.00, cost_qty25=1.00, cost_qty100=0.60,
        supplier="Camera repair suppliers",
        lead_time="1 week",
        category="Purchased",
    ))
    pnum += 1
    item_num += 1

    # Pressure plate spring
    items.append(BOMItem(
        item_number=item_num,
        part_name="Pressure Plate Springs (pair)",
        part_number=f"S8C-{pnum}",
        material="Spring steel wire",
        qty=1,
        make_or_buy="Buy",
        cost_qty1=1.50, cost_qty25=0.80, cost_qty100=0.50,
        supplier="McMaster-Carr / Lee Spring",
        lead_time="1-2 weeks",
        category="Purchased",
    ))
    item_num += 1

    return items


# =========================================================================
# Cost summary
# =========================================================================

def calculate_totals(items: List[BOMItem]) -> Dict:
    """Calculate BOM cost totals at each quantity break."""
    total_1 = sum(i.cost_qty1 * i.qty for i in items if "user-supplied" not in i.part_name.lower())
    total_25 = sum(i.cost_qty25 * i.qty for i in items if "user-supplied" not in i.part_name.lower())
    total_100 = sum(i.cost_qty100 * i.qty for i in items if "user-supplied" not in i.part_name.lower())

    by_category = {}
    for item in items:
        if "user-supplied" in item.part_name.lower():
            continue
        cat = item.category
        if cat not in by_category:
            by_category[cat] = {"qty1": 0, "qty25": 0, "qty100": 0, "count": 0}
        by_category[cat]["qty1"] += item.cost_qty1 * item.qty
        by_category[cat]["qty25"] += item.cost_qty25 * item.qty
        by_category[cat]["qty100"] += item.cost_qty100 * item.qty
        by_category[cat]["count"] += item.qty

    return {
        "total_qty1": round(total_1, 2),
        "total_qty25": round(total_25, 2),
        "total_qty100": round(total_100, 2),
        "by_category": by_category,
        "line_items": len(items),
        "total_parts": sum(i.qty for i in items),
    }


# =========================================================================
# CSV export
# =========================================================================

def export_csv(filepath: str = None) -> str:
    """Export BOM as CSV.  Returns the output path."""
    if filepath is None:
        filepath = os.path.join(EXPORT_DIR, "bom.csv")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    items = generate_bom()
    fieldnames = [
        "Item", "Part Name", "Part Number", "Material", "Qty",
        "Make/Buy", "Cost (qty 1)", "Cost (qty 25)", "Cost (qty 100)",
        "Supplier", "Lead Time", "Category", "Notes",
    ]

    with open(filepath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for item in items:
            w.writerow({
                "Item": item.item_number,
                "Part Name": item.part_name,
                "Part Number": item.part_number,
                "Material": item.material,
                "Qty": item.qty,
                "Make/Buy": item.make_or_buy,
                "Cost (qty 1)": f"${item.cost_qty1:.2f}",
                "Cost (qty 25)": f"${item.cost_qty25:.2f}",
                "Cost (qty 100)": f"${item.cost_qty100:.2f}",
                "Supplier": item.supplier,
                "Lead Time": item.lead_time,
                "Category": item.category,
                "Notes": item.notes,
            })

    # Append totals row
    totals = calculate_totals(items)
    with open(filepath, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([])
        w.writerow(["", "TOTAL", "", "", totals["total_parts"],
                    "", f"${totals['total_qty1']:.2f}",
                    f"${totals['total_qty25']:.2f}",
                    f"${totals['total_qty100']:.2f}",
                    "", "", "", ""])

    print(f"  Exported BOM CSV: {filepath} ({len(items)} line items)")
    return filepath


# =========================================================================
# PDF export
# =========================================================================

def export_pdf(filepath: str = None) -> str:
    """Export BOM as formatted PDF.  Returns the output path."""
    if filepath is None:
        filepath = os.path.join(EXPORT_DIR, "bom.pdf")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    items = generate_bom()
    totals = calculate_totals(items)

    # Page setup: landscape letter
    fig_w, fig_h = 14.0, 8.5
    rows_per_page = 30
    pages = (len(items) + rows_per_page - 1) // rows_per_page + 1  # +1 for summary

    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(filepath) as pdf:
        # ---- Item pages ----
        for page_idx in range((len(items) + rows_per_page - 1) // rows_per_page):
            fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
            ax.set_xlim(0, fig_w)
            ax.set_ylim(0, fig_h)
            ax.axis("off")

            # Title
            ax.text(fig_w / 2, fig_h - 0.3, "SUPER 8 CAMERA — BILL OF MATERIALS",
                    fontsize=12, ha="center", fontweight="bold")
            ax.text(fig_w / 2, fig_h - 0.55,
                    f"Page {page_idx + 1} of {(len(items) + rows_per_page - 1) // rows_per_page + 1}",
                    fontsize=8, ha="center")

            # Column headers
            cols = [
                (0.2, 0.5, "Item"),
                (0.7, 2.8, "Part Name"),
                (3.5, 1.2, "Part No."),
                (4.7, 1.2, "Material"),
                (5.9, 0.4, "Qty"),
                (6.3, 0.6, "M/B"),
                (6.9, 1.0, "Cost @1"),
                (7.9, 1.0, "Cost @25"),
                (8.9, 1.0, "Cost @100"),
                (9.9, 2.0, "Supplier"),
                (11.9, 1.2, "Lead Time"),
            ]

            header_y = fig_h - 0.9
            for x, w, label in cols:
                ax.text(x + 0.05, header_y, label, fontsize=6.5, fontweight="bold", va="center")
            ax.plot([0.15, fig_w - 0.15], [header_y - 0.12, header_y - 0.12],
                    "k-", linewidth=0.8)

            # Data rows
            start = page_idx * rows_per_page
            end = min(start + rows_per_page, len(items))
            row_h = 0.22
            for ri, item in enumerate(items[start:end]):
                y = header_y - 0.3 - ri * row_h
                bg_color = "#f0f0f0" if ri % 2 == 0 else "white"
                ax.add_patch(Rectangle((0.15, y - row_h / 2), fig_w - 0.3, row_h,
                                        facecolor=bg_color, edgecolor="none"))

                vals = [
                    str(item.item_number),
                    item.part_name[:30],
                    item.part_number,
                    item.material[:12],
                    str(item.qty),
                    item.make_or_buy[:4],
                    f"${item.cost_qty1:.2f}",
                    f"${item.cost_qty25:.2f}",
                    f"${item.cost_qty100:.2f}",
                    item.supplier[:20],
                    item.lead_time[:12],
                ]
                for (x, w, _), val in zip(cols, vals):
                    ax.text(x + 0.05, y, val, fontsize=5.5, va="center", fontfamily="monospace")

            pdf.savefig(fig, dpi=150, bbox_inches="tight")
            plt.close(fig)

        # ---- Summary page ----
        fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
        ax.set_xlim(0, fig_w)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        ax.text(fig_w / 2, fig_h - 0.4, "BOM COST SUMMARY",
                fontsize=14, ha="center", fontweight="bold")

        y = fig_h - 1.2
        fs = 9

        # Category breakdown
        ax.text(1.0, y, "Category", fontsize=fs, fontweight="bold")
        ax.text(4.0, y, "Items", fontsize=fs, fontweight="bold", ha="right")
        ax.text(6.5, y, "Cost @1", fontsize=fs, fontweight="bold", ha="right")
        ax.text(8.5, y, "Cost @25", fontsize=fs, fontweight="bold", ha="right")
        ax.text(10.5, y, "Cost @100", fontsize=fs, fontweight="bold", ha="right")
        y -= 0.15
        ax.plot([0.8, 11.0], [y, y], "k-", linewidth=1.0)
        y -= 0.35

        for cat, data in sorted(totals["by_category"].items()):
            ax.text(1.0, y, cat, fontsize=fs)
            ax.text(4.0, y, str(data["count"]), fontsize=fs, ha="right")
            ax.text(6.5, y, f"${data['qty1']:.2f}", fontsize=fs, ha="right")
            ax.text(8.5, y, f"${data['qty25']:.2f}", fontsize=fs, ha="right")
            ax.text(10.5, y, f"${data['qty100']:.2f}", fontsize=fs, ha="right")
            y -= 0.35

        y -= 0.1
        ax.plot([0.8, 11.0], [y, y], "k-", linewidth=1.5)
        y -= 0.35
        ax.text(1.0, y, "TOTAL (per camera)", fontsize=fs + 1, fontweight="bold")
        ax.text(4.0, y, str(totals["total_parts"]), fontsize=fs + 1,
                fontweight="bold", ha="right")
        ax.text(6.5, y, f"${totals['total_qty1']:.2f}", fontsize=fs + 1,
                fontweight="bold", ha="right")
        ax.text(8.5, y, f"${totals['total_qty25']:.2f}", fontsize=fs + 1,
                fontweight="bold", ha="right")
        ax.text(10.5, y, f"${totals['total_qty100']:.2f}", fontsize=fs + 1,
                fontweight="bold", ha="right")

        y -= 0.8
        ax.text(1.0, y, "Notes:", fontsize=fs, fontweight="bold")
        y -= 0.35
        notes = [
            "Qty 1 costs assume prototype pricing (single unit CNC, retail components)",
            "Qty 25 costs assume small batch CNC with setup amortization",
            "Qty 100 costs assume production tooling and volume component pricing",
            "Labor and assembly costs not included",
            "C-mount lens listed but excluded from totals (user-supplied)",
            "Prices are estimates and may vary by supplier and market conditions",
        ]
        for note in notes:
            ax.text(1.2, y, f"- {note}", fontsize=7)
            y -= 0.3

        pdf.savefig(fig, dpi=150, bbox_inches="tight")
        plt.close(fig)

    print(f"  Exported BOM PDF: {filepath}")
    return filepath


# =========================================================================
# Public API (backward-compatible)
# =========================================================================

def generate_all(output_dir: str = EXPORT_DIR) -> Dict:
    """Generate BOM in all formats.  Returns summary dict."""
    csv_path = export_csv(os.path.join(output_dir, "bom.csv"))
    pdf_path = export_pdf(os.path.join(output_dir, "bom.pdf"))
    items = generate_bom()
    totals = calculate_totals(items)
    return {
        "csv_path": csv_path,
        "pdf_path": pdf_path,
        "totals": totals,
        "items": items,
    }


if __name__ == "__main__":
    result = generate_all()
    t = result["totals"]
    print(f"\nBOM: {t['line_items']} line items, {t['total_parts']} total parts")
    print(f"  Cost per camera @qty 1:   ${t['total_qty1']:.2f}")
    print(f"  Cost per camera @qty 25:  ${t['total_qty25']:.2f}")
    print(f"  Cost per camera @qty 100: ${t['total_qty100']:.2f}")
