#!/usr/bin/env python3
"""Generate JSON data files for the Super 8 Camera webapp.

Reads from the super8cam package and exports all data structures
as JSON files in webapp/src/data/.

Usage:
    cd Super-8-Camera
    python webapp/generate_data.py
"""

import json
import os
import sys
import shutil

# Add project root to path so we can import super8cam
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "data")
EXPORT_DIR = os.path.join(project_root, "export")
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", "models")


def copy_stl_files():
    """Copy STL files from export/ to webapp/public/models/."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    stl_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith(".stl")]
    for f in stl_files:
        shutil.copy2(os.path.join(EXPORT_DIR, f), os.path.join(MODELS_DIR, f))
    print(f"  Copied {len(stl_files)} STL files to webapp/public/models/")


def generate_modules_json():
    """Export module definitions."""
    from super8cam.specs.modularity import MODULES
    data = {}
    for mod_id, mod in MODULES.items():
        data[mod_id] = {
            "moduleId": mod.module_id,
            "name": mod.name.replace("_", " ").title(),
            "partsIncluded": mod.parts_included,
            "interfaceType": mod.interface_type,
            "connectsTo": mod.connects_to,
            "repairLevel": mod.repair_level,
            "repairLevelName": {1: "User", 2: "Technician", 3: "Factory"}[mod.repair_level],
            "swapTimeSeconds": mod.swap_time_seconds,
            "toolsRequired": mod.tools_required,
            "printableParts": mod.printable_parts,
            "precisionParts": mod.precision_parts,
        }
    write_json("modules_generated.json", data)


def generate_parts_json():
    """Export part catalog."""
    from super8cam.specs.modularity import PART_CATALOG
    data = {}
    for pn, part in PART_CATALOG.items():
        data[pn] = {
            "partNumber": part.part_number,
            "name": part.name,
            "module": part.module,
            "material": part.material,
            "isPrintable": part.is_printable,
            "isWearItem": part.is_wear_item,
            "replacementInterval": part.replacement_interval_cartridges,
            "estimatedCost": part.estimated_cost,
            "repairLevel": part.repair_level,
            "procedure": part.replacement_procedure,
        }
    write_json("parts_generated.json", data)


def generate_store_json():
    """Export store catalog."""
    from super8cam.business.store_catalog import STORE_CATALOG
    data = []
    for sku, product in STORE_CATALOG.items():
        data.append({
            "sku": product.sku,
            "name": product.name,
            "price": product.price_usd,
            "category": product.category,
            "weight": f"{product.weight_g:.0f}g",
            "description": product.description,
            "tags": product.tags,
            "inStock": product.in_stock,
            "leadTime": product.lead_time_days,
        })
    write_json("store_generated.json", data)


def generate_specs_json():
    """Export key specifications."""
    from super8cam.specs.master_specs import (
        FILM, CMOUNT, CAMERA, MOTOR, GEARBOX, BATTERY, SHUTTER, TOL, PCB, DERIVED
    )
    data = {
        "film": {
            "frameSize": f"{FILM.frame_w} x {FILM.frame_h} mm",
            "perfPitch": f"{FILM.perf_pitch} mm",
            "filmWidth": f"{FILM.width} mm",
        },
        "lens": {
            "threadDiameter": f"{CMOUNT.thread_od} mm",
            "flangeFocalDist": f"{CMOUNT.flange_focal_dist} mm",
        },
        "body": {
            "envelope": f"{CAMERA.body_length} x {CAMERA.body_height} x {CAMERA.body_depth} mm",
            "wallThickness": f"{CAMERA.wall_thickness} mm",
            "estWeight": f"~{DERIVED.total_weight_g:.0f} g",
        },
        "shutter": {
            "openingAngle": f"{CAMERA.shutter_opening_angle} degrees",
            "speed18fps": f"1/{SHUTTER.exposure_reciprocal(18):.0f} s",
            "speed24fps": f"1/{SHUTTER.exposure_reciprocal(24):.0f} s",
        },
        "motor": {
            "model": MOTOR.model,
            "voltage": f"{MOTOR.nominal_voltage} V",
            "noLoadRpm": MOTOR.no_load_rpm,
        },
        "gearbox": {
            "ratio": f"{GEARBOX.ratio}:1",
            "stages": GEARBOX.stages,
        },
        "battery": {
            "type": f"{BATTERY.cell_count}x{BATTERY.cell_type}",
            "voltage": f"{BATTERY.pack_voltage_nom} V",
            "runtime": f"~{DERIVED.battery_life_24fps_min:.0f} min @ 24fps",
        },
    }
    write_json("specs_generated.json", data)


def write_json(filename, data):
    """Write a JSON file to the data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Generated: {filename}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n  Super 8 Camera — Webapp Data Generator")
    print("  " + "=" * 45)

    # Copy STL models
    print("\n  Copying STL files...")
    copy_stl_files()

    # Try to import super8cam for generated data
    try:
        print("\n  Generating JSON from super8cam package...")
        generate_modules_json()
        generate_parts_json()
        generate_store_json()
        generate_specs_json()
        print("\n  All generated files written successfully.")
    except ImportError as e:
        print(f"\n  Note: Could not import super8cam ({e})")
        print("  Using pre-built JSON data files instead.")
        print("  (Install super8cam to regenerate: pip install -e .)")

    print("\n  Done! Run 'npm run dev' to start the webapp.\n")


if __name__ == "__main__":
    main()
