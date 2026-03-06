"""generate_checklist.py — Multi-page PDF production build checklist.

Generates a complete checklist for building one Super 8 camera, with sections:
  1. Incoming Inspection (every purchased part, 3 critical dims each)
  2. Sub-Assembly: Film Transport
  3. Sub-Assembly: Shutter
  4. Sub-Assembly: Drivetrain
  5. Sub-Assembly: Electronics
  6. Final Assembly
  7. Final QC

Each item has: checkbox, specification/tolerance, space for measured value,
pass/fail, technician initials, date.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

from super8cam.specs.master_specs import (
    CAMERA, FILM, CMOUNT, TOL, FASTENERS, FASTENER_USAGE,
    MATERIALS, MATERIAL_USAGE, BEARINGS, MOTOR, BATTERY, GEARBOX, PCB,
)
from super8cam.manufacturing.generate_drawings import PART_NUMBERS

EXPORT_DIR = "export"


# =========================================================================
# Checklist data structures
# =========================================================================

@dataclass
class CheckItem:
    """A single checklist item."""
    description: str
    spec: str = ""          # specification or tolerance
    measured: str = ""      # space label for measured value
    pass_fail: bool = True  # has pass/fail column
    notes: str = ""


@dataclass
class CheckSection:
    """A section of the checklist."""
    title: str
    section_number: int
    items: List[CheckItem]
    preamble: str = ""


# =========================================================================
# Section builders
# =========================================================================

def _build_incoming_inspection() -> CheckSection:
    """Section 1: Incoming inspection of every part."""
    items = []

    # --- Machined parts: 3 critical dims each ---
    parts_to_inspect = [
        ("Film Gate", PART_NUMBERS["film_gate"], [
            (f"Aperture width: {FILM.frame_w} \u00b1{TOL.gate_aperture} mm", "Width"),
            (f"Aperture height: {FILM.frame_h} \u00b1{TOL.gate_aperture} mm", "Height"),
            (f"Channel depth: {CAMERA.gate_channel_depth} \u00b1{TOL.gate_channel_depth} mm", "Depth"),
        ]),
        ("Pressure Plate", PART_NUMBERS["pressure_plate"], [
            (f"Thickness: {CAMERA.pressure_plate_thick} \u00b1{TOL.cnc_fine} mm", "Thick"),
            (f"Width: {CAMERA.pressure_plate_w} \u00b1{TOL.cnc_general} mm", "Width"),
            (f"Flatness: < 0.01 mm (verify with surface plate)", "Flatness"),
        ]),
        ("Registration Pin", PART_NUMBERS["registration_pin"], [
            (f"Pin dia: {CAMERA.reg_pin_dia} +{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm", "Dia"),
            (f"Protrusion: {CAMERA.reg_pin_length} \u00b1{TOL.cnc_fine} mm", "Protrusion"),
            (f"Surface finish: no burrs (inspect under 10x loupe)", "Visual"),
        ]),
        ("Main Shaft", PART_NUMBERS["main_shaft"], [
            (f"Shaft diameter: {CAMERA.shaft_dia} mm {TOL.bearing_shaft} fit", "Dia"),
            (f"Overall length: {CAMERA.shaft_length} \u00b1{TOL.cnc_general} mm", "Length"),
            (f"Keyway width: {CAMERA.shutter_keyway_w} \u00b1{TOL.cnc_fine} mm", "Keyway"),
        ]),
        ("Shutter Disc", PART_NUMBERS["shutter_disc"], [
            (f"OD: {CAMERA.shutter_od} \u00b10.1 mm", "OD"),
            (f"Thickness: {CAMERA.shutter_thickness} \u00b1{TOL.cnc_fine} mm", "Thick"),
            (f"Bore: {CAMERA.shutter_shaft_hole} mm {TOL.press_fit_hole} fit", "Bore"),
        ]),
        ("Gearbox Housing", PART_NUMBERS["gearbox_housing"], [
            (f"Main bore: {BEARINGS['main_shaft'].od} mm {TOL.bearing_seat}", "Bore"),
            (f"Stage 1 C-C: {GEARBOX.stage1_center_distance:.1f} \u00b1{TOL.cnc_fine} mm", "C-C dist"),
            (f"Stage 2 C-C: {GEARBOX.stage2_center_distance:.1f} \u00b1{TOL.cnc_fine} mm", "C-C dist"),
        ]),
        ("Claw Mechanism", PART_NUMBERS["claw_mechanism"], [
            (f"Tip width: {CAMERA.claw_tip_w} \u00b1{TOL.cnc_fine} mm", "Tip W"),
            (f"Arm length: {CAMERA.claw_arm_length} \u00b1{TOL.cnc_general} mm", "Length"),
            (f"Stroke clearance: tip fits inside {FILM.perf_w}x{FILM.perf_h} mm perf", "Fit check"),
        ]),
        ("Cam Follower", PART_NUMBERS["cam_follower"], [
            (f"Cam OD: {CAMERA.cam_od} \u00b1{TOL.cnc_fine} mm", "OD"),
            (f"Bore: {CAMERA.cam_id} mm {TOL.press_fit_hole} fit", "Bore"),
            (f"Lobe lift: {CAMERA.cam_lobe_lift} \u00b1{TOL.cnc_fine} mm", "Lift"),
        ]),
        ("Body Left", PART_NUMBERS["body_left"], [
            (f"Length: {CAMERA.body_length} \u00b1{TOL.cnc_general} mm", "Length"),
            (f"Wall thickness: {CAMERA.wall_thickness} \u00b1{TOL.cnc_general} mm (spot check)", "Wall"),
            (f"Mating face flatness: < 0.05 mm", "Flatness"),
        ]),
        ("Body Right", PART_NUMBERS["body_right"], [
            (f"Length: {CAMERA.body_length} \u00b1{TOL.cnc_general} mm", "Length"),
            (f"Wall thickness: {CAMERA.wall_thickness} \u00b1{TOL.cnc_general} mm (spot check)", "Wall"),
            (f"Mating face flatness: < 0.05 mm", "Flatness"),
        ]),
        ("Lens Mount", PART_NUMBERS["lens_mount"], [
            (f"Thread OD: {CMOUNT.thread_od} \u00b10.025 mm (thread gauge)", "Thread"),
            (f"Flange focal dist: {CMOUNT.flange_focal_dist} \u00b10.01 mm", "FFD"),
            (f"Boss OD: {CAMERA.lens_boss_od} \u00b1{TOL.cnc_general} mm", "Boss OD"),
        ]),
        ("Film Channel", PART_NUMBERS["film_channel"], [
            (f"Channel width: {CAMERA.film_channel_width} \u00b1{TOL.cnc_fine} mm", "Width"),
            (f"Channel length: {CAMERA.film_channel_length} \u00b1{TOL.cnc_general} mm", "Length"),
            (f"Surface finish: smooth, no burrs on film path", "Visual"),
        ]),
    ]

    # Gear inspections
    for name, pn, teeth, module in [
        ("Stage 1 Pinion", PART_NUMBERS["stage1_pinion"],
         GEARBOX.stage1_pinion_teeth, GEARBOX.stage1_module),
        ("Stage 1 Gear", PART_NUMBERS["stage1_gear"],
         GEARBOX.stage1_gear_teeth, GEARBOX.stage1_module),
        ("Stage 2 Pinion", PART_NUMBERS["stage2_pinion"],
         GEARBOX.stage2_pinion_teeth, GEARBOX.stage2_module),
        ("Stage 2 Gear", PART_NUMBERS["stage2_gear"],
         GEARBOX.stage2_gear_teeth, GEARBOX.stage2_module),
    ]:
        pcd = teeth * module
        parts_to_inspect.append((name, pn, [
            (f"Tooth count: {teeth}", "Count"),
            (f"PCD: {pcd:.1f} \u00b1{TOL.cnc_fine} mm", "PCD"),
            (f"Bore: {CAMERA.shaft_dia} mm {TOL.press_fit_hole} fit", "Bore"),
        ]))

    for part_name, pn, dims in parts_to_inspect:
        items.append(CheckItem(
            description=f"--- {part_name} ({pn}) ---",
            spec="",
            pass_fail=False,
        ))
        for spec_text, meas_label in dims:
            items.append(CheckItem(
                description=f"  Verify: {spec_text}",
                spec=spec_text.split(":")[0] if ":" in spec_text else spec_text,
                measured=meas_label,
            ))
        items.append(CheckItem(
            description=f"  Visual inspection: no cracks, scratches, or damage",
            spec="Visual OK",
            measured="Visual",
        ))

    # Purchased parts visual
    purchased = [
        (f"Bearing {BEARINGS['main_shaft'].designation} (main shaft)", "Spins freely, no grit"),
        (f"Bearing {BEARINGS['cam_follower'].designation} (cam follower)", "Spins freely, no grit"),
        (f"Bearing {BEARINGS['shutter_shaft_support'].designation} (shutter support)", "Spins freely"),
        (f"Motor {MOTOR.model}", f"Shaft spins at {MOTOR.nominal_voltage}V, draws < {MOTOR.no_load_current_ma}mA"),
        ("Control PCB", "Visual: solder joints, component orientation, no bridges"),
        ("Battery holder", "Contacts clean, wiring intact"),
        ("Light seal foam", "Adhesive intact, no tears"),
        ("Pressure plate springs (pair)", "Free length correct, no deformation"),
    ]
    items.append(CheckItem(description="--- Purchased Components ---", spec="", pass_fail=False))
    for desc, spec in purchased:
        items.append(CheckItem(description=f"  {desc}", spec=spec, measured="Visual"))

    return CheckSection(
        title="INCOMING INSPECTION",
        section_number=1,
        items=items,
        preamble="Inspect every part against drawing dimensions before assembly. "
                 "Reject any part outside tolerance.",
    )


def _build_film_transport() -> CheckSection:
    """Section 2: Film transport sub-assembly."""
    return CheckSection(
        title="SUB-ASSEMBLY: FILM TRANSPORT",
        section_number=2,
        items=[
            CheckItem(
                "Install registration pin into film gate (press-fit)",
                f"Press-fit force: smooth, no cracking. Pin protrusion: {CAMERA.reg_pin_length} mm",
                "Protrusion height",
            ),
            CheckItem(
                "Verify registration pin protrusion with pin gauge",
                f"{CAMERA.reg_pin_length} \u00b1{TOL.cnc_fine} mm above gate surface",
                "Pin gauge reading",
            ),
            CheckItem(
                "Inspect registration pin alignment (perpendicular to gate face)",
                "Pin perpendicular within 0.5 deg (visual with square)",
                "Visual",
            ),
            CheckItem(
                "Install pressure plate springs on gate assembly",
                "Equal spacing, springs seated in grooves",
                "Visual",
            ),
            CheckItem(
                "Verify pressure plate spring force",
                f"Target: {CAMERA.pressure_plate_force_n} N (\u00b120%)",
                "Force gauge N",
            ),
            CheckItem(
                "Assemble pressure plate onto film gate",
                "Plate sits flat, springs provide even pressure",
                "Visual",
            ),
            CheckItem(
                "Test: pass scrap film strip through gate assembly",
                "Film passes smoothly without catching or excessive resistance",
                "Smooth pass",
            ),
            CheckItem(
                "Install claw mechanism",
                "Pivot smooth, no binding",
                "Visual",
            ),
            CheckItem(
                "Verify claw tip enters film perforation cleanly",
                f"Tip {CAMERA.claw_tip_w}x{CAMERA.claw_tip_h} mm fits in "
                f"{FILM.perf_w}x{FILM.perf_h} mm perf with clearance",
                "Fit test",
            ),
            CheckItem(
                "Verify claw passes through gate slot without binding",
                "Full stroke travel with no contact on slot walls",
                "Stroke test",
            ),
            CheckItem(
                "Install film channel guide rails",
                "Aligned with gate aperture center, smooth film path",
                "Visual",
            ),
        ],
        preamble="Build the film transport sub-assembly. Handle film gate with gloves "
                 "to avoid contaminating polished surfaces.",
    )


def _build_shutter() -> CheckSection:
    """Section 3: Shutter sub-assembly."""
    return CheckSection(
        title="SUB-ASSEMBLY: SHUTTER",
        section_number=3,
        items=[
            CheckItem(
                "Press shutter disc onto main shaft",
                "Keyway aligned, disc seated fully against shoulder",
                "Visual",
            ),
            CheckItem(
                "Verify keyway alignment: opening faces correct direction",
                f"Opening angle: {CAMERA.shutter_opening_angle}\u00b0, "
                "aligned with cam engagement phase",
                "Visual",
            ),
            CheckItem(
                "Install front bearing (694ZZ) into housing",
                f"Press into {TOL.bearing_seat} bore, smooth rotation after install",
                "Rotation check",
            ),
            CheckItem(
                "Install rear bearing (694ZZ) into housing",
                f"Press into {TOL.bearing_seat} bore, smooth rotation after install",
                "Rotation check",
            ),
            CheckItem(
                "Insert shaft assembly through bearings",
                "Shaft spins freely in both bearings, no axial play > 0.1 mm",
                "Spin check",
            ),
            CheckItem(
                "Spin test: shaft should spin freely for >5 seconds from finger flick",
                ">5 seconds free spin from flick",
                "Time (sec)",
            ),
            CheckItem(
                "Verify shutter clears film gate",
                f"Use 0.25 mm feeler gauge between disc and gate. "
                f"Nominal gap: {CAMERA.shutter_to_gate_clearance} mm",
                "Feeler gauge",
            ),
            CheckItem(
                "Verify shutter disc does not contact any housing walls",
                "360\u00b0 rotation with no rubbing or noise",
                "Rotation check",
            ),
            CheckItem(
                "Check disc runout with dial indicator (if available)",
                "Total runout < 0.05 mm",
                "Runout mm",
            ),
        ],
        preamble="Build the shutter sub-assembly. Use bearing press tool — do NOT "
                 "hammer bearings directly.",
    )


def _build_drivetrain() -> CheckSection:
    """Section 4: Drivetrain sub-assembly."""
    return CheckSection(
        title="SUB-ASSEMBLY: DRIVETRAIN",
        section_number=4,
        items=[
            CheckItem(
                "Install Stage 1 pinion onto motor shaft",
                f"Press-fit, {GEARBOX.stage1_pinion_teeth}T pinion, "
                f"module {GEARBOX.stage1_module}",
                "Visual",
            ),
            CheckItem(
                "Install Stage 1 gear onto intermediate shaft",
                f"{GEARBOX.stage1_gear_teeth}T gear, verify mesh with pinion",
                "Visual",
            ),
            CheckItem(
                "Install Stage 2 pinion on intermediate shaft",
                f"{GEARBOX.stage2_pinion_teeth}T pinion, integral with Stage 1 gear shaft",
                "Visual",
            ),
            CheckItem(
                "Install Stage 2 gear onto main shaft",
                f"{GEARBOX.stage2_gear_teeth}T gear, "
                f"module {GEARBOX.stage2_module}",
                "Visual",
            ),
            CheckItem(
                "Assemble gearbox housing halves",
                "Dowel pins aligned, screws torqued to 0.2 N-m",
                "Torque check",
            ),
            CheckItem(
                "Verify no gear binding throughout full rotation",
                "Turn main shaft slowly by hand through 10+ full rotations",
                "Smooth rotation",
            ),
            CheckItem(
                "Check gear backlash (should be minimal but non-zero)",
                "Slight rotational play at output — no tight spots",
                "Play check",
            ),
            CheckItem(
                "Connect motor, run briefly at low voltage (3V)",
                "Main shaft turns in correct direction (verify with arrow marking)",
                "Direction OK",
            ),
            CheckItem(
                "Run at full voltage, verify no unusual noise",
                f"Motor at {MOTOR.nominal_voltage}V, listen for grinding or whine",
                "Sound check",
            ),
            CheckItem(
                "Verify gear reduction ratio",
                f"Count motor revs per main shaft rev: should be ~{GEARBOX.ratio:.0f}:1",
                "Ratio",
            ),
        ],
        preamble="Assemble the gear train. Apply light Delrin-safe lubricant to gear teeth. "
                 "Handle gears with clean hands — oil from skin is sufficient for Delrin.",
    )


def _build_electronics() -> CheckSection:
    """Section 5: Electronics sub-assembly."""
    return CheckSection(
        title="SUB-ASSEMBLY: ELECTRONICS",
        section_number=5,
        items=[
            CheckItem(
                "Visual inspection of PCB",
                "All solder joints wetted, no bridges, correct component orientation",
                "Visual",
            ),
            CheckItem(
                "Check MCU orientation (pin 1 indicator)",
                "STM32L031K6 pin 1 matches PCB marking",
                "Visual",
            ),
            CheckItem(
                "Power-on test: apply 6V to battery input",
                "No smoke, no hot components after 10 seconds",
                "Visual/touch",
            ),
            CheckItem(
                "Verify 3.3V rail",
                "3.3V \u00b150mV on LDO output test point",
                "Voltage (V)",
            ),
            CheckItem(
                "Verify motor driver quiescent current",
                "< 5 mA with no motor connected",
                "Current (mA)",
            ),
            CheckItem(
                "Flash firmware via SWD",
                "Flash successful, no verify errors",
                "Flash OK",
            ),
            CheckItem(
                "UART debug output test",
                "Connect serial monitor at 115200 baud, verify telemetry output",
                "Serial OK",
            ),
            CheckItem(
                "Motor control test: connect motor",
                "Hold trigger, verify PID loop achieves target fps on UART",
                "FPS reading",
            ),
            CheckItem(
                "Verify 18 fps mode",
                "FPS select switch low: UART shows ~18.0 fps at steady state",
                "FPS",
            ),
            CheckItem(
                "Verify 24 fps mode",
                "FPS select switch high: UART shows ~24.0 fps at steady state",
                "FPS",
            ),
            CheckItem(
                "Metering test: aim photodiode at known light source",
                "EV reading within \u00b10.5 EV of reference meter",
                "EV reading",
            ),
            CheckItem(
                "Verify galvanometer needle responds to light changes",
                "Needle sweeps from min to max as light varies",
                "Needle sweep",
            ),
            CheckItem(
                "Verify LED indicators",
                "Green LED on when exposure OK, red blinks when out of range",
                "LED check",
            ),
            CheckItem(
                "Battery voltage monitoring",
                "UART shows correct battery voltage (\u00b1200 mV of multimeter)",
                "Bat voltage",
            ),
            CheckItem(
                "Low battery shutdown test (if safe to test)",
                "Reduce supply voltage below 3.6V, verify shutdown behavior",
                "Shutdown OK",
            ),
        ],
        preamble="Test all electronics before final assembly. Use ESD precautions when "
                 "handling PCB. Have a multimeter and serial adapter ready.",
    )


def _build_final_assembly() -> CheckSection:
    """Section 6: Final assembly."""
    items = [
        CheckItem(
            "Apply light seal foam to body left mating face groove",
            "Continuous bead, no gaps, adhesive side down",
            "Visual",
        ),
        CheckItem(
            "Install film transport sub-assembly into body left",
            "Film gate aligned with lens mount aperture, M2x5 screws at 0.2 N-m",
            "Torque",
            notes="2x M2x5 SHCS",
        ),
        CheckItem(
            "Install shutter/shaft sub-assembly",
            "Shaft through bearing seats, shutter clears gate (verify 0.25mm feeler gauge)",
            "Clearance check",
        ),
        CheckItem(
            "Install drivetrain sub-assembly",
            "Gearbox seats against body wall, motor mount screws: M3x8 at 0.7 N-m",
            "Torque",
            notes="2x M3x8 SHCS",
        ),
        CheckItem(
            "Route motor wires to PCB connector location",
            "Wires clear of all moving parts, secured with wire tie",
            "Visual",
        ),
        CheckItem(
            "Install PCB bracket",
            "M2x8 standoff screws at 0.2 N-m",
            "Torque",
            notes="4x M2x8 SHCS",
        ),
        CheckItem(
            "Mount control PCB onto bracket",
            "All standoffs engaged, PCB level",
            "Visual",
        ),
        CheckItem(
            "Connect motor harness to PCB",
            "Correct polarity (verify motor direction before securing)",
            "Polarity check",
        ),
        CheckItem(
            "Connect encoder sensor",
            "Sensor aligned with encoder disc slot, cable routed clear",
            "Visual",
        ),
        CheckItem(
            "Connect photodiode / metering sensor",
            "Sensor faces lens mount aperture, cable secured",
            "Visual",
        ),
        CheckItem(
            "Connect battery holder leads",
            "Red to V+, black to GND, verify polarity",
            "Polarity check",
        ),
        CheckItem(
            "Install battery holder in battery compartment",
            "Holder seats flush, leads not pinched",
            "Visual",
        ),
        CheckItem(
            "Install trigger mechanism",
            "Smooth action, microswitch clicks at proper travel",
            "Action check",
        ),
        CheckItem(
            "Join body halves: apply body right onto body left",
            f"All 12x M2.5x6 body screws at 0.4 N-m, tighten in star pattern",
            "Torque",
            notes="12x M2.5x6 SHCS",
        ),
        CheckItem(
            "Install top plate",
            "Viewfinder aligned, screws at 0.4 N-m",
            "Torque",
        ),
        CheckItem(
            "Install bottom plate",
            "Tripod mount insert threaded in, screws at 0.4 N-m",
            "Torque",
        ),
        CheckItem(
            "Install cartridge door with hinge",
            "Door opens/closes smoothly, latch engages",
            "Action check",
        ),
        CheckItem(
            "Install battery door",
            "Door latches securely, easy to open for battery change",
            "Action check",
        ),
        CheckItem(
            "LIGHT LEAK TEST: in darkroom, shine flashlight around all seams",
            "No light visible from inside with door closed (check cartridge door, "
            "battery door, body seam, lens mount)",
            "No leaks",
        ),
        CheckItem(
            "FILM TEST: load cartridge, run 10 seconds at 18 fps",
            "Smooth transport, no jams, no unusual noise",
            "Smooth run",
        ),
        CheckItem(
            "Verify frame count on UART matches expected (~180 frames in 10 sec)",
            "Frame count within \u00b110 of expected",
            "Frame count",
        ),
        CheckItem(
            "FRAME REGISTRATION TEST: run 1 cartridge, develop, check alignment",
            "Frames evenly spaced, no double-exposure, no drift",
            "Alignment check",
            notes="Full test requires film processing",
        ),
    ]

    return CheckSection(
        title="FINAL ASSEMBLY",
        section_number=6,
        items=items,
        preamble="Assemble all sub-assemblies into the camera body. Follow torque specs "
                 "exactly. Use threadlocker (Loctite 222) on all screws unless noted.\n\n"
                 "Torque values:  M2: 0.2 N-m  |  M2.5: 0.4 N-m  |  M3: 0.7 N-m",
    )


def _build_final_qc() -> CheckSection:
    """Section 7: Final QC."""
    return CheckSection(
        title="FINAL QC",
        section_number=7,
        items=[
            CheckItem(
                "Assign serial number",
                "Format: S8C-YYMM-NNN (year, month, unit number)",
                "Serial #",
                pass_fail=False,
            ),
            CheckItem(
                "Record serial number on camera body (engraved or label)",
                "Legible, permanent marking on bottom plate",
                "Visual",
            ),
            CheckItem(
                "Calibration: metering accuracy check",
                "Compare camera EV reading vs reference light meter at 3 levels "
                "(low/medium/high). All within \u00b10.5 EV",
                "Max EV error",
            ),
            CheckItem(
                "Calibration: fps accuracy at 18 fps",
                "Measure with external tachometer or UART. Target: 18.0 \u00b10.5 fps",
                "FPS reading",
            ),
            CheckItem(
                "Calibration: fps accuracy at 24 fps",
                "Target: 24.0 \u00b10.5 fps",
                "FPS reading",
            ),
            CheckItem(
                "Record calibration data on certificate",
                "Metering EV offset, fps at 18 and 24, battery voltage reading",
                "Cal cert #",
                pass_fail=False,
            ),
            CheckItem(
                "Cosmetic inspection: exterior surfaces",
                "No scratches deeper than anodize layer, uniform color, "
                "all markings legible",
                "Visual",
            ),
            CheckItem(
                "Cosmetic inspection: lens mount thread",
                "Thread clean, no chips, test lens screws in smoothly",
                "Thread check",
            ),
            CheckItem(
                "Functional test: complete trigger-to-stop cycle",
                "Press trigger: motor starts, runs steady, release: motor stops cleanly",
                "Cycle test",
            ),
            CheckItem(
                "Functional test: cartridge load/unload",
                "Cartridge inserts and ejects smoothly, door latches",
                "Cart test",
            ),
            CheckItem(
                "Functional test: battery install/remove",
                "Batteries insert/remove easily, correct polarity enforced by holder",
                "Batt test",
            ),
            CheckItem(
                "Functional test: all LEDs operational",
                "Green (OK), Red (warning) — both illuminate on command",
                "LED test",
            ),
            CheckItem(
                "Final sign-off: unit passes all tests",
                "All sections 1-7 complete with no open failures",
                "PASS/FAIL",
            ),
            CheckItem(
                "Pack camera in protective bag, place in shipping box",
                "Include: camera, lens cap, manual, warranty card, cal certificate",
                "Pack check",
            ),
            CheckItem(
                "Seal shipping box, apply shipping label",
                "Serial number on packing slip matches camera",
                "Ship check",
            ),
        ],
        preamble="Final quality control. All previous sections must be complete "
                 "before starting final QC. Any failure requires rework and re-test.",
    )


# =========================================================================
# PDF renderer
# =========================================================================

def _render_section_pages(pdf: PdfPages, section: CheckSection,
                          fig_w: float = 8.5, fig_h: float = 11.0):
    """Render one section as one or more PDF pages."""
    items_per_page = 18  # conservative to allow spacing
    total_pages = max(1, (len(section.items) + items_per_page - 1) // items_per_page)

    for page_idx in range(total_pages):
        fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
        ax.set_xlim(0, fig_w)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Border
        margin = 0.4
        ax.add_patch(Rectangle((margin, margin),
                                fig_w - 2 * margin, fig_h - 2 * margin,
                                fill=False, edgecolor="black", linewidth=1.5))

        # Header
        y = fig_h - 0.7
        ax.text(fig_w / 2, y, "SUPER 8 CAMERA — PRODUCTION BUILD CHECKLIST",
                fontsize=10, ha="center", fontweight="bold")
        y -= 0.35
        ax.text(fig_w / 2, y,
                f"Section {section.section_number}: {section.title}  "
                f"(Page {page_idx + 1}/{total_pages})",
                fontsize=9, ha="center")
        y -= 0.25
        ax.plot([margin + 0.1, fig_w - margin - 0.1], [y, y], "k-", linewidth=1.0)

        # Preamble (first page only)
        if page_idx == 0 and section.preamble:
            y -= 0.35
            # Word-wrap preamble
            words = section.preamble.split()
            line = ""
            for word in words:
                test = line + " " + word if line else word
                if len(test) > 85:
                    ax.text(margin + 0.3, y, line, fontsize=7, va="top", style="italic")
                    y -= 0.22
                    line = word
                else:
                    line = test
            if line:
                ax.text(margin + 0.3, y, line, fontsize=7, va="top", style="italic")
                y -= 0.22
            y -= 0.15

        # Column headers
        y -= 0.25
        col_x = {
            "check": margin + 0.15,
            "desc": margin + 0.55,
            "spec": 4.8,
            "meas": 6.3,
            "pf": 7.15,
            "init": 7.55,
            "date": 7.95,
        }

        ax.text(col_x["check"], y, "\u2610", fontsize=8, va="center")
        ax.text(col_x["desc"], y, "Description", fontsize=7, fontweight="bold", va="center")
        ax.text(col_x["spec"], y, "Specification", fontsize=7, fontweight="bold", va="center")
        ax.text(col_x["meas"], y, "Measured", fontsize=7, fontweight="bold", va="center")
        ax.text(col_x["pf"], y, "P/F", fontsize=7, fontweight="bold", va="center")
        ax.text(col_x["init"], y, "Init", fontsize=7, fontweight="bold", va="center")
        ax.text(col_x["date"], y, "Date", fontsize=7, fontweight="bold", va="center")

        y -= 0.12
        ax.plot([margin + 0.1, fig_w - margin - 0.1], [y, y], "k-", linewidth=0.5)

        # Items
        start = page_idx * items_per_page
        end = min(start + items_per_page, len(section.items))
        row_h = 0.42

        for i, item in enumerate(section.items[start:end]):
            y -= row_h
            if y < margin + 0.5:
                break

            # Alternating background
            if i % 2 == 0:
                ax.add_patch(Rectangle((margin + 0.1, y - row_h * 0.3),
                                        fig_w - 2 * margin - 0.2, row_h,
                                        facecolor="#f5f5f5", edgecolor="none"))

            # Section header items (--- Name ---)
            if item.description.startswith("---"):
                ax.text(col_x["desc"], y, item.description,
                        fontsize=7, fontweight="bold", va="center")
                continue

            # Checkbox
            ax.add_patch(Rectangle((col_x["check"], y - 0.06), 0.18, 0.18,
                                    fill=False, edgecolor="black", linewidth=0.5))

            # Description (may need wrapping)
            desc = item.description
            if len(desc) > 55:
                ax.text(col_x["desc"], y + 0.06, desc[:55], fontsize=6, va="center")
                ax.text(col_x["desc"], y - 0.1, desc[55:110], fontsize=6, va="center")
            else:
                ax.text(col_x["desc"], y, desc, fontsize=6, va="center")

            # Spec (abbreviated)
            spec_text = item.spec[:25] if item.spec else ""
            ax.text(col_x["spec"], y, spec_text, fontsize=5.5, va="center")

            # Measured value box
            if item.measured:
                ax.add_patch(Rectangle((col_x["meas"], y - 0.08), 0.7, 0.2,
                                        fill=False, edgecolor="gray", linewidth=0.3))
                ax.text(col_x["meas"] + 0.02, y - 0.12, item.measured,
                        fontsize=4.5, va="top", color="gray")

            # Pass/Fail boxes
            if item.pass_fail:
                ax.add_patch(Rectangle((col_x["pf"], y - 0.06), 0.18, 0.18,
                                        fill=False, edgecolor="black", linewidth=0.3))

            # Initials box
            ax.add_patch(Rectangle((col_x["init"], y - 0.06), 0.25, 0.18,
                                    fill=False, edgecolor="gray", linewidth=0.3))

            # Date box
            ax.add_patch(Rectangle((col_x["date"], y - 0.06), 0.4, 0.18,
                                    fill=False, edgecolor="gray", linewidth=0.3))

        # Footer
        ax.text(fig_w / 2, margin + 0.15,
                "Technician: ________________  Supervisor: ________________  Date: __________",
                fontsize=7, ha="center", va="center")

        pdf.savefig(fig, dpi=150, bbox_inches="tight")
        plt.close(fig)


def _render_cover_page(pdf: PdfPages, fig_w: float = 8.5, fig_h: float = 11.0):
    """Render the checklist cover page."""
    fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    margin = 0.4
    ax.add_patch(Rectangle((margin, margin),
                            fig_w - 2 * margin, fig_h - 2 * margin,
                            fill=False, edgecolor="black", linewidth=2.0))

    cx = fig_w / 2
    y = fig_h * 0.75
    ax.text(cx, y, "SUPER 8 CAMERA", fontsize=20, ha="center", fontweight="bold")
    y -= 0.6
    ax.text(cx, y, "PRODUCTION BUILD CHECKLIST", fontsize=16, ha="center", fontweight="bold")
    y -= 0.8
    ax.text(cx, y, "Complete this checklist for each camera unit.", fontsize=10, ha="center")

    y -= 1.2
    sections = [
        "1. Incoming Inspection",
        "2. Sub-Assembly: Film Transport",
        "3. Sub-Assembly: Shutter",
        "4. Sub-Assembly: Drivetrain",
        "5. Sub-Assembly: Electronics",
        "6. Final Assembly",
        "7. Final QC",
    ]
    ax.text(cx, y, "SECTIONS", fontsize=12, ha="center", fontweight="bold")
    y -= 0.5
    for sec in sections:
        ax.text(cx, y, sec, fontsize=10, ha="center")
        y -= 0.35

    y -= 0.8
    fields = [
        "Camera Serial Number: _________________________",
        "Build Start Date:     _________________________",
        "Build End Date:       _________________________",
        "Built By:             _________________________",
        "QC Approved By:       _________________________",
    ]
    for f in fields:
        ax.text(1.5, y, f, fontsize=10, fontfamily="monospace")
        y -= 0.45

    y -= 0.6
    ax.text(cx, y, "Torque Specifications", fontsize=10, ha="center", fontweight="bold")
    y -= 0.35
    torques = [
        "M2 Socket Head Cap Screw:    0.2 N-m  (1.8 in-lb)",
        "M2.5 Socket Head Cap Screw:  0.4 N-m  (3.5 in-lb)",
        "M3 Socket Head Cap Screw:    0.7 N-m  (6.2 in-lb)",
    ]
    for t in torques:
        ax.text(1.5, y, t, fontsize=9, fontfamily="monospace")
        y -= 0.3

    pdf.savefig(fig, dpi=150, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Public API
# =========================================================================

def generate_checklist(output_dir: str = EXPORT_DIR) -> str:
    """Generate the complete production checklist as PDF.

    Returns the output path.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "production_checklist.pdf")

    sections = [
        _build_incoming_inspection(),
        _build_film_transport(),
        _build_shutter(),
        _build_drivetrain(),
        _build_electronics(),
        _build_final_assembly(),
        _build_final_qc(),
    ]

    total_items = sum(len(s.items) for s in sections)

    with PdfPages(filepath) as pdf:
        _render_cover_page(pdf)
        for section in sections:
            _render_section_pages(pdf, section)

    print(f"  Exported production checklist: {filepath}")
    print(f"    {len(sections)} sections, {total_items} check items")
    return filepath


def get_inspection_criteria() -> dict:
    """Return inspection criteria derived from master specs (backward-compatible)."""
    return {
        "gate_aperture_w": f"{FILM.frame_w} +/- {TOL.gate_aperture} mm",
        "gate_aperture_h": f"{FILM.frame_h} +/- {TOL.gate_aperture} mm",
        "reg_pin_dia": (f"{CAMERA.reg_pin_dia} "
                        f"+{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm"),
        "gate_channel_depth": f"{CAMERA.gate_channel_depth} +/- {TOL.gate_channel_depth} mm",
        "shutter_od": f"{CAMERA.shutter_od} +/- 0.1 mm",
        "shaft_dia": f"{CAMERA.shaft_dia} mm {TOL.bearing_shaft} fit",
    }


if __name__ == "__main__":
    path = generate_checklist()
    print(f"\nChecklist generated: {path}")
