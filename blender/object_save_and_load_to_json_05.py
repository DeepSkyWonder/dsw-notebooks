import bpy  
import bmesh
from mathutils import Vector
import json
import os

def print_console(*data):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'CONSOLE':
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.console.scrollback_append(override, text=str(" ".join([str(x) for x in data])), type="OUTPUT")

def vec_to_list(vec, decimals=4, separator=','):
    
    result = []
    
    for element in vec:
        result.append(element)
        
    return result

def object_from_data(data, name, collection, select=True):
    """ Create a mesh object and link it to a scene """

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(data['verts'], data['edges'], data['faces'])

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    mesh.validate(verbose=True)

    return obj

def recalculate_normals(mesh):
    """ Make normals consistent for mesh """

    bm = bmesh.new()
    bm.from_mesh(mesh)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(mesh)
    bm.free()


def set_smooth(obj):
    """ Enable smooth shading on an mesh object """

    for face in obj.data.polygons:
        face.use_smooth = True
        
TEST = False
        
if TEST:
    
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete(use_global=False)

    bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    obj = bpy.context.active_object 

lc = bpy.context.view_layer.layer_collection.children['Collection']
bpy.context.view_layer.active_layer_collection = lc
collection = bpy.context.collection

obj = bpy.context.active_object 
data = obj.data
name = obj.name

nverts = len(obj.data.vertices)

vertices = obj.data.vertices
vertex_list = []

polygons = obj.data.polygons
faces_list = []

#print_console(nverts)

for index in range(nverts):
    
    vertex_list.append(vec_to_list(obj.data.vertices[index].co))
    
#print_console(vertex_list)

for fn, polygon in enumerate(polygons):
    
    face = []
    
    for element in range(len(polygon.vertices)):
        
        vertex_no = polygon.vertices[element]
        face.append(vertex_no)
        
    faces_list.append(face)

#print_console(faces_list)

data = {
    'verts': vertex_list,
    'edges': [],
    'faces': faces_list,
    }
    
#print_console(data)

scene = bpy.context.scene
obj_02 = object_from_data(data, name + '_02', collection)
bpy.context.view_layer.objects.active = obj_02
recalculate_normals(obj_02.data)
bpy.ops.object.modifier_add(type='BEVEL')
bpy.context.object.modifiers["Bevel"].segments = 5
set_smooth(obj_02)
obj_02.location = 0.0, 2.5, 0.0

json_object = json.dumps(data) 
#print(json_object)

base_path = '/Users/cmcewing/Documents/blender_docs/'
json_base_path = os.path.join(base_path, 'json/')
json_path = os.path.join(json_base_path, 'prefect_quad_sphere.json')
#print_console(json_path)

with open(json_path, 'w') as outfile:
    #json.dump(data, outfile)
    outfile.write(json_object)
    
with open(json_path, 'r') as jsonfile:
    mesh_data = json.load(jsonfile)

scene = bpy.context.scene

obj_03 = object_from_data(mesh_data, name + '_03', collection)

bpy.context.view_layer.objects.active = obj_03

recalculate_normals(obj_03.data)

BEVEL = True
SUBSURF = True
CYCLES = True
SMOOTH = True

if BEVEL:
    
    bpy.ops.object.modifier_add(type='BEVEL')
    bpy.context.object.modifiers["Bevel"].segments = 5
    bpy.context.object.modifiers["Bevel"].width = 0.001

if SUBSURF:

    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].levels = 3
    bpy.context.object.modifiers["Subdivision"].render_levels = 3
    bpy.context.object.modifiers["Subdivision"].use_custom_normals = False

if CYCLES:
    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.feature_set = 'EXPERIMENTAL'
    bpy.context.scene.cycles.device = 'GPU'
    bpy.context.scene.cycles.max_subdivisions = 6
    bpy.context.object.cycles.use_adaptive_subdivision = True

if SMOOTH:
    
    set_smooth(obj_03)

# bpy.context.object.active_material.cycles.displacement_method = 'BOTH'

obj_03.location = 0.0, 5.0, 0.0
obj_03.dimensions = 2.0, 2.0, 1.0

# move mesh points to sphere
#bpy.ops.transform.tosphere(value=1.0)
#bpy.context.object.modifiers["Cast"].factor = 0
