"""master_specs.py — Single Source of Truth for the Super 8 Camera Project

EVERY dimension, tolerance, material property, and design constant lives here.
No other file in the project should contain magic numbers.  Import what you
need:

    from super8cam.specs.master_specs import FILM, CMOUNT, CAMERA, TOL, ...

Organisation:
    FILM        Kodak Super 8 film standard
    CARTRIDGE   Kodak Type A cartridge dimensions
    CMOUNT      C-mount lens standard
    CAMERA      Our design parameters (adjustable)
    TOL         Tolerance specifications
    FASTENERS   Screw / insert catalogue
    MATERIALS   Material property dictionary
    BEARINGS    Bearing catalogue
    MOTOR       Motor specifications
    GEARBOX     Gear train parameters
    PCB         Control board dimensions
    BATTERY     Power system
    SHUTTER     Shutter timing (derived)
    DERIVED     Computed values (call derive() to refresh)

All linear dimensions in millimetres unless otherwise noted.
All angles in degrees unless otherwise noted.
All masses in grams, densities in g/cm^3.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# =========================================================================
# KODAK SUPER 8 FILM STANDARD
# =========================================================================

@dataclass(frozen=True)
class FilmSpec:
    """Kodak Super 8 film geometry — immutable standard values."""

    # Image area (exposed frame)
    frame_w: float = 5.79           # mm — horizontal
    frame_h: float = 4.01           # mm — vertical (along film travel)

    # Perforation geometry
    perf_pitch: float = 4.234       # mm — center-to-center between perfs
    perf_w: float = 1.143           # mm — perforation width
    perf_h: float = 0.914           # mm — perforation height
    perf_to_frame_edge: float = 0.51  # mm — perf center to near edge of frame

    # Film strip
    width: float = 8.0              # mm — total film strip width
    thickness: float = 0.155        # mm — base + emulsion combined
    base_thickness: float = 0.115   # mm — PET base alone
    emulsion_thickness: float = 0.040  # mm — emulsion layer

    # Film edge to image area
    edge_to_image_near: float = 0.51   # mm — edge nearest perforations
    edge_to_image_far: float = 1.70    # mm — far edge

    # Registration pin position (relative to frame center)
    reg_pin_below_frame_center: float = 4.234  # mm — one perf pitch below


FILM = FilmSpec()


# =========================================================================
# KODAK TYPE A CARTRIDGE
# =========================================================================

@dataclass(frozen=True)
class CartridgeSpec:
    """Kodak Super 8 Type A cartridge outer dimensions and internal layout."""

    # Overall outer envelope
    length: float = 67.0            # mm — longest dimension
    width: float = 62.0             # mm
    depth: float = 21.0             # mm — thickness

    # Film exit slot (where film leaves cartridge toward gate)
    exit_slot_w: float = 9.5        # mm — slot width (>= film width + clearance)
    exit_slot_h: float = 2.0        # mm — slot height
    exit_slot_x: float = 33.5       # mm — from cartridge left edge to slot center
    exit_slot_y: float = 0.0        # mm — at cartridge face

    # Film entry slot (film returns to takeup side)
    entry_slot_w: float = 9.5       # mm
    entry_slot_h: float = 2.0       # mm
    entry_slot_x: float = 33.5      # mm
    entry_slot_y: float = 21.0      # mm — opposite face

    # Spool positions (center of spindle, from cartridge corner)
    supply_spool_x: float = 20.0    # mm
    supply_spool_y: float = 10.5    # mm — in depth axis
    supply_spool_dia: float = 40.0  # mm — max spool OD when full
    takeup_spool_x: float = 47.0    # mm
    takeup_spool_y: float = 10.5    # mm
    takeup_spool_dia: float = 40.0  # mm

    # Cartridge notch (for camera detection / type sensing)
    notch_present: bool = True
    notch_w: float = 4.0            # mm
    notch_depth: float = 2.0        # mm


CARTRIDGE = CartridgeSpec()


# =========================================================================
# C-MOUNT LENS STANDARD
# =========================================================================

@dataclass(frozen=True)
class CMountSpec:
    """C-mount (ANSI/ASA B3.19) lens interface."""

    thread_od: float = 25.4         # mm — 1 inch nominal
    thread_tpi: int = 32            # threads per inch
    thread_pitch: float = 25.4 / 32 # mm — 0.79375 mm per thread
    thread_depth: float = 3.8       # mm — engagement length
    flange_focal_dist: float = 17.526  # mm — mount face to film plane

    # Derived thread parameters
    thread_major_dia: float = 25.4  # mm
    thread_minor_dia: float = 25.4 - 2 * 0.6134 * (25.4 / 32)  # UNF formula


CMOUNT = CMountSpec()


# =========================================================================
# CAMERA DESIGN PARAMETERS (our choices — adjustable)
# =========================================================================

@dataclass
class CameraDesign:
    """Adjustable design parameters for our Super 8 camera."""

    # Body envelope
    body_length: float = 148.0      # mm (X — left/right)
    body_height: float = 88.0       # mm (Z — vertical)
    body_depth: float = 52.0        # mm (Y — front/back, lens axis)
    wall_thickness: float = 2.5     # mm
    body_fillet: float = 4.0        # mm — outer edge radius

    # Shutter
    shutter_opening_angle: float = 180.0  # degrees (adjustable)
    shutter_od: float = 30.0        # mm — disc outer diameter
    shutter_thickness: float = 0.8  # mm — aluminum sheet
    shutter_shaft_hole: float = 4.0 # mm — matches main shaft
    shutter_keyway_w: float = 1.0   # mm
    shutter_keyway_depth: float = 0.5  # mm
    shutter_to_gate_clearance: float = 0.3  # mm

    # Frame rates
    fps_options: List[int] = field(default_factory=lambda: [18, 24])

    # Main shaft
    shaft_dia: float = 4.0          # mm
    shaft_length: float = 38.0      # mm — total usable length

    # Film gate (brass C360)
    gate_plate_w: float = 25.0      # mm
    gate_plate_h: float = 18.0      # mm
    gate_plate_thick: float = 3.0   # mm
    gate_channel_w: float = 8.0     # mm — film channel width
    gate_channel_depth: float = 0.1 # mm
    gate_lip_w: float = 0.8         # mm — pressure plate lip width
    gate_lip_h: float = 0.05        # mm — lip protrusion
    gate_fillet: float = 1.0        # mm — plate corner fillet
    gate_aperture_fillet: float = 0.15  # mm — aperture corner radius

    # Registration pin
    reg_pin_dia: float = 0.813      # mm — nominal
    reg_pin_length: float = 1.5     # mm — protrusion into film

    # Pressure plate
    pressure_plate_w: float = 20.0  # mm
    pressure_plate_h: float = 14.0  # mm
    pressure_plate_thick: float = 1.0  # mm — spring steel
    pressure_plate_force_n: float = 0.5  # N — target spring force

    # Claw mechanism
    claw_stroke: float = 4.234      # mm — equals perforation pitch
    claw_tip_w: float = 0.7         # mm — must fit inside perforation
    claw_tip_h: float = 0.6         # mm
    claw_engage_depth: float = 0.5  # mm — into perforation
    claw_retract_dist: float = 2.5  # mm — clearance when retracted
    claw_arm_length: float = 12.0   # mm — pivot to tip
    claw_arm_w: float = 2.0         # mm
    claw_arm_thick: float = 0.8     # mm

    # Cam follower (drives the claw)
    cam_od: float = 12.0            # mm — cam lobe outer diameter
    cam_id: float = 4.0             # mm — shaft bore (= shaft_dia)
    cam_width: float = 3.0          # mm — axial width
    cam_lobe_lift: float = 4.234    # mm — pulldown distance
    cam_follower_dia: float = 3.0   # mm — roller diameter

    # Film channel / guide rails
    film_channel_length: float = 30.0  # mm — total guided length around gate
    film_channel_width: float = 8.2    # mm — slight clearance over film width

    # Lens mount boss
    lens_boss_od: float = 32.0      # mm — outer diameter of mount boss
    lens_boss_protrusion: float = 4.0  # mm — protrudes from front face
    lens_mount_offset_x: float = -18.0  # mm — left of body center

    # Cartridge door
    cart_door_w: float = 60.0       # mm
    cart_door_h: float = 50.0       # mm
    cart_door_thick: float = 2.5    # mm

    # Battery compartment (4xAA in 2x2 config)
    batt_pocket_l: float = 58.0     # mm — 2× AA length (50.5) + clearance
    batt_pocket_w: float = 30.0     # mm — 2× AA dia (14.5) + wall
    batt_pocket_depth: float = 16.0 # mm
    batt_door_thick: float = 2.0    # mm

    # Viewfinder
    viewfinder_type: str = "galilean"  # simple optical viewfinder
    viewfinder_eye_dia: float = 8.0    # mm — eyepiece aperture
    viewfinder_obj_dia: float = 10.0   # mm — objective aperture
    viewfinder_length: float = 35.0    # mm — tube length
    viewfinder_magnification: float = 0.5  # wide-angle for framing

    # Motor mount
    motor_mount_screws: int = 2
    motor_mount_screw_spacing: float = 15.0  # mm

    # Tripod mount
    tripod_boss_dia: float = 14.0   # mm
    tripod_boss_depth: float = 8.0  # mm
    tripod_thread: str = "1/4-20"
    tripod_insert_depth: float = 6.0  # mm

    # PCB mounting
    pcb_standoff_rect_w: float = 50.0  # mm
    pcb_standoff_rect_h: float = 30.0  # mm
    pcb_standoff_height: float = 8.0   # mm
    pcb_standoff_dia: float = 5.0      # mm
    pcb_mount_offset_x: float = -15.0  # mm — toward lens side


CAMERA = CameraDesign()


# =========================================================================
# TOLERANCES
# =========================================================================

@dataclass(frozen=True)
class Tolerances:
    """Manufacturing tolerances for critical and general dimensions."""

    # Film gate (precision ground)
    gate_aperture: float = 0.005        # mm — +/- on aperture W and H
    gate_channel_depth: float = 0.02    # mm

    # Registration pin
    reg_pin_dia_plus: float = 0.000     # mm — max oversize
    reg_pin_dia_minus: float = 0.005    # mm — max undersize
    reg_pin_position: float = 0.01      # mm — pin to aperture center

    # Shutter clearance
    shutter_clearance: float = 0.05     # mm — on the 0.3mm nominal gap

    # General CNC machining
    cnc_general: float = 0.05           # mm
    cnc_fine: float = 0.02              # mm

    # Fits (ISO system)
    press_fit_hole: str = "H7"          # hole tolerance band
    press_fit_shaft: str = "p6"         # shaft tolerance band
    bearing_seat: str = "H7"            # bearing housing bore
    bearing_shaft: str = "k6"           # shaft under bearing

    # Screw holes
    screw_clearance_oversize: float = 0.1  # mm added to nominal diameter

    # Surface finish (Ra in micrometers)
    gate_surface_ra: float = 0.4        # um — polished film contact
    bearing_seat_ra: float = 0.8        # um
    general_machined_ra: float = 1.6    # um
    body_exterior_ra: float = 0.8       # um — anodize-ready


TOL = Tolerances()


# =========================================================================
# FASTENERS CATALOGUE
# =========================================================================

@dataclass(frozen=True)
class Fastener:
    thread: str             # e.g. "M2"
    length: float           # mm
    head_type: str          # e.g. "socket_head_cap"
    head_dia: float         # mm
    head_height: float      # mm
    clearance_hole: float   # mm — drill size for clearance
    tap_hole: float         # mm — drill size for tapping
    torque_nm: float        # N-m — recommended tightening torque


FASTENERS = {
    "M2x5_shcs": Fastener(
        thread="M2", length=5.0, head_type="socket_head_cap",
        head_dia=3.8, head_height=2.0,
        clearance_hole=2.2, tap_hole=1.6, torque_nm=0.10),
    "M2x8_shcs": Fastener(
        thread="M2", length=8.0, head_type="socket_head_cap",
        head_dia=3.8, head_height=2.0,
        clearance_hole=2.2, tap_hole=1.6, torque_nm=0.10),
    "M2_5x6_shcs": Fastener(
        thread="M2.5", length=6.0, head_type="socket_head_cap",
        head_dia=4.5, head_height=2.5,
        clearance_hole=2.7, tap_hole=2.05, torque_nm=0.20),
    "M3x8_shcs": Fastener(
        thread="M3", length=8.0, head_type="socket_head_cap",
        head_dia=5.5, head_height=3.0,
        clearance_hole=3.2, tap_hole=2.5, torque_nm=0.50),
    "quarter20x6": Fastener(
        thread="1/4-20", length=6.0, head_type="helicoil_insert",
        head_dia=6.35, head_height=6.0,
        clearance_hole=6.6, tap_hole=5.1, torque_nm=0.50),
}

# Usage map: which fastener goes where
FASTENER_USAGE = {
    "film_gate_mount":  ("M2x5_shcs", 2),
    "pcb_standoffs":    ("M2x8_shcs", 4),
    "body_assembly":    ("M2_5x6_shcs", 12),
    "motor_mount":      ("M3x8_shcs", 2),
    "tripod_mount":     ("quarter20x6", 1),
}


# =========================================================================
# MATERIALS
# =========================================================================

@dataclass(frozen=True)
class Material:
    name: str
    designation: str
    density: float              # g/cm^3
    youngs_modulus: float       # GPa
    yield_strength: float       # MPa
    ultimate_strength: float    # MPa
    thermal_expansion: float    # um/m/K (ppm/K)
    hardness: str               # e.g. "HB 95" or "HRC 30"
    machinability: str          # qualitative note
    finish: str                 # intended surface treatment


MATERIALS = {
    "brass_c360": Material(
        name="Brass C360 (Free-Machining)",
        designation="C36000",
        density=8.49,
        youngs_modulus=97.0,
        yield_strength=310.0,
        ultimate_strength=385.0,
        thermal_expansion=20.5,
        hardness="HB 120 (half hard)",
        machinability="Excellent — 100% machinability rating",
        finish="Mirror polish on film contact surfaces",
    ),
    "alu_6061_t6": Material(
        name="Aluminum 6061-T6",
        designation="6061-T6",
        density=2.70,
        youngs_modulus=68.9,
        yield_strength=276.0,
        ultimate_strength=310.0,
        thermal_expansion=23.6,
        hardness="HB 95",
        machinability="Good — use carbide tooling",
        finish="Black anodize Type II, 15-25 um",
    ),
    "steel_302": Material(
        name="Stainless Steel 302 (Spring Temper)",
        designation="AISI 302",
        density=7.86,
        youngs_modulus=193.0,
        yield_strength=520.0,
        ultimate_strength=860.0,
        thermal_expansion=17.3,
        hardness="HRC 38-42 (spring temper)",
        machinability="Fair — requires slow feeds",
        finish="Passivated",
    ),
    "steel_4140": Material(
        name="Chrome-Moly Steel 4140",
        designation="AISI 4140",
        density=7.85,
        youngs_modulus=205.0,
        yield_strength=655.0,
        ultimate_strength=1020.0,
        thermal_expansion=12.3,
        hardness="HRC 28-32",
        machinability="Good when annealed",
        finish="Black oxide",
    ),
    "delrin_150": Material(
        name="Delrin 150 (Acetal Homopolymer)",
        designation="POM-H",
        density=1.42,
        youngs_modulus=3.1,
        yield_strength=70.0,
        ultimate_strength=70.0,
        thermal_expansion=110.0,
        hardness="HRM 94",
        machinability="Excellent — self-lubricating",
        finish="As machined",
    ),
}

# Material assignments
MATERIAL_USAGE = {
    "film_gate":      "brass_c360",
    "pressure_plate": "steel_302",
    "shutter_disc":   "alu_6061_t6",
    "body_shell":     "alu_6061_t6",
    "main_shaft":     "steel_4140",
    "cam":            "steel_4140",
    "claw":           "steel_4140",
    "gears":          "delrin_150",
    "registration_pin": "steel_4140",
}


# =========================================================================
# BEARINGS
# =========================================================================

@dataclass(frozen=True)
class Bearing:
    designation: str
    bore: float         # mm — ID
    od: float           # mm — OD
    width: float        # mm — axial width
    seal: str           # ZZ = shielded, 2RS = sealed
    dynamic_load: float # N — C rating
    static_load: float  # N — C0 rating
    max_rpm: int


BEARINGS = {
    "main_shaft": Bearing(
        designation="694ZZ",
        bore=4.0, od=11.0, width=4.0,
        seal="ZZ", dynamic_load=680.0, static_load=270.0,
        max_rpm=36000),
    "cam_follower": Bearing(
        designation="683ZZ",
        bore=3.0, od=7.0, width=3.0,
        seal="ZZ", dynamic_load=340.0, static_load=100.0,
        max_rpm=45000),
    "shutter_shaft_support": Bearing(
        designation="694ZZ",
        bore=4.0, od=11.0, width=4.0,
        seal="ZZ", dynamic_load=680.0, static_load=270.0,
        max_rpm=36000),
}


# =========================================================================
# MOTOR
# =========================================================================

@dataclass(frozen=True)
class MotorSpec:
    """Mabuchi FF-130SH (or equivalent micro DC motor)."""

    model: str = "FF-130SH"
    shaft_dia: float = 2.0          # mm
    shaft_length: float = 6.5       # mm
    body_dia: float = 20.4          # mm — cylindrical body OD
    body_length: float = 25.0       # mm — excluding shaft
    mount_hole_spacing: float = 15.0  # mm — between M3 holes
    nominal_voltage: float = 6.0    # V
    no_load_rpm: int = 9600         # RPM at 6V
    no_load_current_ma: int = 120   # mA
    stall_current_ma: int = 2200    # mA
    stall_torque_gcm: float = 55.0  # g-cm
    rated_torque_gcm: float = 11.5  # g-cm (max efficiency point)
    rated_rpm: int = 7800           # RPM at rated torque
    rated_current_ma: int = 500     # mA
    weight_g: float = 18.0          # grams


MOTOR = MotorSpec()


# =========================================================================
# GEARBOX
# =========================================================================

@dataclass
class GearboxSpec:
    """Gear reduction between motor and main shaft."""

    ratio: float = 15.0             # motor turns : shaft turns
    stages: int = 2                 # number of gear stages

    # Stage 1: motor pinion → intermediate gear
    stage1_pinion_teeth: int = 10
    stage1_gear_teeth: int = 50     # ratio = 5:1
    stage1_module: float = 0.5      # mm — metric gear module

    # Stage 2: intermediate pinion → output gear
    stage2_pinion_teeth: int = 12
    stage2_gear_teeth: int = 36     # ratio = 3:1
    stage2_module: float = 0.7      # mm

    # Combined: 5 × 3 = 15:1
    gear_face_width: float = 3.0    # mm
    gear_pressure_angle: float = 20.0  # degrees
    gear_material: str = "delrin_150"

    # Efficiency estimate
    efficiency: float = 0.85        # 85% — Delrin on Delrin, lubricated

    @property
    def output_rpm_18fps(self) -> float:
        """Main shaft RPM for 18 fps (1 rev per frame)."""
        return 18.0 * 60.0  # 1080 RPM

    @property
    def output_rpm_24fps(self) -> float:
        return 24.0 * 60.0  # 1440 RPM

    @property
    def motor_rpm_18fps(self) -> float:
        return self.output_rpm_18fps * self.ratio  # 16200 RPM

    @property
    def motor_rpm_24fps(self) -> float:
        return self.output_rpm_24fps * self.ratio  # 21600 RPM

    # Pitch circle diameters (mm)
    @property
    def stage1_pinion_pcd(self) -> float:
        return self.stage1_pinion_teeth * self.stage1_module

    @property
    def stage1_gear_pcd(self) -> float:
        return self.stage1_gear_teeth * self.stage1_module

    @property
    def stage2_pinion_pcd(self) -> float:
        return self.stage2_pinion_teeth * self.stage2_module

    @property
    def stage2_gear_pcd(self) -> float:
        return self.stage2_gear_teeth * self.stage2_module

    @property
    def stage1_center_distance(self) -> float:
        return (self.stage1_pinion_pcd + self.stage1_gear_pcd) / 2.0

    @property
    def stage2_center_distance(self) -> float:
        return (self.stage2_pinion_pcd + self.stage2_gear_pcd) / 2.0


GEARBOX = GearboxSpec()


# =========================================================================
# PCB
# =========================================================================

@dataclass(frozen=True)
class PCBSpec:
    width: float = 55.0             # mm
    height: float = 35.0            # mm
    thickness: float = 1.6          # mm
    layers: int = 4
    copper_weight_oz: float = 1.0   # oz/ft^2
    finish: str = "ENIG"            # Electroless Nickel Immersion Gold
    mount_hole_dia: float = 2.2     # mm — M2 clearance
    mount_hole_inset: float = 3.0   # mm — from board edge


PCB = PCBSpec()


# =========================================================================
# BATTERY / POWER
# =========================================================================

@dataclass(frozen=True)
class BatterySpec:
    """4× AA in 2×2 configuration."""

    cell_type: str = "AA"
    cell_count: int = 4
    cell_voltage_nom: float = 1.5   # V — alkaline
    cell_voltage_min: float = 1.0   # V — end-of-life
    cell_capacity_mah: int = 2500   # mAh — typical alkaline
    cell_dia: float = 14.5          # mm
    cell_length: float = 50.5       # mm
    cell_weight_g: float = 23.0     # grams each

    @property
    def pack_voltage_nom(self) -> float:
        return self.cell_voltage_nom * self.cell_count  # 6.0 V

    @property
    def pack_voltage_min(self) -> float:
        return self.cell_voltage_min * self.cell_count  # 4.0 V

    @property
    def pack_weight_g(self) -> float:
        return self.cell_weight_g * self.cell_count


BATTERY = BatterySpec()


# =========================================================================
# SHUTTER TIMING (derived from geometry)
# =========================================================================

@dataclass
class ShutterTiming:
    """Shutter timing derived from opening angle and frame rate."""

    opening_angle: float = CAMERA.shutter_opening_angle

    @property
    def duty_cycle(self) -> float:
        """Fraction of revolution the shutter is open."""
        return self.opening_angle / 360.0

    def exposure_time(self, fps: int) -> float:
        """Effective shutter speed in seconds at given fps."""
        return self.duty_cycle / fps

    def exposure_reciprocal(self, fps: int) -> float:
        """Shutter speed as 1/N (e.g. 36 for 1/36s at 18fps)."""
        return 1.0 / self.exposure_time(fps)

    # Phase boundaries (degrees of shaft rotation)
    phase1_start: float = 0.0           # shutter open
    phase1_end: float = 180.0           # shutter closes
    phase2_start: float = 180.0         # claw engage begins
    phase2_end: float = 230.0           # claw fully engaged
    phase3_start: float = 230.0         # pulldown begins
    phase3_end: float = 330.0           # pulldown complete
    phase4_start: float = 330.0         # claw retract
    phase4_end: float = 360.0           # cycle complete

    @property
    def pulldown_arc(self) -> float:
        """Degrees of shaft rotation devoted to pulldown."""
        return self.phase3_end - self.phase3_start  # 100 deg

    def pulldown_time(self, fps: int) -> float:
        """Pulldown duration in seconds."""
        return (self.pulldown_arc / 360.0) / fps

    def settle_time(self, fps: int) -> float:
        """Film settling time (phase 4) in seconds."""
        return ((self.phase4_end - self.phase4_start) / 360.0) / fps


SHUTTER = ShutterTiming()


# =========================================================================
# ENCODER / FIRMWARE PARAMETERS
# =========================================================================

@dataclass(frozen=True)
class EncoderSpec:
    """Optical encoder disc on main shaft — 1 slot per revolution."""
    slots_per_rev: int = 1
    slot_width_deg: float = 10.0    # angular width of the slot
    sensor_type: str = "slotted_optical"
    sensor_gap: float = 3.0         # mm — LED to phototransistor gap
    flag_width: float = 2.0         # mm — notch for sensor


ENCODER = EncoderSpec()


@dataclass(frozen=True)
class FirmwareParams:
    """Constants matching the embedded firmware."""
    pid_kp: float = 1.8
    pid_ki: float = 0.9
    pid_kd: float = 0.05
    pid_interval_ms: int = 20
    pwm_frequency_hz: int = 1000
    pwm_duty_min: int = 50
    pwm_duty_max: int = 999
    ramp_step: int = 5
    ramp_interval_ms: int = 10
    stall_timeout_ms: int = 200
    adc_sample_hz: int = 100
    adc_filter_size: int = 16
    low_battery_mv: int = 4200


FIRMWARE = FirmwareParams()


# =========================================================================
# DERIVED VALUES — computed from the parameters above
# =========================================================================

class DerivedValues:
    """Values computed from the primary specs.  Call refresh() if you
    change any CAMERA parameters at runtime."""

    def __init__(self):
        self.refresh()

    def refresh(self):
        # Film plane position (from front face of body)
        self.film_plane_y = CMOUNT.flange_focal_dist + CAMERA.wall_thickness

        # Shutter disc center (between lens and gate)
        self.shutter_center_y = self.film_plane_y - CAMERA.shutter_to_gate_clearance \
                                - CAMERA.shutter_thickness / 2

        # Motor shaft speed at each fps
        self.motor_rpm_18 = GEARBOX.motor_rpm_18fps
        self.motor_rpm_24 = GEARBOX.motor_rpm_24fps

        # Motor voltage estimate (linear approx from no-load to rated)
        self.motor_voltage_18fps = MOTOR.nominal_voltage * (
            GEARBOX.motor_rpm_18fps / MOTOR.no_load_rpm)
        self.motor_voltage_24fps = MOTOR.nominal_voltage * (
            GEARBOX.motor_rpm_24fps / MOTOR.no_load_rpm)

        # Exposure times
        self.shutter_speed_18 = SHUTTER.exposure_time(18)  # 1/36 s
        self.shutter_speed_24 = SHUTTER.exposure_time(24)  # 1/48 s

        # Pulldown velocity (mm/s)
        self.pulldown_vel_18 = FILM.perf_pitch / SHUTTER.pulldown_time(18)
        self.pulldown_vel_24 = FILM.perf_pitch / SHUTTER.pulldown_time(24)

        # Film consumption (meters per minute)
        self.film_consumption_18 = FILM.perf_pitch * 18 * 60 / 1000  # m/min
        self.film_consumption_24 = FILM.perf_pitch * 24 * 60 / 1000

        # Battery life estimate (minutes at 24fps)
        motor_current_a = MOTOR.rated_current_ma / 1000.0
        self.battery_life_24fps_min = (BATTERY.cell_capacity_mah / 1000.0) / \
                                       motor_current_a * 60

        # Gear pitch circle diameters
        self.gear1_pinion_pcd = GEARBOX.stage1_pinion_pcd
        self.gear1_gear_pcd = GEARBOX.stage1_gear_pcd
        self.gear2_pinion_pcd = GEARBOX.stage2_pinion_pcd
        self.gear2_gear_pcd = GEARBOX.stage2_gear_pcd

        # Weight estimates (rough, body only)
        body_vol_cm3 = (CAMERA.body_length * CAMERA.body_height * CAMERA.body_depth -
                        (CAMERA.body_length - 2*CAMERA.wall_thickness) *
                        (CAMERA.body_height - 2*CAMERA.wall_thickness) *
                        (CAMERA.body_depth - 2*CAMERA.wall_thickness)) / 1000.0
        alu = MATERIALS["alu_6061_t6"]
        self.body_weight_g = body_vol_cm3 * alu.density
        self.total_weight_g = self.body_weight_g + BATTERY.pack_weight_g + \
                              MOTOR.weight_g + 50  # 50g estimate for internals


DERIVED = DerivedValues()


# =========================================================================
# Convenience: print a summary
# =========================================================================

def print_specs():
    """Print a human-readable summary of all key specifications."""
    sep = "=" * 68
    print(sep)
    print("  SUPER 8 CAMERA — MASTER SPECIFICATIONS")
    print(sep)
    print()
    print("  KODAK SUPER 8 FILM")
    print(f"    Frame:         {FILM.frame_w} x {FILM.frame_h} mm")
    print(f"    Perf pitch:    {FILM.perf_pitch} mm")
    print(f"    Perf size:     {FILM.perf_w} x {FILM.perf_h} mm")
    print(f"    Film width:    {FILM.width} mm")
    print(f"    Thickness:     {FILM.thickness} mm")
    print()
    print("  C-MOUNT LENS")
    print(f"    Thread:        {CMOUNT.thread_od}mm, {CMOUNT.thread_tpi} TPI")
    print(f"    Flange dist:   {CMOUNT.flange_focal_dist} mm")
    print()
    print("  CAMERA BODY")
    print(f"    Envelope:      {CAMERA.body_length} x {CAMERA.body_height} x "
          f"{CAMERA.body_depth} mm")
    print(f"    Wall:          {CAMERA.wall_thickness} mm ({MATERIAL_USAGE['body_shell']})")
    print(f"    Est. weight:   {DERIVED.total_weight_g:.0f} g (with batteries)")
    print()
    print("  SHUTTER")
    print(f"    Opening:       {CAMERA.shutter_opening_angle} deg")
    print(f"    Speed @18fps:  1/{SHUTTER.exposure_reciprocal(18):.0f} s")
    print(f"    Speed @24fps:  1/{SHUTTER.exposure_reciprocal(24):.0f} s")
    print()
    print("  DRIVETRAIN")
    print(f"    Motor:         {MOTOR.model} ({MOTOR.nominal_voltage}V)")
    print(f"    Gear ratio:    {GEARBOX.ratio}:1 ({GEARBOX.stages}-stage)")
    print(f"    Shaft @18fps:  {GEARBOX.output_rpm_18fps:.0f} RPM")
    print(f"    Shaft @24fps:  {GEARBOX.output_rpm_24fps:.0f} RPM")
    print(f"    Motor @24fps:  {GEARBOX.motor_rpm_24fps:.0f} RPM")
    print()
    print("  POWER")
    print(f"    Battery:       {BATTERY.cell_count}x{BATTERY.cell_type} "
          f"({BATTERY.pack_voltage_nom}V nom)")
    print(f"    Est. runtime:  {DERIVED.battery_life_24fps_min:.0f} min @24fps")
    print()
    print(f"  TOLERANCES")
    print(f"    Gate aperture: +/-{TOL.gate_aperture} mm")
    print(f"    Reg pin dia:   {CAMERA.reg_pin_dia} "
          f"+{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm")
    print(f"    CNC general:   +/-{TOL.cnc_general} mm")
    print()
    print("  " + sep)


if __name__ == "__main__":
    print_specs()
