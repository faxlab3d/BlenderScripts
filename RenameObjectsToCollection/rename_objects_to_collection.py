bl_info = {
    "name": "Rename by Collection",
    "author": "FaxLab3D",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > FaxLab3D",
    "description": "Renames selected objects by the name of their first collection",
    "category": "Object"
}

import bpy

class OBJECT_OT_rename_by_collection(bpy.types.Operator):
    bl_idname = "object.rename_by_collection"
    bl_label = "Rename by Collection"
    bl_description = "Rename selected objects by their first collection name"

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        for obj in context.selected_objects:
            colls = [col for col in obj.users_collection if col.name != "Scene Collection"]
            if colls:
                obj.name = colls[0].name
        return {'FINISHED'}

class VIEW3D_PT_rename_by_collection(bpy.types.Panel):
    bl_label = "Rename by Collection"
    bl_idname = "VIEW3D_PT_rename_by_collection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FaxLab3D"   # <- Category changed

    def draw(self, context):
        layout = self.layout
        layout.operator("object.rename_by_collection")

classes = (
    OBJECT_OT_rename_by_collection,
    VIEW3D_PT_rename_by_collection,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
