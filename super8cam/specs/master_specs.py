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
    CAM_SPEC    Cam and follower mechanism dimensions
    SHAFT_DIMS  Main shaft section dimensions
    TRIGGER_SPEC  Trigger lever and switch dimensions
    VF_SPEC     Viewfinder tube and optics
    DOOR_SPEC   Battery and cartridge door dimensions
    PP_SPEC     Pressure plate dimensions
    RECV_SPEC   Cartridge receiver, spindle, and latch
    ANALYSIS    Analysis thresholds and physical constants
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
    shutter_od: float = 28.0        # mm — disc outer diameter
    shutter_thickness: float = 0.8  # mm — aluminum sheet
    shutter_shaft_hole: float = 4.0 # mm — matches main shaft
    shutter_keyway_w: float = 1.0   # mm
    shutter_keyway_depth: float = 0.5  # mm
    shutter_to_gate_clearance: float = 0.3  # mm
    shutter_flag_w: float = 2.0     # mm — encoder flag notch width
    shutter_flag_depth: float = 1.0 # mm — encoder flag radial depth
    shutter_max_imbalance_gmm: float = 0.1  # g·mm — static imbalance limit

    # Frame rates
    fps_options: List[int] = field(default_factory=lambda: [18, 24])

    # Main shaft
    shaft_dia: float = 4.0          # mm
    shaft_length: float = 38.0      # mm — total usable length

    # Film gate (brass C360)
    gate_plate_w: float = 24.0      # mm — overall gate width
    gate_plate_h: float = 20.0      # mm — overall gate height (film travel dir)
    gate_plate_thick: float = 4.0   # mm — overall gate thickness
    gate_channel_w: float = 8.2     # mm — film channel width (film 8.0 + clearance)
    gate_channel_depth: float = 0.20  # mm — film rides in this recess
    gate_rail_w: float = 1.5        # mm — pressure plate contact rail width
    gate_rail_h: float = 0.15       # mm — rail raised above channel floor
    gate_aperture_taper: float = 0.2  # mm — total widening on lens side
    gate_aperture_chamfer: float = 0.05  # mm — lens-side chamfer
    gate_perf_slot_w: float = 1.5   # mm — perforation clearance slot width
    gate_claw_slot_w: float = 2.0   # mm — claw access slot width
    gate_claw_slot_h: float = 8.0   # mm — claw access slot height
    gate_reg_pin_hole_dia: float = 0.82  # mm — H7 for 0.813mm pin press-fit
    gate_reg_pin_protrusion: float = 0.5  # mm — pin protrusion into channel
    gate_mount_pattern_x: float = 20.0   # mm — bolt pattern horizontal span
    gate_mount_pattern_y: float = 16.0   # mm — bolt pattern vertical span
    gate_m2_thread_depth: float = 3.0    # mm — thread depth for M2 screws
    gate_dowel_dia: float = 2.0     # mm — alignment dowel pin diameter
    gate_dowel_depth: float = 3.0   # mm — alignment dowel pin depth
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
    claw_tip_w: float = 0.5         # mm — must fit inside perforation (1.143mm wide)
    claw_tip_h: float = 0.3         # mm — tip thickness
    claw_tip_radius: float = 0.1    # mm — fillet on tip to avoid tearing film
    claw_engage_depth: float = 0.5  # mm — into perforation
    claw_retract_dist: float = 2.5  # mm — clearance when retracted
    claw_arm_length: float = 15.0   # mm — pivot to tip
    claw_arm_w: float = 3.0         # mm
    claw_arm_thick: float = 1.0     # mm
    claw_pivot_pin_dia: float = 1.5   # mm
    claw_pivot_pin_length: float = 5.0  # mm — protrudes through arm + link
    claw_eclip_groove_w: float = 0.4   # mm — e-clip groove width on pivot pin

    # Cam follower (drives the claw) — summary dims; see CAM_SPEC for full detail
    cam_od: float = 16.0            # mm — cam disc outer diameter
    cam_id: float = 4.0             # mm — shaft bore (= shaft_dia)
    cam_width: float = 3.0          # mm — axial width
    cam_lobe_lift: float = 4.234    # mm — pulldown distance
    cam_follower_dia: float = 3.0   # mm — roller diameter

    # Film channel / guide rails
    film_channel_length: float = 30.0  # mm — total guided length around gate
    film_channel_width: float = 8.2    # mm — slight clearance over film width

    # Lens mount boss
    lens_boss_od: float = 30.0      # mm — outer diameter of mount boss
    lens_boss_protrusion: float = 5.0  # mm — protrudes from front face
    lens_mount_offset_x: float = -18.0  # mm — left of body center
    lens_clearance_bore_dia: float = 26.0  # mm — clears lens rear element
    lens_locating_pin_dia: float = 1.5    # mm — anti-rotation pin at 12 o'clock
    lens_locating_pin_depth: float = 2.0  # mm — blind hole depth
    lens_mount_hole_angles: List[int] = field(default_factory=lambda: [0, 120, 240])

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
    motor_mount_bracket_thick: float = 3.0   # mm — motor cradle wall thickness

    # Gearbox housing
    gearbox_housing_wall: float = 2.0  # mm — gearbox enclosure wall thickness

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
    reg_pin_dia_minus: float = 0.002    # mm — max undersize
    reg_pin_position: float = 0.005     # mm — pin to aperture center (jig-ground)

    # Shutter clearance
    shutter_clearance: float = 0.01     # mm — precision ground shim sets gap

    # General CNC machining
    cnc_general: float = 0.05           # mm
    cnc_fine: float = 0.02              # mm

    # Fits (ISO system)
    press_fit_hole: str = "H6"          # hole tolerance band
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

    ratio: float = 6.0              # motor turns : shaft turns
    stages: int = 2                 # number of gear stages

    # Stage 1: motor pinion → intermediate gear
    stage1_pinion_teeth: int = 12
    stage1_gear_teeth: int = 36     # ratio = 3:1
    stage1_module: float = 0.5      # mm — metric gear module

    # Stage 2: intermediate pinion → output gear
    stage2_pinion_teeth: int = 15
    stage2_gear_teeth: int = 30     # ratio = 2:1
    stage2_module: float = 0.7      # mm

    # Combined: 3 × 2 = 6:1
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
# CAM & FOLLOWER MECHANISM
# =========================================================================

@dataclass(frozen=True)
class CamSpec:
    """Pulldown face cam, secondary eccentric, follower, and guide hardware."""

    # Cam disc (pulldown face cam)
    cam_od: float = 16.0            # mm — outer diameter of disc
    cam_thick: float = 3.0          # mm — axial thickness
    cam_keyway_w: float = 1.0       # mm — drive keyway width
    cam_keyway_depth: float = 0.5   # mm

    # Groove in front face
    groove_w: float = 1.5           # mm — groove width
    groove_depth: float = 1.0       # mm — groove depth into face
    groove_track_r_min: float = 4.5 # mm — inner edge of groove at dwell

    # Secondary eccentric (engage / retract)
    eccentric_od: float = 10.0      # mm — outer diameter
    eccentric_thick: float = 3.0    # mm
    eccentric_offset: float = 0.8   # mm — eccentricity (produces ~2mm claw travel)
    eccentric_phase: float = 90.0   # degrees ahead of pulldown cam

    # Follower pin (rides in cam groove)
    follower_pin_dia: float = 0.8   # mm — rides in the 1.5mm groove
    follower_pin_length: float = 3.0  # mm

    # Connecting link (eccentric → claw horizontal motion)
    link_length: float = 8.0        # mm — center-to-center
    link_w: float = 3.0             # mm — width
    link_thick: float = 1.0         # mm — thickness
    link_bore_claw: float = 1.5     # mm — pivot pin bore on claw end

    # Guide rail pins (constrain claw to vertical travel)
    guide_pin_dia: float = 1.5      # mm
    guide_pin_length: float = 15.0  # mm
    guide_pin_spacing: float = 10.0 # mm — between the two guide pins

    # E-clip retaining clips
    eclip_od: float = 3.0           # mm
    eclip_thick: float = 0.3        # mm
    eclip_bore: float = 1.5         # mm

    # Horizontal claw stroke (engage/retract travel)
    stroke_h: float = 2.0           # mm


CAM_SPEC = CamSpec()


# =========================================================================
# MAIN SHAFT SECTIONS
# =========================================================================

@dataclass(frozen=True)
class ShaftSpec:
    """Stepped main shaft section dimensions.

    Layout (rear to front): gear end → bearing 1 → cam → bearing 2 →
    shutter → encoder end.  Bearing seats and shaft dia from CAMERA.
    """

    # Section 1: Gear end (rear)
    sec1_dia: float = 3.0           # mm — reduced diameter for gear bore
    sec1_len: float = 8.0           # mm
    sec1_keyway_w: float = 0.6      # mm — gear drive keyway width
    sec1_keyway_depth: float = 0.3  # mm

    # Section 3: Cam section
    sec3_len: float = 6.0           # mm — room for pulldown cam + eccentric
    sec3_keyway_w: float = 1.0      # mm — cam drive keyway
    sec3_keyway_depth: float = 0.5  # mm

    # Section 5: Shutter section
    sec5_len: float = 3.0           # mm

    # Section 6: Encoder end (front)
    sec6_dia: float = 3.0           # mm — reduced for encoder disc
    sec6_len: float = 4.0           # mm
    sec6_thread_dia: float = 3.0    # mm — M3 external thread
    sec6_thread_len: float = 3.0    # mm — threaded length at tip

    # Transitions
    chamfer: float = 0.3            # mm — 45° chamfer at diameter transitions


SHAFT_DIMS = ShaftSpec()


# =========================================================================
# TRIGGER MECHANISM
# =========================================================================

@dataclass(frozen=True)
class TriggerSpec:
    """Trigger lever, microswitch, and return spring dimensions."""

    # Lever body
    lever_length: float = 22.0      # mm — pivot to finger tip
    lever_width: float = 10.0       # mm — across finger
    lever_thick: float = 3.0        # mm — lever body thickness

    # Finger pad
    pad_l: float = 12.0             # mm — along lever
    pad_w: float = 8.0              # mm — across finger
    pad_depth: float = 0.8          # mm — concave depth for ergonomics

    # Pivot
    pivot_pin_dia: float = 2.0      # mm
    pivot_bushing_od: float = 4.0   # mm — boss around pivot

    # Internal actuator arm (extends past pivot toward microswitch)
    arm_length: float = 8.0         # mm — from pivot toward switch
    arm_thick: float = 2.0          # mm

    # Microswitch placeholder
    switch_l: float = 6.0           # mm
    switch_w: float = 3.0           # mm
    switch_h: float = 4.0           # mm
    switch_button_dia: float = 1.0  # mm — actuator button
    switch_button_h: float = 1.0    # mm — button protrusion

    # Return spring
    spring_od: float = 3.0          # mm
    spring_free_length: float = 5.0 # mm
    spring_wire_dia: float = 0.3    # mm
    spring_post_dia: float = 1.5    # mm — post that guides the spring

    # Total trigger travel
    travel: float = 2.0             # mm — at the finger pad


TRIGGER_SPEC = TriggerSpec()


# =========================================================================
# VIEWFINDER
# =========================================================================

@dataclass(frozen=True)
class ViewfinderSpec:
    """Galilean optical viewfinder tube, optics, and mounting."""

    # Tube dimensions
    tube_w: float = 10.0            # mm — width (horizontal)
    tube_h: float = 8.0             # mm — height (vertical)
    tube_length: float = 40.0       # mm — front to rear
    tube_wall: float = 1.0          # mm — wall thickness

    # Optical elements
    lens_dia: float = 8.0           # mm — both elements
    lens_thick: float = 1.5         # mm — disc thickness for modeling
    front_focal_length: float = -20.0  # mm — plano-concave (diverging)
    rear_focal_length: float = 30.0    # mm — plano-convex (eyepiece)
    rear_element_z: float = 2.0     # mm from eye end
    front_sag: float = 0.4          # mm — concave surface sag

    # Bright-line frame
    frame_wire_dia: float = 0.3     # mm — wire thickness

    # Mounting tabs
    tab_w: float = 6.0              # mm — each tab width
    tab_h: float = 5.0              # mm — extends below tube
    tab_thick: float = 2.0          # mm — thickness along optical axis
    tab_spacing: float = 30.0       # mm — center-to-center along tube

    # Viewfinder offset from taking lens
    offset_up: float = 20.0         # mm — above optical axis
    offset_left: float = 5.0        # mm — to the left

    # Optical performance
    fov_horizontal_deg: float = 42.0  # degrees — horizontal field of view
    magnification: float = 0.5        # wide-angle for framing


VF_SPEC = ViewfinderSpec()


# =========================================================================
# DOOR DIMENSIONS (battery + cartridge)
# =========================================================================

@dataclass(frozen=True)
class DoorSpec:
    """Battery door and cartridge door dimensions."""

    # Battery door
    batt_overlap: float = 2.0          # mm — overlap beyond pocket opening
    batt_fillet: float = 1.5           # mm — corner radius
    batt_trap_groove_w: float = 1.0    # mm — light-trap groove width
    batt_trap_groove_depth: float = 0.8  # mm — light-trap step depth
    batt_hinge_pin_dia: float = 1.5    # mm
    batt_hinge_ear_w: float = 4.0      # mm — each ear
    batt_hinge_ear_h: float = 3.0      # mm — extends from door edge
    batt_latch_slot_w: float = 10.0    # mm — coin slot width
    batt_latch_slot_h: float = 2.0     # mm — slot height
    batt_latch_slot_depth: float = 1.0 # mm
    batt_contact_dia: float = 5.0      # mm — spring button diameter
    batt_contact_height: float = 1.0   # mm — protrusion

    # Cartridge door
    cart_overlap: float = 2.0          # mm — door overlaps body
    cart_fillet: float = 2.0           # mm — corner radius
    cart_trap_w: float = 1.0           # mm — light-trap groove width
    cart_trap_depth: float = 1.5       # mm — step depth
    cart_trap_rim_h: float = 1.5       # mm — raised rim height on interior
    cart_hinge_pin_dia: float = 2.0    # mm
    cart_hinge_knuckle_dia: float = 4.0  # mm — knuckle OD
    cart_hinge_knuckle_w: float = 5.0  # mm — each knuckle width
    cart_latch_button_dia: float = 6.0 # mm
    cart_latch_button_length: float = 4.0  # mm — protrusion when unlatched
    cart_latch_pocket_depth: float = 8.0   # mm — bore into door edge
    cart_foam_w: float = 3.0           # mm — foam channel width
    cart_foam_depth: float = 1.0       # mm — recess depth


DOOR_SPEC = DoorSpec()


# =========================================================================
# PRESSURE PLATE
# =========================================================================

@dataclass(frozen=True)
class PressurePlateSpec:
    """Spring-steel pressure plate dimensions and spring parameters."""

    # Plate body
    plate_w: float = 22.0           # mm — slightly smaller than gate
    plate_h: float = 18.0           # mm
    plate_thick: float = 0.3        # mm — thin spring steel

    # Raised contact pads — align with gate's pressure rails
    pad_w: float = 3.0              # mm — width (X direction)
    pad_l: float = 12.0             # mm — length (Y direction, along film)
    pad_h: float = 0.05             # mm — raised above plate surface

    # Aperture window clearance
    window_clearance: float = 0.5   # mm — each side beyond film frame

    # Leaf spring geometry
    spring_count: int = 2           # one from top, one from bottom
    spring_w: float = 4.0           # mm — beam width
    spring_l: float = 6.0           # mm — free cantilever length


PP_SPEC = PressurePlateSpec()


# =========================================================================
# CARTRIDGE RECEIVER
# =========================================================================

@dataclass(frozen=True)
class CartridgeReceiverSpec:
    """Cartridge receiver pocket, registration pins, spindle, and latch."""

    # Pocket dimensions
    pocket_clearance: float = 0.5     # mm — all-around insertion clearance
    pocket_wall: float = 2.0          # mm — receiver wall thickness

    # Registration pins (locate cartridge relative to gate)
    reg_pin_dia: float = 2.0          # mm
    reg_pin_height: float = 3.0       # mm — protrusion above pocket floor
    reg_pin_fit: float = 0.01         # mm — H7/h6 alignment fit
    reg_pin1_offset_x: float = 5.0    # mm — pin 1 offset from exit slot
    reg_pin1_offset_y: float = 8.0    # mm — pin 1 offset from edge
    reg_pin2_offset_x: float = 12.0   # mm — pin 2 offset from far side
    reg_pin2_offset_y: float = 8.0    # mm — pin 2 offset from opposite corner

    # Takeup drive spindle
    spindle_dia: float = 6.0          # mm — body diameter
    spindle_tip_dia: float = 4.0      # mm — cross-shaped engagement tip
    spindle_tip_height: float = 5.0   # mm — engagement depth into cartridge
    spindle_cross_w: float = 1.5      # mm — width of each cross arm
    spindle_total_h: float = 10.0     # mm — total spindle length

    # Friction clutch
    clutch_od: float = 10.0           # mm
    clutch_thick: float = 1.5         # mm
    clutch_spring_force: float = 0.5  # N — slip torque ~1.5 mN·m

    # Leaf spring latch
    latch_w: float = 8.0              # mm — spring width
    latch_l: float = 15.0             # mm — cantilever length
    latch_thick: float = 0.5          # mm — spring steel
    latch_force: float = 1.0          # N — holds cartridge down


RECV_SPEC = CartridgeReceiverSpec()


# =========================================================================
# ANALYSIS PARAMETERS — physical constants and thresholds
# =========================================================================

@dataclass(frozen=True)
class AnalysisParams:
    """Physical constants, material properties, and analysis thresholds
    used by kinematics, thermal, timing, and tolerance stack-up modules."""

    # Film physical properties
    film_density_g_cm3: float = 1.39      # PET base density
    mu_film_gate: float = 0.15            # friction coefficient film-on-brass

    # Force limits
    max_perf_force_n: float = 1.0         # our limit (Kodak allows 1.5 N)

    # Thermal: convection coefficients
    ambient_temp_c: float = 25.0          # standard room temperature
    natural_convection_h: float = 10.0    # W/m²·K — still air
    forced_convection_h: float = 25.0     # W/m²·K — walking / light breeze

    # Thermal: film zone limits
    film_zone_limit_c: float = 35.0       # emulsion sensitivity drift onset
    film_absolute_limit_c: float = 50.0   # base softening concern

    # Thermal: motor model
    motor_thermal_resistance: float = 10.0  # K/W — motor to body
    gate_thermal_fraction: float = 0.3      # coupling factor (0=body, 1=motor)
    motor_load_factor: float = 0.15         # light mechanical load fraction

    # Electrical: regulators / PCB
    logic_voltage_v: float = 3.3
    logic_current_ma: float = 50.0
    motor_driver_dropout_v: float = 0.2   # MOSFET Rds_on approximate
    pcb_misc_power_mw: float = 30.0       # misc PCB components

    # Timing validation thresholds
    claw_engage_threshold: float = 1.0    # mm — claw x > this = engaged
    pin_engage_hysteresis: float = 0.1    # mm — pin engages when claw_x < this
    pin_disengage_hysteresis: float = 0.3 # mm — pin disengages when claw_x > this
    min_dwell_deg: float = 5.0            # degrees — min film dwell before shutter
    film_vel_threshold: float = 0.05      # mm/deg — below this = stationary
    timing_resolution: int = 720          # angular steps for timing analysis

    # Tolerance stack-up parameters
    bearing_radial_play: float = 0.010    # mm — 694ZZ radial play per bearing
    disc_flatness: float = 0.02           # mm — precision stamped + ground
    gate_flatness: float = 0.01           # mm — precision lapped brass
    bearing_span: float = 10.0            # mm — span between shaft bearings
    shutter_overhang: float = 5.0         # mm — disc past front bearing
    design_min_clearance: float = 0.05    # mm — minimum acceptable shutter gap

    # Flange distance acceptance
    flange_acceptance_tol: float = 0.02   # mm — ±tolerance for C-mount

    # Registration accuracy
    kodak_registration_spec: float = 0.025  # mm — Kodak ±frame-to-frame spec
    perf_size_tolerance: float = 0.02     # mm — Kodak film manufacturing tolerance
    gate_body_alignment: float = 0.008    # mm — dowel pin alignment H6
    claw_pulldown_accuracy: float = 0.003 # mm — cam profile + guided claw
    film_stretch_tolerance: float = 0.003 # mm — PET elastic strain at 0.5N


ANALYSIS = AnalysisParams()


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
    phase1_start: float = 10.0          # shutter open
    phase1_end: float = 180.0           # shutter closes
    phase2_start: float = 350.0         # claw engage begins (wraps 0°)
    phase2_end: float = 5.0             # claw fully engaged
    phase3_start: float = 190.0         # pulldown begins
    phase3_end: float = 340.0           # pulldown complete
    phase4_start: float = 340.0         # claw retract
    phase4_end: float = 350.0           # retract complete

    @property
    def pulldown_arc(self) -> float:
        """Degrees of shaft rotation devoted to pulldown."""
        return self.phase3_end - self.phase3_start  # 150 deg

    def pulldown_time(self, fps: int) -> float:
        """Pulldown duration in seconds."""
        return (self.pulldown_arc / 360.0) / fps

    def settle_time(self, fps: int) -> float:
        """Film settling time (dwell before shutter opens) in seconds."""
        # Dwell is 5°→10° = 5°
        return (5.0 / 360.0) / fps


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
