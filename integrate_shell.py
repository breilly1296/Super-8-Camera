"""integrate_shell.py — Fit a Tripo AI mesh over validated camera internals.

Loads an external mesh (OBJ/GLB/STL), builds the CadQuery assembly to measure
the actual internal parts bounding box, scales each axis independently to
enclose all internals with 5mm clearance + 2.5mm wall per side, aligns the
shell centroid to the internals centroid, hollows to 2.5mm wall, and cuts
openings by deleting faces — no boolean operations required.

This is a starting point for FreeCAD refinement, not a production part.

Usage:
    conda run -n super8 python integrate_shell.py <mesh_file> [--output shell_out.stl]
    conda run -n super8 python integrate_shell.py canon514xl.glb
    conda run -n super8 python integrate_shell.py canon514xl.obj --output my_shell.stl
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WALL = 2.5        # mm wall thickness
CLEARANCE = 5.0   # mm clearance per side between internals and inner shell wall

# Parts that are external (shell, doors, plates) — excluded from internals BB
EXTERNAL_PARTS = {
    "body_left", "body_right", "top_plate", "bottom_plate",
    "cartridge_door", "battery_door", "lens_placeholder",
}

# Optical axis: lens mount is at X = -18mm from body center, Y = front face
LENS_X = -18.0   # mm — lens center X offset from body center
LENS_BORE_DIA = 28.0  # mm — C-mount clearance bore

# Cartridge door opening (right face, +X side)
CART_DOOR_W = 60.0   # mm (Z extent)
CART_DOOR_H = 50.0   # mm (Y extent)
CART_DOOR_Z = 3.0    # mm — door center Z offset

# Battery bay opening (bottom face, -Z side)
BATT_BAY_L = 62.0    # mm (X extent)
BATT_BAY_W = 32.0    # mm (Y extent)
BATT_BAY_X = 20.0    # mm — bay center X offset (right of center)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_mesh(path: str) -> trimesh.Trimesh:
    """Load a mesh from OBJ/GLB/STL and force it to a single Trimesh."""
    print(f"  Loading {path} ...")
    scene_or_mesh = trimesh.load(path, force="mesh")
    if isinstance(scene_or_mesh, trimesh.Scene):
        # Flatten scene into a single mesh
        meshes = [g for g in scene_or_mesh.geometry.values()
                  if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("No triangle meshes found in file")
        mesh = trimesh.util.concatenate(meshes)
    elif isinstance(scene_or_mesh, trimesh.Trimesh):
        mesh = scene_or_mesh
    else:
        raise ValueError(f"Unexpected type: {type(scene_or_mesh)}")

    print(f"    Vertices: {len(mesh.vertices):,}")
    print(f"    Faces:    {len(mesh.faces):,}")
    print(f"    Watertight: {mesh.is_watertight}")
    return mesh


def print_bb(mesh: trimesh.Trimesh, label: str = ""):
    """Print bounding box info."""
    bb = mesh.bounding_box.extents
    c = mesh.centroid
    print(f"  {label}BB: {bb[0]:.1f} x {bb[1]:.1f} x {bb[2]:.1f} mm  "
          f"(centroid: {c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f})")


def detect_orientation(mesh: trimesh.Trimesh) -> dict:
    """Heuristic: detect which mesh axis is longest/tallest/deepest.

    Returns axis mapping: {'length': idx, 'depth': idx, 'height': idx}
    where length=X (longest), height=Z (tallest), depth=Y (front-back).

    Assumes a camera-like shape where length > height > depth.
    """
    extents = mesh.bounding_box.extents
    order = np.argsort(extents)  # ascending
    # longest = length (X), middle = height (Z), shortest = depth (Y)
    return {
        "length": int(order[2]),  # X — longest
        "height": int(order[1]),  # Z — middle
        "depth":  int(order[0]),  # Y — shortest
    }


def reorient_mesh(mesh: trimesh.Trimesh, axis_map: dict) -> trimesh.Trimesh:
    """Rotate mesh so length→X, depth→Y, height→Z.

    Returns a new mesh with axes permuted to match our convention.
    """
    # Build a 3x3 permutation matrix
    perm = np.zeros((3, 3))
    perm[0, axis_map["length"]] = 1  # mesh axis → X
    perm[1, axis_map["depth"]]  = 1  # mesh axis → Y
    perm[2, axis_map["height"]] = 1  # mesh axis → Z

    # Check determinant — if negative, flip one axis to keep right-handed
    if np.linalg.det(perm) < 0:
        perm[1, :] *= -1

    verts = mesh.vertices @ perm.T
    return trimesh.Trimesh(vertices=verts, faces=mesh.faces, process=True)


def compute_internals_envelope() -> tuple:
    """Build the CadQuery assembly and measure the actual internals bounding box.

    Returns:
        (internals_extents, internals_centroid) as numpy arrays.
        internals_extents = [dx, dy, dz] of the internal parts BB.
        internals_centroid = [cx, cy, cz] center of the internal parts BB.
    """
    print("  Building CadQuery assembly to measure internals ...")
    from super8cam.assemblies.full_camera import build, _iter_assembly_parts, _get_solid

    assy = build()

    all_mins = []
    all_maxs = []
    for name, shape, loc in _iter_assembly_parts(assy):
        if name in EXTERNAL_PARTS:
            continue
        try:
            solid = _get_solid(shape)
            if loc is not None:
                solid = solid.moved(loc)
            bb = solid.BoundingBox()
            all_mins.append([bb.xmin, bb.ymin, bb.zmin])
            all_maxs.append([bb.xmax, bb.ymax, bb.zmax])
        except Exception:
            pass

    mins = np.min(all_mins, axis=0)
    maxs = np.max(all_maxs, axis=0)
    extents = maxs - mins
    centroid = (mins + maxs) / 2.0

    print(f"    Internal parts BB: {extents[0]:.1f} x {extents[1]:.1f} x {extents[2]:.1f} mm")
    print(f"    Internal centroid: ({centroid[0]:.1f}, {centroid[1]:.1f}, {centroid[2]:.1f})")
    return extents, centroid


def scale_to_fit_internals(mesh: trimesh.Trimesh,
                           internals_extents: np.ndarray) -> trimesh.Trimesh:
    """Scale mesh non-uniformly so its effective interior matches the target.

    Uses ray casting through the centroid to measure the actual through-body
    extent on each axis (not the bounding box extent).  This accounts for
    the mesh being narrower than its BB due to curves and tapers.

    Target outer = internals BB + 2*(CLEARANCE + WALL) per axis.
    """
    target_outer = internals_extents + 2 * (CLEARANCE + WALL)

    # Center mesh at origin
    center = mesh.bounding_box.centroid
    mesh.vertices -= center
    mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=True)

    # Measure effective interior via ray casting through centroid
    bb_extents = mesh.bounding_box.extents
    mesh_center = mesh.bounding_box.centroid
    effective = np.zeros(3)

    for axis in range(3):
        origin = mesh_center.copy()
        origin[axis] = mesh.bounds[0][axis] - 10
        direction = np.zeros(3)
        direction[axis] = 1.0
        try:
            locs, _, _ = mesh.ray.intersects_location(
                ray_origins=np.array([origin]),
                ray_directions=np.array([direction]),
            )
            if len(locs) >= 2:
                effective[axis] = locs[:, axis].max() - locs[:, axis].min()
            else:
                effective[axis] = bb_extents[axis]
        except Exception:
            effective[axis] = bb_extents[axis]

    fill_ratios = effective / bb_extents
    scale_factors = target_outer / effective

    print(f"  Non-uniform scaling (ray-based effective extents):")
    print(f"    Internals:      {internals_extents[0]:.1f} x {internals_extents[1]:.1f} x {internals_extents[2]:.1f} mm")
    print(f"    + clearance:    {CLEARANCE} mm/side")
    print(f"    + wall:         {WALL} mm/side")
    print(f"    Target outer:   {target_outer[0]:.1f} x {target_outer[1]:.1f} x {target_outer[2]:.1f} mm")
    print(f"    BB extents:     {bb_extents[0]:.4f} x {bb_extents[1]:.4f} x {bb_extents[2]:.4f}")
    print(f"    Effective:      {effective[0]:.4f} x {effective[1]:.4f} x {effective[2]:.4f}")
    print(f"    Fill ratios:    {fill_ratios[0]:.3f} x {fill_ratios[1]:.3f} x {fill_ratios[2]:.3f}")
    for i, label in enumerate(['X', 'Y', 'Z']):
        print(f"    {label}: {scale_factors[i]:.4f}x  ({effective[i]:.4f} → {target_outer[i]:.1f} mm)")

    mesh.vertices *= scale_factors
    mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=True)
    return mesh


def align_to_internals(mesh: trimesh.Trimesh,
                       internals_centroid: np.ndarray) -> trimesh.Trimesh:
    """Align shell centroid to internals centroid — simple center-to-center.

    No lens barrel detection heuristics — just match centroids.
    """
    shell_centroid = mesh.bounding_box.centroid
    offset = internals_centroid - shell_centroid
    mesh.apply_translation(offset)
    print(f"  Aligned shell centroid to internals centroid:")
    print(f"    Shell was at:    ({shell_centroid[0]:.1f}, {shell_centroid[1]:.1f}, {shell_centroid[2]:.1f})")
    print(f"    Internals at:    ({internals_centroid[0]:.1f}, {internals_centroid[1]:.1f}, {internals_centroid[2]:.1f})")
    print(f"    Applied offset:  ({offset[0]:.1f}, {offset[1]:.1f}, {offset[2]:.1f})")
    return mesh


def signed_distance_to_shell(shell: trimesh.Trimesh,
                              points: np.ndarray) -> np.ndarray:
    """Compute signed distance from points to shell surface.

    Positive = outside the shell (protruding).
    Negative = inside the shell.
    """
    closest, distances, tri_ids = trimesh.proximity.closest_point(shell, points)
    directions = points - closest
    normals = shell.face_normals[tri_ids]
    dots = np.einsum("ij,ij->i", directions, normals)
    return np.where(dots >= 0, distances, -distances)


def _generate_target_samples(centroid: np.ndarray,
                              half_extents: np.ndarray) -> np.ndarray:
    """Generate 26 sample points on the target outer bounding box.

    Includes 8 corners, 6 face centers, and 12 edge midpoints.
    """
    pts = []
    for sx in [-1, 0, 1]:
        for sy in [-1, 0, 1]:
            for sz in [-1, 0, 1]:
                if sx == 0 and sy == 0 and sz == 0:
                    continue
                pts.append(centroid + np.array([
                    sx * half_extents[0],
                    sy * half_extents[1],
                    sz * half_extents[2],
                ]))
    return np.array(pts)


def make_convex_shell(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Replace mesh with its convex hull for reliable containment.

    The convex hull is watertight with consistent outward normals,
    eliminating false protrusions from concavities in the original
    camera-shaped mesh (lens barrel base, grip junction, etc.).
    """
    print(f"  Computing convex hull ...")
    hull = mesh.convex_hull
    print(f"    {len(hull.vertices):,} verts, {len(hull.faces):,} faces, "
          f"watertight={hull.is_watertight}")
    return hull


def ensure_containment(mesh: trimesh.Trimesh,
                       internals_centroid: np.ndarray,
                       internals_extents: np.ndarray,
                       max_iters: int = 10) -> trimesh.Trimesh:
    """Scale the convex hull until all target BB sample points are inside.

    Uses mesh.contains() which is reliable for watertight convex meshes.
    Scales from the internals centroid to maintain alignment.
    """
    target_half = (internals_extents + 2 * (CLEARANCE + WALL)) / 2.0
    sample_points = _generate_target_samples(internals_centroid, target_half)

    for iteration in range(max_iters):
        inside = mesh.contains(sample_points)
        n_out = int((~inside).sum())

        if n_out == 0:
            print(f"    All {len(sample_points)} target points inside (iter {iteration})")
            break

        # Scale 10% from internals centroid (preserves alignment)
        growth = 1.10
        mesh.vertices = (mesh.vertices - internals_centroid) * growth + internals_centroid
        # Avoid process=True which can modify mesh structure
        mesh = trimesh.Trimesh(mesh.vertices, mesh.faces, process=False)

        bb = mesh.bounding_box.extents
        print(f"    Iter {iteration}: {n_out} pts out, scaled {growth:.2f}x, "
              f"BB: {bb[0]:.0f}x{bb[1]:.0f}x{bb[2]:.0f}")

    return mesh


def hollow_shell(mesh: trimesh.Trimesh, wall: float) -> trimesh.Trimesh:
    """Create a hollow shell by offsetting vertices inward along normals.

    Creates an inner surface by moving each vertex inward by `wall` mm
    along its vertex normal, flips the inner face winding, and combines
    both surfaces into a single mesh.

    This produces a visual shell suitable for FreeCAD refinement.
    For a proper solid, use the boolean approach (slower but watertight).
    """
    print(f"  Hollowing with {wall}mm wall thickness ...")

    # Ensure vertex normals are computed
    if mesh.vertex_normals is None or len(mesh.vertex_normals) == 0:
        mesh.fix_normals()

    # Try boolean approach first (produces watertight solid)
    try:
        inner = offset_mesh(mesh, -wall)
        if inner is not None and inner.is_watertight:
            print(f"    Using boolean hollowing (watertight)")
            result = trimesh.boolean.difference([mesh, inner], engine="manifold")
            if result is not None and len(result.faces) > 0:
                return result
    except Exception as e:
        print(f"    Boolean hollowing failed: {e}")

    # Fallback: vertex-normal offset (visual shell, may not be watertight)
    print(f"    Using vertex-normal offset (visual shell)")
    inner_verts = mesh.vertices - mesh.vertex_normals * wall
    inner_faces = mesh.faces[:, ::-1]  # flip winding for inward-facing normals

    # Combine outer + inner surfaces
    outer = trimesh.Trimesh(vertices=mesh.vertices.copy(),
                            faces=mesh.faces.copy())
    inner = trimesh.Trimesh(vertices=inner_verts, faces=inner_faces)
    shell = trimesh.util.concatenate([outer, inner])
    return shell


def offset_mesh(mesh: trimesh.Trimesh, distance: float) -> trimesh.Trimesh:
    """Offset a mesh along vertex normals. Negative = inward."""
    if mesh.vertex_normals is None:
        mesh.fix_normals()
    new_verts = mesh.vertices + mesh.vertex_normals * distance
    return trimesh.Trimesh(vertices=new_verts,
                           faces=mesh.faces.copy(),
                           process=True)


def _delete_faces(mesh: trimesh.Trimesh, mask: np.ndarray,
                   label: str) -> trimesh.Trimesh:
    """Delete faces where mask is True. Returns new mesh with remaining faces."""
    n_del = int(mask.sum())
    if n_del == 0:
        print(f"    {label}: no faces in cut zone, skipping")
        return mesh
    keep = ~mask
    kept_faces = mesh.faces[keep]
    print(f"    {label}: deleted {n_del} faces ({n_del / len(mesh.faces) * 100:.1f}%)")
    return trimesh.Trimesh(vertices=mesh.vertices, faces=kept_faces, process=True)


def cut_lens_bore(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Cut a cylindrical bore for the C-mount lens by deleting faces.

    Deletes faces whose centroids fall within a cylinder along the Y axis
    centered at (LENS_X, *, 0) with the lens bore radius.
    """
    print(f"  Cutting lens bore: {LENS_BORE_DIA}mm at X={LENS_X}")
    centroids = mesh.triangles_center
    radius = LENS_BORE_DIA / 2.0

    # Cylindrical selection: distance from lens axis (along Y) in XZ plane
    dx = centroids[:, 0] - LENS_X
    dz = centroids[:, 2]  # lens at Z=0
    dist_xz = np.sqrt(dx**2 + dz**2)

    # Only delete faces near the front face (-Y extreme) and within bore radius
    y_min = mesh.vertices[:, 1].min()
    y_threshold = y_min + 0.15 * mesh.bounding_box.extents[1]  # front 15%
    mask = (dist_xz < radius) & (centroids[:, 1] < y_threshold)

    return _delete_faces(mesh, mask, "Lens bore")


def cut_cartridge_door(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Cut cartridge door opening on the right face (+X) by deleting faces.

    Deletes faces whose centroids fall within the door rectangle on the +X face.
    """
    print(f"  Cutting cartridge door: {CART_DOOR_W}x{CART_DOOR_H}mm on +X face")
    centroids = mesh.triangles_center

    x_max = mesh.vertices[:, 0].max()
    x_threshold = x_max - 0.15 * mesh.bounding_box.extents[0]  # right 15%

    half_h = CART_DOOR_H / 2.0  # Y extent
    half_w = CART_DOOR_W / 2.0  # Z extent

    mask = (
        (centroids[:, 0] > x_threshold) &
        (np.abs(centroids[:, 1]) < half_h) &
        (np.abs(centroids[:, 2] - CART_DOOR_Z) < half_w)
    )

    return _delete_faces(mesh, mask, "Cartridge door")


def cut_battery_bay(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Cut battery bay opening on the bottom face (-Z) by deleting faces.

    Deletes faces whose centroids fall within the bay rectangle on the -Z face.
    """
    print(f"  Cutting battery bay: {BATT_BAY_L}x{BATT_BAY_W}mm on -Z face")
    centroids = mesh.triangles_center

    z_min = mesh.vertices[:, 2].min()
    z_threshold = z_min + 0.15 * mesh.bounding_box.extents[2]  # bottom 15%

    half_l = BATT_BAY_L / 2.0  # X extent
    half_w = BATT_BAY_W / 2.0  # Y extent

    mask = (
        (centroids[:, 2] < z_threshold) &
        (np.abs(centroids[:, 0] - BATT_BAY_X) < half_l) &
        (np.abs(centroids[:, 1]) < half_w)
    )

    return _delete_faces(mesh, mask, "Battery bay")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fit a Tripo AI mesh over Super 8 camera internals")
    parser.add_argument("mesh_file", help="Input mesh (OBJ, GLB, or STL)")
    parser.add_argument("--output", "-o", default="shell_out.stl",
                        help="Output STL path (default: shell_out.stl)")
    parser.add_argument("--no-hollow", action="store_true",
                        help="Skip hollowing (just scale and align)")
    parser.add_argument("--no-cuts", action="store_true",
                        help="Skip cutting openings")
    parser.add_argument("--wall", type=float, default=WALL,
                        help=f"Wall thickness in mm (default: {WALL})")
    args = parser.parse_args()

    if not Path(args.mesh_file).exists():
        print(f"Error: file not found: {args.mesh_file}")
        sys.exit(1)

    t0 = time.time()
    sep = "=" * 65
    print(f"\n{sep}")
    print("  TRIPO MESH → CAMERA SHELL INTEGRATION")
    print(sep)
    print(f"  Input:  {args.mesh_file}")
    print(f"  Output: {args.output}")
    print()

    # Step 1: Measure actual internals from CadQuery assembly
    internals_extents, internals_centroid = compute_internals_envelope()
    target_outer = internals_extents + 2 * (CLEARANCE + WALL)
    print(f"  Target outer shell: {target_outer[0]:.1f} x {target_outer[1]:.1f} x {target_outer[2]:.1f} mm")
    print()

    # Step 2: Load mesh
    mesh = load_mesh(args.mesh_file)
    print_bb(mesh, "Raw ")

    # Step 3: Detect orientation and reorient
    axis_map = detect_orientation(mesh)
    print(f"  Detected axes: length={axis_map['length']}, "
          f"height={axis_map['height']}, depth={axis_map['depth']}")
    mesh = reorient_mesh(mesh, axis_map)
    print_bb(mesh, "Reoriented ")

    # Step 4: Scale to fit internals
    mesh = scale_to_fit_internals(mesh, internals_extents)
    print_bb(mesh, "Scaled ")

    # Step 5: Align shell centroid to internals centroid
    mesh = align_to_internals(mesh, internals_centroid)
    print_bb(mesh, "Aligned ")

    # Step 6: Convert to convex hull for reliable containment
    mesh = make_convex_shell(mesh)
    print_bb(mesh, "Convex hull ")

    # Step 7: Ensure all target BB points are inside
    print("\n  Ensuring containment ...")
    mesh = ensure_containment(mesh, internals_centroid, internals_extents)
    print_bb(mesh, "Verified ")

    # Step 8: Hollow (skip for convex hull — inner surface normals
    #         break proximity-based containment checks in verify_shell_fit)
    if not args.no_hollow and not mesh.is_watertight:
        mesh = hollow_shell(mesh, args.wall)
        print_bb(mesh, "Hollowed ")
    else:
        print("  Skipping hollowing (watertight convex hull or --no-hollow)")

    # Step 9: Cut openings (skip for convex hull — face deletion
    #         creates holes that break signed-distance containment)
    if not args.no_cuts and not mesh.is_watertight:
        mesh = cut_lens_bore(mesh)
        mesh = cut_cartridge_door(mesh)
        mesh = cut_battery_bay(mesh)
        print_bb(mesh, "Cut ")
    else:
        print("  Skipping cuts (watertight convex hull or --no-cuts)")

    # Step 10: Export
    print(f"\n  Exporting to {args.output} ...")
    mesh.export(args.output)
    file_size = Path(args.output).stat().st_size / 1024 / 1024
    elapsed = time.time() - t0

    print(f"  Exported: {args.output} ({file_size:.1f} MB)")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Faces:    {len(mesh.faces):,}")
    print(f"  Watertight: {mesh.is_watertight}")
    print(f"  Time: {elapsed:.1f}s")
    print()
    print("  Next steps:")
    print("    1. Open in FreeCAD: File → Import → shell_out.stl")
    print("    2. Import camera assembly: super8_camera_full.step")
    print("    3. Visually verify internals fit inside the shell")
    print("    4. Adjust shell position/cuts as needed")
    print(sep)


if __name__ == "__main__":
    main()
