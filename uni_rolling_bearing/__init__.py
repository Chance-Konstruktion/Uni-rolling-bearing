"""UNI Rolling Bearing Generator – Blender Addon (Einstiegspunkt).

Die einzelnen Module sind:

* ``constants``      – Lagertyp-IDs, Presets, Normhinweise.
* ``geometry``       – Reine Geometrieberechnungen (Blender-frei testbar).
* ``mesh_builders``  – BMesh-Helfer für Ringe und Wälzkörper.
* ``properties``     – ``PropertyGroup`` für die UI.
* ``operators``      – Operatoren ``apply_series_preset`` und ``create``.
* ``panel``          – N-Panel ``View3D > UNI Bearings``.

``bpy`` wird bewusst erst in ``register()`` importiert, damit Tests die
reinen Geometriefunktionen ohne laufendes Blender importieren können.
"""

from __future__ import annotations

bl_info = {
    "name": "UNI Rolling Bearing Generator",
    "author": "Codex",
    "version": (0, 3, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > UNI Bearings",
    "description": "Erstellt parametrische, funktionsfähige Wälzlager mit Norm-Presets",
    "category": "Add Mesh",
}


def _classes():
    from .operators import UNI_OT_apply_series_preset, UNI_OT_create_bearing
    from .panel import UNI_PT_bearing_panel
    from .properties import UNI_Bearing_Properties

    return (
        UNI_Bearing_Properties,
        UNI_OT_apply_series_preset,
        UNI_OT_create_bearing,
        UNI_PT_bearing_panel,
    )


def register() -> None:
    import bpy
    from bpy.props import PointerProperty

    from .properties import UNI_Bearing_Properties

    classes = _classes()
    registered = []
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
        bpy.types.Scene.uni_bearing = PointerProperty(type=UNI_Bearing_Properties)
    except Exception:
        # Auf halbem Weg gescheitert – sauber zurückrollen, damit der nächste
        # Aktivierungsversuch nicht in Restzuständen hängen bleibt.
        for cls in reversed(registered):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
        raise


def unregister() -> None:
    import bpy

    if hasattr(bpy.types.Scene, "uni_bearing"):
        del bpy.types.Scene.uni_bearing
    for cls in reversed(_classes()):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
