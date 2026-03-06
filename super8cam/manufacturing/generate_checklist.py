"""generate_checklist.py — Production Build Checklist Generator

Generates a multi-page PDF checklist for building one Super 8 camera.

Sections:
  1. INCOMING INSPECTION — verify every purchased/machined part
  2. SUB-ASSEMBLY: FILM TRANSPORT — gate, claw, registration, pressure plate
  3. SUB-ASSEMBLY: SHUTTER — disc, shaft, bearings, clearance
  4. SUB-ASSEMBLY: DRIVETRAIN — gears, motor, gearbox
  5. SUB-ASSEMBLY: ELECTRONICS — PCB, flash, motor/metering test
  6. FINAL ASSEMBLY — numbered steps with torque values, wiring
  7. FINAL QC — serial number, calibration, cosmetic, functional sign-off

Each item has: checkbox, specification, measured value field, pass/fail,
technician initials, and date.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional

from super8cam.specs.master_specs import (
    FILM, CAMERA, CMOUNT, TOL, MOTOR, GEARBOX, BATTERY, PCB, BEARINGS,
    FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE,
)
from super8cam.manufacturing.gdt_standards import TORQUE_SPECS


# =========================================================================
# CHECKLIST ITEM DATACLASS
# =========================================================================

@dataclass
class CheckItem:
    """Single checklist line item."""
    step: str                   # Step number (e.g. "1.1", "2.3")
    description: str            # What to do / verify
    spec: str                   # Target value / tolerance
    notes: str = ""             # Additional instructions


# =========================================================================
# SECTION 1: INCOMING INSPECTION
# =========================================================================

def _section_incoming() -> List[CheckItem]:
    """Incoming inspection for every part — 3 critical dims each."""
    items = []

    # Film gate
    items.extend([
        CheckItem("1.01", "Film Gate — aperture width",
                  f"{FILM.frame_w} ±{TOL.gate_aperture} mm",
                  "Use calibrated pin gauge set"),
        CheckItem("1.02", "Film Gate — aperture height",
                  f"{FILM.frame_h} ±{TOL.gate_aperture} mm"),
        CheckItem("1.03", "Film Gate — channel depth",
                  f"{CAMERA.gate_channel_depth} ±{TOL.gate_channel_depth} mm",
                  "Depth micrometer"),
        CheckItem("1.04", "Film Gate — visual inspection",
                  "No burrs, scratches on film contact surfaces",
                  "Inspect under 10× loupe"),
    ])

    # Registration pin
    items.extend([
        CheckItem("1.05", "Registration Pin — diameter",
                  f"{CAMERA.reg_pin_dia} +{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm",
                  "Micrometer"),
        CheckItem("1.06", "Registration Pin — length",
                  f"{CAMERA.reg_pin_length} ±0.05 mm"),
        CheckItem("1.07", "Registration Pin — surface finish",
                  f"Ra ≤ {TOL.bearing_seat_ra} µm",
                  "Visual: smooth, polished tip"),
    ])

    # Main shaft
    items.extend([
        CheckItem("1.08", "Main Shaft — overall length",
                  f"{CAMERA.shaft_length} ±{TOL.cnc_general} mm"),
        CheckItem("1.09", "Main Shaft — bearing seat diameter",
                  f"{CAMERA.shaft_dia} mm {TOL.bearing_shaft} fit",
                  "Micrometer at both bearing seats"),
        CheckItem("1.10", "Main Shaft — keyway width",
                  f"{CAMERA.shutter_keyway_w} ±{TOL.cnc_fine} mm"),
    ])

    # Shutter disc
    items.extend([
        CheckItem("1.11", "Shutter Disc — outer diameter",
                  f"{CAMERA.shutter_od} ±0.1 mm"),
        CheckItem("1.12", "Shutter Disc — thickness",
                  f"{CAMERA.shutter_thickness} ±0.05 mm",
                  "Micrometer"),
        CheckItem("1.13", "Shutter Disc — bore diameter",
                  f"{CAMERA.shutter_shaft_hole} mm {TOL.press_fit_hole} fit"),
        CheckItem("1.14", "Shutter Disc — visual flatness",
                  "No visible warping",
                  "Lay on granite surface plate"),
    ])

    # Body halves
    items.extend([
        CheckItem("1.15", "Body Left Half — length",
                  f"{CAMERA.body_length} ±{TOL.cnc_general} mm"),
        CheckItem("1.16", "Body Left Half — height",
                  f"{CAMERA.body_height} ±{TOL.cnc_general} mm"),
        CheckItem("1.17", "Body Left Half — wall thickness",
                  f"{CAMERA.wall_thickness} ±{TOL.cnc_general} mm",
                  "Check at 3 locations"),
        CheckItem("1.18", "Body Right Half — matching dimensions",
                  "Same as left half",
                  "Dry-fit both halves, check alignment"),
    ])

    # Bearings
    for bname, brg in BEARINGS.items():
        items.extend([
            CheckItem(f"1.{len(items) + 1:02d}",
                      f"Bearing ({brg.designation}) for {bname} — ID",
                      f"{brg.bore} mm nominal"),
            CheckItem(f"1.{len(items) + 2:02d}",
                      f"Bearing ({brg.designation}) for {bname} — OD",
                      f"{brg.od} mm nominal"),
            CheckItem(f"1.{len(items) + 3:02d}",
                      f"Bearing ({brg.designation}) for {bname} — spin test",
                      "Free rotation, no roughness",
                      "Spin by hand, listen for grinding"),
        ])

    # Gears
    items.extend([
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Stage 1 Pinion (10T) — tooth count and bore",
                  f"10 teeth, M{GEARBOX.stage1_module}, bore ={MOTOR.shaft_dia}mm"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Stage 1 Gear (50T) — tooth count",
                  f"50 teeth, M{GEARBOX.stage1_module}"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Stage 2 Pinion (12T) — tooth count and bore",
                  f"12 teeth, M{GEARBOX.stage2_module}"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Stage 2 Gear (36T) — tooth count and bore",
                  f"36 teeth, M{GEARBOX.stage2_module}, bore ={CAMERA.shaft_dia}mm"),
    ])

    # Motor
    items.extend([
        CheckItem(f"1.{len(items) + 1:02d}",
                  f"Motor ({MOTOR.model}) — shaft diameter",
                  f"{MOTOR.shaft_dia} mm"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  f"Motor — no-load spin test at {MOTOR.nominal_voltage}V",
                  "Smooth rotation, no grinding",
                  "Brief power-on with bench supply"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Motor — current draw (no load)",
                  f"< {MOTOR.no_load_current_ma * 1.5} mA",
                  f"Nominal: {MOTOR.no_load_current_ma} mA"),
    ])

    # PCB
    items.extend([
        CheckItem(f"1.{len(items) + 1:02d}",
                  f"Control PCB — dimensions",
                  f"{PCB.width}×{PCB.height}×{PCB.thickness} mm"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Control PCB — visual solder inspection",
                  "No bridges, cold joints, missing components",
                  "Inspect under 10× loupe"),
        CheckItem(f"1.{len(items) + 1:02d}",
                  "Control PCB — mounting holes",
                  f"4× Ø{PCB.mount_hole_dia} mm clearance"),
    ])

    # Re-number all items sequentially
    for i, item in enumerate(items, 1):
        item.step = f"1.{i:02d}"

    return items


# =========================================================================
# SECTION 2: SUB-ASSEMBLY — FILM TRANSPORT
# =========================================================================

def _section_film_transport() -> List[CheckItem]:
    return [
        CheckItem("2.01",
                  "Press registration pin into film gate",
                  f"Pin protrusion: {CAMERA.reg_pin_length} ±0.05 mm",
                  "Use arbor press.  Verify protrusion with depth gauge."),
        CheckItem("2.02",
                  "Verify pin position relative to aperture center",
                  f"Center-to-pin: {FILM.reg_pin_below_frame_center} ±{TOL.reg_pin_position} mm",
                  "Optical comparator or calibrated pin gauge"),
        CheckItem("2.03",
                  "Attach pressure plate springs to gate body",
                  f"Target force: {CAMERA.pressure_plate_force_n} N per spring",
                  "Springs must seat fully in pockets"),
        CheckItem("2.04",
                  "Install pressure plate onto springs",
                  "Plate must float freely, parallel to gate face",
                  "Press and release — should spring back evenly"),
        CheckItem("2.05",
                  "Film strip pass-through test",
                  "Film slides smoothly with light finger pressure",
                  "Use scrap Super 8 film strip.  Insert from supply side, "
                  "pull through to takeup.  No catching or binding."),
        CheckItem("2.06",
                  "Verify claw passes through gate slot",
                  "Claw tip moves freely in slot, no binding",
                  "Manually cycle claw through full pulldown stroke"),
        CheckItem("2.07",
                  "Verify claw tip engages perforation",
                  f"Claw tip: {CAMERA.claw_tip_w}×{CAMERA.claw_tip_h} mm enters "
                  f"perf {FILM.perf_w}×{FILM.perf_h} mm",
                  "Lay film across gate, manually engage claw into perf"),
        CheckItem("2.08",
                  "Film channel guide rails — smooth edges",
                  "No burrs or sharp edges on guide rail surfaces",
                  "Run finger along rails; check under magnification"),
    ]


# =========================================================================
# SECTION 3: SUB-ASSEMBLY — SHUTTER
# =========================================================================

def _section_shutter() -> List[CheckItem]:
    return [
        CheckItem("3.01",
                  "Press shutter disc onto main shaft",
                  f"Keyway aligned to cam timing mark (180° offset)",
                  "Verify keyway engagement before pressing.  "
                  "Use arbor press — do NOT hammer."),
        CheckItem("3.02",
                  "Verify shutter disc is perpendicular to shaft",
                  "Run-out < 0.05 mm at disc OD",
                  "Spin in V-blocks with dial indicator on disc edge"),
        CheckItem("3.03",
                  "Install main shaft bearings",
                  f"Bearing: {BEARINGS['main_shaft'].designation} "
                  f"({BEARINGS['main_shaft'].bore}×{BEARINGS['main_shaft'].od}×"
                  f"{BEARINGS['main_shaft'].width} mm)",
                  "Press bearings into housing bore.  "
                  "Apply force to outer race only."),
        CheckItem("3.04",
                  "Verify shaft spins freely in bearings",
                  "Shaft spins > 5 seconds from a finger flick",
                  "No axial play, no roughness felt.  "
                  "Time with stopwatch."),
        CheckItem("3.05",
                  "Shutter-to-gate clearance check",
                  f"Gap ≥ {CAMERA.shutter_to_gate_clearance} mm "
                  f"(nominal {CAMERA.shutter_to_gate_clearance} mm)",
                  "Use 0.25 mm feeler gauge between shutter disc "
                  "and film gate face at closest approach."),
        CheckItem("3.06",
                  "Rotate shaft 360° — check for shutter rubbing",
                  "No contact throughout full rotation",
                  "Slowly rotate by hand, listen/feel for contact"),
        CheckItem("3.07",
                  "Verify shutter opening angle",
                  f"{CAMERA.shutter_opening_angle}° ±2°",
                  "Optical protractor or angle gauge on shaft"),
    ]


# =========================================================================
# SECTION 4: SUB-ASSEMBLY — DRIVETRAIN
# =========================================================================

def _section_drivetrain() -> List[CheckItem]:
    return [
        CheckItem("4.01",
                  "Install Stage 1 pinion onto motor shaft",
                  f"10T, M{GEARBOX.stage1_module}, bore Ø{MOTOR.shaft_dia} mm",
                  "Press-fit or set screw.  Verify no axial play."),
        CheckItem("4.02",
                  "Install Stage 1 gear onto intermediate shaft",
                  f"50T, M{GEARBOX.stage1_module}",
                  "Verify mesh with pinion — smooth tooth engagement"),
        CheckItem("4.03",
                  "Install Stage 2 pinion onto intermediate shaft",
                  f"12T, M{GEARBOX.stage2_module}",
                  "Integral with intermediate shaft or pressed on"),
        CheckItem("4.04",
                  "Install Stage 2 gear onto main shaft",
                  f"36T, M{GEARBOX.stage2_module}, bore Ø{CAMERA.shaft_dia} mm",
                  "Verify keyway engagement, no axial play"),
        CheckItem("4.05",
                  "Assemble gearbox housing halves",
                  "All shafts captured, no binding",
                  "Hand-tighten screws first, check rotation, "
                  "then torque to spec"),
        CheckItem("4.06",
                  "Full rotation test — no gear binding",
                  "Main shaft rotates smoothly through 10 full revolutions",
                  "Turn main shaft by hand.  Feel for tight spots, "
                  "listen for clicking."),
        CheckItem("4.07",
                  "Apply gear lubricant",
                  "Light film of PTFE grease on all gear teeth",
                  "Molykote EM-30L or equivalent.  Avoid excess."),
        CheckItem("4.08",
                  "Connect motor, brief run test",
                  "Main shaft turns in correct direction",
                  f"Apply {MOTOR.nominal_voltage}V briefly.  "
                  "Shaft should turn CCW viewed from lens side."),
        CheckItem("4.09",
                  "Verify gear ratio",
                  f"{GEARBOX.ratio}:1 (mark motor shaft, count main shaft revs)",
                  f"{int(GEARBOX.ratio)} motor revolutions = 1 main shaft revolution"),
    ]


# =========================================================================
# SECTION 5: SUB-ASSEMBLY — ELECTRONICS
# =========================================================================

def _section_electronics() -> List[CheckItem]:
    return [
        CheckItem("5.01",
                  "Visual inspection of PCB",
                  "All components present, correct orientation",
                  "Check ICs, polarized caps, LEDs, connectors. "
                  "Use assembly drawing as reference."),
        CheckItem("5.02",
                  "Solder joint inspection",
                  "No bridges, cold joints, or lifted pads",
                  "Inspect under 10× magnification.  "
                  "Reflow any suspect joints."),
        CheckItem("5.03",
                  "Power-on test — 3.3V rail",
                  "3.30 ±0.10 V on LDO output",
                  f"Connect {MOTOR.nominal_voltage}V supply.  "
                  "Measure with DMM at test point."),
        CheckItem("5.04",
                  "Power-on test — current draw (idle)",
                  "< 25 mA total (no motor)",
                  "MCU + regulator + sensor quiescent current"),
        CheckItem("5.05",
                  "Flash firmware via ST-Link",
                  "Programming successful, no errors",
                  "pio run -t upload.  Verify UART startup message."),
        CheckItem("5.06",
                  "UART debug output test",
                  "Telemetry lines at 115200 baud every 500 ms",
                  "Connect serial terminal.  Verify state=IDLE, "
                  "EV and f-stop updating."),
        CheckItem("5.07",
                  "Motor control test — connect motor",
                  "PID achieves target FPS within 2 seconds",
                  f"Set FPS switch to 18.  Press trigger.  "
                  f"UART should show FPS_ACT ≈ 18.0 ±0.5"),
        CheckItem("5.08",
                  "Motor control test — 24 fps",
                  "PID achieves 24 FPS stable",
                  "Toggle FPS switch to 24 while running.  "
                  "Verify smooth transition, no overshoot > 2 fps."),
        CheckItem("5.09",
                  "Stall detection test",
                  "Motor stops and STALL state within 200 ms",
                  "Block motor shaft while running.  "
                  "Verify UART shows STALL state, fault LED blinks."),
        CheckItem("5.10",
                  "Metering test — known light source",
                  "EV reading within ±0.5 EV of reference meter",
                  "Aim photodiode at calibrated light source.  "
                  "Compare UART EV output with Sekonic or similar."),
        CheckItem("5.11",
                  "Exposure LEDs test",
                  "Green ON in daylight, Red blinks in darkness",
                  "Cover photodiode → red blinks.  "
                  "Expose to room light → green steady."),
        CheckItem("5.12",
                  "DIP switch test — cycle all ASA values",
                  "UART shows ASA 50, 100, 200, 500 as DIP changes",
                  "Toggle each DIP combination, verify UART output"),
    ]


# =========================================================================
# SECTION 6: FINAL ASSEMBLY
# =========================================================================

def _section_final_assembly() -> List[CheckItem]:
    items = []

    # Torque values from gdt_standards
    t_m2 = TORQUE_SPECS.get("M2", 0.2)
    t_m25 = TORQUE_SPECS.get("M2.5", 0.4)
    t_m3 = TORQUE_SPECS.get("M3", 0.7)

    items.extend([
        CheckItem("6.01",
                  "Install film gate assembly into left body half",
                  f"2× M2×5 SHCS at {t_m2} N·m",
                  "Gate seats flush against datum face.  "
                  "Verify aperture centered in body window."),
        CheckItem("6.02",
                  "Install film channel guides",
                  f"Guide rails aligned with gate channel",
                  "Film path must be straight and unobstructed"),
        CheckItem("6.03",
                  "Install shutter/shaft assembly into left body half",
                  "Bearings press into housing bores",
                  "Verify shaft rotates freely after installation.  "
                  "Re-check shutter clearance to gate."),
        CheckItem("6.04",
                  "Install cam and claw mechanism",
                  "Cam keyway aligned to shaft timing mark",
                  "Verify claw engages film perforations at correct "
                  "shaft angle (180° from shutter opening)."),
        CheckItem("6.05",
                  "Install gearbox assembly",
                  "Gearbox output gear meshes with main shaft gear",
                  "Check backlash: slight free play is normal"),
        CheckItem("6.06",
                  "Install motor into motor mount bracket",
                  f"2× M3×8 SHCS at {t_m3} N·m",
                  "Motor pinion meshes with gearbox input.  "
                  "Verify full rotation without binding."),
        CheckItem("6.07",
                  "Install cartridge receiver",
                  "Receiver aligned with film channel entry/exit",
                  "Dry-fit a Super 8 cartridge — must insert and "
                  "eject smoothly"),
        CheckItem("6.08",
                  "Route motor wires to PCB connector",
                  "Red → +, Black → GND, secure with tie point",
                  "Leave service loop for future removal.  "
                  "No wire crossing moving parts."),
        CheckItem("6.09",
                  "Route encoder sensor wires to PCB",
                  "VCC, GND, Signal (3 wires)",
                  "Sensor positioned to read encoder flag on shaft"),
        CheckItem("6.10",
                  "Route metering sensor wires to PCB",
                  "Photodiode: anode → TIA input, cathode → GND",
                  "Verify photodiode faces front of camera"),
        CheckItem("6.11",
                  "Install PCB on standoffs in left body half",
                  f"4× M2×8 SHCS at {t_m2} N·m",
                  "Verify all connectors accessible before closing"),
        CheckItem("6.12",
                  "Connect battery holder leads to PCB",
                  "Red → VBAT+, Black → GND",
                  "Verify polarity with DMM before connecting"),
        CheckItem("6.13",
                  "Install battery compartment holder",
                  "Holder seated in battery pocket",
                  "Verify batteries fit without force"),
        CheckItem("6.14",
                  "Close right body half onto left half",
                  f"12× M2.5×6 SHCS at {t_m25} N·m",
                  "Start all screws finger-tight first.  "
                  "Torque in cross pattern.  No pinched wires."),
        CheckItem("6.15",
                  "Install top plate with viewfinder",
                  f"M2.5 SHCS at {t_m25} N·m",
                  "Viewfinder aligned with lens axis"),
        CheckItem("6.16",
                  "Install bottom plate",
                  f"M2.5 SHCS at {t_m25} N·m",
                  "Tripod mount accessible, flush with bottom"),
        CheckItem("6.17",
                  "Install lens mount boss",
                  "Thread into front face, Loctite 242 on threads",
                  f"C-mount: {CMOUNT.thread_tpi} TPI, "
                  f"flange distance {CMOUNT.flange_focal_dist} mm"),
        CheckItem("6.18",
                  "Verify flange focal distance",
                  f"{CMOUNT.flange_focal_dist} ±0.02 mm",
                  "Use C-mount depth gauge or calibrated spacer"),
        CheckItem("6.19",
                  "Install cartridge door with hinge",
                  "Door closes flush, light-tight",
                  "Apply light-seal foam strip to door edges"),
        CheckItem("6.20",
                  "Install battery door",
                  "Latch engages securely",
                  "Verify batteries accessible, door light-tight"),
        CheckItem("6.21",
                  "Install trigger mechanism",
                  "Trigger spring returns button, microswitch clicks",
                  "Verify trigger GPIO reads correctly on UART"),
        CheckItem("6.22",
                  "Light leak test",
                  "No visible light leaks at any seam",
                  "In darkroom: shine bright LED flashlight around "
                  "all seams, door edges, and viewfinder.  "
                  "Check with loaded film or light sensor inside."),
        CheckItem("6.23",
                  "Film transport test",
                  "Smooth transport at 18 fps for 10 seconds",
                  "Load cartridge.  Run 10 seconds.  "
                  "Listen for smooth, even cadence.  "
                  "No stalling, no grinding."),
        CheckItem("6.24",
                  "Frame registration test",
                  "Frame-to-frame alignment within ±0.025 mm",
                  "Run 1 full cartridge.  Develop film.  "
                  "Check frame alignment on viewer/projector.  "
                  "Sprocket holes should align consistently."),
    ])

    return items


# =========================================================================
# SECTION 7: FINAL QC
# =========================================================================

def _section_final_qc() -> List[CheckItem]:
    return [
        CheckItem("7.01",
                  "Assign serial number",
                  "Format: S8C-YYMM-NNN (e.g. S8C-2603-001)",
                  "Engrave or label inside battery compartment"),
        CheckItem("7.02",
                  "Record serial number in production log",
                  "Log: serial, build date, technician, batch",
                  "Enter in production database / spreadsheet"),
        CheckItem("7.03",
                  "Metering calibration — EV accuracy check",
                  "Within ±0.5 EV at EV 8, 10, 12, 14",
                  "Compare UART EV output against reference meter "
                  "at 4 light levels.  Record all values."),
        CheckItem("7.04",
                  "Metering calibration — f-stop accuracy",
                  "Galvanometer needle within ±1/3 stop of reference",
                  "At each EV level, verify needle position matches "
                  "expected f-stop for ASA 100, 180° shutter"),
        CheckItem("7.05",
                  "Motor speed calibration — 18 fps",
                  f"18.0 ±0.5 fps (encoder measured)",
                  "Run for 30 seconds.  UART average should be "
                  "18.0 fps ±0.5."),
        CheckItem("7.06",
                  "Motor speed calibration — 24 fps",
                  f"24.0 ±0.5 fps (encoder measured)",
                  "Run for 30 seconds.  Verify stability."),
        CheckItem("7.07",
                  "Battery voltage reading accuracy",
                  "UART Vbat within ±100 mV of DMM reading",
                  "Measure battery voltage with DMM, compare to "
                  "UART Vbat output"),
        CheckItem("7.08",
                  "Low battery detection test",
                  f"Warning LED at < {BATTERY.pack_voltage_nom * 0.7:.0f} mV",
                  "Use variable bench supply to simulate low battery.  "
                  "Verify LED blinks and motor stops."),
        CheckItem("7.09",
                  "Cosmetic inspection — body exterior",
                  "No scratches, dents, anodize defects",
                  "Inspect under bright light.  Note any cosmetic "
                  "imperfections in QC log."),
        CheckItem("7.10",
                  "Cosmetic inspection — controls and indicators",
                  "All LEDs visible, trigger smooth, door latches secure",
                  "Cycle all user-facing controls"),
        CheckItem("7.11",
                  "Weight check",
                  "Within ±10% of target weight",
                  "Weigh assembled camera with batteries on calibrated scale"),
        CheckItem("7.12",
                  "Functional test — complete filming cycle",
                  "Load cartridge → trigger → 5 sec run → release → stop",
                  "Full end-to-end test: metering preview, motor start, "
                  "stable running, clean stop.  UART log saved."),
        CheckItem("7.13",
                  "Functional test sign-off",
                  "All tests PASS",
                  "QC inspector signature and date"),
        CheckItem("7.14",
                  "Pack for shipping",
                  "Camera in foam insert, accessories bag, manual",
                  "Include: lens cap, wrist strap, battery set, "
                  "QC certificate, user manual"),
    ]


# =========================================================================
# FULL CHECKLIST
# =========================================================================

SECTIONS = [
    ("1. INCOMING INSPECTION",      _section_incoming),
    ("2. FILM TRANSPORT SUB-ASSY",  _section_film_transport),
    ("3. SHUTTER SUB-ASSEMBLY",     _section_shutter),
    ("4. DRIVETRAIN SUB-ASSEMBLY",  _section_drivetrain),
    ("5. ELECTRONICS SUB-ASSEMBLY", _section_electronics),
    ("6. FINAL ASSEMBLY",           _section_final_assembly),
    ("7. FINAL QC & SIGN-OFF",      _section_final_qc),
]


def get_all_sections() -> list:
    """Return all sections as (title, [CheckItem]) tuples."""
    return [(title, fn()) for title, fn in SECTIONS]


def get_inspection_criteria() -> dict:
    """Return key inspection criteria (backward-compatible API)."""
    return {
        "gate_aperture_w": f"{FILM.frame_w} ±{TOL.gate_aperture} mm",
        "gate_aperture_h": f"{FILM.frame_h} ±{TOL.gate_aperture} mm",
        "reg_pin_dia": (f"{CAMERA.reg_pin_dia} "
                        f"+{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm"),
        "gate_channel_depth": (f"{CAMERA.gate_channel_depth} "
                               f"±{TOL.gate_channel_depth} mm"),
        "shutter_od": f"{CAMERA.shutter_od} ±0.1 mm",
        "shaft_dia": f"{CAMERA.shaft_dia} mm {TOL.bearing_shaft} fit",
    }


# =========================================================================
# PDF EXPORT
# =========================================================================

def export_pdf(filepath: str = "export/production_checklist.pdf"):
    """Export the full production checklist as a multi-page PDF."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    sections = get_all_sections()

    with PdfPages(filepath) as pdf:
        # ---- Cover page ----
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")

        ax.text(0.5, 0.85, "SUPER 8 CAMERA", ha="center", va="top",
                fontsize=24, fontweight="bold")
        ax.text(0.5, 0.78, "PRODUCTION BUILD CHECKLIST", ha="center",
                va="top", fontsize=18, color="#2c3e50")
        ax.text(0.5, 0.72, "Document: S8C-CHK-001  Rev A", ha="center",
                va="top", fontsize=11, color="gray")

        # Signature block on cover
        cover_fields = [
            ("Serial Number:", 0.55),
            ("Build Date:", 0.50),
            ("Technician:", 0.45),
            ("QC Inspector:", 0.40),
            ("Batch Number:", 0.35),
        ]
        for label, y in cover_fields:
            ax.text(0.15, y, label, fontsize=12, fontweight="bold")
            ax.plot([0.42, 0.85], [y - 0.01, y - 0.01], "k-", linewidth=0.5)

        # Section summary
        ax.text(0.15, 0.24, "Sections:", fontsize=11, fontweight="bold")
        for i, (title, items) in enumerate(sections):
            ax.text(0.18, 0.20 - i * 0.025,
                    f"{title}  ({len(items)} items)",
                    fontsize=9)

        total_items = sum(len(items) for _, items in sections)
        ax.text(0.18, 0.20 - len(sections) * 0.025 - 0.01,
                f"Total: {total_items} items", fontsize=9,
                fontweight="bold")

        pdf.savefig(fig)
        plt.close(fig)

        # ---- Section pages ----
        for section_title, items in sections:
            # Chunk items to fit ~15 per page
            chunk_size = 12
            for chunk_start in range(0, len(items), chunk_size):
                chunk = items[chunk_start:chunk_start + chunk_size]

                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.axis("off")

                # Section header
                page_num = chunk_start // chunk_size + 1
                total_pages = (len(items) + chunk_size - 1) // chunk_size
                ax.text(0.02, 0.97, section_title, fontsize=13,
                        fontweight="bold", va="top")
                ax.text(0.98, 0.97,
                        f"Page {page_num}/{total_pages}",
                        fontsize=9, ha="right", va="top", color="gray")

                # Column headers
                col_heads = ["Step", "Description", "Specification",
                             "Measured", "P/F", "Init", "Date"]
                col_x = [0.02, 0.08, 0.50, 0.72, 0.82, 0.88, 0.94]
                y = 0.93
                for x, h in zip(col_x, col_heads):
                    ax.text(x, y, h, fontsize=7, fontweight="bold",
                            va="top")
                ax.plot([0.02, 0.98], [y - 0.01, y - 0.01],
                        "k-", linewidth=0.8)

                # Items
                y -= 0.02
                row_height = 0.065
                for item in chunk:
                    y -= row_height

                    # Checkbox
                    ax.text(col_x[0], y + 0.02, "\u2610", fontsize=10)

                    # Step number
                    ax.text(col_x[0] + 0.025, y + 0.025,
                            item.step, fontsize=7, fontweight="bold")

                    # Description (wrap if long)
                    desc = item.description
                    if len(desc) > 55:
                        desc = desc[:52] + "..."
                    ax.text(col_x[1], y + 0.025, desc, fontsize=6.5)

                    # Spec
                    spec = item.spec
                    if len(spec) > 30:
                        spec = spec[:27] + "..."
                    ax.text(col_x[2], y + 0.025, spec, fontsize=6.5,
                            color="#2c3e50")

                    # Measured value field (underline)
                    ax.plot([col_x[3], col_x[3] + 0.08],
                            [y + 0.01, y + 0.01], "k-", linewidth=0.3)

                    # Pass/Fail field
                    ax.plot([col_x[4], col_x[4] + 0.04],
                            [y + 0.01, y + 0.01], "k-", linewidth=0.3)

                    # Initials field
                    ax.plot([col_x[5], col_x[5] + 0.04],
                            [y + 0.01, y + 0.01], "k-", linewidth=0.3)

                    # Date field
                    ax.plot([col_x[6], col_x[6] + 0.04],
                            [y + 0.01, y + 0.01], "k-", linewidth=0.3)

                    # Notes (small text below description)
                    if item.notes:
                        note = item.notes
                        if len(note) > 80:
                            note = note[:77] + "..."
                        ax.text(col_x[1], y + 0.005, note,
                                fontsize=5.5, color="gray", style="italic")

                    # Separator line
                    ax.plot([0.02, 0.98], [y - 0.005, y - 0.005],
                            color="#ecf0f1", linewidth=0.3)

                pdf.savefig(fig)
                plt.close(fig)

    print(f"  Exported: {filepath} ({total_items} checklist items)")
    return filepath


# =========================================================================
# CONSOLE REPORT
# =========================================================================

def print_checklist_summary():
    """Print a summary of all checklist sections."""
    sections = get_all_sections()
    sep = "=" * 70

    print(sep)
    print("  SUPER 8 CAMERA — PRODUCTION BUILD CHECKLIST SUMMARY")
    print(sep)

    total = 0
    for title, items in sections:
        print(f"\n  {title} ({len(items)} items)")
        for item in items:
            print(f"    [{' '}] {item.step}  {item.description}")
            if item.spec:
                print(f"          Spec: {item.spec}")
        total += len(items)

    print(f"\n  TOTAL CHECKLIST ITEMS: {total}")
    print(sep)


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    print_checklist_summary()
    print()
    export_pdf()
