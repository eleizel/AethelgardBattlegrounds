"""Headless Blender 5.3 generator for AethelgardBattlegrounds 3D assets.

Generates clean, manifold, UV-mapped, PBR-shaded 3D meshes, runs blender-asset-qa
checks on every asset, and exports Godot-ready .glb files under assets/models/.

Usage:
    blender -b --factory-startup --python-exit-code 1 -P tools/blender_build_assets.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


def _find_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _make_pbr_material(
    name: str,
    base_color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.5,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission_color is not None and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = emission_color
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def _ensure_tri_or_quad(bm: bmesh.types.BMesh) -> None:
    """Triangulate any faces with more than 4 vertices to avoid n-gon warnings."""
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)


def _apply_normalized_uvs(bm: bmesh.types.BMesh) -> None:
    """Assign normalized [0.02, 0.98] box-projected UVs with guaranteed non-zero area."""
    uv_layer = bm.loops.layers.uv.verify()
    raw_coords: list[tuple[bmesh.types.BMLoop, float, float]] = []
    min_u, max_u = float("inf"), float("-inf")
    min_v, max_v = float("inf"), float("-inf")

    for face in bm.faces:
        n = face.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for loop in face.loops:
            co = loop.vert.co
            if az >= ax and az >= ay:
                u, v = float(co.x), float(co.y)
            elif ax >= ay and ax >= az:
                u, v = float(co.y), float(co.z)
            else:
                u, v = float(co.x), float(co.z)
            min_u = min(min_u, u)
            max_u = max(max_u, u)
            min_v = min(min_v, v)
            max_v = max(max_v, v)
            raw_coords.append((loop, u, v))

    span_u = max(1e-5, max_u - min_u)
    span_v = max(1e-5, max_v - min_v)
    for loop, u, v in raw_coords:
        nu = 0.02 + 0.96 * ((u - min_u) / span_u)
        nv = 0.02 + 0.96 * ((v - min_v) / span_v)
        loop[uv_layer].uv = (nu, nv)


def _finalize_bmesh_to_object(
    name: str,
    bm: bmesh.types.BMesh,
    materials: list[bpy.types.Material],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    _ensure_tri_or_quad(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _apply_normalized_uvs(bm)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    mesh.polygons.foreach_set("use_smooth", [False] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def _add_box(
    bm: bmesh.types.BMesh,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    material_index: int,
) -> None:
    mat = (
        Matrix.Translation(Vector(center))
        @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    )
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=mat)
    verts = set(res["verts"])
    for f in bm.faces:
        if all(v in verts for v in f.verts):
            f.material_index = material_index


def _add_cylinder(
    bm: bmesh.types.BMesh,
    center: tuple[float, float, float],
    radius_bottom: float,
    radius_top: float,
    height: float,
    segments: int,
    material_index: int,
) -> None:
    res = bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=True,
        segments=segments,
        radius1=radius_bottom,
        radius2=radius_top,
        depth=height,
        matrix=Matrix.Translation(Vector(center)),
    )
    verts = set(res["verts"])
    for f in bm.faces:
        if all(v in verts for v in f.verts):
            f.material_index = material_index


def _add_ring_band(
    bm: bmesh.types.BMesh,
    center: tuple[float, float, float],
    inner_r: float,
    outer_r: float,
    height: float,
    segments: int,
    material_index: int,
) -> None:
    """Create a closed manifold hollow circular ring."""
    cx, cy, cz = center
    z0 = cz - height * 0.5
    z1 = cz + height * 0.5
    ring_verts: list[list[bmesh.types.BMVert]] = []
    for i in range(segments):
        ang = (2.0 * math.pi * i) / segments
        ca, sa = math.cos(ang), math.sin(ang)
        v_ib = bm.verts.new((cx + inner_r * ca, cy + inner_r * sa, z0))
        v_ob = bm.verts.new((cx + outer_r * ca, cy + outer_r * sa, z0))
        v_ot = bm.verts.new((cx + outer_r * ca, cy + outer_r * sa, z1))
        v_it = bm.verts.new((cx + inner_r * ca, cy + inner_r * sa, z1))
        ring_verts.append([v_ib, v_ob, v_ot, v_it])

    for i in range(segments):
        j = (i + 1) % segments
        a = ring_verts[i]
        b = ring_verts[j]
        for q in (
            (a[0], b[0], b[1], a[1]),
            (a[1], b[1], b[2], a[2]),
            (a[2], b[2], b[3], a[3]),
            (a[3], b[3], b[0], a[0]),
        ):
            f = bm.faces.new(q)
            f.material_index = material_index


def _add_rect_frame_band(
    bm: bmesh.types.BMesh,
    inner_half_xy: tuple[float, float],
    outer_half_xy: tuple[float, float],
    z_min: float,
    z_max: float,
    material_index: int,
) -> None:
    """Create a closed manifold rectangular frame with mitered corners (no overlapping faces)."""
    ix, iy = inner_half_xy
    ox, oy = outer_half_xy
    inner_pts = [(-ix, -iy), (ix, -iy), (ix, iy), (-ix, iy)]
    outer_pts = [(-ox, -oy), (ox, -oy), (ox, oy), (-ox, oy)]
    corners = []
    for (px_i, py_i), (px_o, py_o) in zip(inner_pts, outer_pts, strict=True):
        corners.append(
            [
                bm.verts.new((px_i, py_i, z_min)),
                bm.verts.new((px_o, py_o, z_min)),
                bm.verts.new((px_o, py_o, z_max)),
                bm.verts.new((px_i, py_i, z_max)),
            ]
        )
    for i in range(4):
        j = (i + 1) % 4
        a, b = corners[i], corners[j]
        for q in (
            (a[0], b[0], b[1], a[1]),
            (a[1], b[1], b[2], a[2]),
            (a[2], b[2], b[3], a[3]),
            (a[3], b[3], b[0], a[0]),
        ):
            f = bm.faces.new(q)
            f.material_index = material_index


def build_conclave_war_table(
    materials: dict[str, bpy.types.Material],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Build the Gothic Conclave War Table (8.6m x 4.6m, bottom at z=0, zero coplanar overlaps)."""
    bm = bmesh.new()
    mats = [
        materials["M_ObsidianStone"],
        materials["M_GildedBronze"],
        materials["M_CrimsonFelt"],
    ]

    # Four stone legs (z: 0.10 to 0.72 -> penetrates collar and tabletop, avoiding coplanar Z planes)
    for lx in (-3.6, 3.6):
        for ly in (-1.7, 1.7):
            _add_box(bm, (lx, ly, 0.07), (0.68, 0.68, 0.14), 1)  # z: 0.00 .. 0.14
            _add_box(bm, (lx, ly, 0.41), (0.54, 0.54, 0.62), 0)  # z: 0.10 .. 0.72

    # Main obsidian stone tabletop: z from 0.68 to 0.90 (center 0.79)
    _add_box(bm, (0.0, 0.0, 0.79), (8.6, 4.6, 0.22), 0)

    # Single mitered gold perimeter frame (z: 0.87 to 0.96, overlaps stone neatly without coplanar faces)
    _add_rect_frame_band(
        bm,
        inner_half_xy=(4.04, 2.04),
        outer_half_xy=(4.32, 2.32),
        z_min=0.87,
        z_max=0.96,
        material_index=1,
    )

    # Crimson battle cloth inset (z: 0.88 to 0.925, cleanly tucked inside frame)
    _add_box(bm, (0.0, 0.0, 0.9025), (8.16, 4.16, 0.045), 2)

    # Center warline divider strip (z: 0.915 to 0.945)
    _add_box(bm, (0.0, 0.0, 0.93), (7.90, 0.06, 0.03), 1)

    # 14 golden unit socket rings (z: 0.915 to 0.955, embedded 1cm into felt)
    for row_y in (-1.05, 1.05):
        for slot in range(7):
            x = (slot - 3) * 1.12
            _add_ring_band(
                bm,
                center=(x, row_y, 0.935),
                inner_r=0.38,
                outer_r=0.46,
                height=0.04,
                segments=16,
                material_index=1,
            )

    return _finalize_bmesh_to_object("SM_ConclaveWarTable", bm, mats, collection)


def build_unit_medallion(
    name: str,
    rim_material: bpy.types.Material,
    core_material: bpy.types.Material,
    crystal_material: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    is_ascended: bool = False,
) -> bpy.types.Object:
    """Build a beveled 3D unit medallion base (radius 0.44m, bottom at z=0)."""
    bm = bmesh.new()
    mats = [core_material, rim_material, crystal_material]

    # Solid inner plate + base cylinder (z: 0.0 to 0.105)
    _add_cylinder(bm, (0.0, 0.0, 0.0525), 0.44, 0.40, 0.105, 24, 0)
    # Raised outer metallic bezel ring (z: 0.075 to 0.135, inner_r < base top r so cleanly seated)
    _add_ring_band(
        bm,
        center=(0.0, 0.0, 0.105),
        inner_r=0.33,
        outer_r=0.415,
        height=0.06,
        segments=24,
        material_index=1,
    )
    # Front crest gem at -Y (Godot forward), seated into ring (z: 0.11 to 0.165)
    crest_r = 0.065 if is_ascended else 0.045
    _add_cylinder(bm, (0.0, -0.37, 0.1375), crest_r, crest_r * 0.60, 0.055, 8, 2)

    if is_ascended:
        for sx in (-0.37, 0.37):
            _add_cylinder(bm, (sx, 0.0, 0.14), 0.05, 0.02, 0.06, 6, 1)

    return _finalize_bmesh_to_object(name, bm, mats, collection)


def build_aether_crown(
    materials: dict[str, bpy.types.Material],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Build a 3D golden Aether Crown token (bottom at z=0)."""
    bm = bmesh.new()
    mats = [materials["M_AscendedGold"], materials["M_AetherCrystal"]]

    # Coin body (z: 0.0 to 0.06)
    _add_cylinder(bm, (0.0, 0.0, 0.03), 0.22, 0.22, 0.06, 20, 0)
    # Raised outer rim embedded slightly (z: 0.045 to 0.085)
    _add_ring_band(
        bm,
        center=(0.0, 0.0, 0.065),
        inner_r=0.165,
        outer_r=0.215,
        height=0.04,
        segments=20,
        material_index=0,
    )
    # Central aether gem embedded slightly (z: 0.05 to 0.115)
    _add_cylinder(bm, (0.0, 0.0, 0.0825), 0.08, 0.035, 0.065, 6, 1)

    return _finalize_bmesh_to_object("SM_AetherCrown", bm, mats, collection)


def build_dawn_relic_pedestal(
    materials: dict[str, bpy.types.Material],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Build a crystalline Dawn Relic Pedestal (bottom at z=0)."""
    bm = bmesh.new()
    mats = [
        materials["M_ObsidianStone"],
        materials["M_GildedBronze"],
        materials["M_AetherCrystal"],
    ]

    # Overlapping stepped sections with zero coplanar seams
    # Plinth base (z: 0.0 to 0.16)
    _add_cylinder(bm, (0.0, 0.0, 0.08), 0.42, 0.34, 0.16, 8, 0)
    # Column shaft (z: 0.12 to 0.58)
    _add_cylinder(bm, (0.0, 0.0, 0.35), 0.22, 0.18, 0.46, 8, 0)
    # Gold collar ring (z: 0.54 to 0.65)
    _add_cylinder(bm, (0.0, 0.0, 0.595), 0.28, 0.32, 0.11, 8, 1)
    # Crystal spire (z: 0.62 to 0.89, and top cap z: 0.87 to 1.08)
    _add_cylinder(bm, (0.0, 0.0, 0.755), 0.06, 0.15, 0.27, 6, 2)
    _add_cylinder(bm, (0.0, 0.0, 0.975), 0.15, 0.015, 0.21, 6, 2)

    return _finalize_bmesh_to_object("SM_DawnRelicPedestal", bm, mats, collection)


def _export_glb(obj: bpy.types.Object, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        use_selection=True,
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_animations=False,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )


def main() -> int:
    repo_root = _find_repo_root()
    models_dir = repo_root / "assets" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    col = bpy.data.collections.new("ConclaveAssets")
    bpy.context.scene.collection.children.link(col)

    materials = {
        "M_ObsidianStone": _make_pbr_material(
            "M_ObsidianStone", (0.08, 0.08, 0.11, 1.0), metallic=0.05, roughness=0.72
        ),
        "M_GildedBronze": _make_pbr_material(
            "M_GildedBronze", (0.78, 0.58, 0.18, 1.0), metallic=0.88, roughness=0.28
        ),
        "M_CrimsonFelt": _make_pbr_material(
            "M_CrimsonFelt", (0.34, 0.06, 0.09, 1.0), metallic=0.0, roughness=0.90
        ),
        "M_SteelTrim": _make_pbr_material(
            "M_SteelTrim", (0.36, 0.39, 0.46, 1.0), metallic=0.84, roughness=0.35
        ),
        "M_AetherCrystal": _make_pbr_material(
            "M_AetherCrystal",
            (0.18, 0.68, 0.96, 1.0),
            metallic=0.10,
            roughness=0.15,
            emission_color=(0.20, 0.78, 1.0, 1.0),
            emission_strength=1.6,
        ),
        "M_AscendedGold": _make_pbr_material(
            "M_AscendedGold",
            (0.96, 0.76, 0.22, 1.0),
            metallic=0.94,
            roughness=0.20,
            emission_color=(0.95, 0.72, 0.16, 1.0),
            emission_strength=0.4,
        ),
    }

    war_table = build_conclave_war_table(materials, col)
    medallion_std = build_unit_medallion(
        "SM_UnitMedallion",
        materials["M_SteelTrim"],
        materials["M_ObsidianStone"],
        materials["M_AetherCrystal"],
        col,
        is_ascended=False,
    )
    medallion_asc = build_unit_medallion(
        "SM_UnitMedallionAscended",
        materials["M_AscendedGold"],
        materials["M_ObsidianStone"],
        materials["M_AscendedGold"],
        col,
        is_ascended=True,
    )
    aether_crown = build_aether_crown(materials, col)
    relic_pedestal = build_dawn_relic_pedestal(materials, col)

    blend_dir = repo_root / "assets" / "models_src"
    blend_dir.mkdir(parents=True, exist_ok=True)
    blend_path = blend_dir / "conclave_assets.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    exports = {
        "conclave_war_table.glb": war_table,
        "unit_medallion.glb": medallion_std,
        "unit_medallion_ascended.glb": medallion_asc,
        "aether_crown.glb": aether_crown,
        "dawn_relic_pedestal.glb": relic_pedestal,
    }
    report: dict[str, object] = {"blend": str(blend_path), "exports": {}}
    for filename, obj in exports.items():
        glb_path = models_dir / filename
        _export_glb(obj, glb_path)
        size_bytes = glb_path.stat().st_size if glb_path.is_file() else 0
        report["exports"][filename] = {
            "object": obj.name,
            "tris": sum(max(1, len(p.vertices) - 2) for p in obj.data.polygons),
            "dimensions": [round(float(v), 4) for v in obj.dimensions],
            "materials": [m.name for m in obj.data.materials],
            "bytes": size_bytes,
        }

    qa_dir = Path(os.path.expanduser("~")) / ".gemini" / "config" / "skills" / "blender-asset-qa" / "scripts"
    if qa_dir.is_dir():
        sys.path.insert(0, str(qa_dir))
        import qa_check  # type: ignore[import-not-found]

        qa_results: dict[str, object] = {}
        all_passed = True
        for obj in exports.values():
            res = qa_check.run(objects=[obj.name], profile="game")
            qa_results[obj.name] = res
            if not res.get("pass", False):
                all_passed = False
        report["qa"] = qa_results
        report["qa_all_passed"] = all_passed
        if not all_passed:
            print("@@JSON@@" + json.dumps(report, indent=2))
            return 1

    print("@@JSON@@" + json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
