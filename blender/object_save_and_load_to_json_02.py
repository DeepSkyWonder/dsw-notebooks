import bpy  
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

def object_from_data(data, name, scene, select=True):
    """ Create a mesh object and link it to a scene """

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(data['verts'], data['edges'], data['faces'])

    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    mesh.validate(verbose=True)

    return obj

obj = bpy.context.active_object 

data = obj.data

nverts = len(obj.data.vertices)

vertices = obj.data.vertices
vertex_list = []

polygons = obj.data.polygons
faces_list = []

print_console(nverts)

for index in range(nverts):
    
    vertex_list.append(vec_to_list(obj.data.vertices[index].co))
    
print_console(vertex_list)

for fn, polygon in enumerate(polygons):
    
    face = []
    
    for element in range(len(polygon.vertices)):
        
        vertex_no = polygon.vertices[element]
        face.append(vertex_no)
        
    faces_list.append(face)

print_console(faces_list)

data = {
    'verts': vertex_list,
    'edges': [],
    'faces': faces_list,
    }
    
print_console(data)

scene = bpy.context.scene
cube_02 = object_from_data(data, 'Cube 2', scene)
cube_02.location = 0.0, 2.5, 0.0

json_object = json.dumps(data) 
print(json_object)

base_path = '/Users/cmcewing/Documents/blender_docs/'
json_base_path = os.path.join(base_path, 'json/')
json_path = os.path.join(json_base_path, 'cube_2.json')
print_console(json_path)

with open(json_path, 'w') as outfile:
    #json.dump(data, outfile)
    outfile.write(json_object)
    
with open(json_path, 'r') as jsonfile:
    mesh_data = json.load(jsonfile)

scene = bpy.context.scene
cube_03 = object_from_data(mesh_data, 'Cube 3', scene)

cube_03.location = 0.0, 5.0, 0.0