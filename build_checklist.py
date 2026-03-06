#!/usr/bin/env python3
"""build_checklist.py — Super 8 Camera Production Build Checklist (PDF)

Generates a comprehensive, print-ready checklist covering every step of
building one Super 8 camera unit:
  1. Header with serial number, date, technician fields
  2. Incoming inspection (every BOM part with acceptance criteria)
  3. Sub-assembly procedures (film gate, shutter, motor, PCB)
  4. Final assembly sequence (numbered, torque specs, alignment)
  5. Calibration (metering, motor speed)
  6. Quality control tests (film advance, light leak, shutter timing, battery)
  7. Sign-off block

Usage:
    python build_checklist.py                     # super8_build_checklist.pdf
    python build_checklist.py -o custom_name.pdf  # custom output path
"""

import argparse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import (
    HexColor, black, white, grey, lightgrey, red, darkgreen
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# =========================================================================
# Colour palette
# =========================================================================

CLR_HEADER_BG  = HexColor("#1a1a2e")
CLR_HEADER_FG  = white
CLR_SECTION_BG = HexColor("#334155")
CLR_SECTION_FG = white
CLR_SUBSEC_BG  = HexColor("#94a3b8")
CLR_SUBSEC_FG  = black
CLR_ROW_ALT    = HexColor("#f1f5f9")
CLR_BORDER     = HexColor("#64748b")
CLR_PASS       = HexColor("#16a34a")
CLR_FAIL       = HexColor("#dc2626")

# =========================================================================
# Checklist data
# =========================================================================

INCOMING_INSPECTION = [
    # (Reference, Part, Acceptance Criteria)
    ("U1", "STM32L031K6T6 LQFP-32", "Correct marking, no bent pins, verify date code"),
    ("U2", "DRV8837 WSON-8", "Marking matches MPN, pad exposure visible"),
    ("U3", "MCP6001 SOT-23-5", "Correct orientation dot, no damaged leads"),
    ("U4", "AMS1117-5.0 SOT-223", "Verify 5.0 marking (not 3.3)"),
    ("U5", "AMS1117-3.3 SOT-223", "Verify 3.3 marking (not 5.0)"),
    ("Q1", "SI2301 P-FET SOT-23", "Verify P-channel marking, correct pinout"),
    ("F1", "500mA Polyfuse 1206", "Verify 500mA rating marking"),
    ("D1", "BPW34 Photodiode", "Glass window clean, no cracks, leads intact"),
    ("D2-D6", "LEDs (R/G/Y) 0603", "Correct colour per ref, verify with test current"),
    ("R1", "1M 0603 1%", "Verify value with DMM: 1.00M +/-1%"),
    ("R2-R3", "10K 0603 5%", "Verify value with DMM: 10K +/-5%"),
    ("R4-R8", "330R 0603 5%", "Verify value with DMM: 330 +/-5%"),
    ("C1", "10pF C0G 0603", "Marking/bag label matches value"),
    ("C10-C15", "100nF X7R 0603 (x6)", "Marking/bag matches, qty=6"),
    ("C20-C24", "10uF X5R 0805 (x5)", "Marking/bag matches, qty=5"),
    ("J1", "JST-PH 4-pin vertical", "4 pins, no bent contacts, latch intact"),
    ("J2", "JST-PH 2-pin vertical", "2 pins, latch intact"),
    ("J3", "2x3 pin header 2.54mm", "Straight pins, correct pitch"),
    ("SW1", "Trigger push-button", "Tactile click, <100 ohm closed, >1M open"),
    ("SW2", "SPDT toggle switch", "Firm detent both positions, wipe resistance <50m"),
    ("SW3", "2-pos DIP switch SMD", "Both positions click, contact resistance <100m"),
    ("--", "Film gate (machined)", "Aperture 5.79+/-0.02 x 4.01+/-0.02mm, no burrs, channel 0.1mm deep"),
    ("--", "Shutter disc (stamped)", "OD 30.0+/-0.1mm, shaft hole 3.0+0.02/-0mm, balance holes present"),
    ("--", "DC motor + gearbox", "Shaft spins freely, no grinding, 6V nom."),
    ("--", "Camera body shell", "No warping, all cutouts present, M2 bosses intact"),
    ("--", "C-mount lens assembly", "Threads clean, focus smooth, rear element clean"),
    ("--", "Super 8 cartridge door", "Hinge pin fit, latch engages, light-tight"),
    ("--", "Optical encoder disc+sensor", "Slot aligned, sensor responds to interruption"),
    ("--", "PCB (bare, from fab)", "No shorts (visual), via fill OK, silkscreen legible"),
    ("--", "Fasteners kit", "M2x5 (x8), M2x8 (x4), M2 nuts (x12), M2 washers (x12)"),
    ("--", "4xAA battery holder", "Spring contacts intact, polarity marked, lead length OK"),
]

SUBASSEMBLY_FILM_GATE = [
    ("FG-1", "Clean gate plate with IPA and lint-free wipe"),
    ("FG-2", "Inspect aperture under 10x loupe — no scratches or burrs on film-side lip"),
    ("FG-3", "Verify registration pin hole: insert 0.80mm gauge pin — must pass freely"),
    ("FG-4", "Verify channel depth with depth gauge: 0.10 +/- 0.02mm"),
    ("FG-5", "Install pressure plate springs (2x) — verify even tension by feel"),
    ("FG-6", "Function check: slide test film strip through channel — must glide without catching"),
]

SUBASSEMBLY_SHUTTER = [
    ("SH-1", "Press keyway shaft coupling onto motor shaft — align keyway, firm press fit"),
    ("SH-2", "Mount shutter disc on coupling — verify keyway engagement, no play"),
    ("SH-3", "Spin by hand — disc must rotate freely with no wobble (< 0.1mm runout)"),
    ("SH-4", "Verify optical sensor flag notch clears the sensor body with > 0.5mm gap"),
    ("SH-5", "Connect motor to bench supply at 6V — verify smooth rotation both directions"),
    ("SH-6", "Measure balance: hold shaft horizontal — disc should not settle to one position"),
]

SUBASSEMBLY_MOTOR = [
    ("MT-1", "Install motor into body shell pocket — secure with 2x M2x8 screws"),
    ("MT-2", "Torque motor screws to 0.15 N-m (finger-tight + 1/8 turn)"),
    ("MT-3", "Route motor leads through body channel — verify no pinch points"),
    ("MT-4", "Install encoder disc on secondary shaft — verify slot aligns with sensor"),
    ("MT-5", "Mount optical encoder sensor bracket — adjust gap to 1.0 +/- 0.3mm"),
    ("MT-6", "Connect motor leads to J1 pigtail — verify polarity (red=A, black=B)"),
    ("MT-7", "Spin shaft by hand — encoder sensor output toggles (verify with scope or LED)"),
]

SUBASSEMBLY_PCB = [
    ("PCB-1", "Apply solder paste to PCB using stencil — inspect for bridging under 10x loupe"),
    ("PCB-2", "Place all SMD components per pick-and-place coordinates"),
    ("PCB-3", "Reflow solder — standard lead-free profile (peak 245C, 60-90s above liquidus)"),
    ("PCB-4", "Post-reflow inspection: check all joints under 10x — rework any cold joints"),
    ("PCB-5", "Solder through-hole: J1, J2, J3 connectors — verify flush seating"),
    ("PCB-6", "Clean flux residue with IPA"),
    ("PCB-7", "Continuity check: 3V3 to GND > 1K ohm (no short), 5V to GND > 1K ohm"),
    ("PCB-8", "Power-on test: connect 6V bench supply to J2 — verify 5.0V +/-0.1V on 5V rail"),
    ("PCB-9", "Verify 3.3V +/-0.1V on 3V3 rail"),
    ("PCB-10", "Flash firmware via J3 (SWD) — verify successful program/verify cycle"),
    ("PCB-11", "Post-flash: MCU heartbeat LED blinks (if debug LED populated)"),
]

FINAL_ASSEMBLY = [
    ("FA-1", "Install PCB on standoff posts inside body — 4x M2x5 screws, "
             "torque 0.10 N-m", "Verify PCB clears all internal features"),
    ("FA-2", "Connect motor JST cable to J1", "Verify latch clicks"),
    ("FA-3", "Connect battery holder leads to J2", "Red=pin 1 (VIN), Black=pin 2 (GND)"),
    ("FA-4", "Route all wires in body channels — secure with adhesive clips",
             "No wires cross moving parts"),
    ("FA-5", "Install film gate sub-assembly — 2x M2x5 screws, torque 0.10 N-m",
             "Aperture centered in body window"),
    ("FA-6", "Align film gate: insert alignment gauge through gate and lens opening",
             "Gate must be perpendicular to optical axis within 0.5 deg"),
    ("FA-7", "Install shutter sub-assembly — verify disc clears gate by > 0.3mm",
             "Spin check: no contact with gate or body"),
    ("FA-8", "Set C-mount flange distance: 17.526mm from sensor plane to mount face",
             "Use flange distance gauge or calibrated spacer"),
    ("FA-9", "Install C-mount lens ring — thread in, verify firm stop",
             "Test-fit a lens: focus reaches infinity"),
    ("FA-10", "Install trigger button and FPS toggle switch in body cutouts",
              "Verify actuation feel and detent"),
    ("FA-11", "Install DIP switch (ASA select) in body recess",
              "All 4 positions readable by firmware"),
    ("FA-12", "Install LEDs in body light pipes / windows",
              "Verify visibility from outside: power on, cycle all LEDs"),
    ("FA-13", "Install cartridge door — hinge pin, latch mechanism",
              "Door opens > 90 deg, latches firmly closed"),
    ("FA-14", "Install battery compartment door on bottom",
              "Verify spring contacts engage battery holder"),
    ("FA-15", "Install tripod mount insert (1/4-20) — thread in with Loctite 242",
              "Torque to 0.5 N-m, verify thread engagement > 5mm"),
    ("FA-16", "Final exterior inspection: all screws flush, no gaps > 0.2mm, "
              "cosmetic check",
              "Label serial number on inside of battery door"),
]

CALIBRATION_METERING = [
    ("CM-1", "Set up calibration light source: integrating sphere or uniform diffuser at EV 10"),
    ("CM-2", "Set DIP to ASA 100, FPS to 18"),
    ("CM-3", "Read ADC value at EV 10 — record: _______ mV (expected ~950 mV)"),
    ("CM-4", "Adjust calibration table entry for EV 10 if off by > 50mV"),
    ("CM-5", "Repeat at EV 6 (dim) and EV 14 (bright) — record values"),
    ("CM-6", "Verify galvanometer needle: at EV 12 / ASA 100 / 18fps, needle should read ~f/5.6"),
    ("CM-7", "Verify green LED on at EV 12, red LED on at EV 4 (underexposed)"),
    ("CM-8", "Cycle through all 4 ASA settings — needle must respond correctly"),
]

CALIBRATION_MOTOR = [
    ("CMS-1", "Load dummy film cartridge (or use encoder-only test mode)"),
    ("CMS-2", "Set FPS switch to 18 — press trigger"),
    ("CMS-3", "Wait for PID to settle (2 seconds) — measure fps with strobe or scope"),
    ("CMS-4", "Record: measured fps = _______ (accept: 18.0 +/- 0.5 fps)"),
    ("CMS-5", "Switch FPS to 24 during run — verify smooth transition"),
    ("CMS-6", "Record: measured fps = _______ (accept: 24.0 +/- 0.5 fps)"),
    ("CMS-7", "Release trigger — verify soft stop (no abrupt halt)"),
    ("CMS-8", "Stall test: hold shutter disc — motor must shut off within 200ms, LED blinks"),
]

QC_TESTS = [
    ("QC-1", "Film advance test",
     "Load dummy cartridge, run 50 frames at 18fps. "
     "Count encoder pulses: must be 50 +/- 1. "
     "Inspect film — no scratches, perforations intact.",
     "PASS / FAIL"),
    ("QC-2", "Film advance test (24fps)",
     "Run 50 frames at 24fps. Verify count and film condition.",
     "PASS / FAIL"),
    ("QC-3", "Light leak check",
     "Load unexposed test film, close cartridge door, "
     "expose body to bright light (60W lamp at 15cm) for 60 seconds. "
     "Develop film — no fogging on any frame.",
     "PASS / FAIL"),
    ("QC-4", "Shutter timing verification",
     "Use phototransistor + oscilloscope at gate aperture. "
     "Measure open/closed duty cycle at 18fps: expect 50% +/- 3%. "
     "Repeat at 24fps.",
     "18fps: ____% | 24fps: ____%"),
    ("QC-5", "Metering accuracy spot check",
     "Compare needle reading to reference meter at EV 8, 10, 12 (ASA 100). "
     "Must agree within +/- 0.5 EV.",
     "EV8: +/-___ | EV10: +/-___ | EV12: +/-___"),
    ("QC-6", "Battery life spot check",
     "Insert fresh 4xAA alkaline. Run motor at 24fps continuously. "
     "Record time until low-battery LED lights. "
     "Minimum acceptable: 30 minutes.",
     "Time: ___ min"),
    ("QC-7", "Cartridge-end detection",
     "With motor running, simulate cartridge end (block encoder). "
     "Camera must stop motor and blink warning within 5 missed frames.",
     "PASS / FAIL"),
    ("QC-8", "Drop / shock test (optional)",
     "10cm drop onto padded surface, 3 axes. "
     "Verify all functions still work. No loose parts rattling.",
     "PASS / FAIL / SKIP"),
]


# =========================================================================
# PDF generation
# =========================================================================

def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    s_title = ParagraphStyle("Title2", parent=styles["Title"],
                             fontSize=18, textColor=CLR_HEADER_BG,
                             spaceAfter=2 * mm)
    s_subtitle = ParagraphStyle("Sub", parent=styles["Normal"],
                                fontSize=10, textColor=grey,
                                spaceAfter=4 * mm)
    s_section = ParagraphStyle("Section", parent=styles["Heading1"],
                               fontSize=13, textColor=CLR_SECTION_BG,
                               spaceBefore=6 * mm, spaceAfter=3 * mm,
                               borderPadding=(2, 2, 2, 2))
    s_body = ParagraphStyle("Body", parent=styles["Normal"],
                            fontSize=9, leading=12)
    s_small = ParagraphStyle("Small", parent=styles["Normal"],
                             fontSize=8, leading=10, textColor=grey)
    s_cell = ParagraphStyle("Cell", parent=styles["Normal"],
                            fontSize=8, leading=10)
    s_cell_bold = ParagraphStyle("CellBold", parent=s_cell,
                                 fontName="Helvetica-Bold")
    s_checkbox = ParagraphStyle("Check", parent=styles["Normal"],
                                fontSize=10, alignment=TA_CENTER)

    elements = []

    CHK = "[ ]"  # checkbox placeholder

    # ---- Helper: section header ----
    def add_section(title, number=None):
        prefix = "{}. ".format(number) if number else ""
        elements.append(Paragraph("{}{}".format(prefix, title), s_section))

    # ---- Helper: standard checklist table ----
    def make_check_table(data, col_widths):
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), CLR_SECTION_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), CLR_SECTION_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CLR_ROW_ALT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(style)
        return t

    # =====================================================================
    # PAGE 1: Title + Header Fields + Incoming Inspection
    # =====================================================================

    elements.append(Paragraph("SUPER 8 CAMERA", s_title))
    elements.append(Paragraph("Production Build Checklist", s_subtitle))
    elements.append(Spacer(1, 2 * mm))

    # Header fields table
    header_data = [
        [Paragraph("<b>Serial Number:</b>", s_cell), "________________",
         Paragraph("<b>Date:</b>", s_cell), "________________"],
        [Paragraph("<b>Technician:</b>", s_cell), "________________",
         Paragraph("<b>Initials:</b>", s_cell), "________"],
        [Paragraph("<b>Firmware Ver:</b>", s_cell), "________________",
         Paragraph("<b>Work Order:</b>", s_cell), "________________"],
    ]
    header_table = Table(header_data,
                         colWidths=[25 * mm, 55 * mm, 22 * mm, 55 * mm])
    header_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), CLR_ROW_ALT),
        ("BACKGROUND", (2, 0), (2, -1), CLR_ROW_ALT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5 * mm))

    # ---- Section 1: Incoming Inspection ----
    add_section("INCOMING INSPECTION", 1)
    elements.append(Paragraph(
        "Verify each component against acceptance criteria before starting assembly. "
        "Reject or quarantine any part that fails.",
        s_small))
    elements.append(Spacer(1, 2 * mm))

    insp_data = [[CHK, "Ref", "Part Description", "Acceptance Criteria", "OK"]]
    for ref, part, criteria in INCOMING_INSPECTION:
        insp_data.append([
            CHK, ref,
            Paragraph(part, s_cell),
            Paragraph(criteria, s_cell),
            CHK,
        ])

    insp_table = make_check_table(
        insp_data,
        col_widths=[10 * mm, 18 * mm, 52 * mm, 82 * mm, 10 * mm]
    )
    elements.append(insp_table)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Incoming inspection complete: _______ (initials)  Date: _________", s_small))
    elements.append(PageBreak())

    # =====================================================================
    # PAGE 2+: Sub-Assemblies
    # =====================================================================

    add_section("SUB-ASSEMBLY: FILM GATE", 2)
    fg_data = [[CHK, "Step", "Procedure"]]
    for step_id, desc in SUBASSEMBLY_FILM_GATE:
        fg_data.append([CHK, step_id, Paragraph(desc, s_cell)])
    elements.append(make_check_table(fg_data, [10 * mm, 14 * mm, 148 * mm]))
    elements.append(Spacer(1, 3 * mm))

    add_section("SUB-ASSEMBLY: SHUTTER DISC", 3)
    sh_data = [[CHK, "Step", "Procedure"]]
    for step_id, desc in SUBASSEMBLY_SHUTTER:
        sh_data.append([CHK, step_id, Paragraph(desc, s_cell)])
    elements.append(make_check_table(sh_data, [10 * mm, 14 * mm, 148 * mm]))
    elements.append(Spacer(1, 3 * mm))

    add_section("SUB-ASSEMBLY: MOTOR + GEARBOX + ENCODER", 4)
    mt_data = [[CHK, "Step", "Procedure"]]
    for step_id, desc in SUBASSEMBLY_MOTOR:
        mt_data.append([CHK, step_id, Paragraph(desc, s_cell)])
    elements.append(make_check_table(mt_data, [10 * mm, 14 * mm, 148 * mm]))
    elements.append(Spacer(1, 3 * mm))

    add_section("SUB-ASSEMBLY: PCB STUFFING + TEST", 5)
    pcb_data = [[CHK, "Step", "Procedure"]]
    for step_id, desc in SUBASSEMBLY_PCB:
        pcb_data.append([CHK, step_id, Paragraph(desc, s_cell)])
    elements.append(make_check_table(pcb_data, [10 * mm, 16 * mm, 146 * mm]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Sub-assemblies complete: _______ (initials)  Date: _________", s_small))
    elements.append(PageBreak())

    # =====================================================================
    # Final Assembly
    # =====================================================================

    add_section("FINAL ASSEMBLY", 6)
    elements.append(Paragraph(
        "Complete steps in order. Do not skip ahead. "
        "Record torque values where specified.",
        s_small))
    elements.append(Spacer(1, 2 * mm))

    fa_data = [[CHK, "Step", "Procedure", "Verification"]]
    for item in FINAL_ASSEMBLY:
        step_id, procedure, verification = item
        fa_data.append([
            CHK, step_id,
            Paragraph(procedure, s_cell),
            Paragraph(verification, s_cell),
        ])
    elements.append(make_check_table(
        fa_data, [10 * mm, 16 * mm, 95 * mm, 51 * mm]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Final assembly complete: _______ (initials)  Date: _________", s_small))
    elements.append(PageBreak())

    # =====================================================================
    # Calibration
    # =====================================================================

    add_section("CALIBRATION: METERING SYSTEM", 7)
    elements.append(Paragraph(
        "Requires: calibrated light source, reference light meter, "
        "serial debug connection.",
        s_small))
    elements.append(Spacer(1, 2 * mm))

    cm_data = [[CHK, "Step", "Procedure"]]
    for step_id, desc in CALIBRATION_METERING:
        cm_data.append([CHK, step_id, Paragraph(desc, s_cell)])
    elements.append(make_check_table(cm_data, [10 * mm, 16 * mm, 146 * mm]))
    elements.append(Spacer(1, 5 * mm))

    add_section("CALIBRATION: MOTOR SPEED", 8)
    elements.append(Paragraph(
        "Requires: dummy film cartridge or encoder test jig, strobe/oscilloscope.",
        s_small))
    elements.append(Spacer(1, 2 * mm))

    cms_data = [[CHK, "Step", "Procedure"]]
    for step_id, desc in CALIBRATION_MOTOR:
        cms_data.append([CHK, step_id, Paragraph(desc, s_cell)])
    elements.append(make_check_table(cms_data, [10 * mm, 16 * mm, 146 * mm]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Calibration complete: _______ (initials)  Date: _________", s_small))
    elements.append(PageBreak())

    # =====================================================================
    # Quality Control Tests
    # =====================================================================

    add_section("QUALITY CONTROL TESTS", 9)
    elements.append(Paragraph(
        "All tests must pass before the unit ships. "
        "Record results in the Result column.",
        s_small))
    elements.append(Spacer(1, 2 * mm))

    qc_data = [[CHK, "Test ID", "Test Name", "Procedure", "Result"]]
    for test_id, name, procedure, result_fmt in QC_TESTS:
        qc_data.append([
            CHK, test_id,
            Paragraph("<b>{}</b>".format(name), s_cell),
            Paragraph(procedure, s_cell),
            Paragraph(result_fmt, s_cell),
        ])
    elements.append(make_check_table(
        qc_data, [10 * mm, 14 * mm, 28 * mm, 82 * mm, 38 * mm]))
    elements.append(Spacer(1, 8 * mm))

    # =====================================================================
    # Sign-off
    # =====================================================================

    add_section("FINAL SIGN-OFF", 10)

    signoff_data = [
        ["", "Name (print)", "Signature", "Date"],
        ["Built by:", "________________", "________________", "__________"],
        ["QC inspected by:", "________________", "________________", "__________"],
        ["Approved for ship:", "________________", "________________", "__________"],
    ]
    signoff_table = Table(signoff_data,
                          colWidths=[35 * mm, 50 * mm, 55 * mm, 30 * mm])
    signoff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLR_SECTION_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), CLR_SECTION_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CLR_ROW_ALT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(signoff_table)
    elements.append(Spacer(1, 8 * mm))

    elements.append(Paragraph("Notes / Non-conformances:", s_body))
    elements.append(Spacer(1, 2 * mm))
    # Lined area for notes
    for _ in range(8):
        elements.append(Paragraph(
            "_" * 95, ParagraphStyle("Lines", parent=s_body,
                                     textColor=lightgrey, spaceAfter=4 * mm)))

    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(
        "Serial #: ____________  |  "
        "Final status: PASS / FAIL / CONDITIONAL  |  "
        "Date shipped: ___________",
        ParagraphStyle("Footer", parent=s_body, fontSize=10,
                       fontName="Helvetica-Bold")))

    # ---- Build the PDF ----
    doc.build(elements)
    print("  Generated: {}".format(output_path))


# =========================================================================
# Main
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Super 8 Camera Build Checklist PDF")
    parser.add_argument("-o", "--output", default="super8_build_checklist.pdf",
                        help="Output PDF path")
    args = parser.parse_args()

    sep = "=" * 60
    print(sep)
    print("  SUPER 8 CAMERA — BUILD CHECKLIST GENERATOR")
    print(sep)
    print()

    build_pdf(args.output)

    # Count items
    total_checks = (
        len(INCOMING_INSPECTION)
        + len(SUBASSEMBLY_FILM_GATE)
        + len(SUBASSEMBLY_SHUTTER)
        + len(SUBASSEMBLY_MOTOR)
        + len(SUBASSEMBLY_PCB)
        + len(FINAL_ASSEMBLY)
        + len(CALIBRATION_METERING)
        + len(CALIBRATION_MOTOR)
        + len(QC_TESTS)
    )

    print()
    print("  Sections:     10")
    print("  Total items:  {}".format(total_checks))
    print("  Inspection:   {} parts".format(len(INCOMING_INSPECTION)))
    print("  Sub-assembly: {} steps".format(
        len(SUBASSEMBLY_FILM_GATE) + len(SUBASSEMBLY_SHUTTER)
        + len(SUBASSEMBLY_MOTOR) + len(SUBASSEMBLY_PCB)))
    print("  Final assy:   {} steps".format(len(FINAL_ASSEMBLY)))
    print("  Calibration:  {} steps".format(
        len(CALIBRATION_METERING) + len(CALIBRATION_MOTOR)))
    print("  QC tests:     {} tests".format(len(QC_TESTS)))
    print()
    print("  " + sep)


if __name__ == "__main__":
    main()
