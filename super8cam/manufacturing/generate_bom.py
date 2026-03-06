"""Generate a consolidated BOM from master_specs."""

import csv
from super8cam.specs.master_specs import (
    FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE, BEARINGS,
    MOTOR, PCB, BATTERY,
)


def generate_bom():
    """Build full BOM list."""
    bom = []

    # Fasteners
    for usage, (fkey, qty) in FASTENER_USAGE.items():
        f = FASTENERS[fkey]
        bom.append({
            "category": "Fastener",
            "ref": fkey,
            "description": f"{f.thread} x {f.length}mm {f.head_type}",
            "qty": qty,
            "usage": usage,
        })

    # Bearings
    for usage, brg in BEARINGS.items():
        bom.append({
            "category": "Bearing",
            "ref": brg.designation,
            "description": f"{brg.bore}x{brg.od}x{brg.width}mm {brg.seal}",
            "qty": 1,
            "usage": usage,
        })

    # Motor
    bom.append({
        "category": "Motor",
        "ref": MOTOR.model,
        "description": f"DC motor {MOTOR.nominal_voltage}V {MOTOR.body_dia}mm dia",
        "qty": 1,
        "usage": "drivetrain",
    })

    # Materials (stock)
    for usage, mat_key in MATERIAL_USAGE.items():
        mat = MATERIALS[mat_key]
        bom.append({
            "category": "Material",
            "ref": mat.designation,
            "description": f"{mat.name} for {usage}",
            "qty": 1,
            "usage": usage,
        })

    return bom


def export_csv(filepath="export/bom.csv"):
    """Export BOM as CSV."""
    import os
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bom = generate_bom()
    with open(filepath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "ref", "description", "qty", "usage"])
        w.writeheader()
        w.writerows(bom)
    print(f"  Exported: {filepath} ({len(bom)} items)")


if __name__ == "__main__":
    export_csv()
