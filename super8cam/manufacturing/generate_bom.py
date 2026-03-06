"""generate_bom.py — Complete Bill of Materials Generator

Generates a comprehensive BOM with:
  - Logical part numbering (S8C-1xx mechanical, S8C-2xx electronics,
    S8C-3xx fasteners, S8C-4xx purchased parts)
  - Material specifications
  - Make/buy designation
  - Cost estimates at qty 1, 25, and 100
  - Supplier and lead time
  - CSV and formatted PDF export

All dimensions and counts derived from master_specs.py.
"""

from __future__ import annotations
import csv
import os
from dataclasses import dataclass, field
from typing import List, Optional

from super8cam.specs.master_specs import (
    CAMERA, FILM, CMOUNT, MOTOR, GEARBOX, BATTERY, PCB,
    FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE, BEARINGS,
)


# =========================================================================
# BOM ITEM DATACLASS
# =========================================================================

@dataclass
class BOMItem:
    """Single line item in the Bill of Materials."""
    item_num: int
    part_number: str            # e.g. "S8C-101"
    part_name: str
    material: str               # e.g. "Brass C360" or "N/A" for purchased
    qty: int                    # quantity per camera
    make_buy: str               # "Make" or "Buy"
    cost_qty1: float            # estimated unit cost at qty 1
    cost_qty25: float           # at qty 25
    cost_qty100: float          # at qty 100
    supplier: str               # supplier / source
    lead_time: str              # e.g. "2 weeks"
    notes: str = ""


# =========================================================================
# PART DEFINITIONS
#
# Organised by series:
#   S8C-100: CNC-machined mechanical parts
#   S8C-200: Electronics / PCB
#   S8C-300: Fasteners
#   S8C-400: Purchased parts (motor, bearings, battery, etc.)
# =========================================================================

def _build_mechanical_parts() -> List[BOMItem]:
    """S8C-100 series: CNC-machined parts."""
    m = MATERIALS
    mu = MATERIAL_USAGE
    parts = []

    def mat_name(key: str) -> str:
        return m[mu[key]].name if key in mu else "Alu 6061-T6"

    def mat_short(key: str) -> str:
        return m[mu[key]].designation if key in mu else "6061-T6"

    # (part_number, name, material_key, qty, cost1, cost25, cost100, supplier, lead, notes)
    defs = [
        ("S8C-101", "Body Shell — Left Half",    "body_shell",       1, 85.00, 52.00, 38.00, "CNC shop / Xometry",      "2-3 weeks", "5-axis CNC, black anodize"),
        ("S8C-102", "Body Shell — Right Half",    "body_shell",       1, 85.00, 52.00, 38.00, "CNC shop / Xometry",      "2-3 weeks", "5-axis CNC, black anodize"),
        ("S8C-103", "Top Plate",                  "body_shell",       1, 28.00, 18.00, 14.00, "CNC shop",                "2 weeks",   "3-axis CNC, black anodize"),
        ("S8C-104", "Bottom Plate",               "body_shell",       1, 30.00, 19.00, 15.00, "CNC shop",                "2 weeks",   "Tripod boss, 3-axis CNC"),
        ("S8C-105", "Cartridge Door",             "body_shell",       1, 22.00, 14.00, 10.00, "CNC shop",                "2 weeks",   "Sheet + hinge, anodize"),
        ("S8C-106", "Battery Door",               "body_shell",       1, 15.00, 10.00,  8.00, "CNC shop",                "2 weeks",   "Sheet + latch, anodize"),
        ("S8C-107", "Film Gate",                  "film_gate",        1, 45.00, 30.00, 22.00, "Precision CNC shop",      "3 weeks",   "Precision ground, lapped"),
        ("S8C-108", "Pressure Plate",             "pressure_plate",   1, 18.00, 12.00,  9.00, "Spring steel supplier",   "2 weeks",   "Wire EDM + spring temper"),
        ("S8C-109", "Lens Mount Boss",            "body_shell",       1, 25.00, 16.00, 12.00, "CNC shop",                "2 weeks",   "C-mount thread, CNC lathe"),
        ("S8C-110", "Main Shaft",                 "main_shaft",       1, 20.00, 14.00, 10.00, "CNC lathe shop",          "2 weeks",   "Ground bearing seats"),
        ("S8C-111", "Shutter Disc",               "shutter_disc",     1, 15.00, 10.00,  8.00, "CNC shop / waterjet",     "1-2 weeks", "0.8mm aluminium, balanced"),
        ("S8C-112", "Pulldown Cam",               "cam",              1, 30.00, 20.00, 15.00, "CNC shop",                "2-3 weeks", "4-axis CNC, hardened 4140"),
        ("S8C-113", "Secondary Eccentric",        "cam",              1, 18.00, 12.00,  9.00, "CNC shop",                "2 weeks",   "4140 steel, ground OD"),
        ("S8C-114", "Cam Follower Pin",           "cam",              1,  8.00,  5.00,  4.00, "CNC lathe",               "1 week",    "Dowel pin, ground"),
        ("S8C-115", "Claw Mechanism",             "claw",             1, 35.00, 22.00, 16.00, "Wire EDM / CNC",          "2-3 weeks", "Hardened 4140, tight tols"),
        ("S8C-116", "Registration Pin",           "registration_pin", 1, 12.00,  8.00,  6.00, "CNC swiss lathe",         "1-2 weeks", f"Ø{CAMERA.reg_pin_dia}mm ground"),
        ("S8C-117", "Gearbox Housing",            "body_shell",       1, 25.00, 16.00, 12.00, "CNC shop",                "2 weeks",   "Alu 6061 2-piece"),
        ("S8C-118", "Stage 1 Pinion (10T)",       "gears",            1,  8.00,  5.00,  3.50, "CNC shop / gear cutter",  "2 weeks",   f"Delrin, M{GEARBOX.stage1_module}"),
        ("S8C-119", "Stage 1 Gear (50T)",         "gears",            1, 10.00,  6.00,  4.00, "CNC shop / gear cutter",  "2 weeks",   f"Delrin, M{GEARBOX.stage1_module}"),
        ("S8C-120", "Stage 2 Pinion (12T)",       "gears",            1,  8.00,  5.00,  3.50, "CNC shop / gear cutter",  "2 weeks",   f"Delrin, M{GEARBOX.stage2_module}"),
        ("S8C-121", "Stage 2 Gear (36T)",         "gears",            1, 10.00,  6.00,  4.00, "CNC shop / gear cutter",  "2 weeks",   f"Delrin, M{GEARBOX.stage2_module}"),
        ("S8C-122", "Motor Mount Bracket",        "body_shell",       1, 12.00,  8.00,  6.00, "CNC shop",                "1-2 weeks", "Alu 6061, anodize"),
        ("S8C-123", "PCB Mounting Bracket",       "body_shell",       1, 10.00,  7.00,  5.00, "CNC shop / sheet metal",  "1-2 weeks", "Alu standoffs"),
        ("S8C-124", "Film Channel Guide",         "body_shell",       1, 18.00, 12.00,  9.00, "CNC shop",                "2 weeks",   "Alu 6061, polished rails"),
        ("S8C-125", "Cartridge Receiver",         "body_shell",       1, 20.00, 13.00, 10.00, "CNC shop",                "2 weeks",   "Alu 6061, precise slot"),
        ("S8C-126", "Viewfinder Tube",            "body_shell",       1, 15.00, 10.00,  8.00, "CNC lathe",               "1-2 weeks", "Alu tube, black anodize"),
        ("S8C-127", "Trigger Button",             "body_shell",       1,  8.00,  5.00,  4.00, "CNC shop",                "1 week",    "Alu + spring, anodize"),
    ]

    for i, (pn, name, mat_key, qty, c1, c25, c100, sup, lead, note) in enumerate(defs, 1):
        parts.append(BOMItem(
            item_num=i,
            part_number=pn,
            part_name=name,
            material=mat_short(mat_key),
            qty=qty,
            make_buy="Make",
            cost_qty1=c1,
            cost_qty25=c25,
            cost_qty100=c100,
            supplier=sup,
            lead_time=lead,
            notes=note,
        ))

    return parts


def _build_electronics() -> List[BOMItem]:
    """S8C-200 series: Electronics."""
    return [
        BOMItem(201, "S8C-201", "Control PCB (assembled)",
                f"FR4 {PCB.layers}L {PCB.finish}", 1, "Make",
                45.00, 28.00, 18.00, "JLCPCB / PCBWay", "2-3 weeks",
                f"{PCB.width}x{PCB.height}mm, STM32L031K6"),
        BOMItem(202, "S8C-202", "Photodiode (BPW34)",
                "Silicon PIN", 1, "Buy",
                1.50, 1.20, 0.90, "Mouser / DigiKey", "In stock",
                "Metering sensor"),
        BOMItem(203, "S8C-203", "Optical Encoder Sensor",
                "GP1A57HRJ00F", 1, "Buy",
                2.80, 2.20, 1.80, "Mouser / DigiKey", "In stock",
                "Slotted photointerrupter"),
        BOMItem(204, "S8C-204", "Motor Driver MOSFET",
                "IRLML6344", 1, "Buy",
                0.45, 0.35, 0.25, "Mouser / DigiKey", "In stock",
                "N-ch logic-level, SOT-23"),
        BOMItem(205, "S8C-205", "Galvanometer Meter Movement",
                "100µA FSD", 1, "Buy",
                8.00, 6.50, 5.00, "eBay / AliExpress", "2-4 weeks",
                "Moving-coil, panel mount"),
        BOMItem(206, "S8C-206", "Battery Holder (4×AA)",
                "BH-341", 1, "Buy",
                1.50, 1.20, 0.90, "Mouser", "In stock",
                "2×2 AA holder with leads"),
        BOMItem(207, "S8C-207", "Wire Harness",
                "26AWG", 1, "Make",
                3.00, 2.00, 1.50, "In-house", "1 day",
                "Motor, encoder, meter, battery"),
    ]


def _build_fasteners() -> List[BOMItem]:
    """S8C-300 series: Fasteners."""
    parts = []
    pn_base = 301
    fu = FASTENER_USAGE
    fs = FASTENERS

    for usage, (fkey, qty) in fu.items():
        f = fs[fkey]
        parts.append(BOMItem(
            item_num=pn_base,
            part_number=f"S8C-{pn_base}",
            part_name=f"{f.thread}×{f.length:.0f} {f.head_type.replace('_', ' ').title()}",
            material="A2 stainless" if f.thread != "1/4-20" else "Stainless helicoil",
            qty=qty,
            make_buy="Buy",
            cost_qty1=0.15 * qty,
            cost_qty25=0.10 * qty,
            cost_qty100=0.07 * qty,
            supplier="McMaster-Carr / Bolt Depot",
            lead_time="In stock",
            notes=f"For: {usage.replace('_', ' ')} — {f.torque_nm} N·m",
        ))
        pn_base += 1

    return parts


def _build_purchased() -> List[BOMItem]:
    """S8C-400 series: Purchased components."""
    parts = []

    # Motor
    parts.append(BOMItem(
        401, "S8C-401",
        f"DC Motor ({MOTOR.model})",
        "Mabuchi FF-130SH", 1, "Buy",
        3.50, 2.80, 2.20,
        "Amazon / AliExpress / eBay",
        "1-2 weeks",
        f"{MOTOR.nominal_voltage}V, {MOTOR.no_load_rpm} RPM no-load",
    ))

    # Bearings
    brg_items = [
        ("main_shaft",           "Main Shaft Bearing",     2),
        ("cam_follower",         "Cam Follower Bearing",   1),
        ("shutter_shaft_support","Shutter Support Bearing", 1),
    ]
    pn = 402
    for bkey, bname, qty in brg_items:
        b = BEARINGS[bkey]
        parts.append(BOMItem(
            pn, f"S8C-{pn}",
            f"{bname} ({b.designation})",
            f"{b.bore}×{b.od}×{b.width}mm {b.seal}",
            qty, "Buy",
            1.80 * qty, 1.40 * qty, 1.00 * qty,
            "McMaster-Carr / VXB",
            "In stock",
            f"C={b.dynamic_load}N, {b.max_rpm} RPM max",
        ))
        pn += 1

    # Batteries
    parts.append(BOMItem(
        405, "S8C-405",
        f"Alkaline Battery ({BATTERY.cell_type})",
        "Alkaline 1.5V",
        BATTERY.cell_count, "Buy",
        0.50 * BATTERY.cell_count,
        0.40 * BATTERY.cell_count,
        0.30 * BATTERY.cell_count,
        "Any retailer",
        "In stock",
        f"{BATTERY.cell_count}×{BATTERY.cell_type} = {BATTERY.pack_voltage_nom}V",
    ))

    # Viewfinder lenses
    parts.append(BOMItem(
        406, "S8C-406",
        "Viewfinder Lens Set",
        "BK7 optical glass", 1, "Buy",
        5.00, 3.50, 2.50,
        "Surplus Shed / Edmund Optics",
        "1-2 weeks",
        "Galilean doublet, 0.5× magnification",
    ))

    # Pressure plate springs
    parts.append(BOMItem(
        407, "S8C-407",
        "Pressure Plate Springs",
        "302 SS spring wire", 2, "Buy",
        0.60, 0.40, 0.30,
        "McMaster-Carr / Lee Spring",
        "In stock",
        f"~{CAMERA.pressure_plate_force_n}N target force",
    ))

    # Helicoil insert (tripod)
    parts.append(BOMItem(
        408, "S8C-408",
        "Helicoil Insert 1/4-20",
        "Stainless", 1, "Buy",
        1.20, 0.90, 0.70,
        "McMaster-Carr",
        "In stock",
        "Tripod mount, 6mm depth",
    ))

    # O-ring / light seal
    parts.append(BOMItem(
        409, "S8C-409",
        "Light Seal Foam Strip",
        "Closed-cell polyurethane", 1, "Buy",
        2.00, 1.50, 1.00,
        "Amazon / camera repair supplier",
        "In stock",
        "1mm thick, self-adhesive, door seals",
    ))

    return parts


# =========================================================================
# BOM ASSEMBLY
# =========================================================================

def generate_bom() -> List[BOMItem]:
    """Build the complete BOM from all series."""
    bom = []
    bom.extend(_build_mechanical_parts())
    bom.extend(_build_electronics())
    bom.extend(_build_fasteners())
    bom.extend(_build_purchased())

    # Re-number sequentially
    for i, item in enumerate(bom, 1):
        item.item_num = i

    return bom


def compute_totals(bom: List[BOMItem]) -> dict:
    """Compute total costs at each quantity break."""
    total_1 = sum(item.cost_qty1 for item in bom)
    total_25 = sum(item.cost_qty25 for item in bom)
    total_100 = sum(item.cost_qty100 for item in bom)

    make_count = sum(1 for item in bom if item.make_buy == "Make")
    buy_count = sum(1 for item in bom if item.make_buy == "Buy")
    total_parts = sum(item.qty for item in bom)

    return {
        "total_qty1": total_1,
        "total_qty25": total_25,
        "total_qty100": total_100,
        "line_items": len(bom),
        "total_parts": total_parts,
        "make_items": make_count,
        "buy_items": buy_count,
    }


# =========================================================================
# CSV EXPORT
# =========================================================================

BOM_CSV_FIELDS = [
    "item_num", "part_number", "part_name", "material",
    "qty", "make_buy",
    "cost_qty1", "cost_qty25", "cost_qty100",
    "supplier", "lead_time", "notes",
]


def export_csv(filepath: str = "export/bom.csv"):
    """Export the BOM as a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bom = generate_bom()

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=BOM_CSV_FIELDS)
        writer.writeheader()
        for item in bom:
            row = {
                "item_num": item.item_num,
                "part_number": item.part_number,
                "part_name": item.part_name,
                "material": item.material,
                "qty": item.qty,
                "make_buy": item.make_buy,
                "cost_qty1": f"{item.cost_qty1:.2f}",
                "cost_qty25": f"{item.cost_qty25:.2f}",
                "cost_qty100": f"{item.cost_qty100:.2f}",
                "supplier": item.supplier,
                "lead_time": item.lead_time,
                "notes": item.notes,
            }
            writer.writerow(row)

        # Totals row
        totals = compute_totals(bom)
        writer.writerow({
            "item_num": "",
            "part_number": "",
            "part_name": "TOTAL",
            "material": "",
            "qty": totals["total_parts"],
            "make_buy": f"{totals['make_items']}M/{totals['buy_items']}B",
            "cost_qty1": f"{totals['total_qty1']:.2f}",
            "cost_qty25": f"{totals['total_qty25']:.2f}",
            "cost_qty100": f"{totals['total_qty100']:.2f}",
            "supplier": "",
            "lead_time": "",
            "notes": "",
        })

    print(f"  Exported: {filepath} ({len(bom)} line items)")
    return filepath


# =========================================================================
# PDF EXPORT (formatted table via matplotlib)
# =========================================================================

def export_pdf(filepath: str = "export/bom.pdf"):
    """Export the BOM as a formatted PDF table."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bom = generate_bom()
    totals = compute_totals(bom)

    with PdfPages(filepath) as pdf:
        # ---- Page 1: Summary ----
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")

        ax.text(0.5, 0.95, "SUPER 8 CAMERA — BILL OF MATERIALS",
                ha="center", va="top", fontsize=16, fontweight="bold")
        ax.text(0.5, 0.90, "Document: S8C-BOM-001  Rev A",
                ha="center", va="top", fontsize=10, color="gray")

        summary = (
            f"Total Line Items:     {totals['line_items']}\n"
            f"Total Parts/Camera:   {totals['total_parts']}\n"
            f"Make Items:           {totals['make_items']}\n"
            f"Buy Items:            {totals['buy_items']}\n\n"
            f"Estimated Cost per Camera:\n"
            f"  Qty 1:    ${totals['total_qty1']:>8.2f}\n"
            f"  Qty 25:   ${totals['total_qty25']:>8.2f}\n"
            f"  Qty 100:  ${totals['total_qty100']:>8.2f}\n\n"
            f"Cost Reduction (1→100):  "
            f"{(1 - totals['total_qty100'] / totals['total_qty1']) * 100:.0f}%"
        )
        ax.text(0.1, 0.78, summary, va="top", fontsize=11,
                fontfamily="monospace")

        pdf.savefig(fig)
        plt.close(fig)

        # ---- Pages 2+: Detail table (chunked to fit pages) ----
        cols = ["#", "Part No.", "Part Name", "Material", "Qty", "M/B",
                "$1", "$25", "$100", "Lead"]
        chunk_size = 30

        for start in range(0, len(bom), chunk_size):
            chunk = bom[start:start + chunk_size]

            table_data = []
            for item in chunk:
                table_data.append([
                    str(item.item_num),
                    item.part_number,
                    item.part_name[:32],
                    item.material[:16],
                    str(item.qty),
                    item.make_buy[0],
                    f"${item.cost_qty1:.2f}",
                    f"${item.cost_qty25:.2f}",
                    f"${item.cost_qty100:.2f}",
                    item.lead_time[:12],
                ])

            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis("off")

            table = ax.table(
                cellText=table_data,
                colLabels=cols,
                cellLoc="center",
                loc="upper center",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(7)
            table.scale(1.0, 1.3)

            # Header styling
            for j in range(len(cols)):
                cell = table[0, j]
                cell.set_facecolor("#2c3e50")
                cell.set_text_props(color="white", fontweight="bold")

            # Alternating row colors
            for i in range(1, len(table_data) + 1):
                for j in range(len(cols)):
                    if i % 2 == 0:
                        table[i, j].set_facecolor("#ecf0f1")

            page_num = start // chunk_size + 2
            ax.set_title(f"Bill of Materials — Detail (page {page_num})",
                         fontsize=10, pad=20)

            pdf.savefig(fig)
            plt.close(fig)

        # ---- Final page: Totals ----
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")

        totals_table = [
            ["", "", "TOTALS", "", str(totals["total_parts"]),
             f"{totals['make_items']}M/{totals['buy_items']}B",
             f"${totals['total_qty1']:.2f}",
             f"${totals['total_qty25']:.2f}",
             f"${totals['total_qty100']:.2f}", ""],
        ]
        table = ax.table(
            cellText=totals_table,
            colLabels=cols,
            cellLoc="center",
            loc="upper center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.0, 1.5)

        for j in range(len(cols)):
            table[0, j].set_facecolor("#2c3e50")
            table[0, j].set_text_props(color="white", fontweight="bold")
            table[1, j].set_facecolor("#f39c12")
            table[1, j].set_text_props(fontweight="bold")

        pdf.savefig(fig)
        plt.close(fig)

    print(f"  Exported: {filepath} (BOM PDF)")
    return filepath


# =========================================================================
# CONSOLE REPORT
# =========================================================================

def print_bom_report():
    """Print a formatted BOM report to console."""
    bom = generate_bom()
    totals = compute_totals(bom)

    sep = "=" * 100
    print(sep)
    print("  SUPER 8 CAMERA — BILL OF MATERIALS")
    print(sep)
    print()

    # Header
    print(f"{'#':>3}  {'Part No.':<10} {'Part Name':<34} {'Material':<16} "
          f"{'Qty':>3} {'M/B':<4} {'$1':>8} {'$25':>8} {'$100':>8}")
    print("-" * 100)

    # Current section tracking
    prev_series = ""
    for item in bom:
        series = item.part_number[:5]
        if series != prev_series:
            if series.startswith("S8C-1"):
                print("\n  --- MECHANICAL PARTS (S8C-100) ---")
            elif series.startswith("S8C-2"):
                print("\n  --- ELECTRONICS (S8C-200) ---")
            elif series.startswith("S8C-3"):
                print("\n  --- FASTENERS (S8C-300) ---")
            elif series.startswith("S8C-4"):
                print("\n  --- PURCHASED PARTS (S8C-400) ---")
            prev_series = series

        print(f"{item.item_num:>3}  {item.part_number:<10} "
              f"{item.part_name:<34} {item.material:<16} "
              f"{item.qty:>3} {item.make_buy:<4} "
              f"${item.cost_qty1:>7.2f} ${item.cost_qty25:>7.2f} "
              f"${item.cost_qty100:>7.2f}")

    print("-" * 100)
    print(f"     {'':10} {'TOTAL':<34} {'':16} "
          f"{totals['total_parts']:>3} {'':4} "
          f"${totals['total_qty1']:>7.2f} ${totals['total_qty25']:>7.2f} "
          f"${totals['total_qty100']:>7.2f}")
    print()
    print(f"  Line items: {totals['line_items']}  |  "
          f"Make: {totals['make_items']}  |  Buy: {totals['buy_items']}  |  "
          f"Cost reduction (1→100): "
          f"{(1 - totals['total_qty100'] / totals['total_qty1']) * 100:.0f}%")
    print(sep)


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    print_bom_report()
    print()
    export_csv()
    export_pdf()
