bl_info = {
    "name": "UNI Rolling Bearing Generator",
    "author": "Codex",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > UNI Bearings",
    "description": "Erstellt parametrische Wälzlager mit Norm-Presets und N-Panel UI",
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

# Vereinfachte Start-Presets (DIN 625 / ISO 15 Reihen) als praxisnaher Einstieg.
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


def _new_mesh_object(name: str):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj, mesh


def _finish_bmesh(name: str, bm: bmesh.types.BMesh):
    obj, mesh = _new_mesh_object(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.validate(verbose=False)
    return obj


def _make_hollow_ring(name: str, inner_d: float, outer_d: float, width: float, segments: int):
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
    return _finish_bmesh(name, bm)


def _add_uv_sphere(name: str, radius: float, location, segments: int, rings: int):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=max(8, segments),
        v_segments=max(6, rings),
        radius=radius,
    )
    bmesh.ops.translate(bm, vec=Vector(location), verts=bm.verts)
    return _finish_bmesh(name, bm)


def _add_cylinder(name: str, radius: float, depth: float, location, segments: int):
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
    return _finish_bmesh(name, bm)


def _distribute_elements(props, pitch_diameter, element_radius, factory, count, name_prefix, z=0.0):
    objs = []
    ring_r = pitch_diameter * 0.5
    for i in range(count):
        a = 2.0 * math.pi * i / count
        x = ring_r * math.cos(a)
        y = ring_r * math.sin(a)
        obj = factory(
            f"{name_prefix}_{i+1:02d}",
            element_radius,
            (x, y, z),
            props.segments,
        )
        objs.append(obj)
    return objs


def _join_and_recalc(objs, target_name):
    if not objs:
        return None
    ctx = bpy.context
    for o in ctx.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    ctx.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = ctx.view_layer.objects.active
    joined.name = target_name

    bm = bmesh.new()
    bm.from_mesh(joined.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(joined.data)
    bm.free()
    joined.data.update()
    joined.data.validate(verbose=False)
    return joined


def _build_bearing(props):
    inner_ring = _make_hollow_ring(
        "InnerRing", props.bore_diameter, props.bore_diameter + props.ring_thickness * 2.0, props.width, props.segments
    )
    outer_ring = _make_hollow_ring(
        "OuterRing", props.outer_diameter - props.ring_thickness * 2.0, props.outer_diameter, props.width, props.segments
    )

    pitch = (props.bore_diameter + props.outer_diameter) * 0.5

    if props.bearing_type == "BALL":
        elements = _distribute_elements(
            props,
            pitch_diameter=pitch,
            element_radius=props.roller_diameter * 0.5,
            factory=lambda n, r, loc, seg: _add_uv_sphere(n, r, loc, seg, max(8, seg // 2)),
            count=props.element_count,
            name_prefix="Ball",
        )
    elif props.bearing_type == "CYLINDRICAL":
        elements = _distribute_elements(
            props,
            pitch_diameter=pitch,
            element_radius=props.roller_diameter * 0.5,
            factory=lambda n, r, loc, seg: _add_cylinder(n, r, props.width * 0.8, loc, seg),
            count=props.element_count,
            name_prefix="CylRoller",
        )
    elif props.bearing_type == "NEEDLE":
        elements = _distribute_elements(
            props,
            pitch_diameter=pitch,
            element_radius=props.roller_diameter * 0.5,
            factory=lambda n, r, loc, seg: _add_cylinder(n, r, props.width * 0.95, loc, max(12, seg)),
            count=props.element_count,
            name_prefix="Needle",
        )
    elif props.bearing_type == "TAPERED":
        elements = []
        ring_r = pitch * 0.5
        half_len = props.width * 0.45
        for i in range(props.element_count):
            a = 2.0 * math.pi * i / props.element_count
            x = ring_r * math.cos(a)
            y = ring_r * math.sin(a)
            bm = bmesh.new()
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=False,
                segments=max(12, props.segments),
                radius1=props.roller_diameter * 0.35,
                radius2=props.roller_diameter * 0.55,
                depth=half_len * 2.0,
            )
            bmesh.ops.translate(bm, vec=Vector((x, y, 0.0)), verts=bm.verts)
            obj = _finish_bmesh(f"TaperRoller_{i+1:02d}", bm)
            obj.rotation_euler[2] = a
            elements.append(obj)
    else:  # SPHERICAL / Tonnenlager
        elements = []
        ring_r = pitch * 0.5
        for i in range(props.element_count):
            a = 2.0 * math.pi * i / props.element_count
            x = ring_r * math.cos(a)
            y = ring_r * math.sin(a)
            bm = bmesh.new()
            # Vereinfachter Tonnenkörper als zwei gekoppelte Kegelstümpfe
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=False,
                segments=max(12, props.segments),
                radius1=props.roller_diameter * 0.45,
                radius2=props.roller_diameter * 0.65,
                depth=props.width * 0.45,
            )
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=False,
                segments=max(12, props.segments),
                radius1=props.roller_diameter * 0.65,
                radius2=props.roller_diameter * 0.45,
                depth=props.width * 0.45,
                matrix=Matrix.Translation((0.0, 0.0, props.width * 0.45)),
            )
            bmesh.ops.translate(bm, vec=Vector((x, y, -props.width * 0.225)), verts=bm.verts)
            obj = _finish_bmesh(f"BarrelRoller_{i+1:02d}", bm)
            obj.rotation_euler[2] = a
            elements.append(obj)

    all_parts = [inner_ring, outer_ring, *elements]
    bearing = _join_and_recalc(all_parts, "Bearing")
    if bearing is None:
        return None

    # finaler Manifold-Check je Kante
    bm_check = bmesh.new()
    bm_check.from_mesh(bearing.data)
    non_manifold = [e for e in bm_check.edges if not e.is_manifold]
    bm_check.free()
    if non_manifold:
        print(f"[UNI Bearing] Warnung: {len(non_manifold)} nicht-manifold Kanten erkannt.")
    return bearing


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
    element_count: IntProperty(name="Wälzkörper Anzahl", default=10, min=4, max=128)
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
    bl_description = "Erstellt das konfigurierte Wälzlager als manifold Mesh"

    def execute(self, context):
        props = context.scene.uni_bearing

        if props.bore_diameter >= props.outer_diameter:
            self.report({'ERROR'}, "Innendurchmesser muss kleiner als Außendurchmesser sein.")
            return {'CANCELLED'}
        if props.ring_thickness * 2.0 >= (props.outer_diameter - props.bore_diameter):
            self.report({'ERROR'}, "Ringstärke ist zu groß für die gewählten Durchmesser.")
            return {'CANCELLED'}

        scale = 0.001  # mm -> m (Blender)
        old_cursor = context.scene.cursor.location.copy()

        bearing = _build_bearing(props)
        if bearing is None:
            self.report({'ERROR'}, "Lager konnte nicht erzeugt werden.")
            return {'CANCELLED'}

        bearing.scale = (scale, scale, scale)
        bearing.location = old_cursor
        bearing["bearing_type"] = props.bearing_type
        bearing["norm_hint"] = "ISO 15 / DIN 625 Preset-basiert"
        bearing["precision_class"] = props.precision_class
        bearing["radial_clearance_mm"] = props.radial_clearance

        self.report({'INFO'}, "Wälzlager wurde erzeugt.")
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

        if props.bearing_type in {"NEEDLE", "CYLINDRICAL"}:
            roller.label(text="Hinweis: Zylindrische Rollen werden erzeugt.")
        elif props.bearing_type == "TAPERED":
            roller.label(text="Hinweis: Kegelrollen werden erzeugt.")
        elif props.bearing_type == "SPHERICAL":
            roller.label(text="Hinweis: Tonnenrollen werden erzeugt.")

        quality = layout.box()
        quality.label(text="5) Mesh Qualität")
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
