bl_info = {
    "name": "Align UV Islands by Longest Edge",
    "author": "Kajus + GPT",
    "version": (1, 3, 0),
    "blender": (4, 0, 0),
    "location": "UV Editor > UV > Align by Longest Edge",
    "description": "Rotates each UV island so its longest UV edge becomes horizontal. Handles Alt+D linked meshes once.",
    "category": "UV",
}

import bpy
import bmesh
import math
from mathutils import Vector


# ---------- core uv utils ----------

def _active_uv_layer(bm):
    uv = bm.loops.layers.uv.active
    if uv is None:
        raise RuntimeError("No active UV layer")
    return uv


def _face_uv_edge_keys(face, uv_layer, tol=0.0):
    """Return normalized UV-edge keys for all edges of a face."""
    keys = []
    loops = face.loops
    n = len(loops)
    for i in range(n):
        uv1 = loops[i][uv_layer].uv
        uv2 = loops[(i + 1) % n][uv_layer].uv
        if tol > 0.0:
            u1 = (round(uv1.x / tol) * tol, round(uv1.y / tol) * tol)
            u2 = (round(uv2.x / tol) * tol, round(uv2.y / tol) * tol)
            a, b = Vector(u1), Vector(u2)
        else:
            a, b = Vector((uv1.x, uv1.y)), Vector((uv2.x, uv2.y))
        # order independent key
        if (a.x, a.y) < (b.x, b.y):
            key = (a.x, a.y, b.x, b.y)
        else:
            key = (b.x, b.y, a.x, a.y)
        keys.append(key)
    return keys


def _build_islands(bm, respect_selection):
    """Return list of sets of faces. Connectivity by shared identical UV edges."""
    uv = _active_uv_layer(bm)
    faces = [f for f in bm.faces if (f.select if respect_selection else True)]
    if not faces:
        return []

    edge_map = {}
    for f in faces:
        for key in _face_uv_edge_keys(f, uv):
            edge_map.setdefault(key, []).append(f)

    # adjacency
    nbrs = {f: set() for f in faces}
    for flist in edge_map.values():
        if len(flist) > 1:
            for i in range(len(flist)):
                fi = flist[i]
                for j in range(i + 1, len(flist)):
                    fj = flist[j]
                    nbrs[fi].add(fj)
                    nbrs[fj].add(fi)

    # BFS
    islands = []
    seen = set()
    for f in faces:
        if f in seen:
            continue
        stack = [f]
        comp = set()
        seen.add(f)
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for nb in nbrs[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        islands.append(comp)
    return islands


def _island_longest_edge_uv(island_faces, uv_layer):
    """Return (p,q) UV coords of the longest edge in the island."""
    max_len = -1.0
    best = (Vector((0.0, 0.0)), Vector((1.0, 0.0)))
    seen_keys = set()
    for f in island_faces:
        loops = f.loops
        n = len(loops)
        for i in range(n):
            u = Vector(loops[i][uv_layer].uv)
            v = Vector(loops[(i + 1) % n][uv_layer].uv)
            # de-dup with normalized key
            key = tuple(sorted(((u.x, u.y), (v.x, v.y))))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            d = v - u
            L = d.length
            if L > max_len:
                max_len = L
                best = (u.copy(), v.copy())
    return best


def _island_centroid_uv(island_faces, uv_layer):
    """Centroid of unique UV vertices in island."""
    uniq = {}
    for f in island_faces:
        for l in f.loops:
            uv = l[uv_layer].uv
            uniq[(uv.x, uv.y)] = uv
    if not uniq:
        return Vector((0.0, 0.0))
    s = Vector((0.0, 0.0))
    for uv in uniq.values():
        s.x += uv.x
        s.y += uv.y
    c = 1.0 / len(uniq)
    return Vector((s.x * c, s.y * c))


def _rotate_island(island_faces, uv_layer, angle_rad, pivot):
    ca = math.cos(angle_rad)
    sa = math.sin(angle_rad)
    # mutate each loop uv
    for f in island_faces:
        for l in f.loops:
            uv = l[uv_layer].uv
            x = uv.x - pivot.x
            y = uv.y - pivot.y
            rx = x * ca - y * sa
            ry = x * sa + y * ca
            uv.x = rx + pivot.x
            uv.y = ry + pivot.y


def _align_islands_in_bmesh(bm, respect_selection):
    uv = _active_uv_layer(bm)
    islands = _build_islands(bm, respect_selection)
    total = 0
    for isl in islands:
        if not isl:
            continue
        a, b = _island_longest_edge_uv(isl, uv)
        d = b - a
        if d.length_squared == 0.0:
            continue
        ang = -math.atan2(d.y, d.x)  # rotate so edge becomes horizontal
        pivot = _island_centroid_uv(isl, uv)
        _rotate_island(isl, uv, ang, pivot)
        total += 1
    return total


# ---------- object processing with Alt+D grouping ----------

def _groups_by_mesh(objs):
    groups = {}
    for o in objs:
        if o.type != 'MESH':
            continue
        key = o.data.as_pointer()
        groups.setdefault(key, []).append(o)
    return list(groups.values())


def process_object(obj, respect_selection):
    """Process one Mesh datablock. Uses edit-BMesh if obj in EDIT, else temp BMesh."""
    if obj.type != 'MESH':
        return 0

    # EDIT mode: edit-bmesh is shared across all linked users of this Mesh
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        count = _align_islands_in_bmesh(bm, respect_selection=True)
        bmesh.update_edit_mesh(obj.data, loop_triangles=False)
        return count

    # OBJECT mode: operate once on the Mesh
    me = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        count = _align_islands_in_bmesh(bm, respect_selection=False)
        bm.to_mesh(me)
        me.update()
        return count
    finally:
        bm.free()


# ---------- operator ----------

class UV_OT_align_by_longest_edge(bpy.types.Operator):
    bl_idname = "uv.align_by_longest_edge"
    bl_label = "Align by Longest Edge"
    bl_description = "Rotate each UV island so its longest UV edge becomes horizontal. Processes each unique Mesh once."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if not sel:
            self.report({'ERROR'}, "Select at least one mesh object")
            return {'CANCELLED'}

        total_islands = 0
        processed_meshes = 0

        for group in _groups_by_mesh(sel):
            # Prefer an edit-mode representative if present
            rep = None
            for o in group:
                if o.mode == 'EDIT':
                    rep = o
                    break
            if rep is None:
                rep = group[0]

            total_islands += process_object(rep, respect_selection=(rep.mode == 'EDIT'))
            processed_meshes += 1

        self.report({'INFO'}, f"Processed {processed_meshes} mesh(es). Islands aligned: {total_islands}")
        return {'FINISHED'}


# ---------- ui ----------

def _menu_func(self, _context):
    self.layout.operator(UV_OT_align_by_longest_edge.bl_idname, icon='UV')


classes = (
    UV_OT_align_by_longest_edge,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    try:
        bpy.types.IMAGE_MT_uvs.append(_menu_func)
    except Exception:
        pass


def unregister():
    try:
        bpy.types.IMAGE_MT_uvs.remove(_menu_func)
    except Exception:
        pass
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
