bl_info = {
    "name": "Layout objects Along Axis",
    "author": "FaxLab3D",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Layout",
    "description": "Layout Selected objects end-to-end along X/Y/Z with a gap",
    "category": "Object"
}

import bpy
from bpy.props import EnumProperty, FloatProperty

# Add sort_method to PropertyGroup
class LayoutObjectsSettings(bpy.types.PropertyGroup):
    axis: EnumProperty(
        name="Axis",
        items=[('X',"X",""),('Y',"Y",""),('Z',"Z","")],
        default='X'
    )
    gap: FloatProperty(
        name="Distance",
        description="Gap between objects",
        default=0.1,
        min=0.0
    )
    sort_method: EnumProperty(
        name="Sort by",
        items=[('NAME', "Name", "Sort by Name"),
               ('VOLUME', "Volume", "Sort by Bounding Box Volume")],
        default='VOLUME'
    )

class OBJECT_OT_pack_on_axis(bpy.types.Operator):
    bl_idname = "object.pack_on_axis"
    bl_label = "Layout Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.layout_objects_settings
        objs = list(context.selected_objects)
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        if len(objs) < 2:
            self.report({'WARNING'}, "Select at least two objects")
            return {'CANCELLED'}

        # Sort objects
        if s.sort_method == 'NAME':
            objs.sort(key=lambda ob: ob.name)
        elif s.sort_method == 'VOLUME':
            def get_volume(ob):
                d = ob.dimensions
                return d.x * d.y * d.z
            objs.sort(key=get_volume, reverse=True)  # Largest first. Remove reverse=True for smallest first.

        ax = 'XYZ'.index(s.axis)

        prev_center = objs[0].location[ax]
        prev_half = objs[0].dimensions[ax] / 2.0
        prev_end = prev_center + prev_half

        for ob in objs[1:]:
            half = ob.dimensions[ax] / 2.0
            new_center = prev_end + s.gap + half

            loc = ob.location.copy()
            loc[ax] = new_center
            ob.location = loc

            prev_end = new_center + half

        return {'FINISHED'}

class VIEW3D_PT_pack_objects(bpy.types.Panel):
    bl_label = "Layout objects"
    bl_idname = "VIEW3D_PT_pack_objects"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FaxLab3D"

    def draw(self, context):
        layout = self.layout
        s = context.scene.layout_objects_settings

        layout.prop(s, "axis")
        layout.prop(s, "gap")
        layout.prop(s, "sort_method")
        layout.separator()
        layout.operator("object.pack_on_axis", text="Layout Selected")

classes = (
    LayoutObjectsSettings,
    OBJECT_OT_pack_on_axis,
    VIEW3D_PT_pack_objects,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.layout_objects_settings = bpy.props.PointerProperty(type=LayoutObjectsSettings)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.layout_objects_settings

if __name__ == "__main__":
    register()
