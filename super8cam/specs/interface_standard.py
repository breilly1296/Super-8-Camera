"""interface_standard.py — FROZEN interface specification for modular compatibility.

    *** THIS FILE IS LOCKED. DO NOT MODIFY EXISTING VALUES. ***

This is the contract that guarantees any v1 part works in a v5 camera.
All dimensions, positions, pinouts, and fastener choices defined here are
immutable across camera versions.  New versions may ADD new expansion
slots or connector IDs, but NEVER change existing ones.

Think of this as the "USB spec" for the Super 8 Camera platform:
- A MOD-100 Film Transport from 2026 drops into a MOD-100 slot from 2030.
- A J3 battery connector always has 4 pins in the same order.
- The dovetail rail is always 60 deg, 4mm top, 6mm base, 3mm deep.

Usage:
    from super8cam.specs.interface_standard import (
        INTERFACE_VERSION,
        DOVETAIL_RAIL_SPEC,
        MODULE_SLOT_POSITIONS,
        CONNECTOR_STANDARD,
        FASTENER_STANDARD,
        EXPANSION_SLOT,
        compatibility_check,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =========================================================================
# VERSION — monotonically increasing, never reset
# =========================================================================

INTERFACE_VERSION = "1.0"


# =========================================================================
# DOVETAIL RAIL SPEC — FROZEN
# =========================================================================

@dataclass(frozen=True)
class DovetailRailSpec:
    """60-degree ISO-style machine dovetail profile.

    Cross-section (looking down the rail axis):

          |<- top_w ->|
          +----------+              ---
         /            \\              |  depth
        /              \\             |
       +----------------+           ---
       |<--- base_w --->|

    Included angle = 60 degrees (each side wall is 30 deg from vertical).
    """
    included_angle_deg: float       # 60 degrees — FROZEN
    top_width_mm: float             # 4.0 mm — narrow (exposed) face
    base_width_mm: float            # 6.0 mm — wide (seated) face
    depth_mm: float                 # 3.0 mm — profile depth
    clearance_per_side_mm: float    # 0.15 mm — slider fit tolerance
    thumbscrew_thread: str          # "M3" — FROZEN
    thumbscrew_spacing_mm: float    # 20.0 mm — center-to-center
    thumbscrew_engagement_mm: float # 5.0 mm — thread engagement depth


DOVETAIL_RAIL_SPEC = DovetailRailSpec(
    included_angle_deg=60.0,
    top_width_mm=4.0,
    base_width_mm=6.0,
    depth_mm=3.0,
    clearance_per_side_mm=0.15,
    thumbscrew_thread="M3",
    thumbscrew_spacing_mm=20.0,
    thumbscrew_engagement_mm=5.0,
)


# =========================================================================
# RAIL POSITIONS ON CHASSIS — FROZEN
# =========================================================================

@dataclass(frozen=True)
class RailPosition:
    """Exact mounting position of a dovetail rail on the chassis.

    All coordinates relative to chassis datum (body center = origin).
    Orientation: X = length, Y = depth (front-back), Z = height.
    """
    rail_id: str
    x_mm: float
    y_mm: float
    z_mm: float
    axis: str               # "X", "Y", or "Z" — rail runs along this axis
    length_mm: float         # rail extrusion length
    description: str


RAIL_POSITIONS: Dict[str, RailPosition] = {
    "RAIL_LEFT": RailPosition(
        rail_id="RAIL_LEFT",
        x_mm=-55.0,
        y_mm=0.0,
        z_mm=-25.0,
        axis="X",
        length_mm=80.0,
        description="Left interior rail — mounts Film Transport, Shutter, Drivetrain modules",
    ),
    "RAIL_RIGHT": RailPosition(
        rail_id="RAIL_RIGHT",
        x_mm=30.0,
        y_mm=0.0,
        z_mm=-25.0,
        axis="X",
        length_mm=50.0,
        description="Right interior rail — mounts Cartridge Bay, Optics modules",
    ),
}


# =========================================================================
# MODULE SLOT POSITIONS — FROZEN
# =========================================================================

@dataclass(frozen=True)
class ModuleSlotPosition:
    """Exact mounting position for a module relative to chassis datum.

    A MOD-100 Film Transport from 2026 must drop into a MOD-100 slot
    from 2030.  These coordinates are FROZEN per slot ID.
    """
    slot_id: str                # matches module_id (e.g. "MOD-100")
    x_mm: float                 # module center X
    y_mm: float                 # module center Y
    z_mm: float                 # module center Z
    orientation_deg: float      # rotation about Z axis (0 = standard)
    rail_id: str                # which rail this module slides onto
    connector_id: str           # primary electrical connector
    connector_x_mm: float       # connector position X (on PCB edge)
    connector_y_mm: float       # connector position Y
    connector_z_mm: float       # connector position Z
    description: str


MODULE_SLOT_POSITIONS: Dict[str, ModuleSlotPosition] = {

    "MOD-100": ModuleSlotPosition(
        slot_id="MOD-100",
        x_mm=-18.0,
        y_mm=-8.0,
        z_mm=0.0,
        orientation_deg=0.0,
        rail_id="RAIL_LEFT",
        connector_id="J4",
        connector_x_mm=-40.0,
        connector_y_mm=0.0,
        connector_z_mm=-30.0,
        description="Film Transport — gate, pressure plate, claw, cam, channel",
    ),

    "MOD-200": ModuleSlotPosition(
        slot_id="MOD-200",
        x_mm=-18.0,
        y_mm=-5.0,
        z_mm=16.0,
        orientation_deg=0.0,
        rail_id="RAIL_LEFT",
        connector_id="J2",
        connector_x_mm=-40.0,
        connector_y_mm=2.0,
        connector_z_mm=-30.0,
        description="Shutter — disc and main shaft",
    ),

    "MOD-300": ModuleSlotPosition(
        slot_id="MOD-300",
        x_mm=17.0,
        y_mm=7.0,
        z_mm=-2.0,
        orientation_deg=0.0,
        rail_id="RAIL_LEFT",
        connector_id="J1",
        connector_x_mm=-40.0,
        connector_y_mm=4.0,
        connector_z_mm=-30.0,
        description="Drivetrain — motor, gearbox, gears",
    ),

    "MOD-400": ModuleSlotPosition(
        slot_id="MOD-400",
        x_mm=31.25,
        y_mm=0.0,
        z_mm=3.0,
        orientation_deg=0.0,
        rail_id="RAIL_RIGHT",
        connector_id="J5",
        connector_x_mm=50.0,
        connector_y_mm=0.0,
        connector_z_mm=-30.0,
        description="Cartridge Bay — receiver and door",
    ),

    "MOD-500": ModuleSlotPosition(
        slot_id="MOD-500",
        x_mm=-42.0,
        y_mm=0.0,
        z_mm=-33.0,
        orientation_deg=0.0,
        rail_id="RAIL_LEFT",
        connector_id="J6",
        connector_x_mm=-40.0,
        connector_y_mm=6.0,
        connector_z_mm=-30.0,
        description="Electronics — main PCB and bracket",
    ),

    "MOD-600": ModuleSlotPosition(
        slot_id="MOD-600",
        x_mm=0.0,
        y_mm=0.0,
        z_mm=-40.0,
        orientation_deg=0.0,
        rail_id="RAIL_LEFT",
        connector_id="J3",
        connector_x_mm=-40.0,
        connector_y_mm=8.0,
        connector_z_mm=-30.0,
        description="Power — battery compartment and door",
    ),

    "MOD-700": ModuleSlotPosition(
        slot_id="MOD-700",
        x_mm=-18.0,
        y_mm=-24.0,
        z_mm=0.0,
        orientation_deg=0.0,
        rail_id="RAIL_RIGHT",
        connector_id="J6",
        connector_x_mm=50.0,
        connector_y_mm=2.0,
        connector_z_mm=-30.0,
        description="Optics — lens mount and viewfinder",
    ),
}


# =========================================================================
# CONNECTOR STANDARD — FROZEN pinouts
# =========================================================================

@dataclass(frozen=True)
class ConnectorPinout:
    """Frozen electrical connector specification.

    New modules can use fewer pins (leave extras NC) but NEVER more.
    Pin order, families, wire colors, and max current are immutable.
    """
    connector_id: str
    pin_count: int
    jst_family: str               # "XH" (2.5mm) or "VH" (3.96mm)
    signal_names: Tuple[str, ...]  # ordered pin 1..N
    wire_colors: Tuple[str, ...]   # ordered pin 1..N
    max_current_ma: float
    pcb_edge_offset_mm: float      # distance from PCB corner to connector center


CONNECTOR_STANDARD: Dict[str, ConnectorPinout] = {

    "J1": ConnectorPinout(
        connector_id="J1",
        pin_count=2,
        jst_family="VH",
        signal_names=("MOTOR+", "MOTOR-"),
        wire_colors=("red", "black"),
        max_current_ma=800.0,
        pcb_edge_offset_mm=5.0,
    ),

    "J2": ConnectorPinout(
        connector_id="J2",
        pin_count=3,
        jst_family="XH",
        signal_names=("ENCODER_A", "ENCODER_B", "ENCODER_GND"),
        wire_colors=("orange", "yellow", "brown"),
        max_current_ma=20.0,
        pcb_edge_offset_mm=14.0,
    ),

    "J3": ConnectorPinout(
        connector_id="J3",
        pin_count=4,
        jst_family="XH",
        signal_names=("VBATT", "GND", "BATT_SENSE", "THERM"),
        wire_colors=("red", "black", "white", "green"),
        max_current_ma=1200.0,
        pcb_edge_offset_mm=24.0,
    ),

    "J4": ConnectorPinout(
        connector_id="J4",
        pin_count=5,
        jst_family="XH",
        signal_names=("FPS_SEL_A", "FPS_SEL_B", "TRIG_SW", "LED_STATUS", "SIG_GND"),
        wire_colors=("blue", "violet", "grey", "white", "black"),
        max_current_ma=50.0,
        pcb_edge_offset_mm=37.0,
    ),

    "J5": ConnectorPinout(
        connector_id="J5",
        pin_count=6,
        jst_family="XH",
        signal_names=("CART_DET", "FILM_END", "DOOR_SW", "NOTCH_SNS", "LAMP_DRV", "DET_GND"),
        wire_colors=("red", "orange", "yellow", "green", "blue", "black"),
        max_current_ma=100.0,
        pcb_edge_offset_mm=52.0,
    ),

    "J6": ConnectorPinout(
        connector_id="J6",
        pin_count=7,
        jst_family="XH",
        signal_names=("SDA", "SCL", "MOSI", "MISO", "SCK", "CS_EXP", "DBUS_GND"),
        wire_colors=("red", "orange", "yellow", "green", "blue", "violet", "black"),
        max_current_ma=30.0,
        pcb_edge_offset_mm=68.0,
    ),

    "J7": ConnectorPinout(
        connector_id="J7",
        pin_count=8,
        jst_family="XH",
        signal_names=("UART_TX", "UART_RX", "I2C_SDA", "I2C_SCL",
                       "PWM_LIGHT", "AUX_SENSE", "3V3_OUT", "DBG_GND"),
        wire_colors=("red", "orange", "yellow", "green",
                      "blue", "violet", "grey", "black"),
        max_current_ma=200.0,
        pcb_edge_offset_mm=86.0,
    ),
}


# =========================================================================
# FASTENER STANDARD — FROZEN
# =========================================================================

@dataclass(frozen=True)
class FastenerSpec:
    """Frozen fastener specification. No M4, no M1.6, no proprietary, ever."""
    size: str
    thread: str
    use_case: str
    max_torque_nm: float


FASTENER_STANDARD: Dict[str, FastenerSpec] = {
    "M2": FastenerSpec(
        size="M2",
        thread="M2x0.4",
        use_case="Internal precision parts (gate, lens mount, PCB standoffs)",
        max_torque_nm=0.10,
    ),
    "M2.5": FastenerSpec(
        size="M2.5",
        thread="M2.5x0.45",
        use_case="Shell-to-chassis (body halves, top plate, bottom plate)",
        max_torque_nm=0.20,
    ),
    "M3": FastenerSpec(
        size="M3",
        thread="M3x0.5",
        use_case="Module retention (dovetail thumb screws, motor mount)",
        max_torque_nm=0.35,
    ),
    "1/4-20": FastenerSpec(
        size="1/4-20",
        thread="1/4-20 UNC",
        use_case="Tripod mount (helicoil insert in bottom plate)",
        max_torque_nm=1.50,
    ),
}

# Explicit exclusion list — these are NEVER used
FORBIDDEN_FASTENERS = frozenset([
    "M1", "M1.2", "M1.4", "M1.6", "M4", "M5", "M6", "M8",
    "#2-56", "#4-40", "#6-32", "#8-32",
])


# =========================================================================
# EXPANSION SLOT — future-proofing
# =========================================================================

@dataclass(frozen=True)
class ExpansionSlotSpec:
    """Reserved expansion slot for community-designed modules.

    The slot exists in the chassis design even if v1 ships with a blank
    cover plate.  Enables: digital frame counter, Bluetooth sync,
    intervalometer, sound recording, GPS logger, light meter, etc.
    """
    slot_id: str
    x_mm: float
    y_mm: float
    z_mm: float
    orientation_deg: float
    rail_id: str
    connector_id: str
    connector_pin_count: int
    connector_family: str
    signal_names: Tuple[str, ...]
    wire_colors: Tuple[str, ...]
    max_current_ma: float
    description: str


EXPANSION_SLOT = ExpansionSlotSpec(
    slot_id="MOD-EXP",
    x_mm=50.0,
    y_mm=10.0,
    z_mm=25.0,
    orientation_deg=0.0,
    rail_id="RAIL_RIGHT",
    connector_id="J8",
    connector_pin_count=10,
    connector_family="XH",
    signal_names=(
        "SDA", "SCL", "TX", "RX", "PWM1",
        "PWM2", "3V3", "5V", "GND", "GND",
    ),
    wire_colors=(
        "white", "grey", "orange", "yellow", "blue",
        "violet", "red", "brown", "black", "black",
    ),
    max_current_ma=500.0,
    description=(
        "Reserved expansion slot for community-designed modules. "
        "I2C bus (SDA/SCL), UART (TX/RX), 2x PWM outputs, "
        "dual power rails (3V3 + 5V), dual ground. "
        "Blank cover plate ships with v1."
    ),
)


# =========================================================================
# COMPATIBILITY CHECK
# =========================================================================

def compatibility_check(module_version: str, chassis_version: str) -> bool:
    """Check if a module is compatible with a chassis.

    Rules:
    - Same major version = always compatible (1.0 with 1.9 = OK)
    - Module major <= chassis major = compatible (v1 module in v2 chassis = OK)
    - Module major > chassis major = NOT compatible (v2 module in v1 chassis = NO)
    - Any module built against interface v1.0 works in any chassis >= v1.0

    Args:
        module_version: Interface spec version the module was built against (e.g. "1.0")
        chassis_version: Interface spec version of the chassis (e.g. "1.0")

    Returns:
        True if the module will physically and electrically fit the chassis.
    """
    try:
        mod_major, mod_minor = [int(x) for x in module_version.split(".")]
        chs_major, chs_minor = [int(x) for x in chassis_version.split(".")]
    except (ValueError, AttributeError):
        return False

    # A newer-major module cannot fit an older-major chassis
    # (it may use expansion connectors that don't exist yet)
    if mod_major > chs_major:
        return False

    # Same or older major version = compatible
    # The chassis is backward-compatible with all older interface versions
    return True


# =========================================================================
# PRINT SUMMARY
# =========================================================================

def print_interface_spec():
    """Print a human-readable summary of the frozen interface standard."""
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  INTERFACE STANDARD v{INTERFACE_VERSION}  —  FROZEN, DO NOT MODIFY")
    print(sep)

    print(f"\n  DOVETAIL RAIL PROFILE")
    print(f"  {'─' * 40}")
    print(f"    Included angle:   {DOVETAIL_RAIL_SPEC.included_angle_deg}°")
    print(f"    Top width:        {DOVETAIL_RAIL_SPEC.top_width_mm} mm")
    print(f"    Base width:       {DOVETAIL_RAIL_SPEC.base_width_mm} mm")
    print(f"    Depth:            {DOVETAIL_RAIL_SPEC.depth_mm} mm")
    print(f"    Clearance/side:   {DOVETAIL_RAIL_SPEC.clearance_per_side_mm} mm")
    print(f"    Thumb screw:      {DOVETAIL_RAIL_SPEC.thumbscrew_thread}")
    print(f"    Screw spacing:    {DOVETAIL_RAIL_SPEC.thumbscrew_spacing_mm} mm c/c")

    print(f"\n  RAIL POSITIONS ON CHASSIS")
    print(f"  {'─' * 40}")
    for rail in RAIL_POSITIONS.values():
        print(f"    {rail.rail_id}: ({rail.x_mm}, {rail.y_mm}, {rail.z_mm}) mm, "
              f"along {rail.axis}, {rail.length_mm} mm long")
        print(f"      {rail.description}")

    print(f"\n  MODULE SLOT POSITIONS")
    print(f"  {'─' * 40}")
    for slot in MODULE_SLOT_POSITIONS.values():
        print(f"    {slot.slot_id}: ({slot.x_mm}, {slot.y_mm}, {slot.z_mm}) mm, "
              f"{slot.orientation_deg}° — {slot.description}")
        print(f"      Connector {slot.connector_id} at "
              f"({slot.connector_x_mm}, {slot.connector_y_mm}, {slot.connector_z_mm})")

    print(f"\n  CONNECTOR PINOUTS (FROZEN)")
    print(f"  {'─' * 40}")
    for conn in CONNECTOR_STANDARD.values():
        signals = ", ".join(conn.signal_names)
        colors = ", ".join(conn.wire_colors)
        print(f"    {conn.connector_id}: {conn.pin_count}P {conn.jst_family}, "
              f"{conn.max_current_ma:.0f} mA max, PCB offset {conn.pcb_edge_offset_mm} mm")
        print(f"      Signals: {signals}")
        print(f"      Colors:  {colors}")

    print(f"\n  FASTENER STANDARD (FROZEN)")
    print(f"  {'─' * 40}")
    for fs in FASTENER_STANDARD.values():
        print(f"    {fs.size} ({fs.thread}): {fs.use_case}")
        print(f"      Max torque: {fs.max_torque_nm} N·m")
    print(f"    Forbidden: {', '.join(sorted(FORBIDDEN_FASTENERS))}")

    print(f"\n  EXPANSION SLOT")
    print(f"  {'─' * 40}")
    print(f"    {EXPANSION_SLOT.slot_id}: ({EXPANSION_SLOT.x_mm}, "
          f"{EXPANSION_SLOT.y_mm}, {EXPANSION_SLOT.z_mm}) mm")
    print(f"    Connector {EXPANSION_SLOT.connector_id}: "
          f"{EXPANSION_SLOT.connector_pin_count}P {EXPANSION_SLOT.connector_family}")
    print(f"    Signals: {', '.join(EXPANSION_SLOT.signal_names)}")
    print(f"    {EXPANSION_SLOT.description}")

    print(f"\n{sep}\n")


if __name__ == "__main__":
    print_interface_spec()
