"""store_catalog.py — Complete product catalog for a Shopify-style spare parts store.

Defines every product listing with SKU, pricing, descriptions, compatibility,
and shipping data.  Generates:
  - Formatted console catalog
  - Shopify-compatible CSV for product import
  - Per-SKU margin analysis

Usage:
    conda run -n super8 python -m super8cam.business.store_catalog
    conda run -n super8 python -m super8cam.business.store_catalog --csv export/shopify_products.csv
    conda run -n super8 python -m super8cam.business.store_catalog --margins
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from super8cam.specs.interface_standard import INTERFACE_VERSION


# =========================================================================
# PRODUCT LISTING
# =========================================================================

@dataclass
class ProductListing:
    """A single product in the spare parts store."""
    sku: str
    name: str
    description: str
    price_usd: float
    category: str
    weight_g: float
    dimensions_mm: Tuple[float, float, float]   # (L, W, H)
    compatible_versions: List[str]
    images: List[str]
    install_guide_url: str
    qr_code_url: str
    in_stock: bool
    lead_time_days: int
    tags: List[str]
    cost_usd: float = 0.0  # internal cost for margin calc


BASE_URL = "https://super8camera.com"
PARTS_URL = f"{BASE_URL}/parts"
GUIDE_URL = f"{BASE_URL}/repair-guide"

V1 = [INTERFACE_VERSION]


# =========================================================================
# PRODUCT CATALOG
# =========================================================================

STORE_CATALOG: Dict[str, ProductListing] = {

    # ----- INDIVIDUAL PARTS (Precision) ------------------------------------

    "S8C-101": ProductListing(
        sku="S8C-101",
        name="Film Gate (Brass, CNC)",
        description=(
            "CNC-machined brass C360 film gate with precision aperture "
            "(5.79 x 4.01 mm), registration pin bore, and guide rails. "
            "Replace when frame edges show scratching or uneven exposure. "
            "Compatible with all v1.x camera chassis."
        ),
        price_usd=45.00,
        category="Precision Parts",
        weight_g=18.0,
        dimensions_mm=(24.0, 20.0, 4.0),
        compatible_versions=V1,
        images=["s8c-101_front.jpg", "s8c-101_rear.jpg", "s8c-101_installed.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-101",
        qr_code_url=f"{PARTS_URL}/S8C-101",
        in_stock=True,
        lead_time_days=3,
        tags=["film gate", "brass", "cnc", "precision", "aperture", "wear item"],
        cost_usd=12.00,
    ),

    "S8C-102": ProductListing(
        sku="S8C-102",
        name="Pressure Plate (Spring Steel)",
        description=(
            "Spring-tempered 302 stainless steel pressure plate. Maintains "
            "0.5 N film contact force for sharp focus. Replace when plate "
            "shows wear marks or film isn't lying flat."
        ),
        price_usd=18.00,
        category="Precision Parts",
        weight_g=3.5,
        dimensions_mm=(22.0, 14.0, 1.0),
        compatible_versions=V1,
        images=["s8c-102_top.jpg", "s8c-102_profile.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-102",
        qr_code_url=f"{PARTS_URL}/S8C-102",
        in_stock=True,
        lead_time_days=3,
        tags=["pressure plate", "spring steel", "film plane", "focus", "wear item"],
        cost_usd=3.50,
    ),

    "S8C-103": ProductListing(
        sku="S8C-103",
        name="Claw Tip (Hardened Steel)",
        description=(
            "Hardened 4140 steel claw tip for the pulldown mechanism. "
            "Engages film perforations with 4.234 mm stroke. Replace if "
            "perforations show tearing or pulldown becomes inconsistent."
        ),
        price_usd=5.00,
        category="Precision Parts",
        weight_g=0.8,
        dimensions_mm=(16.5, 3.0, 1.0),
        compatible_versions=V1,
        images=["s8c-103_detail.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-103",
        qr_code_url=f"{PARTS_URL}/S8C-103",
        in_stock=True,
        lead_time_days=3,
        tags=["claw", "pulldown", "hardened steel", "film transport", "wear item"],
        cost_usd=1.50,
    ),

    "S8C-104": ProductListing(
        sku="S8C-104",
        name="Registration Pin (Steel)",
        description=(
            "Precision-ground 4140 steel registration pin, 0.813 mm diameter "
            "(+0/-0.002 mm). Press-fit into film gate. Replace if frame "
            "registration jitter exceeds 0.025 mm."
        ),
        price_usd=3.00,
        category="Precision Parts",
        weight_g=0.2,
        dimensions_mm=(0.8, 0.8, 3.5),
        compatible_versions=V1,
        images=["s8c-104_macro.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-104",
        qr_code_url=f"{PARTS_URL}/S8C-104",
        in_stock=True,
        lead_time_days=3,
        tags=["registration pin", "precision", "film gate", "alignment"],
        cost_usd=0.50,
    ),

    "S8C-201": ProductListing(
        sku="S8C-201",
        name="Shutter Disc 180 deg (Aluminum, Anodized)",
        description=(
            "Black-anodized 6061-T6 aluminum shutter disc, 28 mm OD, 0.8 mm "
            "thick, 180-degree opening angle. Standard exposure: 1/36 s at "
            "18 fps, 1/48 s at 24 fps. Balanced and deburred."
        ),
        price_usd=15.00,
        category="Precision Parts",
        weight_g=2.5,
        dimensions_mm=(28.0, 28.0, 0.8),
        compatible_versions=V1,
        images=["s8c-201_front.jpg", "s8c-201_installed.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-201",
        qr_code_url=f"{PARTS_URL}/S8C-201",
        in_stock=True,
        lead_time_days=5,
        tags=["shutter", "180 degree", "aluminum", "anodized", "standard"],
        cost_usd=4.00,
    ),

    "S8C-201-135": ProductListing(
        sku="S8C-201-135",
        name="Shutter Disc 135 deg (Aluminum, Anodized)",
        description=(
            "135-degree opening shutter disc for longer exposures and "
            "increased motion blur. Exposure: 1/48 s at 18 fps. "
            "Same mounting as standard 180-degree disc."
        ),
        price_usd=15.00,
        category="Precision Parts",
        weight_g=2.8,
        dimensions_mm=(28.0, 28.0, 0.8),
        compatible_versions=V1,
        images=["s8c-201-135_front.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-201",
        qr_code_url=f"{PARTS_URL}/S8C-201-135",
        in_stock=True,
        lead_time_days=5,
        tags=["shutter", "135 degree", "long exposure", "motion blur"],
        cost_usd=4.00,
    ),

    "S8C-201-220": ProductListing(
        sku="S8C-201-220",
        name="Shutter Disc 220 deg (Aluminum, Anodized)",
        description=(
            "220-degree opening shutter disc for shorter exposures and "
            "reduced motion blur. Popular for sports and action. "
            "Exposure: 1/29 s at 18 fps."
        ),
        price_usd=15.00,
        category="Precision Parts",
        weight_g=2.2,
        dimensions_mm=(28.0, 28.0, 0.8),
        compatible_versions=V1,
        images=["s8c-201-220_front.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-201",
        qr_code_url=f"{PARTS_URL}/S8C-201-220",
        in_stock=True,
        lead_time_days=5,
        tags=["shutter", "220 degree", "short exposure", "sports", "action"],
        cost_usd=4.00,
    ),

    "S8C-301": ProductListing(
        sku="S8C-301",
        name="Motor Pre-wired (Mabuchi FF-130SH + JST)",
        description=(
            "Mabuchi FF-130SH DC motor, 6V nominal, 9600 RPM no-load, "
            "pre-wired with 150 mm leads and JST VH 2-pin connector (J1). "
            "Plug-and-play replacement — no soldering required."
        ),
        price_usd=8.00,
        category="Precision Parts",
        weight_g=18.0,
        dimensions_mm=(25.0, 20.0, 15.0),
        compatible_versions=V1,
        images=["s8c-301_motor.jpg", "s8c-301_connector.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-301",
        qr_code_url=f"{PARTS_URL}/S8C-301",
        in_stock=True,
        lead_time_days=3,
        tags=["motor", "mabuchi", "ff-130sh", "pre-wired", "jst", "drivetrain"],
        cost_usd=2.50,
    ),

    "S8C-302": ProductListing(
        sku="S8C-302",
        name="Gear Set (4 Delrin Gears)",
        description=(
            "Complete 2-stage spur gear set in Delrin 150 (acetal). "
            "Stage 1: 12T pinion + 36T gear. Stage 2: 14T pinion + 28T gear. "
            "6:1 total reduction. Replace if teeth show visible wear or "
            "camera speed becomes inconsistent."
        ),
        price_usd=12.00,
        category="Precision Parts",
        weight_g=8.0,
        dimensions_mm=(25.0, 25.0, 10.0),
        compatible_versions=V1,
        images=["s8c-302_set.jpg", "s8c-302_installed.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-302",
        qr_code_url=f"{PARTS_URL}/S8C-302",
        in_stock=True,
        lead_time_days=5,
        tags=["gears", "delrin", "acetal", "spur gear", "drivetrain", "wear item"],
        cost_usd=3.00,
    ),

    "S8C-302M": ProductListing(
        sku="S8C-302M",
        name="Metal Gear Set Upgrade (4 CNC Steel Gears)",
        description=(
            "Premium CNC-machined 4140 steel gear set. Drop-in replacement "
            "for the standard Delrin gears. Virtually zero wear — lifetime "
            "upgrade. Slightly louder than Delrin but indestructible."
        ),
        price_usd=25.00,
        category="Precision Parts",
        weight_g=35.0,
        dimensions_mm=(25.0, 25.0, 10.0),
        compatible_versions=V1,
        images=["s8c-302m_set.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-302",
        qr_code_url=f"{PARTS_URL}/S8C-302M",
        in_stock=True,
        lead_time_days=10,
        tags=["gears", "steel", "cnc", "upgrade", "metal", "lifetime"],
        cost_usd=8.00,
    ),

    "S8C-501": ProductListing(
        sku="S8C-501",
        name="Main PCB (Assembled, Firmware Flashed)",
        description=(
            "Fully assembled and tested main control board. STM32L031K6 "
            "microcontroller with motor driver, encoder input, metering, "
            "and all 7 JST connectors populated. Firmware pre-flashed. "
            "All connectors keyed to prevent cross-connection."
        ),
        price_usd=25.00,
        category="Electronics",
        weight_g=12.0,
        dimensions_mm=(55.0, 35.0, 8.0),
        compatible_versions=V1,
        images=["s8c-501_top.jpg", "s8c-501_bottom.jpg", "s8c-501_connectors.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-501",
        qr_code_url=f"{PARTS_URL}/S8C-501",
        in_stock=True,
        lead_time_days=7,
        tags=["pcb", "electronics", "control board", "stm32", "assembled", "firmware"],
        cost_usd=8.00,
    ),

    "S8C-502": ProductListing(
        sku="S8C-502",
        name="Power Board (Assembled)",
        description=(
            "Power regulation board with reverse-polarity protection, "
            "battery voltage sensing, and thermal shutdown. Connects to "
            "main PCB via J3 (4-pin JST XH)."
        ),
        price_usd=10.00,
        category="Electronics",
        weight_g=5.0,
        dimensions_mm=(30.0, 20.0, 6.0),
        compatible_versions=V1,
        images=["s8c-502_board.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-502",
        qr_code_url=f"{PARTS_URL}/S8C-502",
        in_stock=True,
        lead_time_days=7,
        tags=["power", "regulator", "battery", "electronics"],
        cost_usd=3.50,
    ),

    "S8C-503": ProductListing(
        sku="S8C-503",
        name="Wiring Harness (Complete, 7 JST Connectors)",
        description=(
            "Complete wire harness with all 7 JST connectors (J1-J7) "
            "pre-crimped and labeled. Color-coded per interface standard. "
            "150 mm lead lengths with strain relief boots. "
            "Plug-and-play — no crimping tools needed."
        ),
        price_usd=15.00,
        category="Electronics",
        weight_g=25.0,
        dimensions_mm=(160.0, 80.0, 15.0),
        compatible_versions=V1,
        images=["s8c-503_harness.jpg", "s8c-503_connectors.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-503",
        qr_code_url=f"{PARTS_URL}/S8C-503",
        in_stock=True,
        lead_time_days=5,
        tags=["wiring", "harness", "jst", "connectors", "cables", "complete"],
        cost_usd=5.00,
    ),

    "S8C-701": ProductListing(
        sku="S8C-701",
        name="C-mount Lens Ring (Aluminum)",
        description=(
            "6061-T6 aluminum C-mount lens ring with 25.4 mm bore, "
            "32 TPI threads, and 17.526 mm flange focal distance. "
            "Accepts any standard C-mount lens. Replace if threads "
            "are stripped or cross-threaded."
        ),
        price_usd=12.00,
        category="Precision Parts",
        weight_g=10.0,
        dimensions_mm=(30.0, 30.0, 7.5),
        compatible_versions=V1,
        images=["s8c-701_front.jpg", "s8c-701_threaded.jpg"],
        install_guide_url=f"{GUIDE_URL}#s8c-701",
        qr_code_url=f"{PARTS_URL}/S8C-701",
        in_stock=True,
        lead_time_days=5,
        tags=["lens mount", "c-mount", "aluminum", "threads", "optics"],
        cost_usd=4.00,
    ),

    "S8C-BEARING-4PK": ProductListing(
        sku="S8C-BEARING-4PK",
        name="Bearing Kit (4x 694ZZ)",
        description=(
            "Four 694ZZ miniature bearings (4 mm bore, 11 mm OD, 4 mm width). "
            "Two for the main shaft, one for the shutter shaft support, "
            "one spare. Shielded, pre-lubricated, rated to 36,000 RPM."
        ),
        price_usd=3.00,
        category="Hardware Kits",
        weight_g=12.0,
        dimensions_mm=(50.0, 30.0, 10.0),
        compatible_versions=V1,
        images=["s8c-bearing_kit.jpg"],
        install_guide_url=f"{GUIDE_URL}#bearings",
        qr_code_url=f"{PARTS_URL}/S8C-BEARING-4PK",
        in_stock=True,
        lead_time_days=3,
        tags=["bearings", "694zz", "miniature", "shielded", "shaft"],
        cost_usd=1.00,
    ),

    # ----- KITS ------------------------------------------------------------

    "S8C-FASTENER-KIT": ProductListing(
        sku="S8C-FASTENER-KIT",
        name="Complete Fastener Set",
        description=(
            "Every screw, nut, and insert needed for one complete camera: "
            "M2x5, M2x8, M2.5x6, M3x8 socket head cap screws, "
            "1/4-20 helicoil insert, M3 thumb screws, M3 hex nuts, "
            "and e-clips. Sorted in a labeled compartment box."
        ),
        price_usd=5.00,
        category="Hardware Kits",
        weight_g=30.0,
        dimensions_mm=(80.0, 50.0, 15.0),
        compatible_versions=V1,
        images=["s8c-fastener_kit.jpg"],
        install_guide_url=f"{GUIDE_URL}#fasteners",
        qr_code_url=f"{PARTS_URL}/S8C-FASTENER-KIT",
        in_stock=True,
        lead_time_days=3,
        tags=["fasteners", "screws", "nuts", "helicoil", "hardware", "complete"],
        cost_usd=1.50,
    ),

    "S8C-MAINT-KIT": ProductListing(
        sku="S8C-MAINT-KIT",
        name="Maintenance Kit",
        description=(
            "Essential wear items for regular camera maintenance: "
            "1x pressure plate (S8C-102), 1x claw tip (S8C-103), "
            "4x 694ZZ bearings, 1x microfiber lens cloth, "
            "1x tube of Superlube grease. Everything for a 500-cartridge "
            "service interval."
        ),
        price_usd=28.00,
        category="Hardware Kits",
        weight_g=45.0,
        dimensions_mm=(100.0, 60.0, 25.0),
        compatible_versions=V1,
        images=["s8c-maint_kit.jpg", "s8c-maint_contents.jpg"],
        install_guide_url=f"{GUIDE_URL}#maintenance",
        qr_code_url=f"{PARTS_URL}/S8C-MAINT-KIT",
        in_stock=True,
        lead_time_days=3,
        tags=["maintenance", "service", "wear items", "kit", "bearings", "grease"],
        cost_usd=10.00,
    ),

    "S8C-PRINT-KIT": ProductListing(
        sku="S8C-PRINT-KIT",
        name="Printable Parts Filament Kit",
        description=(
            "1 kg spool of PETG filament (black) optimized for camera parts, "
            "plus a printed settings card with layer heights, infill %, "
            "and support settings for each of the 10 printable parts. "
            "Enough filament for 3+ complete shell sets."
        ),
        price_usd=25.00,
        category="Hardware Kits",
        weight_g=1050.0,
        dimensions_mm=(200.0, 200.0, 80.0),
        compatible_versions=V1,
        images=["s8c-print_kit.jpg", "s8c-print_card.jpg"],
        install_guide_url=f"{GUIDE_URL}#printing",
        qr_code_url=f"{PARTS_URL}/S8C-PRINT-KIT",
        in_stock=True,
        lead_time_days=5,
        tags=["filament", "petg", "3d printing", "fdm", "printable", "diy"],
        cost_usd=12.00,
    ),

    # ----- COMPLETE MODULES ------------------------------------------------

    "S8C-MOD100": ProductListing(
        sku="S8C-MOD100",
        name="Film Transport Module (Pre-assembled)",
        description=(
            "Complete MOD-100 Film Transport module: film gate, pressure plate, "
            "claw mechanism, cam follower, film channel, and registration pin — "
            "fully assembled, aligned, and tested. Drop-in replacement via "
            "2 thumb screws. 2-minute swap, technician level."
        ),
        price_usd=65.00,
        category="Complete Modules",
        weight_g=45.0,
        dimensions_mm=(35.0, 35.0, 20.0),
        compatible_versions=V1,
        images=["s8c-mod100_assembled.jpg", "s8c-mod100_exploded.jpg"],
        install_guide_url=f"{GUIDE_URL}#mod-100",
        qr_code_url=f"{PARTS_URL}/S8C-MOD100",
        in_stock=True,
        lead_time_days=10,
        tags=["module", "film transport", "assembled", "drop-in", "mod-100"],
        cost_usd=22.00,
    ),

    "S8C-MOD200": ProductListing(
        sku="S8C-MOD200",
        name="Shutter Module (Pre-assembled)",
        description=(
            "Complete MOD-200 Shutter module: 180-degree shutter disc "
            "pre-mounted on main shaft with bearings installed. "
            "Drop-in replacement, 90-second swap."
        ),
        price_usd=35.00,
        category="Complete Modules",
        weight_g=25.0,
        dimensions_mm=(30.0, 30.0, 40.0),
        compatible_versions=V1,
        images=["s8c-mod200_assembled.jpg"],
        install_guide_url=f"{GUIDE_URL}#mod-200",
        qr_code_url=f"{PARTS_URL}/S8C-MOD200",
        in_stock=True,
        lead_time_days=10,
        tags=["module", "shutter", "assembled", "drop-in", "mod-200"],
        cost_usd=12.00,
    ),

    "S8C-MOD300": ProductListing(
        sku="S8C-MOD300",
        name="Drivetrain Module (Pre-assembled)",
        description=(
            "Complete MOD-300 Drivetrain: motor mount with Mabuchi FF-130SH, "
            "gearbox housing, 4-gear Delrin gear set — assembled and "
            "lubricated. JST VH connector for plug-and-play. 3-minute swap."
        ),
        price_usd=30.00,
        category="Complete Modules",
        weight_g=55.0,
        dimensions_mm=(65.0, 35.0, 30.0),
        compatible_versions=V1,
        images=["s8c-mod300_assembled.jpg", "s8c-mod300_cutaway.jpg"],
        install_guide_url=f"{GUIDE_URL}#mod-300",
        qr_code_url=f"{PARTS_URL}/S8C-MOD300",
        in_stock=True,
        lead_time_days=10,
        tags=["module", "drivetrain", "motor", "gearbox", "assembled", "mod-300"],
        cost_usd=10.00,
    ),

    "S8C-MOD500": ProductListing(
        sku="S8C-MOD500",
        name="Electronics Module (Pre-assembled)",
        description=(
            "Complete MOD-500 Electronics: main PCB + power board + "
            "PCB bracket, firmware flashed and tested. All 7 JST "
            "connectors populated. 60-second swap."
        ),
        price_usd=45.00,
        category="Complete Modules",
        weight_g=30.0,
        dimensions_mm=(60.0, 40.0, 15.0),
        compatible_versions=V1,
        images=["s8c-mod500_assembled.jpg"],
        install_guide_url=f"{GUIDE_URL}#mod-500",
        qr_code_url=f"{PARTS_URL}/S8C-MOD500",
        in_stock=True,
        lead_time_days=10,
        tags=["module", "electronics", "pcb", "assembled", "mod-500"],
        cost_usd=15.00,
    ),

    "S8C-MOD700": ProductListing(
        sku="S8C-MOD700",
        name="Optics Module (with 6mm f/1.4 Lens)",
        description=(
            "Complete MOD-700 Optics: C-mount lens ring + viewfinder + "
            "6mm f/1.4 C-mount lens. Dovetail mount for tool-free "
            "20-second swap. User-serviceable."
        ),
        price_usd=50.00,
        category="Complete Modules",
        weight_g=65.0,
        dimensions_mm=(40.0, 40.0, 45.0),
        compatible_versions=V1,
        images=["s8c-mod700_assembled.jpg", "s8c-mod700_lens.jpg"],
        install_guide_url=f"{GUIDE_URL}#mod-700",
        qr_code_url=f"{PARTS_URL}/S8C-MOD700",
        in_stock=True,
        lead_time_days=10,
        tags=["module", "optics", "lens", "viewfinder", "c-mount", "mod-700"],
        cost_usd=20.00,
    ),

    # ----- COMPLETE CAMERA -------------------------------------------------

    "S8C-KIT-FULL": ProductListing(
        sku="S8C-KIT-FULL",
        name="Builder Kit (Chassis + Precision Parts + PCBs + Hardware)",
        description=(
            "Everything you need except the shell: CNC aluminum chassis, "
            "all precision parts, main PCB and power board, complete wiring "
            "harness, fastener set, bearings, and assembly manual. "
            "You 3D-print the body shells, doors, and printable parts. "
            "Build your own Super 8 camera from scratch."
        ),
        price_usd=249.00,
        category="Full Camera",
        weight_g=380.0,
        dimensions_mm=(200.0, 150.0, 80.0),
        compatible_versions=V1,
        images=["s8c-kit_box.jpg", "s8c-kit_contents.jpg", "s8c-kit_manual.jpg"],
        install_guide_url=f"{GUIDE_URL}#builder-kit",
        qr_code_url=f"{PARTS_URL}/S8C-KIT-FULL",
        in_stock=True,
        lead_time_days=14,
        tags=["kit", "builder", "diy", "complete", "chassis", "assembly"],
        cost_usd=95.00,
    ),

    "S8C-CAMERA": ProductListing(
        sku="S8C-CAMERA",
        name="Complete Camera (Assembled and Tested)",
        description=(
            "Fully assembled, calibrated, and test-fired Super 8 camera. "
            "Includes 6mm f/1.4 C-mount lens, 4x AA batteries, padded "
            "wrist strap, and quick-start guide. Ready to shoot. "
            "Every part is individually replaceable."
        ),
        price_usd=599.00,
        category="Full Camera",
        weight_g=691.0,
        dimensions_mm=(145.0, 90.0, 60.0),
        compatible_versions=V1,
        images=["s8c-camera_hero.jpg", "s8c-camera_side.jpg",
                "s8c-camera_back.jpg", "s8c-camera_film.jpg"],
        install_guide_url=f"{GUIDE_URL}",
        qr_code_url=f"{PARTS_URL}/S8C-CAMERA",
        in_stock=True,
        lead_time_days=21,
        tags=["camera", "complete", "assembled", "super 8", "film camera", "ready to shoot"],
        cost_usd=180.00,
    ),

    "S8C-CAMERA-PRO": ProductListing(
        sku="S8C-CAMERA-PRO",
        name="Complete Camera Pro (+ Spare Parts Kit + Extra Shutters)",
        description=(
            "Everything in the standard camera, plus: maintenance kit "
            "(S8C-MAINT-KIT), 135-degree and 220-degree extra shutter discs, "
            "and a padded carrying case. For serious filmmakers who want "
            "creative control and field serviceability."
        ),
        price_usd=699.00,
        category="Full Camera",
        weight_g=950.0,
        dimensions_mm=(250.0, 200.0, 120.0),
        compatible_versions=V1,
        images=["s8c-camera-pro_box.jpg", "s8c-camera-pro_contents.jpg"],
        install_guide_url=f"{GUIDE_URL}",
        qr_code_url=f"{PARTS_URL}/S8C-CAMERA-PRO",
        in_stock=True,
        lead_time_days=21,
        tags=["camera", "pro", "complete", "spare parts", "shutters", "case", "bundle"],
        cost_usd=230.00,
    ),

    # ----- ACCESSORIES -----------------------------------------------------

    "S8C-SHELL-SET": ProductListing(
        sku="S8C-SHELL-SET",
        name="Shell Set (Body Halves + Top + Bottom + Doors, PETG)",
        description=(
            "Complete exterior shell set: left body half, right body half, "
            "top plate, bottom plate, cartridge door, battery door. "
            "3D printed in PETG. Choose your color at checkout. "
            "Attaches to chassis with M2.5 screws (included)."
        ),
        price_usd=25.00,
        category="Accessories",
        weight_g=120.0,
        dimensions_mm=(150.0, 100.0, 60.0),
        compatible_versions=V1,
        images=["s8c-shell_black.jpg", "s8c-shell_white.jpg", "s8c-shell_red.jpg"],
        install_guide_url=f"{GUIDE_URL}#shell",
        qr_code_url=f"{PARTS_URL}/S8C-SHELL-SET",
        in_stock=True,
        lead_time_days=7,
        tags=["shell", "body", "petg", "3d printed", "color", "exterior", "custom"],
        cost_usd=8.00,
    ),

    "S8C-LENS-6MM": ProductListing(
        sku="S8C-LENS-6MM",
        name="6mm f/1.4 C-mount Lens",
        description=(
            "Wide-angle 6mm f/1.4 C-mount lens with manual iris and focus. "
            "All-glass optics, multi-coated. Ideal for general Super 8 "
            "shooting. Equivalent to ~40mm on 35mm film."
        ),
        price_usd=35.00,
        category="Accessories",
        weight_g=45.0,
        dimensions_mm=(30.0, 30.0, 25.0),
        compatible_versions=V1,
        images=["s8c-lens-6mm.jpg"],
        install_guide_url=f"{GUIDE_URL}#lenses",
        qr_code_url=f"{PARTS_URL}/S8C-LENS-6MM",
        in_stock=True,
        lead_time_days=5,
        tags=["lens", "6mm", "wide angle", "c-mount", "f1.4", "optics"],
        cost_usd=15.00,
    ),

    "S8C-LENS-12MM": ProductListing(
        sku="S8C-LENS-12MM",
        name="12mm f/1.4 C-mount Lens",
        description=(
            "Normal 12mm f/1.4 C-mount lens with manual iris and focus. "
            "All-glass optics, multi-coated. Classic Super 8 focal length. "
            "Equivalent to ~80mm on 35mm film."
        ),
        price_usd=45.00,
        category="Accessories",
        weight_g=55.0,
        dimensions_mm=(30.0, 30.0, 35.0),
        compatible_versions=V1,
        images=["s8c-lens-12mm.jpg"],
        install_guide_url=f"{GUIDE_URL}#lenses",
        qr_code_url=f"{PARTS_URL}/S8C-LENS-12MM",
        in_stock=True,
        lead_time_days=5,
        tags=["lens", "12mm", "normal", "c-mount", "f1.4", "optics", "portrait"],
        cost_usd=20.00,
    ),

    "S8C-GRIP-TPU": ProductListing(
        sku="S8C-GRIP-TPU",
        name="Comfort Grip Overlay (TPU, Textured)",
        description=(
            "Textured TPU (flexible) grip overlay that wraps around the "
            "pistol grip area. Provides cushioned, non-slip handling. "
            "Friction-fit — no adhesive needed, easily removable."
        ),
        price_usd=8.00,
        category="Accessories",
        weight_g=15.0,
        dimensions_mm=(55.0, 30.0, 25.0),
        compatible_versions=V1,
        images=["s8c-grip_tpu.jpg", "s8c-grip_installed.jpg"],
        install_guide_url=f"{GUIDE_URL}#grip",
        qr_code_url=f"{PARTS_URL}/S8C-GRIP-TPU",
        in_stock=True,
        lead_time_days=5,
        tags=["grip", "tpu", "flexible", "comfort", "textured", "ergonomic"],
        cost_usd=3.00,
    ),

    "S8C-CASE": ProductListing(
        sku="S8C-CASE",
        name="Padded Carrying Case",
        description=(
            "Custom-fit padded carrying case with compartments for camera, "
            "2 lenses, extra shutter discs, batteries, and tools. "
            "Splash-resistant exterior, shoulder strap included."
        ),
        price_usd=30.00,
        category="Accessories",
        weight_g=280.0,
        dimensions_mm=(250.0, 180.0, 100.0),
        compatible_versions=V1,
        images=["s8c-case_open.jpg", "s8c-case_closed.jpg"],
        install_guide_url=f"{GUIDE_URL}#accessories",
        qr_code_url=f"{PARTS_URL}/S8C-CASE",
        in_stock=True,
        lead_time_days=7,
        tags=["case", "padded", "carrying", "travel", "protection", "bag"],
        cost_usd=10.00,
    ),

    "S8C-EXPANSION-BLANK": ProductListing(
        sku="S8C-EXPANSION-BLANK",
        name="Expansion Slot Cover Plate",
        description=(
            "Blank cover plate for the expansion module slot. Ships pre-installed "
            "on all cameras. Replace if lost or damaged, or remove to install "
            "a community expansion module (frame counter, Bluetooth, intervalometer, etc.)."
        ),
        price_usd=3.00,
        category="Accessories",
        weight_g=2.0,
        dimensions_mm=(25.0, 15.0, 3.0),
        compatible_versions=V1,
        images=["s8c-expansion-blank.jpg"],
        install_guide_url=f"{GUIDE_URL}#expansion",
        qr_code_url=f"{PARTS_URL}/S8C-EXPANSION-BLANK",
        in_stock=True,
        lead_time_days=3,
        tags=["expansion", "cover", "blank", "slot", "future", "modular"],
        cost_usd=0.50,
    ),
}


# =========================================================================
# OUTPUT FUNCTIONS
# =========================================================================

def print_store_catalog():
    """Print a formatted table of all products."""
    sep = "=" * 95
    print(f"\n{sep}")
    print("  SUPER 8 CAMERA — SPARE PARTS STORE CATALOG")
    print(sep)

    categories = [
        "Precision Parts", "Electronics", "Hardware Kits",
        "Complete Modules", "Full Camera", "Accessories",
    ]

    for cat in categories:
        items = [p for p in STORE_CATALOG.values() if p.category == cat]
        if not items:
            continue

        print(f"\n  {cat.upper()}")
        print(f"  {'─' * 90}")
        fmt = "  {:<18s} {:<42s} {:>7s} {:>7s}  {}"
        print(fmt.format("SKU", "Name", "Price", "Weight", "Stock"))
        print(fmt.format("───", "────", "─────", "──────", "─────"))

        for p in items:
            stock = f"{p.lead_time_days}d" if p.in_stock else "OUT"
            print(fmt.format(
                p.sku,
                p.name[:42],
                f"${p.price_usd:.2f}",
                f"{p.weight_g:.0f}g",
                stock,
            ))

    # Totals
    total_skus = len(STORE_CATALOG)
    total_value = sum(p.price_usd for p in STORE_CATALOG.values())
    print(f"\n  {'─' * 90}")
    print(f"  Total SKUs: {total_skus}")
    print(f"  Total catalog value (1 of each): ${total_value:.2f}")
    print(f"  Interface version: v{INTERFACE_VERSION}")
    print(sep)


def export_shopify_csv(output_path: str = "export/shopify_products.csv"):
    """Export a CSV file compatible with Shopify product import."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    fieldnames = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Product Category",
        "Type", "Tags", "Published", "Option1 Name", "Option1 Value",
        "Variant SKU", "Variant Grams", "Variant Inventory Tracker",
        "Variant Inventory Qty", "Variant Inventory Policy",
        "Variant Fulfillment Service", "Variant Price",
        "Variant Compare At Price", "Variant Requires Shipping",
        "Variant Taxable", "Image Src", "Image Position", "Image Alt Text",
        "SEO Title", "SEO Description", "Status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for p in STORE_CATALOG.values():
            handle = p.sku.lower().replace("_", "-")
            tags = ", ".join(p.tags)
            dims = f"{p.dimensions_mm[0]}x{p.dimensions_mm[1]}x{p.dimensions_mm[2]}mm"
            body_html = (
                f"<p>{p.description}</p>"
                f"<p><strong>Dimensions:</strong> {dims}</p>"
                f"<p><strong>Compatible versions:</strong> "
                f"{', '.join(f'v{v}' for v in p.compatible_versions)}</p>"
                f"<p><a href=\"{p.install_guide_url}\">Installation guide</a></p>"
            )

            row = {
                "Handle": handle,
                "Title": f"{p.sku} — {p.name}",
                "Body (HTML)": body_html,
                "Vendor": "Super 8 Camera Project",
                "Product Category": "Cameras & Optics",
                "Type": p.category,
                "Tags": tags,
                "Published": "TRUE",
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Variant SKU": p.sku,
                "Variant Grams": str(int(p.weight_g)),
                "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": "10" if p.in_stock else "0",
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": f"{p.price_usd:.2f}",
                "Variant Compare At Price": "",
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Image Src": "",
                "Image Position": "1",
                "Image Alt Text": p.name,
                "SEO Title": f"{p.sku} {p.name} — Super 8 Camera",
                "SEO Description": p.description[:160],
                "Status": "active",
            }
            writer.writerow(row)

    print(f"  Shopify CSV exported: {output_path} ({len(STORE_CATALOG)} products)")
    return output_path


def calculate_margin(sku: str) -> Optional[dict]:
    """Calculate cost, price, and margin for a single SKU."""
    product = STORE_CATALOG.get(sku)
    if not product:
        return None

    cost = product.cost_usd
    price = product.price_usd
    margin = price - cost
    margin_pct = (margin / price * 100) if price > 0 else 0

    return {
        "sku": sku,
        "name": product.name,
        "cost": cost,
        "price": price,
        "margin": margin,
        "margin_pct": margin_pct,
    }


def print_all_margins():
    """Print margin analysis for all products."""
    sep = "=" * 85
    print(f"\n{sep}")
    print("  MARGIN ANALYSIS")
    print(sep)

    fmt = "  {:<18s} {:>8s} {:>8s} {:>8s} {:>7s}  {}"
    print(fmt.format("SKU", "Cost", "Price", "Margin", "Pct", "Name"))
    print(fmt.format("───", "────", "─────", "──────", "───", "────"))

    total_cost = 0
    total_revenue = 0

    for sku in STORE_CATALOG:
        m = calculate_margin(sku)
        if m:
            total_cost += m["cost"]
            total_revenue += m["price"]
            print(fmt.format(
                m["sku"],
                f"${m['cost']:.2f}",
                f"${m['price']:.2f}",
                f"${m['margin']:.2f}",
                f"{m['margin_pct']:.0f}%",
                m["name"][:35],
            ))

    total_margin = total_revenue - total_cost
    total_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0
    print(f"\n  {'─' * 80}")
    print(f"  Total (1 of each): cost ${total_cost:.2f}, "
          f"revenue ${total_revenue:.2f}, "
          f"margin ${total_margin:.2f} ({total_pct:.0f}%)")
    print(sep)


# =========================================================================
# CLI
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Super 8 Camera spare parts store catalog")
    parser.add_argument("--csv", nargs="?", const="export/shopify_products.csv",
                        help="Export Shopify CSV (default: export/shopify_products.csv)")
    parser.add_argument("--margins", action="store_true",
                        help="Show margin analysis for all products")
    args = parser.parse_args()

    print_store_catalog()

    if args.margins:
        print_all_margins()

    if args.csv:
        export_shopify_csv(args.csv)


if __name__ == "__main__":
    main()
