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
        
def srgb2lin(s):
    """ Convert SRGB color to Linear RGB color """
    
    if s <= 0.0404482362771082:
        lin = s / 12.92
    else:
        lin = pow(((s + 0.055) / 1.055), 2.4)
    return lin

def lin2srgb(lin):
    """ Convert Linear RGB color to SRGB color """    
    
    if lin > 0.0031308:
        s = 1.055 * (pow(lin, (1.0 / 2.4))) - 0.055
    else:
        s = 12.92 * lin
    return s

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

material_test = {
    'nodes': {},
    'links': {},
    'node_data': {},
    'node_coord': {},
    'data': {}
    }

material_test['nodes'] = {'N_PBSDF': 'ShaderNodeBsdfPrincipled', 
    'N_Emis': 'ShaderNodeEmission', 
    'N_Mix': 'ShaderNodeMixShader', 
    'N_Out': 'ShaderNodeOutputMaterial'
    }
    
material_test['links'] = {
    0: {'Out': ['N_Emis', 'Emission'], 'In': ['N_Mix', 1]},
    1: {'Out': ['N_PBSDF', 'BSDF'], 'In': ['N_Mix', 2]},
    2: {'Out': ['N_Mix', 'Shader'], 'In': ['N_Out', 'Surface']}
    }

material_test['node_data'] = {
    'N_PBSDF': {'Base Color': 'color_bsdf'},
    'N_Emis': {'Color': 'color_emission', 'Strength': 'emission_strength'},
    'N_Mix': {0: 'mix_factor'},
    }
    
material_test['node_coord'] = {
    'N_PBSDF': (-400, 0),
    'N_Emis': (-300, 200),
    'N_Mix': (0, 0),
    'N_Out': (300, 0)
    }
    
material_test['data'] = {
    'color_bsdf': None,
    'color_emission': None,
    'emission_strength': None,
    'mix_factor': None
    }

print_console(material_test)
       
def create_material(material_data):
    
     # Create a new material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    
    # Clear default nodes
    material.node_tree.nodes.clear()
    
    mat_nodes = {}
    
    # Create nodes
    for node in material_data['nodes']:
        
        mat_nodes[node] = material.node_tree.nodes.new(material_data['nodes'][node])
        
    # Configure nodes
    for node in material_data['node_data']:
        
        print_console(node)
        
        for property in material_data['node_data'][node]:
            
            print_console(property)
            print_console(material_data['node_data'][node][property])
            
            mat_nodes[node].inputs[property].default_value = material_data['data'][material_data['node_data'][node][property]]
            
    # Link nodes
    for node in material_data['links']:
        
        link_in = mat_nodes[material_data['links'][node]['In'][0]].inputs[material_data['links'][node]['In'][1]]
        link_out = mat_nodes[material_data['links'][node]['Out'][0]].outputs[material_data['links'][node]['Out'][1]]

        material.node_tree.links.new(link_in, link_out)   
        
    # Set node coordinates
    for node in material_data['node_coord']:
        
        print_console(material_data['node_coord'][node])
        
        mat_nodes[node].location = material_data['node_coord'][node]
        
    return material

def apply_material_to_object(obj, material):
    """ Apply Material to Object """
        
    if obj.data.materials:
        # Assign the material to the first slot
        obj.data.materials[0] = material
    else:
        # Create a new material slot and assign the material
        obj.data.materials.append(material)
           

# Configure Colours

slooh_gold = hex_to_gamma_corrected_blender_color('#B09C78')
slooh_bright_gold = hex_to_gamma_corrected_blender_color('#E4C490')
slooh_red = hex_to_gamma_corrected_blender_color('#DB6448') 
slooh_light_blue = hex_to_gamma_corrected_blender_color('#00A2FF')
slooh_background_blue = hex_to_gamma_corrected_blender_color('#202E40')
slooh_light_background_blue = hex_to_gamma_corrected_blender_color('#40556E')

# Configure Test Material

color_emission = slooh_red #hex_to_gamma_corrected_blender_color('#FF6334')
color_bsdf = slooh_red #hex_to_gamma_corrected_blender_color('#FA9E0F')
emission_strength = 0.2

material_test['data'] = {
    'color_bsdf': slooh_red,
    'color_emission': slooh_red,
    'emission_strength': 0.2,
    'mix_factor': 0.5,
    'material_name': 'hemisphere_material'
    }

materials = {}

# Create Material
materials[material_test['data']['material_name']] = create_material(material_test)

# Apply Material
apply_material_to_object(obj, materials['hemisphere_material'])