"""Blender/BMesh-Builder für Ringe und Wälzkörper.

Alle Funktionen liefern manifold, geschlossene Meshes als eigene Objekte
zurück und arbeiten in Millimetern im lokalen Koordinatensystem.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import bmesh
import bpy
from mathutils import Matrix, Vector

# Mindestauflösungen zur Absicherung gegen zu geringe User-Eingaben.
MIN_RING_SEGMENTS = 8
MIN_SPHERE_U_SEGMENTS = 8
MIN_SPHERE_V_SEGMENTS = 6
MIN_ROLLER_SEGMENTS = 12
# Anzahl Profilpunkte entlang der Tonnenrollen-Längsachse (inkl. beider Enden).
BARREL_PROFILE_RINGS = 9


def _new_mesh_object(name: str, collection) -> Tuple[bpy.types.Object, bpy.types.Mesh]:
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    if collection is None:
        collection = bpy.context.collection
    collection.objects.link(obj)
    return obj, mesh


def _finish_bmesh(name: str, bm: bmesh.types.BMesh, collection) -> bpy.types.Object:
    obj, mesh = _new_mesh_object(name, collection)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.validate(verbose=False)
    return obj


def _quad_safe(bm: bmesh.types.BMesh, verts: Iterable) -> None:
    """Legt ein Face an und ignoriert Duplikate (die BMesh als ValueError meldet)."""
    try:
        bm.faces.new(tuple(verts))
    except ValueError:
        pass


def make_hollow_ring(
    name: str,
    inner_d: float,
    outer_d: float,
    width: float,
    segments: int,
    collection,
) -> bpy.types.Object:
    """Geschlossener, manifold Ring (Zylinderschale mit Innen-/Außen-/Deckflächen)."""
    seg = max(MIN_RING_SEGMENTS, segments)
    inner_r = inner_d * 0.5
    outer_r = outer_d * 0.5
    z0 = -width * 0.5
    z1 = width * 0.5

    bm = bmesh.new()
    # Loops in Reihenfolge außen-unten, außen-oben, innen-oben, innen-unten –
    # beim Überbrücken entstehen Außenmantel, Deckel, Innenmantel, Boden.
    loops = []
    for radius, z in ((outer_r, z0), (outer_r, z1), (inner_r, z1), (inner_r, z0)):
        ring = [
            bm.verts.new(
                (radius * math.cos(2.0 * math.pi * i / seg),
                 radius * math.sin(2.0 * math.pi * i / seg),
                 z)
            )
            for i in range(seg)
        ]
        loops.append(ring)

    for li in range(4):
        nxt = (li + 1) % 4
        for i in range(seg):
            j = (i + 1) % seg
            _quad_safe(bm, (loops[li][i], loops[li][j], loops[nxt][j], loops[nxt][i]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish_bmesh(name, bm, collection)


def make_revolved_ring(
    name: str,
    profile: Sequence[Tuple[float, float]],
    segments: int,
    collection,
) -> bpy.types.Object:
    """Revolviert ein geschlossenes ``(r, z)``-Profil um die Z-Achse.

    Das Profil ist eine Folge von Punkten in der ``r-z``-Ebene; die letzte
    Kante schließt automatisch zum ersten Punkt. Jeder Profilpunkt ergibt eine
    Kreislinie aus ``segments`` Vertices, jede Profilkante ergibt einen
    Quad-Ring – das Ergebnis ist ein manifold geschlossener Volumenkörper,
    sofern kein Profilpunkt auf der Drehachse liegt (``r > 0`` für alle
    Punkte).
    """
    seg = max(MIN_RING_SEGMENTS, segments)
    if len(profile) < 3:
        raise ValueError("Profil benötigt mindestens 3 Punkte.")

    bm = bmesh.new()
    rings: List[List[bmesh.types.BMVert]] = []
    for r, z in profile:
        ring: List[bmesh.types.BMVert] = []
        for i in range(seg):
            angle = 2.0 * math.pi * i / seg
            ring.append(bm.verts.new((r * math.cos(angle), r * math.sin(angle), z)))
        rings.append(ring)

    K = len(rings)
    for k in range(K):
        nk = (k + 1) % K
        for i in range(seg):
            ni = (i + 1) % seg
            _quad_safe(bm, (rings[k][i], rings[k][ni], rings[nk][ni], rings[nk][i]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish_bmesh(name, bm, collection)


def add_uv_sphere(
    name: str,
    radius: float,
    location,
    u_segments: int,
    v_segments: int,
    collection,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=max(MIN_SPHERE_U_SEGMENTS, u_segments),
        v_segments=max(MIN_SPHERE_V_SEGMENTS, v_segments),
        radius=radius,
    )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    return _finish_bmesh(name, bm, collection)


def add_cylinder(
    name: str,
    radius: float,
    depth: float,
    location,
    segments: int,
    collection,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=max(MIN_ROLLER_SEGMENTS, segments),
        radius1=radius,
        radius2=radius,
        depth=depth,
    )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    return _finish_bmesh(name, bm, collection)


def add_tapered_roller(
    name: str,
    radius_small: float,
    radius_large: float,
    depth: float,
    location,
    segments: int,
    collection,
    tilt: float = 0.0,
) -> bpy.types.Object:
    """Kegelrolle, optional um die lokale Y-Achse gekippt (Kontaktwinkel).

    Die Kippung wird im Mesh-Frame angewendet, *bevor* nach ``location``
    verschoben wird. Anschließend kann das Objekt über ``rotation_euler[2]``
    um die Lagerachse rotiert werden, ohne den Kontaktwinkel zu verfälschen.
    """
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=max(MIN_ROLLER_SEGMENTS, segments),
        radius1=radius_small,
        radius2=radius_large,
        depth=depth,
    )
    if tilt:
        bmesh.ops.rotate(
            bm,
            cent=Vector((0.0, 0.0, 0.0)),
            matrix=Matrix.Rotation(tilt, 4, "Y"),
            verts=bm.verts,
        )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish_bmesh(name, bm, collection)


def add_barrel_roller(
    name: str,
    radius_mid: float,
    radius_end: float,
    length: float,
    location,
    segments: int,
    collection,
    profile_rings: int = BARREL_PROFILE_RINGS,
) -> bpy.types.Object:
    """Tonnenrolle als Rotationskörper – ein einziges manifold Mesh.

    Die Vorgänger-Variante stapelte zwei gekappte Kegel und erzeugte dadurch
    doppelte Flächen in der Mitte. Hier wird entlang ``profile_rings``
    Zwischenringen ein glattes Profil (cos²-Interpolation zwischen End- und
    Mittenradius) revolviert.
    """
    seg = max(MIN_ROLLER_SEGMENTS, segments)
    rings_n = max(3, profile_rings)

    bm = bmesh.new()
    rings = []
    for i in range(rings_n):
        t = i / (rings_n - 1)          # 0..1 entlang der Längsachse
        u = 2.0 * t - 1.0              # -1..1
        z = -length * 0.5 + t * length
        r = radius_end + (radius_mid - radius_end) * math.cos(0.5 * math.pi * u) ** 2
        ring = [
            bm.verts.new(
                (r * math.cos(2.0 * math.pi * s / seg),
                 r * math.sin(2.0 * math.pi * s / seg),
                 z)
            )
            for s in range(seg)
        ]
        rings.append(ring)

    for i in range(rings_n - 1):
        for s in range(seg):
            ns = (s + 1) % seg
            _quad_safe(bm, (rings[i][s], rings[i][ns], rings[i + 1][ns], rings[i + 1][s]))

    # Deckel als Triangle-Fan um die Mittelpunkte.
    bottom_center = bm.verts.new((0.0, 0.0, -length * 0.5))
    top_center = bm.verts.new((0.0, 0.0, length * 0.5))
    for s in range(seg):
        ns = (s + 1) % seg
        _quad_safe(bm, (bottom_center, rings[0][ns], rings[0][s]))
        _quad_safe(bm, (top_center, rings[-1][s], rings[-1][ns]))

    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish_bmesh(name, bm, collection)


def add_box(
    name: str,
    size: Tuple[float, float, float],
    location: Tuple[float, float, float],
    rotation_z: float,
    collection,
) -> bpy.types.Object:
    """Achsenausgerichteter Quader, optional um Z gedreht. Manifold."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    if rotation_z:
        bmesh.ops.rotate(
            bm,
            cent=Vector((0.0, 0.0, 0.0)),
            matrix=Matrix.Rotation(rotation_z, 4, "Z"),
            verts=bm.verts,
        )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    return _finish_bmesh(name, bm, collection)


def count_non_manifold_edges(mesh: bpy.types.Mesh) -> int:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return non_manifold


def apply_boolean_difference(
    target: bpy.types.Object,
    cutters: Sequence[bpy.types.Object],
    *,
    solver: str = "EXACT",
) -> int:
    """Subtrahiert ``cutters`` von ``target`` per Boolean-Modifier (DIFFERENCE).

    Wendet pro Cutter einen eigenen Modifier an, sodass ein einzelner
    fehlschlagender Boolean die übrigen nicht blockiert. Cutter-Objekte werden
    nach erfolgreicher (oder fehlgeschlagener) Subtraktion aus der Szene
    entfernt. Liefert die Anzahl erfolgreich angewendeter Booleans.
    """
    if not cutters:
        return 0

    view_layer = bpy.context.view_layer
    prev_active = view_layer.objects.active
    prev_selected = list(bpy.context.selected_objects)

    succeeded = 0
    try:
        # modifier_apply benötigt Aktivobjekt + selektion.
        bpy.ops.object.select_all(action="DESELECT")
        view_layer.objects.active = target
        target.select_set(True)
        for cutter in cutters:
            mod = target.modifiers.new(name="UNI_Pocket", type="BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.object = cutter
            try:
                mod.solver = solver
            except (AttributeError, TypeError):  # pragma: no cover – ältere Blender
                pass
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
                succeeded += 1
            except RuntimeError:
                # Boolean fehlgeschlagen (z. B. nicht-manifolder Cutter) –
                # Modifier entfernen und weiter.
                if mod.name in target.modifiers:
                    target.modifiers.remove(mod)
    finally:
        for cutter in cutters:
            if cutter.name in bpy.data.objects:
                bpy.data.objects.remove(cutter, do_unlink=True)
        # Vorigen Selektionszustand best möglich wiederherstellen.
        bpy.ops.object.select_all(action="DESELECT")
        for obj in prev_selected:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if prev_active is not None and prev_active.name in bpy.data.objects:
            view_layer.objects.active = prev_active
    return succeeded


def get_or_create_collection(name: str) -> bpy.types.Collection:
    """Hole Collection mit passendem Namen oder lege eine neue unter der Szene an."""
    scene = bpy.context.scene
    existing = bpy.data.collections.get(name)
    if existing is not None and existing.name in scene.collection.children:
        return existing
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll


__all__ = [
    "add_barrel_roller",
    "add_box",
    "add_cylinder",
    "add_tapered_roller",
    "add_uv_sphere",
    "apply_boolean_difference",
    "count_non_manifold_edges",
    "get_or_create_collection",
    "make_hollow_ring",
    "make_revolved_ring",
]
