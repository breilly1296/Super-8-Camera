"""generate_drawings.py — 2D engineering drawings for every CNC-machined part.

For each part generates a matplotlib figure with:
  - Three orthographic views (front, top, right side) with hidden lines
  - Key dimensions with tolerance callouts
  - GD&T symbols where critical
  - Material specification and surface finish callouts
  - Part number, revision, scale, and title block

Exports each drawing as PDF to export/drawings/.
"""

import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle

from super8cam.specs.master_specs import (
    CAMERA, FILM, CMOUNT, TOL, FASTENERS, FASTENER_USAGE,
    MATERIALS, MATERIAL_USAGE, BEARINGS, GEARBOX, MOTOR,
)
from super8cam.manufacturing.gdt_standards import (
    get_gdt_callouts, get_surface_finish, GDT_SYMBOLS_ASCII,
    FeatureControlFrame, FINISH_BY_APPLICATION,
)

EXPORT_DIR = os.path.join("export", "drawings")
REV = "A"
SCALE_TEXT = "2:1"
PROJECT = "SUPER 8 CAMERA"
DRAWN_BY = "CAD System"


# =========================================================================
# Part number scheme
# =========================================================================

PART_NUMBERS = {
    # S8C-1xx: Mechanical - body/structure
    "body_left":           "S8C-101",
    "body_right":          "S8C-102",
    "top_plate":           "S8C-103",
    "bottom_plate":        "S8C-104",
    "battery_door":        "S8C-105",
    "cartridge_door":      "S8C-106",
    "trigger":             "S8C-107",
    "lens_mount":          "S8C-108",
    "viewfinder":          "S8C-109",
    "pcb_bracket":         "S8C-110",
    "cartridge_receiver":  "S8C-111",
    "motor_mount":         "S8C-112",
    # S8C-12x: Mechanical - film transport
    "film_gate":           "S8C-120",
    "pressure_plate":      "S8C-121",
    "film_channel":        "S8C-122",
    "registration_pin":    "S8C-123",
    "claw_mechanism":      "S8C-124",
    "cam_follower":        "S8C-125",
    # S8C-13x: Mechanical - drivetrain
    "main_shaft":          "S8C-130",
    "shutter_disc":        "S8C-131",
    "gearbox_housing":     "S8C-132",
    "stage1_pinion":       "S8C-133",
    "stage1_gear":         "S8C-134",
    "stage2_pinion":       "S8C-135",
    "stage2_gear":         "S8C-136",
}


# =========================================================================
# Part drawing specifications
# =========================================================================

@dataclass
class DimCallout:
    """A single dimension callout on a drawing view."""
    label: str
    nominal: float
    tolerance: Optional[float] = None
    tol_plus: Optional[float] = None
    tol_minus: Optional[float] = None
    fit: Optional[str] = None

    def text(self) -> str:
        if self.fit:
            return f"{self.nominal:.3f} {self.fit}"
        if self.tol_plus is not None and self.tol_minus is not None:
            return f"{self.nominal:.3f} +{self.tol_plus:.3f}/-{self.tol_minus:.3f}"
        if self.tolerance is not None:
            return f"{self.nominal:.3f} \u00b1{self.tolerance:.3f}"
        return f"{self.nominal:.2f}"


@dataclass
class PartDrawingSpec:
    """Complete specification for one part's drawing."""
    name: str
    part_number: str
    material: str
    material_designation: str
    surface_finish_ra: float
    surface_finish_note: str
    width: float        # X extent
    height: float       # Z extent
    depth: float        # Y extent
    dims: List[DimCallout]
    gdt_callouts: List[str]
    notes: List[str]


def _build_part_specs() -> Dict[str, PartDrawingSpec]:
    """Build drawing specifications for all machined parts."""
    specs = {}

    # --- Film Gate ---
    mat = MATERIALS[MATERIAL_USAGE["film_gate"]]
    gdt = get_gdt_callouts("film_gate")
    specs["film_gate"] = PartDrawingSpec(
        name="Film Gate",
        part_number=PART_NUMBERS["film_gate"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=TOL.gate_surface_ra,
        surface_finish_note="Mirror polish on film contact surfaces",
        width=CAMERA.gate_plate_w,
        height=CAMERA.gate_plate_h,
        depth=CAMERA.gate_plate_thick,
        dims=[
            DimCallout("Plate W", CAMERA.gate_plate_w, TOL.cnc_general),
            DimCallout("Plate H", CAMERA.gate_plate_h, TOL.cnc_general),
            DimCallout("Plate Thick", CAMERA.gate_plate_thick, TOL.cnc_fine),
            DimCallout("Aperture W", FILM.frame_w, TOL.gate_aperture),
            DimCallout("Aperture H", FILM.frame_h, TOL.gate_aperture),
            DimCallout("Channel Depth", CAMERA.gate_channel_depth, TOL.gate_channel_depth),
            DimCallout("Channel W", CAMERA.gate_channel_w, TOL.cnc_general),
            DimCallout("Reg Pin Hole", CAMERA.reg_pin_dia,
                       tol_plus=TOL.reg_pin_dia_plus, tol_minus=TOL.reg_pin_dia_minus),
            DimCallout("Reg Pin Pos", FILM.reg_pin_below_frame_center, TOL.reg_pin_position),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['position']} {chr(216)}0.010 |A|  Aperture position",
            f"{GDT_SYMBOLS_ASCII['flatness']} 0.005  Film channel flatness",
            f"{GDT_SYMBOLS_ASCII['position']} {chr(216)}0.010 |A|B|  Reg pin hole position",
        ],
        notes=[
            "Datum A: two M2 mounting holes",
            "Datum B: channel centerline",
            "All aperture corners R0.15",
            "Deburr all edges, no sharp edges on film contact surfaces",
        ],
    )

    # --- Main Shaft ---
    mat = MATERIALS[MATERIAL_USAGE["main_shaft"]]
    specs["main_shaft"] = PartDrawingSpec(
        name="Main Shaft",
        part_number=PART_NUMBERS["main_shaft"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=TOL.bearing_seat_ra,
        surface_finish_note="Ground finish on bearing journals",
        width=CAMERA.shaft_length,
        height=CAMERA.shaft_dia,
        depth=CAMERA.shaft_dia,
        dims=[
            DimCallout("Overall Length", CAMERA.shaft_length, TOL.cnc_general),
            DimCallout("Shaft Dia", CAMERA.shaft_dia, fit=TOL.bearing_shaft),
            DimCallout("Keyway W", CAMERA.shutter_keyway_w, TOL.cnc_fine),
            DimCallout("Keyway Depth", CAMERA.shutter_keyway_depth, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['cylindricity']} 0.010  Bearing journal cylindricity",
            f"{GDT_SYMBOLS_ASCII['concentricity']} {chr(216)}0.005 |A|B|  Bearing seats concentric",
        ],
        notes=[
            "Datum A: front bearing seat",
            "Datum B: rear bearing seat",
            "Heat treat to HRC 28-32",
            "Black oxide finish after grinding",
        ],
    )

    # --- Shutter Disc ---
    mat = MATERIALS[MATERIAL_USAGE["shutter_disc"]]
    specs["shutter_disc"] = PartDrawingSpec(
        name="Shutter Disc",
        part_number=PART_NUMBERS["shutter_disc"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize Type II",
        width=CAMERA.shutter_od,
        height=CAMERA.shutter_od,
        depth=CAMERA.shutter_thickness,
        dims=[
            DimCallout("OD", CAMERA.shutter_od, 0.1),
            DimCallout("Thickness", CAMERA.shutter_thickness, TOL.cnc_fine),
            DimCallout("Bore", CAMERA.shutter_shaft_hole, fit=TOL.press_fit_hole),
            DimCallout("Opening Angle", CAMERA.shutter_opening_angle),
            DimCallout("Keyway W", CAMERA.shutter_keyway_w, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['flatness']} 0.050  Disc face flatness",
            f"{GDT_SYMBOLS_ASCII['concentricity']} {chr(216)}0.020 |A|  Bore to OD",
            f"{GDT_SYMBOLS_ASCII['runout']} 0.030 |A|  Face runout",
        ],
        notes=[
            "Datum A: shaft bore axis",
            "Opening angle tolerance: +/-1 deg",
            "Deburr all edges to prevent film damage",
            "Balance disc to < 0.1 g-mm",
        ],
    )

    # --- Gearbox Housing ---
    mat = MATERIALS["alu_6061_t6"]
    specs["gearbox_housing"] = PartDrawingSpec(
        name="Gearbox Housing",
        part_number=PART_NUMBERS["gearbox_housing"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize Type II",
        width=30.0, height=25.0, depth=12.0,
        dims=[
            DimCallout("Main Bore", BEARINGS["main_shaft"].od, fit=TOL.bearing_seat),
            DimCallout("Stage 1 C-C", GEARBOX.stage1_center_distance, TOL.cnc_fine),
            DimCallout("Stage 2 C-C", GEARBOX.stage2_center_distance, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['cylindricity']} 0.010  All bearing bores",
            f"{GDT_SYMBOLS_ASCII['concentricity']} {chr(216)}0.010 |A|  Bores concentric to primary axis",
            f"{GDT_SYMBOLS_ASCII['parallelism']} 0.020 |A|  Mating face parallelism",
        ],
        notes=[
            "Datum A: main shaft bore axis",
            "Press-fit bearing seats per H7 tolerance",
            "Locating dowel holes for housing alignment",
        ],
    )

    # --- Registration Pin ---
    mat = MATERIALS[MATERIAL_USAGE["registration_pin"]]
    specs["registration_pin"] = PartDrawingSpec(
        name="Registration Pin",
        part_number=PART_NUMBERS["registration_pin"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=0.4,
        surface_finish_note="Polished to prevent film damage",
        width=CAMERA.reg_pin_length + 2.0,
        height=CAMERA.reg_pin_dia,
        depth=CAMERA.reg_pin_dia,
        dims=[
            DimCallout("Pin Dia", CAMERA.reg_pin_dia,
                       tol_plus=TOL.reg_pin_dia_plus, tol_minus=TOL.reg_pin_dia_minus),
            DimCallout("Protrusion", CAMERA.reg_pin_length, TOL.cnc_fine),
            DimCallout("Shoulder Dia", CAMERA.reg_pin_dia + 0.5, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['cylindricity']} 0.005  Pin cylindricity",
            f"{GDT_SYMBOLS_ASCII['straightness']} 0.003  Pin straightness",
        ],
        notes=[
            "Tip radius R0.05 max",
            "No burrs — inspect under magnification",
            "Press-fit into gate: p6 shaft tolerance",
        ],
    )

    # --- Pressure Plate ---
    mat = MATERIALS[MATERIAL_USAGE["pressure_plate"]]
    specs["pressure_plate"] = PartDrawingSpec(
        name="Pressure Plate",
        part_number=PART_NUMBERS["pressure_plate"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=0.4,
        surface_finish_note="Polished film contact surface",
        width=CAMERA.pressure_plate_w,
        height=CAMERA.pressure_plate_h,
        depth=CAMERA.pressure_plate_thick,
        dims=[
            DimCallout("Width", CAMERA.pressure_plate_w, TOL.cnc_general),
            DimCallout("Height", CAMERA.pressure_plate_h, TOL.cnc_general),
            DimCallout("Thickness", CAMERA.pressure_plate_thick, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['flatness']} 0.010  Film contact face",
        ],
        notes=[
            "Spring temper — do not anneal",
            "Spring force: 0.5 N nominal",
            "Deburr all edges, round film-contact edge R0.1",
        ],
    )

    # --- Claw Mechanism ---
    mat = MATERIALS[MATERIAL_USAGE["claw"]]
    specs["claw_mechanism"] = PartDrawingSpec(
        name="Claw Mechanism",
        part_number=PART_NUMBERS["claw_mechanism"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black oxide",
        width=CAMERA.claw_arm_length,
        height=CAMERA.claw_arm_w * 3,
        depth=CAMERA.claw_arm_thick,
        dims=[
            DimCallout("Arm Length", CAMERA.claw_arm_length, TOL.cnc_general),
            DimCallout("Tip W", CAMERA.claw_tip_w, TOL.cnc_fine),
            DimCallout("Tip H", CAMERA.claw_tip_h, TOL.cnc_fine),
            DimCallout("Stroke", CAMERA.claw_stroke, TOL.cnc_fine),
            DimCallout("Engage Depth", CAMERA.claw_engage_depth, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['position']} {chr(216)}0.020 |A|  Pivot bore position",
        ],
        notes=[
            "Claw tip must fit inside film perforation",
            f"Perforation: {FILM.perf_w} x {FILM.perf_h} mm",
            "Heat treat tip to HRC 45-50",
            "Polish tip — no burrs",
        ],
    )

    # --- Film Channel ---
    specs["film_channel"] = PartDrawingSpec(
        name="Film Channel",
        part_number=PART_NUMBERS["film_channel"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize Type II",
        width=CAMERA.film_channel_length,
        height=CAMERA.film_channel_width * 2,
        depth=5.0,
        dims=[
            DimCallout("Channel Length", CAMERA.film_channel_length, TOL.cnc_general),
            DimCallout("Channel Width", CAMERA.film_channel_width, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['flatness']} 0.020  Guide rail surfaces",
        ],
        notes=["Channel must align with gate aperture center"],
    )

    # --- Cam Follower ---
    mat = MATERIALS[MATERIAL_USAGE["cam"]]
    specs["cam_follower"] = PartDrawingSpec(
        name="Cam / Follower",
        part_number=PART_NUMBERS["cam_follower"],
        material=mat.name,
        material_designation=mat.designation,
        surface_finish_ra=0.8,
        surface_finish_note="Ground cam lobe surface",
        width=CAMERA.cam_od,
        height=CAMERA.cam_od,
        depth=CAMERA.cam_width,
        dims=[
            DimCallout("Cam OD", CAMERA.cam_od, TOL.cnc_fine),
            DimCallout("Bore", CAMERA.cam_id, fit=TOL.press_fit_hole),
            DimCallout("Width", CAMERA.cam_width, TOL.cnc_general),
            DimCallout("Lobe Lift", CAMERA.cam_lobe_lift, TOL.cnc_fine),
            DimCallout("Follower Dia", CAMERA.cam_follower_dia, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['runout']} 0.020 |A|  Cam lobe profile runout",
        ],
        notes=[
            "Datum A: shaft bore",
            "Cam profile: eccentric per pulldown spec",
            "Follower: press-fit 683ZZ bearing",
        ],
    )

    # --- Body halves, plates, doors ---
    for name, pn in [
        ("body_left", "S8C-101"), ("body_right", "S8C-102"),
        ("top_plate", "S8C-103"), ("bottom_plate", "S8C-104"),
        ("battery_door", "S8C-105"), ("cartridge_door", "S8C-106"),
    ]:
        mat = MATERIALS["alu_6061_t6"]
        is_body = name.startswith("body_")
        specs[name] = PartDrawingSpec(
            name=name.replace("_", " ").title(),
            part_number=pn,
            material=mat.name,
            material_designation=mat.designation,
            surface_finish_ra=TOL.body_exterior_ra,
            surface_finish_note="Black anodize Type II, 15-25 um",
            width=CAMERA.body_length if is_body else CAMERA.body_length * 0.5,
            height=CAMERA.body_height if is_body else CAMERA.body_height * 0.5,
            depth=CAMERA.body_depth / 2 if is_body else CAMERA.wall_thickness,
            dims=[
                DimCallout("Length", CAMERA.body_length if is_body else 60.0, TOL.cnc_general),
                DimCallout("Height", CAMERA.body_height if is_body else 50.0, TOL.cnc_general),
                DimCallout("Wall", CAMERA.wall_thickness, TOL.cnc_general),
            ],
            gdt_callouts=[
                f"{GDT_SYMBOLS_ASCII['flatness']} 0.050  Mating face",
            ] if is_body else [],
            notes=[
                "All M2.5 tap holes per body assembly drawing",
                "Light-seal groove 1.0 x 0.5 mm on mating face" if is_body else "",
            ],
        )

    # --- Lens Mount ---
    specs["lens_mount"] = PartDrawingSpec(
        name="Lens Mount (C-Mount)",
        part_number=PART_NUMBERS["lens_mount"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize, thread uncoated",
        width=CAMERA.lens_boss_od,
        height=CAMERA.lens_boss_od,
        depth=CAMERA.lens_boss_protrusion + 5.0,
        dims=[
            DimCallout("Boss OD", CAMERA.lens_boss_od, TOL.cnc_general),
            DimCallout("Thread OD", CMOUNT.thread_od, 0.025),
            DimCallout("Thread Depth", CMOUNT.thread_depth, TOL.cnc_fine),
            DimCallout("Flange Dist", CMOUNT.flange_focal_dist, 0.01),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['perpendicularity']} 0.030 |A|  Thread axis to film plane",
            f"{GDT_SYMBOLS_ASCII['position']} {chr(216)}0.050 |A|B|  Boss position",
        ],
        notes=[
            "C-mount thread: 1\"-32 UNF (ANSI B3.19)",
            f"Flange focal distance: {CMOUNT.flange_focal_dist} mm critical",
            "Datum A: body mounting face (= film plane reference)",
        ],
    )

    # --- Trigger ---
    specs["trigger"] = PartDrawingSpec(
        name="Trigger",
        part_number=PART_NUMBERS["trigger"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.body_exterior_ra,
        surface_finish_note="Black anodize Type II",
        width=15.0, height=25.0, depth=8.0,
        dims=[
            DimCallout("Pivot Bore", 3.0, fit=TOL.bearing_seat),
            DimCallout("Travel", 3.0, TOL.cnc_general),
        ],
        gdt_callouts=[],
        notes=["Smooth action, return spring 0.3N"],
    )

    # --- Viewfinder ---
    specs["viewfinder"] = PartDrawingSpec(
        name="Viewfinder",
        part_number=PART_NUMBERS["viewfinder"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.body_exterior_ra,
        surface_finish_note="Black anodize inside, satin outside",
        width=CAMERA.viewfinder_length,
        height=CAMERA.viewfinder_obj_dia,
        depth=CAMERA.viewfinder_obj_dia,
        dims=[
            DimCallout("Tube Length", CAMERA.viewfinder_length, TOL.cnc_general),
            DimCallout("Eye Aperture", CAMERA.viewfinder_eye_dia, TOL.cnc_general),
            DimCallout("Obj Aperture", CAMERA.viewfinder_obj_dia, TOL.cnc_general),
        ],
        gdt_callouts=[],
        notes=["Internal surfaces matte black to reduce flare"],
    )

    # --- Motor Mount ---
    specs["motor_mount"] = PartDrawingSpec(
        name="Motor Mount",
        part_number=PART_NUMBERS["motor_mount"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize Type II",
        width=25.0, height=25.0, depth=10.0,
        dims=[
            DimCallout("Motor Bore", MOTOR.body_dia + 0.1, TOL.cnc_general),
            DimCallout("Mount Hole Spacing", MOTOR.mount_hole_spacing, TOL.cnc_fine),
        ],
        gdt_callouts=[
            f"{GDT_SYMBOLS_ASCII['concentricity']} {chr(216)}0.050 |A|  Motor bore to mount holes",
        ],
        notes=[f"Motor: {MOTOR.model}, {MOTOR.body_dia}mm dia"],
    )

    # --- PCB Bracket ---
    specs["pcb_bracket"] = PartDrawingSpec(
        name="PCB Bracket",
        part_number=PART_NUMBERS["pcb_bracket"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize Type II",
        width=CAMERA.pcb_standoff_rect_w + 10,
        height=CAMERA.pcb_standoff_rect_h + 10,
        depth=CAMERA.pcb_standoff_height,
        dims=[
            DimCallout("Standoff Spacing W", CAMERA.pcb_standoff_rect_w, TOL.cnc_general),
            DimCallout("Standoff Spacing H", CAMERA.pcb_standoff_rect_h, TOL.cnc_general),
            DimCallout("Standoff Height", CAMERA.pcb_standoff_height, TOL.cnc_general),
        ],
        gdt_callouts=[],
        notes=["M2 tapped holes in standoffs for PCB mount"],
    )

    # --- Cartridge Receiver ---
    specs["cartridge_receiver"] = PartDrawingSpec(
        name="Cartridge Receiver",
        part_number=PART_NUMBERS["cartridge_receiver"],
        material=MATERIALS["alu_6061_t6"].name,
        material_designation="6061-T6",
        surface_finish_ra=TOL.general_machined_ra,
        surface_finish_note="Black anodize Type II",
        width=65.0, height=55.0, depth=22.0,
        dims=[
            DimCallout("Pocket Length", 67.0, TOL.cnc_general),
            DimCallout("Pocket Width", 62.0, TOL.cnc_general),
            DimCallout("Pocket Depth", 21.0, TOL.cnc_general),
        ],
        gdt_callouts=[],
        notes=["Cartridge must insert and eject smoothly", "Film exit slot aligned with gate"],
    )

    # --- Gears (Delrin) ---
    for gear_name, pn, teeth, module in [
        ("stage1_pinion", "S8C-133", GEARBOX.stage1_pinion_teeth, GEARBOX.stage1_module),
        ("stage1_gear",   "S8C-134", GEARBOX.stage1_gear_teeth, GEARBOX.stage1_module),
        ("stage2_pinion", "S8C-135", GEARBOX.stage2_pinion_teeth, GEARBOX.stage2_module),
        ("stage2_gear",   "S8C-136", GEARBOX.stage2_gear_teeth, GEARBOX.stage2_module),
    ]:
        pcd = teeth * module
        specs[gear_name] = PartDrawingSpec(
            name=gear_name.replace("_", " ").title(),
            part_number=pn,
            material=MATERIALS["delrin_150"].name,
            material_designation="POM-H",
            surface_finish_ra=1.6,
            surface_finish_note="As machined",
            width=pcd + 2 * module,
            height=pcd + 2 * module,
            depth=GEARBOX.gear_face_width,
            dims=[
                DimCallout("Teeth", teeth),
                DimCallout("Module", module),
                DimCallout("PCD", pcd, TOL.cnc_fine),
                DimCallout("Face Width", GEARBOX.gear_face_width, TOL.cnc_general),
                DimCallout("Bore", CAMERA.shaft_dia if "pinion" in gear_name else 4.0,
                           fit=TOL.press_fit_hole),
            ],
            gdt_callouts=[
                f"{GDT_SYMBOLS_ASCII['runout']} 0.030 |A|  Tooth runout",
            ],
            notes=[
                f"Pressure angle: {GEARBOX.gear_pressure_angle} deg",
                "Involute profile per DIN 867",
                "No lubrication required (Delrin self-lubricating)",
            ],
        )

    return specs


# =========================================================================
# Drawing renderer
# =========================================================================

def _draw_title_block(ax, spec: PartDrawingSpec, fig_w: float, fig_h: float):
    """Draw the title block in the lower-right corner."""
    bw, bh = fig_w * 0.45, fig_h * 0.18
    bx, by = fig_w - bw - 0.3, 0.2

    ax.add_patch(Rectangle((bx, by), bw, bh,
                            fill=False, edgecolor="black", linewidth=1.5))

    # Horizontal dividers
    row_h = bh / 5
    for i in range(1, 5):
        y = by + i * row_h
        ax.plot([bx, bx + bw], [y, y], "k-", linewidth=0.5)

    # Vertical divider at midpoint
    mid_x = bx + bw * 0.45
    ax.plot([mid_x, mid_x], [by, by + bh], "k-", linewidth=0.5)

    fs = 6.5
    pad = 0.08

    # Row 0 (bottom): scale + rev
    ax.text(bx + pad, by + 0.5 * row_h, f"SCALE: {SCALE_TEXT}", fontsize=fs, va="center")
    ax.text(mid_x + pad, by + 0.5 * row_h, f"REV: {REV}", fontsize=fs, va="center")

    # Row 1: material
    y1 = by + 1.5 * row_h
    ax.text(bx + pad, y1, f"MATERIAL: {spec.material_designation}", fontsize=fs, va="center")
    ax.text(mid_x + pad, y1, f"Ra {spec.surface_finish_ra} um", fontsize=fs, va="center")

    # Row 2: part number
    y2 = by + 2.5 * row_h
    ax.text(bx + pad, y2, f"PART NO: {spec.part_number}", fontsize=fs + 1,
            va="center", fontweight="bold")
    ax.text(mid_x + pad, y2, f"DRAWN: {DRAWN_BY}", fontsize=fs, va="center")

    # Row 3: part name
    y3 = by + 3.5 * row_h
    ax.text(bx + bw / 2, y3, spec.name, fontsize=fs + 2,
            va="center", ha="center", fontweight="bold")

    # Row 4 (top): project
    y4 = by + 4.5 * row_h
    ax.text(bx + bw / 2, y4, PROJECT, fontsize=fs + 1,
            va="center", ha="center", fontweight="bold")


def _draw_ortho_view(ax, spec: PartDrawingSpec, cx: float, cy: float,
                     w: float, h: float, view_label: str,
                     show_hidden: bool = True):
    """Draw one orthographic view as a simplified rectangle with features."""
    # Outer boundary
    ax.add_patch(Rectangle((cx - w/2, cy - h/2), w, h,
                            fill=False, edgecolor="black", linewidth=1.2))
    ax.text(cx, cy - h/2 - 0.25, view_label, fontsize=7,
            ha="center", va="top", style="italic")

    # For film gate: show aperture as dashed rectangle
    if "gate" in spec.name.lower():
        aw = FILM.frame_w * w / spec.width
        ah = FILM.frame_h * h / spec.height
        ax.add_patch(Rectangle((cx - aw/2, cy - ah/2), aw, ah,
                                fill=False, edgecolor="black", linewidth=0.8,
                                linestyle="--"))
        # Channel
        cw_scaled = CAMERA.gate_channel_w * w / spec.width
        ax.add_patch(Rectangle((cx - cw_scaled/2, cy - h * 0.45), cw_scaled, h * 0.9,
                                fill=False, edgecolor="gray", linewidth=0.5,
                                linestyle=":"))

    # For shutter disc: show circular profile
    elif "shutter" in spec.name.lower():
        r = min(w, h) * 0.48
        circle = plt.Circle((cx, cy), r, fill=False, edgecolor="black", linewidth=1.2)
        ax.add_patch(circle)
        # Bore
        br = r * CAMERA.shutter_shaft_hole / CAMERA.shutter_od
        bore = plt.Circle((cx, cy), br, fill=False, edgecolor="black", linewidth=0.8)
        ax.add_patch(bore)
        # Opening sector
        angle_start = -CAMERA.shutter_opening_angle / 2
        angle_end = CAMERA.shutter_opening_angle / 2
        wedge = mpatches.Wedge((cx, cy), r, angle_start, angle_end,
                                fill=False, edgecolor="gray", linewidth=0.5, linestyle="--")
        ax.add_patch(wedge)

    # For shaft: show as long rectangle with bearing seats
    elif "shaft" in spec.name.lower():
        # Hidden bearing seat lines
        if show_hidden:
            seat_w = w * 0.12
            for sx in [cx - w * 0.42, cx + w * 0.30]:
                ax.add_patch(Rectangle((sx, cy - h * 0.35), seat_w, h * 0.7,
                                        fill=False, edgecolor="gray", linewidth=0.5,
                                        linestyle="--"))

    # For gears: show pitch circle
    elif "gear" in spec.name.lower() or "pinion" in spec.name.lower():
        r = min(w, h) * 0.48
        pcd = plt.Circle((cx, cy), r * 0.85, fill=False,
                          edgecolor="gray", linewidth=0.5, linestyle="-.")
        ax.add_patch(pcd)
        od = plt.Circle((cx, cy), r, fill=False, edgecolor="black", linewidth=1.0)
        ax.add_patch(od)
        br = r * 0.15
        bore = plt.Circle((cx, cy), br, fill=False, edgecolor="black", linewidth=0.8)
        ax.add_patch(bore)

    # Generic hidden lines for other parts
    elif show_hidden:
        ax.plot([cx - w * 0.3, cx + w * 0.3], [cy, cy],
                color="gray", linewidth=0.4, linestyle="--")


def _draw_dimensions(ax, spec: PartDrawingSpec, x_start: float, y_start: float):
    """Draw dimension callouts as a list."""
    fs = 6
    y = y_start
    ax.text(x_start, y, "DIMENSIONS:", fontsize=fs + 1, fontweight="bold", va="top")
    y -= 0.35
    for dim in spec.dims:
        ax.text(x_start + 0.1, y, f"{dim.label}: {dim.text()}", fontsize=fs, va="top",
                fontfamily="monospace")
        y -= 0.25
    return y


def _draw_gdt(ax, spec: PartDrawingSpec, x_start: float, y_start: float):
    """Draw GD&T callouts."""
    if not spec.gdt_callouts:
        return y_start
    fs = 6
    y = y_start - 0.15
    ax.text(x_start, y, "GD&T:", fontsize=fs + 1, fontweight="bold", va="top")
    y -= 0.35
    for callout in spec.gdt_callouts:
        ax.text(x_start + 0.1, y, callout, fontsize=fs, va="top", fontfamily="monospace")
        y -= 0.25
    return y


def _draw_notes(ax, spec: PartDrawingSpec, x_start: float, y_start: float):
    """Draw notes section."""
    if not spec.notes:
        return y_start
    fs = 6
    y = y_start - 0.15
    ax.text(x_start, y, "NOTES:", fontsize=fs + 1, fontweight="bold", va="top")
    y -= 0.35
    for i, note in enumerate(spec.notes, 1):
        if note:
            ax.text(x_start + 0.1, y, f"{i}. {note}", fontsize=fs, va="top")
            y -= 0.25
    return y


def generate_drawing(spec: PartDrawingSpec, output_dir: str = EXPORT_DIR) -> str:
    """Generate a single part drawing as PDF.  Returns the output path."""
    os.makedirs(output_dir, exist_ok=True)

    fig_w, fig_h = 11.0, 8.5  # US Letter landscape (inches)
    fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.set_aspect("equal")
    ax.axis("off")

    # Border
    margin = 0.3
    ax.add_patch(Rectangle((margin, margin), fig_w - 2 * margin, fig_h - 2 * margin,
                            fill=False, edgecolor="black", linewidth=2.0))

    # Scale views to fit in the drawing area
    view_area_w = fig_w * 0.60
    view_area_h = fig_h * 0.55
    max_dim = max(spec.width, spec.height, spec.depth)
    scale = min(view_area_w / (max_dim * 2.5), view_area_h / (max_dim * 1.5)) if max_dim > 0 else 1.0

    sw = spec.width * scale
    sh = spec.height * scale
    sd = spec.depth * scale

    view_y_center = fig_h * 0.58

    # Front view (W x H)
    front_cx = fig_w * 0.22
    _draw_ortho_view(ax, spec, front_cx, view_y_center, sw, sh, "FRONT VIEW")

    # Top view (W x D), above front
    top_cy = view_y_center + sh / 2 + sd / 2 + 0.6
    if top_cy + sd / 2 < fig_h - 0.8:
        _draw_ortho_view(ax, spec, front_cx, top_cy, sw, sd, "TOP VIEW", show_hidden=True)

    # Right side view (D x H)
    right_cx = front_cx + sw / 2 + sd / 2 + 0.8
    if right_cx + sd / 2 < fig_w * 0.55:
        _draw_ortho_view(ax, spec, right_cx, view_y_center, sd, sh, "RIGHT SIDE", show_hidden=True)

    # Dimensions, GD&T, and notes in the right column
    text_x = fig_w * 0.56
    text_y = fig_h - 0.7
    y = _draw_dimensions(ax, spec, text_x, text_y)
    y = _draw_gdt(ax, spec, text_x, y)
    y = _draw_notes(ax, spec, text_x, y)

    # Surface finish callout
    y -= 0.3
    ax.text(text_x, y, f"SURFACE FINISH: Ra {spec.surface_finish_ra} um",
            fontsize=6, va="top", fontweight="bold")
    y -= 0.2
    ax.text(text_x + 0.1, y, spec.surface_finish_note, fontsize=5.5, va="top")

    # Title block
    _draw_title_block(ax, spec, fig_w, fig_h)

    # Save
    filename = f"{spec.part_number}_{spec.name.replace(' ', '_').replace('/', '_')}.pdf"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return filepath


# =========================================================================
# Public API
# =========================================================================

def generate_all(output_dir: str = EXPORT_DIR) -> List[str]:
    """Generate engineering drawings for all machined parts.

    Returns list of output PDF paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    all_specs = _build_part_specs()
    paths = []

    print(f"  Generating {len(all_specs)} engineering drawings...")
    for name, spec in sorted(all_specs.items()):
        try:
            path = generate_drawing(spec, output_dir)
            paths.append(path)
            print(f"    {spec.part_number} {spec.name:30s} -> {os.path.basename(path)}")
        except Exception as e:
            print(f"    {spec.part_number} {spec.name:30s} FAILED: {e}")

    print(f"  {len(paths)} drawings exported to {output_dir}/")
    return paths


def get_part_numbers() -> Dict[str, str]:
    """Return the part number mapping."""
    return dict(PART_NUMBERS)


def get_part_specs() -> Dict[str, PartDrawingSpec]:
    """Return all part drawing specifications."""
    return _build_part_specs()


if __name__ == "__main__":
    paths = generate_all()
    print(f"\nGenerated {len(paths)} drawings.")
