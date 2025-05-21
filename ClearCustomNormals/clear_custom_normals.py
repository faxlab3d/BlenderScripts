bl_info = {
    "name": "Clear Split Normals for Selected Objects",
    "author": "FaxLab3D",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Tool",
    "description": "Clears custom split normals on selected objects",
    "warning": "",
    "category": "Mesh"
}

import bpy

class MESH_OT_clear_split_normals(bpy.types.Operator):
    bl_idname = "mesh.clear_split_normals"
    bl_label = "Clear Split Normals"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in context.selected_objects:
            context.view_layer.objects.active = obj
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        self.report({'INFO'}, "Cleared split normals")
        return {'FINISHED'}


class VIEW3D_PT_clear_split_normals(bpy.types.Panel):
    bl_label = "Normals"
    bl_idname = "VIEW3D_PT_clear_split_normals"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FaxLab3D"

    def draw(self, context):
        self.layout.operator("mesh.clear_split_normals", icon='NORMALS_VERTEX')


classes = (
    MESH_OT_clear_split_normals,
    VIEW3D_PT_clear_split_normals,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
