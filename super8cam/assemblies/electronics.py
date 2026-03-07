"""Electronics assembly — PCB bracket + board + complete wiring harness.

Defines the wiring harness connecting the PCB (MOD-500 ELECTRONICS) to
every other module via JST connectors.  Wire lengths are computed from
the 3D datum positions in full_camera.py.  CadQuery visualization
renders L-shaped wire routes as thin cylinders for assembly verification.

    from super8cam.assemblies.electronics import WIRE_HARNESS, build
"""

import math
import cadquery as cq
from super8cam.specs.master_specs import CAMERA, PCB
from super8cam.parts import pcb_bracket
from super8cam.specs.modularity import CONNECTORS, MODULES


# =========================================================================
# MODULE 3D POSITIONS  (from full_camera.py datum positions)
# =========================================================================
# Each module's representative wiring endpoint — the point where the JST
# connector on that module is located.  PCB is the hub; all wires fan out.

# PCB center (MOD-500)
PCB_X = CAMERA.pcb_mount_offset_x      # -15.0 mm
PCB_Y = 0.0
PCB_Z = (-CAMERA.body_height / 2.0 + CAMERA.wall_thickness
         + CAMERA.pcb_standoff_height + 2.0)  # -31.5 mm

# Module endpoint positions (where the far-end connector sits)
MODULE_POSITIONS = {
    "MOD-100": (-18.0, -34.0, 0.0),       # Film transport — near gate
    "MOD-200": (-18.0, -34.0, 16.0),      # Shutter — on shaft
    "MOD-300": (17.0, -6.5, -2.0),        # Drivetrain — motor area
    "MOD-400": (39.0, 0.0, 3.0),          # Cartridge bay — right side
    "MOD-500": (PCB_X, PCB_Y, PCB_Z),     # Electronics — self (PCB)
    "MOD-600": (20.0, 0.0,
                -CAMERA.body_height / 2.0),  # Power — battery area
    "MOD-700": (-23.0, -26.0, 34.0),      # Optics — viewfinder
}

# PCB edge connector exit point (connectors along the +Y edge of the PCB)
PCB_EDGE_Y = PCB_Y + PCB.height / 2.0    # 17.5 mm


# =========================================================================
# WIRE GAUGE SELECTION
# =========================================================================
# AWG based on max current per connector (JST XH rated for 3A max).
# Conservative: 1A → 26AWG, <100mA → 28AWG, >500mA → 24AWG, >1A → 22AWG.

def _select_wire_gauge(max_current_ma: float) -> int:
    """Select AWG gauge based on max current (mA)."""
    if max_current_ma > 1000:
        return 22
    if max_current_ma > 500:
        return 24
    if max_current_ma > 100:
        return 26
    return 28


# =========================================================================
# WIRE HARNESS COMPUTATION
# =========================================================================
# For each connector, compute the 3D Manhattan (L-route) distance from
# the PCB edge to the target module, plus 30mm service loop allowance.

SERVICE_LOOP = 30.0    # mm extra per wire for connector mating / rework
WIRE_DIA = 0.8         # mm — visual diameter for CadQuery rendering


def _compute_wire_route(conn_id, conn):
    """Compute wire route metadata for a single connector.

    Returns a dict with positions, length, gauge, and routing waypoints.
    """
    # Determine source and destination positions.
    # PCB (MOD-500) is always one end.  The other end is the target module.
    if conn.from_module == "MOD-500":
        pcb_connector_slot = conn_id   # connector header is on the PCB
        target_module = conn.to_module
    else:
        pcb_connector_slot = conn_id
        target_module = conn.from_module

    src = (PCB_X, PCB_EDGE_Y, PCB_Z)
    dst = MODULE_POSITIONS.get(target_module, (0, 0, 0))

    # L-shaped route: go vertically first (Z), then laterally (X), then depth (Y)
    waypoints = [
        src,
        (src[0], src[1], dst[2]),          # vertical leg
        (dst[0], src[1], dst[2]),          # lateral leg
        dst,                               # depth leg to destination
    ]

    # Manhattan distance along L-route segments
    route_length = 0.0
    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        route_length += abs(b[0] - a[0]) + abs(b[1] - a[1]) + abs(b[2] - a[2])

    total_length = route_length + SERVICE_LOOP

    return {
        "connector_id": conn_id,
        "pin_count": conn.pin_count,
        "jst_family": conn.jst_family,
        "wire_colors": list(conn.wire_colors),
        "signal_names": list(conn.signal_names),
        "wire_gauge_awg": _select_wire_gauge(conn.max_current_ma),
        "max_current_ma": conn.max_current_ma,
        "from_module": conn.from_module,
        "to_module": conn.to_module,
        "from_position_xyz": src,
        "to_position_xyz": dst,
        "waypoints": waypoints,
        "route_length_mm": round(route_length, 1),
        "total_length_mm": round(total_length, 1),
    }


# Build the complete harness dictionary
WIRE_HARNESS = {}
for _cid, _conn in CONNECTORS.items():
    WIRE_HARNESS[_cid] = _compute_wire_route(_cid, _conn)


def get_wire_cut_list():
    """Return a flat list of individual wires for manufacturing.

    Each entry: (connector_id, pin_number, color, signal, length_mm, gauge_awg).
    """
    cuts = []
    for cid, route in WIRE_HARNESS.items():
        for pin_idx, (color, signal) in enumerate(
                zip(route["wire_colors"], route["signal_names"])):
            cuts.append({
                "connector_id": cid,
                "pin": pin_idx + 1,
                "color": color,
                "signal": signal,
                "length_mm": route["total_length_mm"],
                "gauge_awg": route["wire_gauge_awg"],
            })
    return cuts


def print_harness_summary():
    """Print a formatted wiring harness summary."""
    sep = "=" * 72
    print(f"\n{sep}")
    print("  WIRING HARNESS — SUPER 8 CAMERA")
    print(sep)
    print(f"  {'ID':<4} {'Pins':<5} {'Family':<6} {'From':<10} {'To':<10} "
          f"{'Route':<8} {'Total':<8} {'AWG':<5} {'Colors'}")
    print(f"  {'--':<4} {'----':<5} {'------':<6} {'--------':<10} {'--------':<10} "
          f"{'-----':<8} {'-----':<8} {'---':<5} {'------'}")
    total_wire = 0.0
    for cid in sorted(WIRE_HARNESS.keys()):
        w = WIRE_HARNESS[cid]
        colors = ", ".join(w["wire_colors"])
        print(f"  {cid:<4} {w['pin_count']:<5} {w['jst_family']:<6} "
              f"{w['from_module']:<10} {w['to_module']:<10} "
              f"{w['route_length_mm']:<8.1f} {w['total_length_mm']:<8.1f} "
              f"{w['wire_gauge_awg']:<5} {colors}")
        total_wire += w["total_length_mm"] * w["pin_count"]

    print(f"\n  Total wire length (all conductors): {total_wire:.0f} mm "
          f"({total_wire / 1000:.2f} m)")
    print(f"  Total connectors: {len(WIRE_HARNESS)}")
    print(f"  Total conductors: {sum(w['pin_count'] for w in WIRE_HARNESS.values())}")
    print(sep)


# =========================================================================
# CADQUERY WIRE ROUTE VISUALIZATION
# =========================================================================

def _build_wire_route(waypoints, color_index=0) -> cq.Workplane:
    """Build a CadQuery cylinder chain following L-shaped waypoints.

    Each segment is a thin cylinder connecting consecutive waypoints.
    Returns a single unioned solid.
    """
    wire = cq.Workplane("XY").box(0.01, 0.01, 0.01)  # seed
    r = WIRE_DIA / 2.0

    for i in range(len(waypoints) - 1):
        ax, ay, az = waypoints[i]
        bx, by, bz = waypoints[i + 1]

        dx = bx - ax
        dy = by - ay
        dz = bz - az
        seg_len = math.sqrt(dx * dx + dy * dy + dz * dz)

        if seg_len < 0.1:
            continue

        # Build a cylinder along each axis-aligned segment
        mid_x = (ax + bx) / 2.0
        mid_y = (ay + by) / 2.0
        mid_z = (az + bz) / 2.0

        if abs(dz) > abs(dx) and abs(dz) > abs(dy):
            # Vertical segment (along Z)
            seg = (
                cq.Workplane("XY")
                .cylinder(seg_len, r)
                .translate((mid_x, mid_y, mid_z))
            )
        elif abs(dx) > abs(dy):
            # Lateral segment (along X)
            seg = (
                cq.Workplane("YZ")
                .cylinder(seg_len, r)
                .translate((mid_x, mid_y, mid_z))
            )
        else:
            # Depth segment (along Y)
            seg = (
                cq.Workplane("XZ")
                .cylinder(seg_len, r)
                .translate((mid_x, mid_y, mid_z))
            )

        wire = wire.union(seg)

    return wire


def build_wire_harness() -> cq.Assembly:
    """Build visual wire harness as a CadQuery Assembly.

    Each connector's wire bundle is a single cylinder chain following
    the L-shaped route from PCB edge to module.
    """
    harness = cq.Assembly(name="wire_harness")

    for cid in sorted(WIRE_HARNESS.keys()):
        route = WIRE_HARNESS[cid]
        wire_solid = _build_wire_route(route["waypoints"])
        harness.add(wire_solid, name=f"wire_{cid}",
                    loc=cq.Location((0, 0, 0)))

    return harness


# =========================================================================
# ASSEMBLY BUILDER
# =========================================================================

def build() -> cq.Assembly:
    """Build the complete electronics assembly with wiring harness."""
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

    # JST connector visualization blocks on PCB edge
    from super8cam.parts.interfaces import make_jst_xh_socket
    connector_y_offset = PCB_EDGE_Y
    connector_spacing = PCB.width / (len(CONNECTORS) + 1)

    for idx, (cid, conn) in enumerate(sorted(CONNECTORS.items())):
        cx = PCB_X - PCB.width / 2.0 + connector_spacing * (idx + 1)
        socket = make_jst_xh_socket(conn.pin_count)
        assy.add(socket, name=f"connector_{cid}",
                 loc=cq.Location((cx, connector_y_offset, PCB_Z)))

    # Wire harness
    assy.add(build_wire_harness(), name="wiring",
             loc=cq.Location((0, 0, 0)))

    return assy


# =========================================================================
# EXPORT
# =========================================================================

def export(output_dir: str = "export"):
    """Export the electronics assembly as STEP."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    solid = build()
    cq.exporters.export(solid.toCompound(),
                        f"{output_dir}/electronics_assembly.step")
    print(f"  Electronics assembly exported to {output_dir}/")
    print_harness_summary()


if __name__ == "__main__":
    print_harness_summary()
