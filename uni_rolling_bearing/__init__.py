bl_info = {
    "name": "UNI Rolling Bearing Generator",
    "author": "Codex",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > UNI Bearings",
    "description": "Erstellt parametrische, funktionsfähige Wälzlager mit Norm-Presets",
    "category": "Add Mesh",
}

import math
import bpy
import bmesh
from mathutils import Matrix, Vector
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)


BEARING_TYPES = [
    ("BALL", "Kugellager", "Rillenkugellager nach DIN 625 / ISO 15"),
    ("CYLINDRICAL", "Zylinderrollenlager", "Zylinderrollenlager nach DIN 5412 / ISO 15 Maßreihen"),
    ("NEEDLE", "Nadellager", "Nadellager nach DIN 617 / ISO 15 Maßreihen"),
    ("TAPERED", "Kegelrollenlager", "Kegelrollenlager nach DIN 720 / ISO 355"),
    ("SPHERICAL", "Tonnenlager", "Pendelrollenlager (Tonnenlager) nach DIN 635 / ISO 15"),
]

PRECISION_CLASSES = [
    ("NORMAL", "Normal", "ISO 492 Normal"),
    ("P6", "P6", "ISO 492 Klasse P6"),
    ("P5", "P5", "ISO 492 Klasse P5"),
    ("P4", "P4", "ISO 492 Klasse P4"),
]

SERIES_PRESETS = {
    "BALL": {
        "6000": (10.0, 26.0, 8.0),
        "6204": (20.0, 47.0, 14.0),
        "6306": (30.0, 72.0, 19.0),
    },
    "CYLINDRICAL": {
        "NU204": (20.0, 47.0, 14.0),
        "NU306": (30.0, 72.0, 19.0),
    },
    "NEEDLE": {
        "HK1010": (10.0, 14.0, 10.0),
        "HK2020": (20.0, 26.0, 20.0),
    },
    "TAPERED": {
        "30204": (20.0, 47.0, 15.25),
        "30206": (30.0, 62.0, 17.25),
    },
    "SPHERICAL": {
        "22206": (30.0, 62.0, 20.0),
        "22210": (50.0, 90.0, 23.0),
    },
}


def _new_mesh_object(name: str, collection=None):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    if collection is None:
        collection = bpy.context.collection
    collection.objects.link(obj)
    return obj, mesh


def _finish_bmesh(name: str, bm: bmesh.types.BMesh, collection=None):
    obj, mesh = _new_mesh_object(name, collection=collection)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.validate(verbose=False)
    return obj


def _make_hollow_ring(name: str, inner_d: float, outer_d: float, width: float, segments: int, collection=None):
    """Erstellt einen geschlossenen, manifold Ring als BMesh (kein Boolean nötig)."""
    inner_r = inner_d * 0.5
    outer_r = outer_d * 0.5
    z0 = -width * 0.5
    z1 = width * 0.5

    bm = bmesh.new()
    loops = []
    for radius, z in ((outer_r, z0), (outer_r, z1), (inner_r, z1), (inner_r, z0)):
        ring = []
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            ring.append(bm.verts.new((radius * math.cos(a), radius * math.sin(a), z)))
        loops.append(ring)

    for li in range(4):
        nxt = (li + 1) % 4
        for i in range(segments):
            j = (i + 1) % segments
            v1 = loops[li][i]
            v2 = loops[li][j]
            v3 = loops[nxt][j]
            v4 = loops[nxt][i]
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                pass

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish_bmesh(name, bm, collection=collection)


def _add_uv_sphere(name: str, radius: float, location, segments: int, rings: int, collection=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=max(8, segments),
        v_segments=max(6, rings),
        radius=radius,
    )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    return _finish_bmesh(name, bm, collection=collection)


def _add_cylinder(name: str, radius: float, depth: float, location, segments: int, collection=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=max(8, segments),
        radius1=radius,
        radius2=radius,
        depth=depth,
    )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    return _finish_bmesh(name, bm, collection=collection)


def _count_non_manifold_edges(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return non_manifold


def _create_collection(name):
    root = bpy.context.scene.collection
    coll = bpy.data.collections.new(name)
    root.children.link(coll)
    return coll


def _dims_from_props(props):
    inner_outer_d = props.bore_diameter + 2.0 * props.ring_thickness
    outer_inner_d = props.outer_diameter - 2.0 * props.ring_thickness
    radial_space = outer_inner_d - inner_outer_d
    return inner_outer_d, outer_inner_d, radial_space


def _max_elements_for_pitch(pitch_diameter, element_diameter, gap_factor):
    circumference = math.pi * pitch_diameter
    element_pitch = max(0.1, element_diameter * (1.0 + gap_factor))
    return max(3, int(circumference // element_pitch))


def _resolve_geometry(props):
    """Löst Parameter auf, damit das Lager geometrisch funktionsfähig bleibt."""
    inner_outer_d, outer_inner_d, radial_space = _dims_from_props(props)
    if radial_space <= 0.0:
        return None, "Ringstärke/Abmessungen erzeugen keinen Laufbahnspalt."

    # freie Radialhöhe für Wälzkörper: zwei Laufspielzonen (innen/außen)
    usable_space = radial_space - 2.0 * props.radial_clearance
    if usable_space <= 0.2:
        return None, "Zu wenig Platz zwischen den Ringen nach Abzug der Lagerluft."

    requested_roller_d = props.roller_diameter
    max_roller_d = usable_space * 0.98
    if requested_roller_d > max_roller_d:
        if not props.auto_fit:
            return None, (
                f"Wälzkörper-Ø ({requested_roller_d:.2f} mm) ist zu groß. "
                f"Maximal zulässig: {max_roller_d:.2f} mm."
            )
        roller_d = max_roller_d
    else:
        roller_d = requested_roller_d

    pitch_d = inner_outer_d + roller_d + 2.0 * props.radial_clearance

    max_elements = _max_elements_for_pitch(pitch_d, roller_d, props.gap_factor)
    if props.element_count > max_elements:
        if not props.auto_fit:
            return None, (
                f"Zu viele Wälzkörper ({props.element_count}). "
                f"Maximal zulässig: {max_elements} für aktuellen Pitch/Ø."
            )
        element_count = max_elements
    else:
        element_count = props.element_count

    if props.bearing_type == "NEEDLE":
        roller_length = props.width * 0.98
    elif props.bearing_type == "CYLINDRICAL":
        roller_length = props.width * 0.82
    elif props.bearing_type == "TAPERED":
        roller_length = props.width * 0.90
    elif props.bearing_type == "SPHERICAL":
        roller_length = props.width * 0.85
    else:
        roller_length = roller_d

    resolved = {
        "inner_outer_d": inner_outer_d,
        "outer_inner_d": outer_inner_d,
        "roller_d": roller_d,
        "roller_length": roller_length,
        "pitch_d": pitch_d,
        "element_count": max(3, element_count),
    }
    return resolved, None


def _build_bearing(props, spec, target_collection):
    inner_ring = _make_hollow_ring(
        "InnerRing",
        props.bore_diameter,
        spec["inner_outer_d"],
        props.width,
        props.segments,
        collection=target_collection,
    )
    outer_ring = _make_hollow_ring(
        "OuterRing",
        spec["outer_inner_d"],
        props.outer_diameter,
        props.width,
        props.segments,
        collection=target_collection,
    )

    elements = []
    ring_r = spec["pitch_d"] * 0.5
    roller_r = spec["roller_d"] * 0.5

    for i in range(spec["element_count"]):
        a = 2.0 * math.pi * i / spec["element_count"]
        x = ring_r * math.cos(a)
        y = ring_r * math.sin(a)

        if props.bearing_type == "BALL":
            obj = _add_uv_sphere(
                f"Ball_{i+1:02d}",
                roller_r,
                (x, y, 0.0),
                props.segments,
                max(8, props.segments // 2),
                collection=target_collection,
            )
        elif props.bearing_type in {"CYLINDRICAL", "NEEDLE"}:
            obj = _add_cylinder(
                f"Roller_{i+1:02d}",
                roller_r,
                spec["roller_length"],
                (x, y, 0.0),
                max(12, props.segments // 2),
                collection=target_collection,
            )
            obj.rotation_euler[2] = a
        elif props.bearing_type == "TAPERED":
            bm = bmesh.new()
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=False,
                segments=max(12, props.segments // 2),
                radius1=roller_r * 0.75,
                radius2=roller_r * 1.15,
                depth=spec["roller_length"],
            )
            bmesh.ops.translate(bm, vec=Vector((x, y, 0.0)), verts=bm.verts)
            obj = _finish_bmesh(f"TaperRoller_{i+1:02d}", bm, collection=target_collection)
            obj.rotation_euler[2] = a
        else:  # SPHERICAL / Tonnenlager
            bm = bmesh.new()
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=False,
                segments=max(12, props.segments // 2),
                radius1=roller_r * 0.85,
                radius2=roller_r * 1.15,
                depth=spec["roller_length"] * 0.5,
            )
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=False,
                segments=max(12, props.segments // 2),
                radius1=roller_r * 1.15,
                radius2=roller_r * 0.85,
                depth=spec["roller_length"] * 0.5,
                matrix=Matrix.Translation((0.0, 0.0, spec["roller_length"] * 0.5)),
            )
            bmesh.ops.translate(bm, vec=Vector((x, y, -spec["roller_length"] * 0.25)), verts=bm.verts)
            obj = _finish_bmesh(f"BarrelRoller_{i+1:02d}", bm, collection=target_collection)
            obj.rotation_euler[2] = a

        elements.append(obj)

    # Funktionsfähig: Komponenten bleiben getrennt und werden unter ein Empty gruppiert.
    assembly = bpy.data.objects.new("Bearing", None)
    target_collection.objects.link(assembly)
    assembly.empty_display_type = 'PLAIN_AXES'

    for part in [inner_ring, outer_ring, *elements]:
        part.parent = assembly

    # Manifold-Qualitätsprüfung je Objekt
    nm_total = 0
    for part in [inner_ring, outer_ring, *elements]:
        nm_total += _count_non_manifold_edges(part.data)

    return assembly, nm_total


class UNI_Bearing_Properties(bpy.types.PropertyGroup):
    bearing_type: EnumProperty(name="Lagertyp", items=BEARING_TYPES, default="BALL")
    series_code: EnumProperty(
        name="Normreihe",
        items=lambda self, context: [
            (code, code, f"Preset {code}") for code in SERIES_PRESETS.get(self.bearing_type, {}).keys()
        ]
        or [("CUSTOM", "Custom", "Benutzerdefiniert")],
    )

    use_preset: BoolProperty(name="Norm-Preset verwenden", default=True)
    bore_diameter: FloatProperty(name="Innendurchmesser d [mm]", default=20.0, min=1.0)
    outer_diameter: FloatProperty(name="Außendurchmesser D [mm]", default=47.0, min=2.0)
    width: FloatProperty(name="Breite B [mm]", default=14.0, min=1.0)

    ring_thickness: FloatProperty(name="Ringstärke [mm]", default=4.0, min=0.5)
    roller_diameter: FloatProperty(name="Wälzkörper-Ø [mm]", default=7.0, min=0.5)
    element_count: IntProperty(name="Wälzkörper Anzahl", default=10, min=3, max=256)
    gap_factor: FloatProperty(
        name="Umfangsspalt Faktor",
        description="Zusätzlicher Umfangsabstand zwischen Wälzkörpern",
        default=0.10,
        min=0.0,
        max=0.8,
    )
    auto_fit: BoolProperty(
        name="Auto-Fit aktiv",
        description="Passt Wälzkörper-Ø und Anzahl automatisch an, damit das Lager funktionsfähig bleibt",
        default=True,
    )

    segments: IntProperty(name="Auflösung Segmente", default=48, min=12, max=256)
    precision_class: EnumProperty(name="Toleranzklasse", items=PRECISION_CLASSES, default="NORMAL")
    radial_clearance: FloatProperty(name="Radiale Lagerluft [mm]", default=0.02, min=0.0)


class UNI_OT_apply_series_preset(bpy.types.Operator):
    bl_idname = "uni_bearing.apply_series_preset"
    bl_label = "Norm-Preset anwenden"
    bl_description = "Überträgt die Maßwerte des ausgewählten Presets"

    def execute(self, context):
        props = context.scene.uni_bearing
        preset = SERIES_PRESETS.get(props.bearing_type, {}).get(props.series_code)
        if preset:
            props.bore_diameter, props.outer_diameter, props.width = preset
        return {'FINISHED'}


class UNI_OT_create_bearing(bpy.types.Operator):
    bl_idname = "uni_bearing.create"
    bl_label = "Erstellen"
    bl_description = "Erstellt das konfigurierte Wälzlager als separate, funktionsfähige Komponenten"

    def execute(self, context):
        props = context.scene.uni_bearing

        if props.bore_diameter >= props.outer_diameter:
            self.report({'ERROR'}, "Innendurchmesser muss kleiner als Außendurchmesser sein.")
            return {'CANCELLED'}

        spec, error = _resolve_geometry(props)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        scale = 0.001  # mm -> m (Blender)
        old_cursor = context.scene.cursor.location.copy()

        coll_name = f"Bearing_{props.bearing_type}"
        target_collection = _create_collection(coll_name)
        assembly, non_manifold_edges = _build_bearing(props, spec, target_collection)

        assembly.scale = (scale, scale, scale)
        assembly.location = old_cursor
        assembly["bearing_type"] = props.bearing_type
        assembly["norm_hint"] = "ISO 15 / DIN 625 Preset-basiert"
        assembly["precision_class"] = props.precision_class
        assembly["radial_clearance_mm"] = props.radial_clearance
        assembly["resolved_roller_d_mm"] = spec["roller_d"]
        assembly["resolved_element_count"] = spec["element_count"]

        if non_manifold_edges > 0:
            self.report({'WARNING'}, f"Lager erstellt, aber {non_manifold_edges} nicht-manifold Kanten erkannt.")
        else:
            self.report(
                {'INFO'},
                f"Wälzlager funktionsfähig erzeugt (ØRoller={spec['roller_d']:.2f} mm, n={spec['element_count']}).",
            )
        return {'FINISHED'}


class UNI_PT_bearing_panel(bpy.types.Panel):
    bl_label = "UNI Rolling Bearing"
    bl_idname = "UNI_PT_BEARING_PANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UNI Bearings"

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing

        col = layout.column(align=True)
        col.label(text="1) Lagertyp wählen")
        col.prop(props, "bearing_type", text="")

        box = layout.box()
        box.label(text="2) Normen & Presets")
        box.prop(props, "precision_class")
        box.prop(props, "radial_clearance")
        box.prop(props, "use_preset")
        if props.use_preset:
            box.prop(props, "series_code")
            box.operator("uni_bearing.apply_series_preset", icon='PRESET')

        settings = layout.box()
        settings.label(text="3) Geometrie")
        settings.prop(props, "bore_diameter")
        settings.prop(props, "outer_diameter")
        settings.prop(props, "width")
        settings.prop(props, "ring_thickness")

        roller = layout.box()
        roller.label(text="4) Wälzkörper")
        roller.prop(props, "roller_diameter")
        roller.prop(props, "element_count")
        roller.prop(props, "gap_factor")
        roller.prop(props, "auto_fit")

        if props.bearing_type in {"NEEDLE", "CYLINDRICAL"}:
            roller.label(text="Hinweis: Zylindrische Rollen werden erzeugt.")
        elif props.bearing_type == "TAPERED":
            roller.label(text="Hinweis: Kegelrollen werden erzeugt.")
        elif props.bearing_type == "SPHERICAL":
            roller.label(text="Hinweis: Tonnenrollen werden erzeugt.")

        preview = layout.box()
        preview.label(text="5) Plausibilitäts-Check")
        spec, error = _resolve_geometry(props)
        if error:
            preview.alert = True
            preview.label(text=error, icon='ERROR')
        else:
            preview.label(text=f"Effektiver Roller-Ø: {spec['roller_d']:.3f} mm")
            preview.label(text=f"Effektive Anzahl: {spec['element_count']}")

        quality = layout.box()
        quality.label(text="6) Mesh Qualität")
        quality.prop(props, "segments")

        layout.separator()
        layout.operator("uni_bearing.create", icon='MESH_TORUS')


CLASSES = (
    UNI_Bearing_Properties,
    UNI_OT_apply_series_preset,
    UNI_OT_create_bearing,
    UNI_PT_bearing_panel,
)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.uni_bearing = PointerProperty(type=UNI_Bearing_Properties)


def unregister():
    del bpy.types.Scene.uni_bearing
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
