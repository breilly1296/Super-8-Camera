"""modularity.py — Modular architecture, connectors, and repairability metadata.

Layered ON TOP of existing part designs.  No part geometry is modified.
This file defines how parts group into field-swappable modules, how
modules interconnect electrically, and how every part can be sourced,
printed, or replaced.

    from super8cam.specs.modularity import MODULES, CONNECTORS, PART_CATALOG
    from super8cam.specs.modularity import print_module_map, print_repair_guide

Part numbering:  S8C-1xx
    100-series = Film transport
    200-series = Shutter / optical path
    300-series = Drivetrain
    400-series = Cartridge bay
    500-series = Electronics
    600-series = Power
    700-series = Optics
    800-series = Structure / body
    900-series = Fasteners & hardware
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# =========================================================================
# MODULE DEFINITION
# =========================================================================

@dataclass(frozen=True)
class Module:
    """A field-replaceable module grouping related parts."""

    module_id: str                          # e.g. "MOD-100"
    name: str                               # human-readable
    parts_included: List[str]               # part file basenames (no .py)
    interface_type: str                     # DOVETAIL / THUMBSCREW / SNAP_FIT / JST
    connects_to: List[str]                  # list of module_ids this plugs into
    repair_level: int                       # 1=user, 2=technician, 3=factory
    swap_time_seconds: int                  # estimated module swap time
    tools_required: List[str]               # tools needed to swap
    printable_parts: List[str]              # parts a user can FDM print
    precision_parts: List[str]              # parts needing CNC / grinding


MODULES: Dict[str, Module] = {

    "MOD-100": Module(
        module_id="MOD-100",
        name="FILM_TRANSPORT",
        parts_included=[
            "film_gate", "pressure_plate", "claw_mechanism",
            "cam_follower", "film_channel", "registration_pin",
        ],
        interface_type="THUMBSCREW",
        connects_to=["MOD-200", "MOD-400"],
        repair_level=2,
        swap_time_seconds=120,
        tools_required=["1.5 mm hex key", "tweezers", "loupe (10x)"],
        printable_parts=["film_channel"],
        precision_parts=[
            "film_gate", "pressure_plate", "claw_mechanism",
            "cam_follower", "registration_pin",
        ],
    ),

    "MOD-200": Module(
        module_id="MOD-200",
        name="SHUTTER",
        parts_included=["shutter_disc", "main_shaft"],
        interface_type="THUMBSCREW",
        connects_to=["MOD-100", "MOD-300"],
        repair_level=2,
        swap_time_seconds=90,
        tools_required=["1.5 mm hex key", "shaft alignment jig"],
        printable_parts=[],
        precision_parts=["shutter_disc", "main_shaft"],
    ),

    "MOD-300": Module(
        module_id="MOD-300",
        name="DRIVETRAIN",
        parts_included=[
            "motor_mount", "gearbox_housing", "gears", "main_shaft",
        ],
        interface_type="THUMBSCREW",
        connects_to=["MOD-200", "MOD-500"],
        repair_level=2,
        swap_time_seconds=180,
        tools_required=["2.0 mm hex key", "2.5 mm hex key", "needle-nose pliers"],
        printable_parts=["motor_mount", "gearbox_housing", "gears"],
        precision_parts=["main_shaft"],
    ),

    "MOD-400": Module(
        module_id="MOD-400",
        name="CARTRIDGE_BAY",
        parts_included=["cartridge_receiver", "cartridge_door"],
        interface_type="SNAP_FIT",
        connects_to=["MOD-100"],
        repair_level=1,
        swap_time_seconds=30,
        tools_required=[],
        printable_parts=["cartridge_door"],
        precision_parts=["cartridge_receiver"],
    ),

    "MOD-500": Module(
        module_id="MOD-500",
        name="ELECTRONICS",
        parts_included=["pcb_bracket"],
        interface_type="JST",
        connects_to=["MOD-300", "MOD-600"],
        repair_level=2,
        swap_time_seconds=60,
        tools_required=["#1 Phillips screwdriver"],
        printable_parts=["pcb_bracket"],
        precision_parts=[],
    ),

    "MOD-600": Module(
        module_id="MOD-600",
        name="POWER",
        parts_included=["battery_door", "bottom_plate"],
        interface_type="SNAP_FIT",
        connects_to=["MOD-500"],
        repair_level=1,
        swap_time_seconds=15,
        tools_required=[],
        printable_parts=["battery_door"],
        precision_parts=["bottom_plate"],
    ),

    "MOD-700": Module(
        module_id="MOD-700",
        name="OPTICS",
        parts_included=["lens_mount", "viewfinder"],
        interface_type="DOVETAIL",
        connects_to=["MOD-100"],
        repair_level=1,
        swap_time_seconds=20,
        tools_required=[],
        printable_parts=["viewfinder"],
        precision_parts=["lens_mount"],
    ),
}


# =========================================================================
# CONNECTOR SPECIFICATION
# =========================================================================

@dataclass(frozen=True)
class ConnectorSpec:
    """Electrical connector between two modules.

    Each connector has a unique pin count or JST family so that connectors
    cannot be accidentally swapped.
    """

    connector_id: str
    pin_count: int
    jst_family: str                         # "XH" (2.5 mm) or "VH" (3.96 mm)
    wire_colors: List[str]
    signal_names: List[str]
    from_module: str                        # module_id
    to_module: str                          # module_id
    max_current_ma: float


CONNECTORS: Dict[str, ConnectorSpec] = {

    "J1": ConnectorSpec(
        connector_id="J1",
        pin_count=2,
        jst_family="VH",
        wire_colors=["red", "black"],
        signal_names=["MOTOR+", "MOTOR-"],
        from_module="MOD-500",
        to_module="MOD-300",
        max_current_ma=800.0,
    ),

    "J2": ConnectorSpec(
        connector_id="J2",
        pin_count=3,
        jst_family="XH",
        wire_colors=["orange", "yellow", "brown"],
        signal_names=["ENCODER_A", "ENCODER_B", "ENCODER_GND"],
        from_module="MOD-200",
        to_module="MOD-500",
        max_current_ma=20.0,
    ),

    "J3": ConnectorSpec(
        connector_id="J3",
        pin_count=4,
        jst_family="XH",
        wire_colors=["red", "black", "white", "green"],
        signal_names=["VBATT", "GND", "BATT_SENSE", "THERM"],
        from_module="MOD-600",
        to_module="MOD-500",
        max_current_ma=1200.0,
    ),

    "J4": ConnectorSpec(
        connector_id="J4",
        pin_count=5,
        jst_family="XH",
        wire_colors=["blue", "violet", "grey", "white", "black"],
        signal_names=["FPS_SEL_A", "FPS_SEL_B", "TRIG_SW", "LED_STATUS", "SIG_GND"],
        from_module="MOD-500",
        to_module="MOD-100",
        max_current_ma=50.0,
    ),

    "J5": ConnectorSpec(
        connector_id="J5",
        pin_count=6,
        jst_family="XH",
        wire_colors=["red", "orange", "yellow", "green", "blue", "black"],
        signal_names=["CART_DET", "FILM_END", "DOOR_SW", "NOTCH_SNS", "LAMP_DRV", "DET_GND"],
        from_module="MOD-400",
        to_module="MOD-500",
        max_current_ma=100.0,
    ),

    "J6": ConnectorSpec(
        connector_id="J6",
        pin_count=7,
        jst_family="XH",
        wire_colors=["red", "orange", "yellow", "green", "blue", "violet", "black"],
        signal_names=["SDA", "SCL", "MOSI", "MISO", "SCK", "CS_EXP", "DBUS_GND"],
        from_module="MOD-500",
        to_module="MOD-700",
        max_current_ma=30.0,
    ),

    "J7": ConnectorSpec(
        connector_id="J7",
        pin_count=8,
        jst_family="XH",
        wire_colors=["red", "orange", "yellow", "green", "blue", "violet", "grey", "black"],
        signal_names=[
            "UART_TX", "UART_RX", "I2C_SDA", "I2C_SCL",
            "PWM_LIGHT", "AUX_SENSE", "3V3_OUT", "DBG_GND",
        ],
        from_module="MOD-500",
        to_module="MOD-600",
        max_current_ma=200.0,
    ),
}


# =========================================================================
# PART CATALOG
# =========================================================================

@dataclass(frozen=True)
class PartCatalogEntry:
    """Every physical part in the camera, with sourcing and repair info."""

    part_number: str                        # S8C-1xx scheme
    name: str
    module: str                             # module_id
    material: str                           # material key or description
    is_printable: bool
    print_settings: Dict[str, str]          # empty if not printable
    is_wear_item: bool
    replacement_interval_cartridges: Optional[int]   # None = lifetime
    estimated_cost: float                   # USD
    repair_level: int                       # 1=user, 2=tech, 3=factory
    replacement_procedure: str


PART_CATALOG: Dict[str, PartCatalogEntry] = {

    # ----- MOD-100  FILM TRANSPORT ------------------------------------------

    "S8C-101": PartCatalogEntry(
        part_number="S8C-101",
        name="Film Gate",
        module="MOD-100",
        material="brass_c360",
        is_printable=False,
        print_settings={},
        is_wear_item=True,
        replacement_interval_cartridges=500,
        estimated_cost=45.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove cartridge and open cartridge door.\n"
            "2. Unscrew 2x M2x5 SHCS from gate mount pattern.\n"
            "3. Lift gate straight out; note dowel pin alignment.\n"
            "4. Place new gate onto dowel pins, press until seated.\n"
            "5. Reinstall 2x M2x5 SHCS to 0.10 N-m.\n"
            "6. Verify film channel alignment with test strip."
        ),
    ),

    "S8C-102": PartCatalogEntry(
        part_number="S8C-102",
        name="Pressure Plate",
        module="MOD-100",
        material="steel_302",
        is_printable=False,
        print_settings={},
        is_wear_item=True,
        replacement_interval_cartridges=300,
        estimated_cost=18.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove film gate (see S8C-101).\n"
            "2. Slide pressure plate out of spring clips.\n"
            "3. Insert new plate; confirm spring pads face gate.\n"
            "4. Reinstall gate and check plate force with gauge (0.5 N)."
        ),
    ),

    "S8C-103": PartCatalogEntry(
        part_number="S8C-103",
        name="Claw Mechanism",
        module="MOD-100",
        material="steel_4140",
        is_printable=False,
        print_settings={},
        is_wear_item=True,
        replacement_interval_cartridges=1000,
        estimated_cost=35.00,
        repair_level=3,
        replacement_procedure=(
            "1. Remove film gate and pressure plate.\n"
            "2. Remove e-clip from claw pivot pin with pliers.\n"
            "3. Slide pivot pin out; remove claw arm.\n"
            "4. Disconnect link from cam eccentric.\n"
            "5. Install new claw arm onto pivot pin.\n"
            "6. Reconnect link; install e-clip.\n"
            "7. Reassemble gate; verify 4.234 mm pulldown with dial indicator."
        ),
    ),

    "S8C-104": PartCatalogEntry(
        part_number="S8C-104",
        name="Cam Follower Assembly",
        module="MOD-100",
        material="steel_4140",
        is_printable=False,
        print_settings={},
        is_wear_item=True,
        replacement_interval_cartridges=2000,
        estimated_cost=40.00,
        repair_level=3,
        replacement_procedure=(
            "1. Remove drivetrain module (MOD-300) to access shaft.\n"
            "2. Remove cam disc retaining screw.\n"
            "3. Slide cam disc off shaft (note keyway alignment).\n"
            "4. Remove eccentric and link assembly.\n"
            "5. Install new cam assembly; align keyway with 10-degree phase mark.\n"
            "6. Reinstall retaining screw; check cam profile with test rotation."
        ),
    ),

    "S8C-105": PartCatalogEntry(
        part_number="S8C-105",
        name="Film Channel",
        module="MOD-100",
        material="delrin_150",
        is_printable=True,
        print_settings={
            "material": "PETG",
            "layer_height": "0.12 mm",
            "infill": "100%",
            "supports": "none",
        },
        is_wear_item=True,
        replacement_interval_cartridges=200,
        estimated_cost=5.00,
        repair_level=1,
        replacement_procedure=(
            "1. Open cartridge door; remove cartridge.\n"
            "2. Unclip film channel from body rails.\n"
            "3. Snap new channel into place; confirm smooth film path."
        ),
    ),

    "S8C-106": PartCatalogEntry(
        part_number="S8C-106",
        name="Registration Pin",
        module="MOD-100",
        material="steel_4140",
        is_printable=False,
        print_settings={},
        is_wear_item=True,
        replacement_interval_cartridges=500,
        estimated_cost=8.00,
        repair_level=3,
        replacement_procedure=(
            "1. Remove film gate (see S8C-101).\n"
            "2. Press out worn pin from rear using 0.8 mm punch.\n"
            "3. Press new pin into H6 bore until 0.5 mm protrusion.\n"
            "4. Verify pin diameter 0.813 +0/-0.002 mm with micrometer.\n"
            "5. Reinstall gate; test registration with film strip."
        ),
    ),

    # ----- MOD-200  SHUTTER -------------------------------------------------

    "S8C-201": PartCatalogEntry(
        part_number="S8C-201",
        name="Shutter Disc",
        module="MOD-200",
        material="alu_6061_t6",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=22.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove top plate (6x M2.5 screws).\n"
            "2. Loosen shutter keyway set screw.\n"
            "3. Slide disc off shaft.\n"
            "4. Install new disc; align keyway.\n"
            "5. Tighten set screw; verify 0.3 mm gate clearance with feeler gauge.\n"
            "6. Spin by hand to check for rubbing."
        ),
    ),

    "S8C-202": PartCatalogEntry(
        part_number="S8C-202",
        name="Main Shaft",
        module="MOD-200",
        material="steel_4140",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=55.00,
        repair_level=3,
        replacement_procedure=(
            "1. Remove top plate, shutter disc, and cam disc.\n"
            "2. Remove both bearing retaining clips.\n"
            "3. Press shaft out from gear-end side.\n"
            "4. Press new shaft into bearings from gear end.\n"
            "5. Reinstall cam disc (keyway aligned), shutter disc, retaining clips.\n"
            "6. Verify runout < 0.01 mm TIR with dial indicator."
        ),
    ),

    # ----- MOD-300  DRIVETRAIN ----------------------------------------------

    "S8C-301": PartCatalogEntry(
        part_number="S8C-301",
        name="Motor Mount",
        module="MOD-300",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PETG",
            "layer_height": "0.20 mm",
            "infill": "60%",
            "supports": "minimal (bracket underside)",
        },
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=8.00,
        repair_level=2,
        replacement_procedure=(
            "1. Disconnect motor connector J1.\n"
            "2. Remove 2x M3x8 motor mount screws.\n"
            "3. Lift motor+mount assembly out.\n"
            "4. Transfer motor to new mount bracket.\n"
            "5. Reinstall; reconnect J1."
        ),
    ),

    "S8C-302": PartCatalogEntry(
        part_number="S8C-302",
        name="Gearbox Housing",
        module="MOD-300",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PETG",
            "layer_height": "0.16 mm",
            "infill": "80%",
            "supports": "yes (bearing bores)",
        },
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=12.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove motor mount assembly (see S8C-301).\n"
            "2. Remove 4x housing cover screws.\n"
            "3. Lift housing halves apart; remove gears.\n"
            "4. Transfer gears and bearings to new housing.\n"
            "5. Reassemble; verify gear mesh by hand rotation."
        ),
    ),

    "S8C-303": PartCatalogEntry(
        part_number="S8C-303",
        name="Gear Set (Stage 1 + Stage 2)",
        module="MOD-300",
        material="delrin_150",
        is_printable=True,
        print_settings={
            "material": "PLA+ or Nylon",
            "layer_height": "0.10 mm",
            "infill": "100%",
            "supports": "none",
        },
        is_wear_item=True,
        replacement_interval_cartridges=5000,
        estimated_cost=15.00,
        repair_level=2,
        replacement_procedure=(
            "1. Open gearbox housing (see S8C-302).\n"
            "2. Remove worn gears from shaft pins.\n"
            "3. Install new gear set; verify mesh pattern.\n"
            "4. Apply small amount of Superlube grease to gear teeth.\n"
            "5. Close housing; run motor for 10s break-in."
        ),
    ),

    # NOTE: main_shaft is shared between MOD-200 and MOD-300.
    # It is cataloged under MOD-200 (S8C-202) as the primary module.

    # ----- MOD-400  CARTRIDGE BAY -------------------------------------------

    "S8C-401": PartCatalogEntry(
        part_number="S8C-401",
        name="Cartridge Receiver",
        module="MOD-400",
        material="alu_6061_t6",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=30.00,
        repair_level=2,
        replacement_procedure=(
            "1. Open cartridge door; remove cartridge.\n"
            "2. Remove 4x M2.5 screws from receiver flange.\n"
            "3. Lift receiver out of body.\n"
            "4. Place new receiver; align with registration pin holes.\n"
            "5. Reinstall screws to 0.20 N-m.\n"
            "6. Test cartridge insertion and latch engagement."
        ),
    ),

    "S8C-402": PartCatalogEntry(
        part_number="S8C-402",
        name="Cartridge Door",
        module="MOD-400",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PETG",
            "layer_height": "0.16 mm",
            "infill": "40%",
            "supports": "yes (hinge knuckles)",
        },
        is_wear_item=True,
        replacement_interval_cartridges=3000,
        estimated_cost=10.00,
        repair_level=1,
        replacement_procedure=(
            "1. Open door fully.\n"
            "2. Push hinge pin out with 2 mm punch.\n"
            "3. Lift door off body.\n"
            "4. Align new door knuckles with body hinges.\n"
            "5. Press hinge pin through; verify smooth operation.\n"
            "6. Check light-trap foam is intact."
        ),
    ),

    # ----- MOD-500  ELECTRONICS ---------------------------------------------

    "S8C-501": PartCatalogEntry(
        part_number="S8C-501",
        name="PCB Bracket",
        module="MOD-500",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PLA+",
            "layer_height": "0.20 mm",
            "infill": "30%",
            "supports": "none",
        },
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=4.00,
        repair_level=2,
        replacement_procedure=(
            "1. Disconnect all JST connectors (J1-J7) from PCB.\n"
            "2. Remove 4x M2x8 standoff screws.\n"
            "3. Lift PCB+bracket assembly out.\n"
            "4. Transfer PCB to new bracket.\n"
            "5. Reinstall; reconnect all connectors."
        ),
    ),

    # ----- MOD-600  POWER ---------------------------------------------------

    "S8C-601": PartCatalogEntry(
        part_number="S8C-601",
        name="Battery Door",
        module="MOD-600",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PETG",
            "layer_height": "0.16 mm",
            "infill": "40%",
            "supports": "yes (hinge ears)",
        },
        is_wear_item=True,
        replacement_interval_cartridges=5000,
        estimated_cost=6.00,
        repair_level=1,
        replacement_procedure=(
            "1. Open battery door; remove batteries.\n"
            "2. Flex hinge ears outward to release pin.\n"
            "3. Lift door away.\n"
            "4. Align new door hinge ears; snap pin into place.\n"
            "5. Verify latch clicks securely closed."
        ),
    ),

    "S8C-602": PartCatalogEntry(
        part_number="S8C-602",
        name="Bottom Plate",
        module="MOD-600",
        material="alu_6061_t6",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=25.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove batteries and battery door.\n"
            "2. Remove 4x M2.5 screws from bottom plate perimeter.\n"
            "3. Lower plate away from body.\n"
            "4. Transfer tripod insert to new plate.\n"
            "5. Reinstall with screws to 0.20 N-m."
        ),
    ),

    # ----- MOD-700  OPTICS --------------------------------------------------

    "S8C-701": PartCatalogEntry(
        part_number="S8C-701",
        name="Lens Mount (C-Mount)",
        module="MOD-700",
        material="brass_c360",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=35.00,
        repair_level=3,
        replacement_procedure=(
            "1. Remove lens from mount.\n"
            "2. Remove 3x M2x5 mount screws (0/120/240-degree pattern).\n"
            "3. Pull mount boss straight forward out of body.\n"
            "4. Insert new mount; align locating pin at 12 o'clock.\n"
            "5. Install 3x M2x5 screws to 0.10 N-m.\n"
            "6. Verify 17.526 mm flange distance with depth gauge."
        ),
    ),

    "S8C-702": PartCatalogEntry(
        part_number="S8C-702",
        name="Viewfinder",
        module="MOD-700",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PETG (black)",
            "layer_height": "0.12 mm",
            "infill": "100% (tube wall)",
            "supports": "yes (lens seats)",
        },
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=15.00,
        repair_level=1,
        replacement_procedure=(
            "1. Remove top plate (6x M2.5 screws).\n"
            "2. Unscrew 2x M2x5 viewfinder tab screws.\n"
            "3. Lift viewfinder tube out.\n"
            "4. Transfer lens elements to new tube if reusing optics.\n"
            "5. Install new tube; tighten tab screws.\n"
            "6. Verify bright-line frame is centered."
        ),
    ),

    # ----- 800-series  STRUCTURE (not in a swappable module) ----------------

    "S8C-801": PartCatalogEntry(
        part_number="S8C-801",
        name="Body Left Half",
        module="STRUCTURE",
        material="alu_6061_t6",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=85.00,
        repair_level=3,
        replacement_procedure=(
            "1. Full disassembly required. Remove all modules.\n"
            "2. Separate body halves (12x M2.5 screws).\n"
            "3. Transfer all internal modules to new body half.\n"
            "4. Reassemble; torque all screws to spec."
        ),
    ),

    "S8C-802": PartCatalogEntry(
        part_number="S8C-802",
        name="Body Right Half",
        module="STRUCTURE",
        material="alu_6061_t6",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=85.00,
        repair_level=3,
        replacement_procedure=(
            "1. Full disassembly required. Remove all modules.\n"
            "2. Separate body halves (12x M2.5 screws).\n"
            "3. Transfer all internal modules to new body half.\n"
            "4. Reassemble; torque all screws to spec."
        ),
    ),

    "S8C-803": PartCatalogEntry(
        part_number="S8C-803",
        name="Top Plate",
        module="STRUCTURE",
        material="alu_6061_t6",
        is_printable=False,
        print_settings={},
        is_wear_item=False,
        replacement_interval_cartridges=None,
        estimated_cost=30.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove 6x M2.5 top plate screws.\n"
            "2. Lift plate; disconnect any accessory shoe wiring.\n"
            "3. Install new plate; reconnect wiring.\n"
            "4. Reinstall screws to 0.20 N-m."
        ),
    ),

    "S8C-804": PartCatalogEntry(
        part_number="S8C-804",
        name="Trigger Assembly",
        module="STRUCTURE",
        material="alu_6061_t6",
        is_printable=True,
        print_settings={
            "material": "PETG",
            "layer_height": "0.16 mm",
            "infill": "60%",
            "supports": "yes (lever pivot)",
        },
        is_wear_item=True,
        replacement_interval_cartridges=10000,
        estimated_cost=12.00,
        repair_level=2,
        replacement_procedure=(
            "1. Remove bottom plate (see S8C-602).\n"
            "2. Disconnect trigger switch wire from PCB (J4 pin 3).\n"
            "3. Remove trigger pivot pin retaining clip.\n"
            "4. Slide trigger assembly out.\n"
            "5. Install new assembly; reinstall pivot pin and clip.\n"
            "6. Reconnect switch wire; verify actuation."
        ),
    ),
}


# =========================================================================
# QUERY FUNCTIONS
# =========================================================================

def get_parts_by_repair_level(level: int) -> List[PartCatalogEntry]:
    """Return all parts at the given repair difficulty level (1-3)."""
    return [p for p in PART_CATALOG.values() if p.repair_level == level]


def _separator(char: str = "=", width: int = 72) -> str:
    return char * width


def _header(title: str, char: str = "=", width: int = 72) -> str:
    line = char * width
    return f"\n{line}\n  {title}\n{line}\n"


# =========================================================================
# PRINT FUNCTIONS
# =========================================================================

def print_module_map() -> str:
    """Show all 7 modules with their parts and interfaces."""
    lines = [_header("MODULE MAP")]
    for mod in MODULES.values():
        lines.append(f"  {mod.module_id}  {mod.name}")
        lines.append(f"    Interface:    {mod.interface_type}")
        lines.append(f"    Connects to:  {', '.join(mod.connects_to)}")
        lines.append(f"    Repair level: {mod.repair_level} "
                      f"({'user' if mod.repair_level == 1 else 'technician' if mod.repair_level == 2 else 'factory'})")
        lines.append(f"    Swap time:    {mod.swap_time_seconds}s")
        if mod.tools_required:
            lines.append(f"    Tools:        {', '.join(mod.tools_required)}")
        else:
            lines.append(f"    Tools:        none (tool-free)")
        lines.append(f"    Parts:")
        for part_name in mod.parts_included:
            marker = "[P]" if part_name in mod.printable_parts else "[C]"
            lines.append(f"      {marker} {part_name}")
        lines.append("")
    lines.append("  Legend: [P] = FDM printable   [C] = CNC / precision")
    lines.append("")
    return "\n".join(lines)


def print_connector_map() -> str:
    """Table of all connectors with pin counts and colors."""
    lines = [_header("CONNECTOR MAP")]
    lines.append(f"  {'ID':<5} {'Pins':<5} {'Family':<7} {'From':<10} {'To':<10} "
                  f"{'Max mA':<8} {'Colors'}")
    lines.append(f"  {'--':<5} {'----':<5} {'------':<7} {'--------':<10} {'--------':<10} "
                  f"{'------':<8} {'------'}")
    for conn in CONNECTORS.values():
        colors = ", ".join(conn.wire_colors)
        lines.append(
            f"  {conn.connector_id:<5} {conn.pin_count:<5} {conn.jst_family:<7} "
            f"{conn.from_module:<10} {conn.to_module:<10} "
            f"{conn.max_current_ma:<8.0f} {colors}"
        )
    lines.append("")
    lines.append("  Signal details:")
    for conn in CONNECTORS.values():
        signals = ", ".join(conn.signal_names)
        lines.append(f"    {conn.connector_id} ({conn.pin_count}P {conn.jst_family}): {signals}")
    lines.append("")
    return "\n".join(lines)


def print_repair_guide() -> str:
    """For each part: symptoms, tools, time, step-by-step procedure."""
    lines = [_header("REPAIR GUIDE")]

    # Symptom lookup — common failure modes per part type
    symptoms = {
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

    for part in PART_CATALOG.values():
        mod = MODULES.get(part.module)
        swap_time = mod.swap_time_seconds if mod else "N/A"
        tools_list = mod.tools_required if mod else []

        lines.append(f"  {part.part_number}  {part.name}")
        lines.append(f"  {'~' * 50}")
        symptom_text = symptoms.get(part.name, "Visual inspection / functional test")
        lines.append(f"    Symptoms:    {symptom_text}")
        lines.append(f"    Module:      {part.module}")
        lines.append(f"    Level:       {part.repair_level} "
                      f"({'user' if part.repair_level == 1 else 'technician' if part.repair_level == 2 else 'factory'})")
        if tools_list:
            lines.append(f"    Tools:       {', '.join(tools_list)}")
        else:
            lines.append(f"    Tools:       none")
        if part.is_wear_item and part.replacement_interval_cartridges:
            lines.append(f"    Interval:    every {part.replacement_interval_cartridges} cartridges")
        elif not part.is_wear_item:
            lines.append(f"    Interval:    lifetime (replace only if damaged)")
        lines.append(f"    Est. cost:   ${part.estimated_cost:.2f}")
        lines.append(f"    Procedure:")
        for proc_line in part.replacement_procedure.split("\n"):
            lines.append(f"      {proc_line}")
        lines.append("")

    return "\n".join(lines)


def print_printable_parts() -> str:
    """List every part that can be FDM printed with settings."""
    lines = [_header("FDM PRINTABLE PARTS")]
    printable = [p for p in PART_CATALOG.values() if p.is_printable]
    for part in printable:
        lines.append(f"  {part.part_number}  {part.name}")
        for k, v in part.print_settings.items():
            lines.append(f"    {k:<14} {v}")
        lines.append(f"    est. cost:     ${part.estimated_cost:.2f} (vs CNC original)")
        lines.append("")
    lines.append(f"  Total printable parts: {len(printable)} / {len(PART_CATALOG)}")
    lines.append("")
    return "\n".join(lines)


def print_spare_parts_catalog() -> str:
    """List parts sold as spares with pricing."""
    lines = [_header("SPARE PARTS CATALOG")]
    lines.append(f"  {'Part #':<10} {'Name':<30} {'Material':<14} "
                  f"{'Wear?':<6} {'Interval':<12} {'Price'}")
    lines.append(f"  {'------':<10} {'----':<30} {'--------':<14} "
                  f"{'-----':<6} {'--------':<12} {'-----'}")
    total = 0.0
    for part in PART_CATALOG.values():
        interval = (f"{part.replacement_interval_cartridges} cart."
                     if part.replacement_interval_cartridges else "lifetime")
        wear = "YES" if part.is_wear_item else " "
        lines.append(
            f"  {part.part_number:<10} {part.name:<30} {part.material:<14} "
            f"{wear:<6} {interval:<12} ${part.estimated_cost:.2f}"
        )
        total += part.estimated_cost
    lines.append("")
    lines.append(f"  Total catalog value (1 of each): ${total:.2f}")

    # Wear items subtotal
    wear_parts = [p for p in PART_CATALOG.values() if p.is_wear_item]
    wear_total = sum(p.estimated_cost for p in wear_parts)
    lines.append(f"  Wear items only ({len(wear_parts)} parts):     ${wear_total:.2f}")
    lines.append("")
    return "\n".join(lines)


def print_full_report() -> str:
    """Generate the complete modularity report."""
    sections = [
        _header("SUPER 8 CAMERA  --  MODULARITY & REPAIRABILITY REPORT"),
        print_module_map(),
        print_connector_map(),
        print_repair_guide(),
        print_printable_parts(),
        print_spare_parts_catalog(),
    ]

    # Repair level summary
    lines = [_header("REPAIR LEVEL SUMMARY")]
    for level, label in [(1, "USER (no tools)"), (2, "TECHNICIAN"), (3, "FACTORY")]:
        parts = get_parts_by_repair_level(level)
        names = ", ".join(p.name for p in parts)
        lines.append(f"  Level {level} — {label}  ({len(parts)} parts)")
        lines.append(f"    {names}")
        lines.append("")
    sections.append("\n".join(lines))

    return "\n".join(sections)


# =========================================================================
# CLI ENTRY POINT
# =========================================================================

if __name__ == "__main__":
    import sys

    report = print_full_report()
    print(report)

    # Save to export/modularity_report.txt
    export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "export")
    os.makedirs(export_dir, exist_ok=True)
    out_path = os.path.join(export_dir, "modularity_report.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  Report saved to {out_path}")
