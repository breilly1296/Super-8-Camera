"""integrate_shell.py — Fit a Tripo AI mesh over validated camera internals.

Loads an external mesh (OBJ/GLB/STL), scales each axis independently to
match the target outer envelope, centers and aligns the lens barrel to the
optical axis, hollows to 2.5mm wall thickness, and cuts openings (lens bore,
cartridge door, battery bay) by deleting faces whose centroids fall within
the cut zone — no boolean operations required (works on non-watertight meshes).

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
# Camera internals geometry (from master_specs + full_camera datums)
# ---------------------------------------------------------------------------

# Current body envelope (what the internals were designed for)
BODY_L = 135.0   # mm (X)
BODY_H = 80.0    # mm (Z)
BODY_D = 48.0    # mm (Y)
WALL   = 2.5     # mm wall thickness

# Minimum interior cavity to fit all internals + 2mm clearance per side
# These are the dimensions the hollowed mesh interior must exceed.
MIN_INTERIOR = np.array([
    BODY_L + 2 * (WALL + 2),   # 152mm X  (internals + wall + clearance)
    BODY_D + 2 * (WALL + 2),   # 57mm  Y
    BODY_H + 2 * (WALL + 2),   # 92mm  Z
])

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


def scale_to_interior(mesh: trimesh.Trimesh,
                      min_interior: np.ndarray) -> trimesh.Trimesh:
    """Scale mesh non-uniformly (per-axis) to match target outer dimensions.

    The outer shell must be at least min_interior + 2*WALL in each dimension
    so that after hollowing with WALL thickness, the cavity >= min_interior.

    Each axis is scaled independently so the bounding box matches the target
    exactly, stretching/compressing the mesh as needed.
    """
    target_outer = min_interior + 2 * WALL  # outer envelope needed
    extents = mesh.bounding_box.extents

    # Per-axis scale factors
    scale_factors = target_outer / extents

    print(f"  Non-uniform scaling:")
    print(f"    X: {scale_factors[0]:.4f}x  ({extents[0]:.1f} → {target_outer[0]:.1f} mm)")
    print(f"    Y: {scale_factors[1]:.4f}x  ({extents[1]:.1f} → {target_outer[1]:.1f} mm)")
    print(f"    Z: {scale_factors[2]:.4f}x  ({extents[2]:.1f} → {target_outer[2]:.1f} mm)")

    # Center at origin, scale per-axis, then re-center
    center = mesh.bounding_box.centroid
    mesh.vertices -= center
    mesh.vertices *= scale_factors
    mesh.vertices += center * scale_factors  # keep centroid consistent

    # Recompute internals after direct vertex modification
    mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=True)

    return mesh


def center_and_align(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Center mesh at origin, then shift so lens barrel aligns with optical axis.

    Convention: the lens is on the front-left of the camera body.
    - Camera center at origin
    - Lens axis at X = LENS_X (-18mm), Y = -body_depth/2 (front face)

    For the Tripo mesh, we assume the lens barrel is the cylindrical
    protrusion on the front-left quadrant. We center the mesh and let
    the user fine-tune in FreeCAD.
    """
    # Center at geometric center of bounding box
    center = mesh.bounding_box.centroid
    mesh.apply_translation(-center)
    print(f"  Centered mesh at origin")

    # The lens is typically at -X, -Y (front-left when viewed from front).
    # We shift the mesh so the approximate lens position aligns with LENS_X.
    # Heuristic: scan the front face (-Y extreme) for the densest cluster
    # of vertices in a cylindrical region, which is likely the lens barrel.
    extents = mesh.bounding_box.extents
    verts = mesh.vertices

    # Front 10% of mesh in Y
    y_min = verts[:, 1].min()
    y_threshold = y_min + 0.1 * extents[1]
    front_verts = verts[verts[:, 1] < y_threshold]

    if len(front_verts) > 10:
        # Find the X centroid of the front vertices — this approximates
        # the lens barrel center X position
        front_cx = np.median(front_verts[:, 0])

        # The lens barrel is often the most protruding part.
        # Find the cluster of front vertices that protrude most in -Y
        y_10pct = np.percentile(front_verts[:, 1], 10)
        protruding = front_verts[front_verts[:, 1] < y_10pct]
        if len(protruding) > 5:
            lens_cx = np.median(protruding[:, 0])
            lens_cz = np.median(protruding[:, 2])

            # Shift mesh so detected lens position maps to LENS_X, Z=0
            dx = LENS_X - lens_cx
            dz = -lens_cz  # lens should be at Z ≈ 0 (optical axis)
            mesh.apply_translation([dx, 0, dz])
            print(f"  Shifted mesh: dX={dx:.1f}, dZ={dz:.1f} "
                  f"(lens barrel → X={LENS_X})")
        else:
            print(f"  Could not isolate lens barrel, using geometric center")
    else:
        print(f"  Few front vertices, using geometric center alignment")

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
    print(f"  Target interior: {MIN_INTERIOR[0]:.0f} x "
          f"{MIN_INTERIOR[2]:.0f} x {MIN_INTERIOR[1]:.0f} mm (X x Z x Y)")
    print()

    # Step 1: Load
    mesh = load_mesh(args.mesh_file)
    print_bb(mesh, "Raw ")

    # Step 2: Detect orientation and reorient
    axis_map = detect_orientation(mesh)
    print(f"  Detected axes: length={axis_map['length']}, "
          f"height={axis_map['height']}, depth={axis_map['depth']}")
    mesh = reorient_mesh(mesh, axis_map)
    print_bb(mesh, "Reoriented ")

    # Step 3: Scale to fit internals
    mesh = scale_to_interior(mesh, MIN_INTERIOR)
    print_bb(mesh, "Scaled ")

    # Step 4: Center and align lens
    mesh = center_and_align(mesh)
    print_bb(mesh, "Aligned ")

    # Step 5: Hollow
    if not args.no_hollow:
        mesh = hollow_shell(mesh, args.wall)
        print_bb(mesh, "Hollowed ")
    else:
        print("  Skipping hollowing (--no-hollow)")

    # Step 6: Cut openings
    if not args.no_cuts:
        mesh = cut_lens_bore(mesh)
        mesh = cut_cartridge_door(mesh)
        mesh = cut_battery_bay(mesh)
        print_bb(mesh, "Cut ")
    else:
        print("  Skipping cuts (--no-cuts)")

    # Step 7: Export
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
