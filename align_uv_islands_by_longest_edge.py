bl_info = {
    "name": "UV: Align by Longest Edge (Multi-Object)",
    "author": "FaxLab3D",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "UV Editor > N-panel > UV",
    "description": "Rotate UV islands so their longest edge is horizontal across all selected objects",
    "category": "UV",
}

import bpy
import bmesh
from math import atan2, cos, sin
from mathutils import Vector

def uv_key(luv):
    return (round(luv.uv.x, 10), round(luv.uv.y, 10))

def gather_islands(bm, uv_layer, limit_to_selected=True):
    sel_faces, any_sel = set(), False
    if limit_to_selected:
        for f in bm.faces:
            for l in f.loops:
                if l[uv_layer].select:
                    any_sel = True
                    sel_faces.add(f)
                    break
    if not any_sel:
        sel_faces = set(bm.faces)

    edge_map = {}
    for f in sel_faces:
        for l in f.loops:
            edge_map.setdefault(l.edge, []).append((f, l, l.link_loop_next))

    unvisited = set(sel_faces)
    islands = []
    while unvisited:
        seed = unvisited.pop()
        stack = [seed]
        island = {seed}
        while stack:
            f = stack.pop()
            for l in f.loops:
                f_uv_edge = {uv_key(l[uv_layer]), uv_key(l.link_loop_next[uv_layer])}
                for of, ol1, ol2 in edge_map.get(l.edge, []):
                    if of in unvisited:
                        of_uv_edge = {uv_key(ol1[uv_layer]), uv_key(ol2[uv_layer])}
                        if f_uv_edge == of_uv_edge:
                            unvisited.remove(of)
                            island.add(of)
                            stack.append(of)
        islands.append(island)
    return islands

def longest_edge_angle(island, uv_layer):
    best_a, best_l2 = 0.0, 0.0
    for f in island:
        ls = f.loops
        n = len(ls)
        for i in range(n):
            a = ls[i][uv_layer].uv
            b = ls[(i+1) % n][uv_layer].uv
            dx, dy = b.x - a.x, b.y - a.y
            l2 = dx*dx + dy*dy
            if l2 > best_l2 and l2 > 1e-20:
                best_l2 = l2
                best_a = atan2(dy, dx)
    return best_a

def rotate_island(island, uv_layer, angle):
    uniq = {}
    for f in island:
        for l in f.loops:
            k = uv_key(l[uv_layer])
            if k not in uniq:
                uniq[k] = l[uv_layer].uv.copy()
    if not uniq:
        return
    c = Vector((0.0, 0.0))
    for v in uniq.values():
        c += v
    c /= len(uniq)

    ca, sa = cos(-angle), sin(-angle)
    for f in island:
        for l in f.loops:
            luv = l[uv_layer]
            v = luv.uv - c
            luv.uv = Vector((v.x * ca - v.y * sa, v.x * sa + v.y * ca)) + c

def process_object(obj, respect_selection=True):
    """Edits UVs for one mesh object. If object is in edit mode, use from_edit_mesh.
       Otherwise, use a temporary BM and write back."""
    if obj.type != 'MESH':
        return 0

    in_edit = obj.mode == 'EDIT'
    if in_edit:
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            return 0
        islands = gather_islands(bm, uv_layer, limit_to_selected=respect_selection)
        for isl in islands:
            a = longest_edge_angle(isl, uv_layer)
            rotate_island(isl, uv_layer, a)
        bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
        return len(islands)
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            bm.free()
            return 0
        islands = gather_islands(bm, uv_layer, limit_to_selected=False)
        for isl in islands:
            a = longest_edge_angle(isl, uv_layer)
            rotate_island(isl, uv_layer, a)
        bm.to_mesh(obj.data)
        obj.data.update()
        bm.free()
        return len(islands)

class UV_OT_align_by_longest_edge(bpy.types.Operator):
    bl_idname = "uv.align_by_longest_edge"
    bl_label = "Align by Longest Edge"
    bl_description = "Rotate UV islands so their longest edge becomes horizontal for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_meshes = [o for o in context.selected_objects if o.type == 'MESH']
        if not selected_meshes:
            self.report({'ERROR'}, "Select at least one mesh object")
            return {'CANCELLED'}

        # If multi-object edit mode is active, Blender only exposes one edit_object.
        # We handle both: edit objects respect UV selection; others process all islands.
        total = 0
        for obj in selected_meshes:
            total += process_object(obj, respect_selection=True)

        self.report({'INFO'}, f"Aligned islands on {len(selected_meshes)} object(s). Total islands: {total}")
        return {'FINISHED'}

class UV_PT_align_longest_edge(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UV'
    bl_label = 'Align by Longest Edge'

    def draw(self, context):
        self.layout.operator("uv.align_by_longest_edge", icon='UV')

classes = (
    UV_OT_align_by_longest_edge,
    UV_PT_align_longest_edge,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    try:
        bpy.types.IMAGE_MT_uvs.append(lambda self, ctx: self.layout.operator("uv.align_by_longest_edge", icon='UV'))
    except Exception:
        pass

def unregister():
    try:
        bpy.types.IMAGE_MT_uvs.remove(lambda self, ctx: self.layout.operator("uv.align_by_longest_edge", icon='UV'))
    except Exception:
        pass
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
