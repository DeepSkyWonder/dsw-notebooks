import bpy  
import bmesh
from mathutils import Vector
import json
import os

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
        
def srgb2lin(s):
    """ Convert SRGB color to Linear RGB color """
    
    if s <= 0.0404482362771082:
        lin = s / 12.92
    else:
        lin = pow(((s + 0.055) / 1.055), 2.4)
    return lin

def hex_to_gamma_corrected_blender_color(hex_color, alpha=1.0):
    """ Convert Hex Color to Blender RGBA Gamma Corrected Color with Alpha 1.0 """
    
    # Remove the '#' symbol from the HEX color string
    hex_color = hex_color.lstrip('#')

    # Convert the HEX color to RGB values
    rgb = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    srgb_tuple = ()
    
    for index in range(len(rgb)):
        
        corrected_color = srgb2lin(rgb[index])       
        srgb_tuple = (*srgb_tuple, corrected_color)
        
    # Add an alpha value of 1.0 to the final color
    rgba = srgb_tuple + (alpha,)
    #print_console(rgba)

    return rgba
        
base_path = '/Users/cmcewing/Documents/blender_docs/'
json_base_path = os.path.join(base_path, 'json/')
json_filename = 'prefect_quad_sphere___.json'
json_path = os.path.join(json_base_path, json_filename)
  
with open(json_path, 'r') as jsonfile:
    mesh_data = json.load(jsonfile)

scene = bpy.context.scene

collection = bpy.data.collections['Collection']

quad_sphere = object_from_data(mesh_data, 'Quad Sphere', collection)

bpy.context.view_layer.objects.active = quad_sphere

recalculate_normals(quad_sphere.data)

BEVEL = False
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
    
    set_smooth(quad_sphere)

# bpy.context.object.active_material.cycles.displacement_method = 'BOTH'

#quad_sphere.location = 0.0, 5.0, 0.0
quad_sphere.dimensions = 2.0, 2.0, 2.0

