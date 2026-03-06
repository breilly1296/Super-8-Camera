"""Electronics assembly — PCB bracket + board outline."""

import cadquery as cq
from super8cam.specs.master_specs import CAMERA, PCB
from super8cam.parts import pcb_bracket


def build() -> cq.Assembly:
    assy = cq.Assembly(name="electronics")

    # PCB bracket
    assy.add(pcb_bracket.build(), name="pcb_bracket",
             loc=cq.Location((CAMERA.pcb_mount_offset_x, 0,
                               -CAMERA.body_height / 2 + CAMERA.wall_thickness)))

    # PCB board (simple box representing the populated board)
    board = (
        cq.Workplane("XY")
        .box(PCB.width, PCB.height, PCB.thickness)
    )
    assy.add(board, name="pcb_board",
             loc=cq.Location((CAMERA.pcb_mount_offset_x, 0,
                               -CAMERA.body_height / 2 + CAMERA.wall_thickness
                               + CAMERA.pcb_standoff_height + PCB.thickness / 2)))

    return assy
