#!/usr/bin/env python3
"""bom_optimizer.py — BOM Cost Analysis & Optimization for Super 8 Camera PCB

Reads a BOM CSV (reference, value, footprint/package, MPN, description, qty),
looks up component pricing at qty 1 / 25 / 100, flags expensive parts,
suggests cheaper drop-in alternatives, and outputs a cost summary.

Pricing data is hardcoded from realistic 2025 LCSC / DigiKey / Mouser ranges.

Usage:
    python bom_optimizer.py                        # uses super8_camera_bom.csv
    python bom_optimizer.py my_bom.csv             # custom BOM file
    python bom_optimizer.py --output report.txt    # write report to file
"""

import csv
import sys

# =========================================================================
# Pricing Database
#
# Keyed by value (or MPN if more specific).  Each entry:
#   { "prices": (qty1, qty25, qty100),   # USD per unit
#     "alt":    ("alt_value", "alt_mpn", (qty1, qty25, qty100), "note") or None }
# =========================================================================

PRICE_DB = {
    # MCU
    "STM32L031K6T6": {
        "prices": (2.45, 2.10, 1.78),
        "alt": ("STM32L011K4T6", "STM32L011K4T6", (1.60, 1.35, 1.12),
                "16KB Flash variant — sufficient if code fits; pin-compatible"),
    },

    # Motor driver
    "DRV8837": {
        "prices": (1.85, 1.52, 1.20),
        "alt": ("MX1508", "MX1508", (0.35, 0.28, 0.22),
                "Budget dual H-bridge; less current limit precision but works for small DC motors"),
    },

    # Op-amp (TIA)
    "MCP6001": {
        "prices": (0.38, 0.30, 0.22),
        "alt": None,   # already cheap
    },

    # Voltage regulators
    "AMS1117-5.0": {
        "prices": (0.45, 0.32, 0.18),
        "alt": ("HT7550", "HT7550-1", (0.15, 0.10, 0.07),
                "SOT-89, lower quiescent current; pin-compatible with adapter pad"),
    },
    "AMS1117-3.3": {
        "prices": (0.42, 0.30, 0.16),
        "alt": ("HT7333", "HT7333-A", (0.12, 0.08, 0.06),
                "SOT-89, 250mA max — sufficient for STM32L0 + peripherals"),
    },

    # P-FET
    "SI2301": {
        "prices": (0.55, 0.40, 0.28),
        "alt": ("AO3401A", "AO3401A", (0.18, 0.12, 0.08),
                "SOT-23 P-FET, -30V -4A, pin-compatible direct replacement"),
    },

    # Polyfuse
    "500mA": {
        "prices": (0.25, 0.18, 0.12),
        "alt": None,
    },

    # Photodiode
    "BPW34": {
        "prices": (1.20, 0.95, 0.72),
        "alt": ("BPW34S", "BPW34S", (0.85, 0.68, 0.52),
                "SMD version of BPW34 — same specs, easier assembly"),
    },

    # Passives — resistors
    "1M": {
        "prices": (0.02, 0.008, 0.004),
        "alt": None,
    },
    "10K": {
        "prices": (0.02, 0.008, 0.004),
        "alt": None,
    },
    "330": {
        "prices": (0.02, 0.008, 0.004),
        "alt": None,
    },

    # Passives — capacitors
    "100nF": {
        "prices": (0.03, 0.012, 0.006),
        "alt": None,
    },
    "10pF": {
        "prices": (0.03, 0.015, 0.008),
        "alt": None,
    },
    "10uF": {
        "prices": (0.08, 0.05, 0.028),
        "alt": None,
    },

    # LEDs
    "LED_Red": {
        "prices": (0.05, 0.025, 0.012),
        "alt": None,
    },
    "LED_Green": {
        "prices": (0.05, 0.025, 0.012),
        "alt": None,
    },
    "LED_Yellow": {
        "prices": (0.05, 0.025, 0.012),
        "alt": None,
    },

    # Connectors
    "JST_PH_4pin": {
        "prices": (0.35, 0.25, 0.15),
        "alt": None,
    },
    "JST_PH_2pin": {
        "prices": (0.25, 0.18, 0.10),
        "alt": None,
    },
    "ISP_6pin": {
        "prices": (0.30, 0.20, 0.12),
        "alt": None,
    },

    # Switches
    "Trigger": {
        "prices": (0.20, 0.12, 0.08),
        "alt": None,
    },
    "FPS_Toggle": {
        "prices": (0.45, 0.32, 0.20),
        "alt": None,
    },
    "DIP_2pos": {
        "prices": (0.30, 0.20, 0.12),
        "alt": None,
    },
}

# Tier labels
TIERS = ("qty_1", "qty_25", "qty_100")
TIER_LABELS = ("1 unit", "25 units", "100 units")

# Cost flag threshold: warn if a single part is >20% of total BOM
COST_FLAG_THRESHOLD = 0.20


# =========================================================================
# BOM Reader
# =========================================================================

def read_bom(filepath):
    """Read BOM CSV, return list of dicts."""
    parts = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize column names (handle different BOM formats)
            ref = row.get("Reference", row.get("reference", ""))
            value = row.get("Value", row.get("value", ""))
            footprint = row.get("Footprint", row.get("package", row.get("Package", "")))
            mpn = row.get("MPN", row.get("mpn", ""))
            desc = row.get("Description", row.get("description", ""))
            qty = int(row.get("Qty", row.get("qty", row.get("Quantity", row.get("quantity", 1)))))

            parts.append({
                "ref": ref.strip(),
                "value": value.strip(),
                "footprint": footprint.strip(),
                "mpn": mpn.strip(),
                "desc": desc.strip(),
                "qty": qty,
            })
    return parts


def lookup_price(part):
    """Find pricing for a part. Try MPN first, then value. Returns price tuple or None."""
    # Try MPN
    if part["mpn"] and part["mpn"] in PRICE_DB:
        return PRICE_DB[part["mpn"]]

    # Try value
    if part["value"] in PRICE_DB:
        return PRICE_DB[part["value"]]

    return None


# =========================================================================
# Analysis
# =========================================================================

def analyze_bom(parts):
    """Compute per-part and total costs at each tier, flag expensive parts."""

    results = []
    totals = [0.0, 0.0, 0.0]  # one per tier

    for part in parts:
        info = lookup_price(part)
        if info:
            prices = info["prices"]
            alt = info.get("alt")
        else:
            # Unknown part — estimate as generic passive
            prices = (0.10, 0.07, 0.05)
            alt = None

        qty = part["qty"]
        line_costs = tuple(p * qty for p in prices)

        for i in range(3):
            totals[i] += line_costs[i]

        results.append({
            "ref": part["ref"],
            "value": part["value"],
            "mpn": part["mpn"],
            "desc": part["desc"],
            "qty": qty,
            "prices": prices,
            "line_costs": line_costs,
            "alt": alt,
        })

    return results, tuple(totals)


def flag_expensive(results, totals):
    """Return list of parts where any tier exceeds COST_FLAG_THRESHOLD of total."""
    flagged = []
    for r in results:
        for i in range(3):
            if totals[i] > 0 and (r["line_costs"][i] / totals[i]) > COST_FLAG_THRESHOLD:
                pct = r["line_costs"][i] / totals[i] * 100
                flagged.append((r["ref"], r["value"], TIER_LABELS[i], pct))
                break  # one flag per part is enough
    return flagged


# =========================================================================
# Report Output
# =========================================================================

def format_report(results, totals, flagged):
    """Build the full text report."""
    lines = []
    sep = "=" * 72

    lines.append(sep)
    lines.append("  SUPER 8 CAMERA — BOM COST ANALYSIS & OPTIMIZATION")
    lines.append(sep)
    lines.append("")

    # ---- Per-part cost table ----
    lines.append("  {:<8} {:<20} {:>3}  {:>8} {:>8} {:>8}".format(
        "Ref", "Value", "Qty", "@ 1pc", "@ 25pc", "@ 100pc"))
    lines.append("  " + "-" * 64)

    for r in results:
        lines.append("  {:<8} {:<20} {:>3}  ${:>6.3f} ${:>6.3f} ${:>6.3f}".format(
            r["ref"], r["value"][:20], r["qty"],
            r["line_costs"][0], r["line_costs"][1], r["line_costs"][2]))

    lines.append("  " + "-" * 64)
    lines.append("  {:<8} {:<20} {:>3}  ${:>6.2f} ${:>6.2f} ${:>6.2f}".format(
        "TOTAL", "", "", totals[0], totals[1], totals[2]))
    lines.append("")

    # ---- Board-level totals (BOM × board quantity) ----
    lines.append("  TOTAL BOM COST PER BOARD:")
    lines.append("  {:>30}  ${:.2f}".format("Prototype (1 board):", totals[0]))
    lines.append("  {:>30}  ${:.2f}  (save {:.0f}%)".format(
        "Small batch (25 boards):", totals[1],
        (1 - totals[1] / totals[0]) * 100 if totals[0] > 0 else 0))
    lines.append("  {:>30}  ${:.2f}  (save {:.0f}%)".format(
        "Production (100 boards):", totals[2],
        (1 - totals[2] / totals[0]) * 100 if totals[0] > 0 else 0))
    lines.append("")

    # ---- Expensive part warnings ----
    if flagged:
        lines.append("  WARNING: Parts exceeding {:.0f}% of total BOM cost:".format(
            COST_FLAG_THRESHOLD * 100))
        for ref, value, tier, pct in flagged:
            lines.append("    ! {:<8} {:<20} — {:.1f}% of total at {}".format(
                ref, value, pct, tier))
        lines.append("")

    # ---- Drop-in alternatives ----
    alts = [(r["ref"], r["value"], r["alt"]) for r in results if r["alt"]]
    if alts:
        lines.append("  SUGGESTED CHEAPER ALTERNATIVES:")
        lines.append("  " + "-" * 64)
        for ref, orig_val, alt in alts:
            alt_val, alt_mpn, alt_prices, note = alt
            orig_entry = next(r for r in results if r["ref"] == ref)
            savings_1 = orig_entry["prices"][0] - alt_prices[0]
            savings_100 = orig_entry["prices"][2] - alt_prices[2]
            lines.append("")
            lines.append("  {} ({})  →  {} ({})".format(ref, orig_val, alt_val, alt_mpn))
            lines.append("    Price: ${:.2f}/${:.2f}/${:.2f}  (save ${:.2f} @ 1pc, "
                         "${:.2f} @ 100pc)".format(
                             alt_prices[0], alt_prices[1], alt_prices[2],
                             savings_1, savings_100))
            lines.append("    Note: {}".format(note))

        # Total savings if all alternatives adopted
        total_savings = [0.0, 0.0, 0.0]
        for ref, orig_val, alt in alts:
            orig_entry = next(r for r in results if r["ref"] == ref)
            _, _, alt_prices, _ = alt
            for i in range(3):
                total_savings[i] += (orig_entry["prices"][i] - alt_prices[i]) * orig_entry["qty"]

        lines.append("")
        lines.append("  TOTAL SAVINGS IF ALL ALTERNATIVES ADOPTED:")
        lines.append("    @ 1 pc:   -${:.2f}  (new total: ${:.2f})".format(
            total_savings[0], totals[0] - total_savings[0]))
        lines.append("    @ 25 pc:  -${:.2f}  (new total: ${:.2f})".format(
            total_savings[1], totals[1] - total_savings[1]))
        lines.append("    @ 100 pc: -${:.2f}  (new total: ${:.2f})".format(
            total_savings[2], totals[2] - total_savings[2]))
    else:
        lines.append("  No cheaper alternatives found.")

    lines.append("")
    lines.append("  " + sep)
    return "\n".join(lines)


# =========================================================================
# Main
# =========================================================================

def main():
    # Parse arguments
    bom_path = "super8_camera_bom.csv"
    output_path = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            bom_path = args[i]
            i += 1

    # Run analysis
    parts = read_bom(bom_path)
    results, totals = analyze_bom(parts)
    flagged = flag_expensive(results, totals)
    report = format_report(results, totals, flagged)

    print(report)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        print("\n  Report saved to: {}".format(output_path))


if __name__ == "__main__":
    main()
