"""verify_shell_fit.py — Check if internal parts fit inside the Tripo shell.

Loads shell_out.stl with trimesh and builds the full CadQuery assembly,
then checks whether each part's world-position bounding box falls within
the shell's interior.  Uses proximity-based signed distance (works on
non-watertight meshes with cut openings).

Usage:
    conda run -n super8 python verify_shell_fit.py
    conda run -n super8 python verify_shell_fit.py --shell my_shell.stl
    conda run -n super8 python verify_shell_fit.py --sample-density 3
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

# ---------------------------------------------------------------------------
# Shell-fit checking
# ---------------------------------------------------------------------------

def load_shell(path: str) -> trimesh.Trimesh:
    """Load the shell mesh from STL."""
    print(f"  Loading shell: {path}")
    mesh = trimesh.load(path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Expected Trimesh, got {type(mesh)}")
    bb = mesh.bounding_box.extents
    print(f"    Vertices: {len(mesh.vertices):,}   Faces: {len(mesh.faces):,}")
    print(f"    BB: {bb[0]:.1f} x {bb[1]:.1f} x {bb[2]:.1f} mm")
    print(f"    Watertight: {mesh.is_watertight}")
    return mesh


def bb_corners(xmin, ymin, zmin, xmax, ymax, zmax) -> np.ndarray:
    """Return the 8 corners of an axis-aligned bounding box."""
    return np.array([
        [xmin, ymin, zmin],
        [xmin, ymin, zmax],
        [xmin, ymax, zmin],
        [xmin, ymax, zmax],
        [xmax, ymin, zmin],
        [xmax, ymin, zmax],
        [xmax, ymax, zmin],
        [xmax, ymax, zmax],
    ])


def bb_edge_samples(xmin, ymin, zmin, xmax, ymax, zmax,
                    n_per_edge: int = 3) -> np.ndarray:
    """Sample points along BB edges and face centers for denser coverage."""
    pts = list(bb_corners(xmin, ymin, zmin, xmax, ymax, zmax))
    # Face centers (6 faces)
    cx, cy, cz = (xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2
    pts.extend([
        [xmin, cy, cz], [xmax, cy, cz],  # ±X faces
        [cx, ymin, cz], [cx, ymax, cz],  # ±Y faces
        [cx, cy, zmin], [cx, cy, zmax],  # ±Z faces
    ])
    # Edge midpoints (12 edges)
    for x in [xmin, xmax]:
        for y in [ymin, ymax]:
            pts.append([x, y, cz])
        for z in [zmin, zmax]:
            pts.append([x, cy, z])
    for y in [ymin, ymax]:
        for z in [zmin, zmax]:
            pts.append([cx, y, z])
    return np.array(pts)


def signed_distance_to_shell(shell: trimesh.Trimesh,
                              points: np.ndarray) -> np.ndarray:
    """Compute signed distance from points to shell surface.

    Positive = outside the shell (protruding).
    Negative = inside the shell.

    Uses closest-point + face-normal dot product, which works on
    non-watertight meshes (unlike ray-based containment tests).
    """
    closest, distances, tri_ids = trimesh.proximity.closest_point(shell, points)
    # Direction from shell surface to test point
    directions = points - closest
    # Face normal at closest triangle
    normals = shell.face_normals[tri_ids]
    # Dot product: positive means point is on the outward side of the surface
    dots = np.einsum("ij,ij->i", directions, normals)
    signed = np.where(dots >= 0, distances, -distances)
    return signed


# ---------------------------------------------------------------------------
# CadQuery part extraction
# ---------------------------------------------------------------------------

def build_assembly_parts() -> list:
    """Build the full camera assembly and extract each part's world BB.

    Returns list of (name, xmin, ymin, zmin, xmax, ymax, zmax).
    """
    print("  Building CadQuery assembly ...")
    from super8cam.assemblies.full_camera import build, _iter_assembly_parts, _get_solid

    assy = build()
    parts = []

    for name, shape, loc in _iter_assembly_parts(assy):
        try:
            solid = _get_solid(shape)
            if loc is not None:
                solid = solid.moved(loc)
            bb = solid.BoundingBox()
            parts.append((name, bb.xmin, bb.ymin, bb.zmin,
                          bb.xmax, bb.ymax, bb.zmax))
        except Exception as e:
            print(f"    WARNING: could not get BB for '{name}': {e}")

    print(f"    Extracted {len(parts)} parts from assembly")
    return parts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

EXTERNAL_PARTS = {
    "body_left", "body_right", "top_plate", "bottom_plate",
    "cartridge_door", "battery_door", "lens_placeholder",
}


def main():
    parser = argparse.ArgumentParser(
        description="Check if internal parts fit inside the shell mesh")
    parser.add_argument("--shell", default="shell_out.stl",
                        help="Shell mesh STL (default: shell_out.stl)")
    parser.add_argument("--sample-density", type=int, default=2,
                        choices=[1, 2, 3],
                        help="1=corners only (8 pts), 2=+edges/faces (26 pts), "
                             "3=dense grid (default: 2)")
    parser.add_argument("--tolerance", type=float, default=0.5,
                        help="Max allowed protrusion in mm (default: 0.5)")
    args = parser.parse_args()

    shell_path = Path(args.shell)
    if not shell_path.exists():
        # Try in project root
        alt = Path(__file__).parent / args.shell
        if alt.exists():
            shell_path = alt
        else:
            print(f"Error: shell mesh not found: {args.shell}")
            sys.exit(1)

    t0 = time.time()
    sep = "=" * 78
    print(f"\n{sep}")
    print("  SHELL FIT VERIFICATION")
    print(sep)

    # Load shell
    shell = load_shell(str(shell_path))
    print()

    # Build assembly parts
    parts = build_assembly_parts()
    print()

    # Check each part
    fmt_hdr = "  {:<24s} {:>7s} {:>7s} {:>7s}  {:>8s}  {:>6s}  {}"
    fmt_row = "  {:<24s} {:>7.1f} {:>7.1f} {:>7.1f}  {:>8.2f}  {:>6s}  {}"
    print(fmt_hdr.format("Part", "dX", "dY", "dZ", "MaxProt", "Status", "Detail"))
    print("  " + "-" * 74)

    n_fit = 0
    n_protrude = 0
    n_external = 0
    protrusions = []

    for name, xmin, ymin, zmin, xmax, ymax, zmax in parts:
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin

        is_external = name in EXTERNAL_PARTS

        # Generate test points
        if args.sample_density == 1:
            pts = bb_corners(xmin, ymin, zmin, xmax, ymax, zmax)
        elif args.sample_density == 2:
            pts = bb_edge_samples(xmin, ymin, zmin, xmax, ymax, zmax)
        else:
            # Dense: 5×5×5 grid inside BB
            xs = np.linspace(xmin, xmax, 5)
            ys = np.linspace(ymin, ymax, 5)
            zs = np.linspace(zmin, zmax, 5)
            grid = np.array(np.meshgrid(xs, ys, zs)).T.reshape(-1, 3)
            pts = grid

        # Compute signed distance
        sd = signed_distance_to_shell(shell, pts)
        max_protrusion = float(np.max(sd))  # positive = outside
        n_outside = int(np.sum(sd > args.tolerance))

        if is_external:
            tag = "EXT"
            detail = "external part (shell/door/plate)"
            n_external += 1
        elif max_protrusion <= args.tolerance:
            tag = "FIT"
            detail = ""
            n_fit += 1
        else:
            tag = "OUT"
            # Find which directions protrude
            corners = bb_corners(xmin, ymin, zmin, xmax, ymax, zmax)
            corner_sd = signed_distance_to_shell(shell, corners)
            worst_idx = int(np.argmax(corner_sd))
            worst_corner = corners[worst_idx]
            dirs = []
            cx = (xmin + xmax) / 2
            cy = (ymin + ymax) / 2
            cz = (zmin + zmax) / 2
            if worst_corner[0] > cx:
                dirs.append("+X")
            else:
                dirs.append("-X")
            if worst_corner[1] > cy:
                dirs.append("+Y")
            else:
                dirs.append("-Y")
            if worst_corner[2] > cz:
                dirs.append("+Z")
            else:
                dirs.append("-Z")
            detail = f"{n_outside} pts out, worst toward {'/'.join(dirs)}"
            n_protrude += 1
            protrusions.append((name, max_protrusion, detail))

        print(fmt_row.format(name, dx, dy, dz, max_protrusion, tag, detail))

    # Summary
    elapsed = time.time() - t0
    print()
    print(f"  {'-' * 74}")
    print(f"  Internal parts that FIT:      {n_fit}")
    print(f"  Internal parts that PROTRUDE: {n_protrude}")
    print(f"  External parts (skipped):     {n_external}")
    print(f"  Tolerance:                    {args.tolerance:.1f} mm")
    print()

    if protrusions:
        print("  PROTRUSION DETAILS:")
        for name, prot, detail in sorted(protrusions, key=lambda x: -x[1]):
            print(f"    {name:<24s}  {prot:>6.2f} mm  {detail}")
        print()

    shell_bb = shell.bounding_box
    sbb = shell_bb.extents
    sc = shell_bb.centroid
    print(f"  Shell BB:     {sbb[0]:.1f} x {sbb[1]:.1f} x {sbb[2]:.1f} mm  "
          f"(centroid: {sc[0]:.1f}, {sc[1]:.1f}, {sc[2]:.1f})")

    # Compute assembly internal envelope
    internal_parts = [(n, x0, y0, z0, x1, y1, z1)
                      for n, x0, y0, z0, x1, y1, z1 in parts
                      if n not in EXTERNAL_PARTS]
    if internal_parts:
        all_mins = np.array([[x0, y0, z0] for _, x0, y0, z0, _, _, _ in internal_parts])
        all_maxs = np.array([[x1, y1, z1] for _, _, _, _, x1, y1, z1 in internal_parts])
        env_min = all_mins.min(axis=0)
        env_max = all_maxs.max(axis=0)
        env_ext = env_max - env_min
        env_ctr = (env_min + env_max) / 2
        print(f"  Internals BB: {env_ext[0]:.1f} x {env_ext[1]:.1f} x {env_ext[2]:.1f} mm  "
              f"(centroid: {env_ctr[0]:.1f}, {env_ctr[1]:.1f}, {env_ctr[2]:.1f})")

        # Check centroid alignment
        offset = env_ctr - sc
        if np.any(np.abs(offset) > 2.0):
            print(f"  WARNING: internals centroid offset from shell by "
                  f"({offset[0]:.1f}, {offset[1]:.1f}, {offset[2]:.1f}) mm")
            print(f"           Consider adjusting shell alignment in integrate_shell.py")

    overall = "PASS" if n_protrude == 0 else "FAIL"
    print(f"\n  Overall: {overall}  ({elapsed:.1f}s)")
    print(sep)

    return n_protrude == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
