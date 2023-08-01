""" Create Animation of Stars Transiting """

# Import Libraries
import re
import os
import bpy
import bmesh
import numpy as np
import pandas as pd
import math
import mathutils
import copy
from bpy import context, data, ops
from math import sin, cos, radians, pi, atan, tan
from mathutils import Vector as Vector

# Store the Sceen Context
scene = context.scene

# Configure Paths
base_path = '/Users/cmcewing/Documents/blender_docs/'
base_path_HDRI = os.path.join(base_path, 'HDRI/') # Path data for stars in CSV format
star_path_csv = os.path.join(base_path, 'star_paths.csv') # Path data for stars in CSV format
slooh_blue_texture = os.path.join(base_path, 'slooh_blue_02.png') # Blue background texture image
meadow_hdri_texture = os.path.join(base_path_HDRI, 'meadow_at_night.hdr') # HDRI starry beadow world background

# Dictionary for Collections
collections = {}

# Store Default Collection
lc = bpy.context.view_layer.layer_collection.children['Collection']
bpy.context.view_layer.active_layer_collection = lc
collection = bpy.context.collection
collections['Collection'] = collection

# Configure camera rotation
camera_rotation = 270.0

# Configure compass label rotation
compass_lable_rotation = 270.0

# Configure compass label text
compass_lable_text = 'EAST'


# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

def create_material(material_data):
    
     # Create a new material
    material = bpy.data.materials.new(material_data['data']['material_name'])
    material.use_nodes = True
    
    # Clear default nodes
    material.node_tree.nodes.clear()
    
    mat_nodes = {}
    
    # Create nodes
    for node in material_data['nodes']:
        
        mat_nodes[node] = material.node_tree.nodes.new(material_data['nodes'][node])
        
    # Configure nodes
    for node in material_data['node_data']:
        
        #print_console(node)
        
        for property in material_data['node_data'][node]:
            
            #print_console(property)
            #print_console(material_data['node_data'][node][property])
            #print_console(material_data['data'][material_data['node_data'][node][property]])
            
            mat_nodes[node].inputs[property].default_value = material_data['data'][material_data['node_data'][node][property]]
            
    # Link nodes
    for node in material_data['links']:
        
        link_in = mat_nodes[material_data['links'][node]['In'][0]].inputs[material_data['links'][node]['In'][1]]
        link_out = mat_nodes[material_data['links'][node]['Out'][0]].outputs[material_data['links'][node]['Out'][1]]

        material.node_tree.links.new(link_in, link_out)   
        
    # Set node coordinates
    for node in material_data['node_coord']:
        
        #print_console(material_data['node_coord'][node])
        
        mat_nodes[node].location = material_data['node_coord'][node]
        
    return material                
                
def print_console(*data):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'CONSOLE':
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.console.scrollback_append(override, text=str(" ".join([str(x) for x in data])), type="OUTPUT")  

def configure_renderer(scene=scene):
    """ Set-up the Redering Engine """    
    
    scene.cycles.device = 'GPU'
    prefs = bpy.context.preferences
    prefs.addons['cycles'].preferences.get_devices()
    cprefs = prefs.addons['cycles'].preferences
    print(cprefs)
    
    # Attempt to set GPU device types if available
    for compute_device_type in ('CUDA', 'OPENCL', 'NONE'):
        try:
            cprefs.compute_device_type = compute_device_type
            print('Device found',compute_device_type)
            break
        except TypeError:
            pass
        
    # Enable all CPU and GPU devices
    for device in cprefs.devices:
        if not re.match('intel', device.name, re.I):
            print('Activating',device)
            device.use = True
        
        
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1280
    scene.render.engine = 'CYCLES'
    scene.cycles.feature_set = 'EXPERIMENTAL'
    scene.cycles.adaptive_threshold = 0.05
    scene.cycles.max_subdivisions = 6


def clear_scene(ops=ops):
    """ Delete all existing items in scene. """  
            
    ops.object.select_all(action='SELECT')
    ops.object.delete(use_global=False)   
    
def set_scene_background_color(color):
    """ Set background color of world. """ 
        
    # Set background color of scene
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.0144438, 0.0273209, 0.0512695, 1)

def set_smooth(obj):
    """ Enable smooth shading on an mesh object """

    for face in obj.data.polygons:
        face.use_smooth = True


def object_from_data(data, name, scene, select=True):
    """ Create a mesh object and link it to a scene """

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(data['verts'], data['edges'], data['faces'])

    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)

    bpy.context.view_layer.objects.active = obj
    #obj.select = True

    mesh.update(calc_edges=True)
    mesh.validate(verbose=True)

    return obj


def recalculate_normals(mesh):
    """ Make normals consistent for mesh """

    bm = bmesh.new()
    bm.from_mesh(mesh)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(mesh)
    bm.free()
    
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
    
def hex_to_blender_color(hex_color, alpha=1.0):
    """ Convert Hex Color to Blender RGBA Color with Alpha 1.0 """
    
    # Remove the '#' symbol from the HEX color string
    hex_color = hex_color.lstrip('#')

    # Convert the HEX color to RGB values
    rgb = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    # Add an alpha value of 1.0 to the final color
    rgba = rgb + (alpha,)

    return rgba

def set_camera_location_rotation(location, rotation):
    """ Set camera location and rotation """       
    
    # Get the active camera
    camera = bpy.context.scene.camera

    if camera is not None:
        # Set the camera's location
        camera.location = location

        # Set the camera's rotation
        camera.rotation_euler = [math.radians(angle) for angle in rotation]

def rotate_camera_location_and_rotation_z_axis(angle):
    """ Rotate Camera about z-axis, but keep it pointed towards scene """    
    
    # Get the active camera
    camera = bpy.context.scene.camera

    if camera is not None:
        # Get the current camera location
        location = camera.location

        # Create a rotation matrix to rotate around the Z-axis
        rotation_matrix = mathutils.Matrix.Rotation(math.radians(angle), 4, 'Z')

        # Rotate the location around the Z-axis
        rotated_location = rotation_matrix @ location

        # Set the new camera location
        camera.location = rotated_location

        # Rotate the camera's rotation around its own Z-axis
        camera.rotation_euler.z += math.radians(angle)

# ------------------------------------------------------------------------------
# Geometry functions
# ------------------------------------------------------------------------------
      
def apply_subdivision(object, subdivision_type='CATMULL_CLARK'):
    """ Apply subdivision to an object """
        
    # set active object
    current_object = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = object    
    
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].quality = 3
    bpy.context.object.modifiers["Subdivision"].levels = 3
    bpy.context.object.modifiers["Subdivision"].render_levels = 3
    bpy.context.object.modifiers["Subdivision"].subdivision_type = subdivision_type
    bpy.context.object.modifiers["Subdivision"].use_limit_surface = True
    bpy.context.object.modifiers["Subdivision"].uv_smooth = 'PRESERVE_CORNERS'
    bpy.context.object.modifiers["Subdivision"].boundary_smooth = 'ALL'
    bpy.context.object.modifiers["Subdivision"].use_creases = True
    bpy.context.object.modifiers["Subdivision"].use_custom_normals = True
    bpy.ops.object.modifier_apply(modifier="Subdivision")
    
     # restore previous active object
    bpy.context.view_layer.objects.active = current_object 
    
def set_object_origin_to_scene_origin(object):
    """ Move object origin to scene origin """
    
    # set active object
    current_object = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = object

    # store the location of current 3d cursor
    saved_location = bpy.context.scene.cursor.location  # returns a vector

    # give 3dcursor new coordinates
    bpy.context.scene.cursor.location = Vector((0.0,0.0,0.0))

    # set the origin on the current object to the 3dcursor location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    # set 3dcursor location back to the stored location
    bpy.context.scene.cursor.location = saved_location
    
    # restore previous active object
    bpy.context.view_layer.objects.active = current_object


# ------------------------------------------------------------------------------
# Main Functions
# ------------------------------------------------------------------------------

def create_colored_material(name, color_bsdf, color_emission, emission_strenght, mix_frac):
    """ Create Material BSDF/Emission Mixed Shader """
    
    # Create a new material
    material = bpy.data.materials.new(name)
    material.use_nodes = True

    # Clear default nodes
    material.node_tree.nodes.clear()

    # Create a Principled BSDF Shader node
    shader_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    shader_bsdf.inputs['Base Color'].default_value = color_bsdf
    shader_bsdf.location = (-400, 0)
    
    # Create a Emission Shader node
    shader_emission = material.node_tree.nodes.new('ShaderNodeEmission')
    shader_emission.inputs['Color'].default_value = color_emission
    shader_emission.inputs['Strength'].default_value = emission_strenght
    shader_emission.location = (-300, 200)
    
    # Create a Mix Shader node
    shader_mix = material.node_tree.nodes.new('ShaderNodeMixShader')
    shader_mix.inputs['Fac'].default_value = mix_frac
    shader_mix.inputs[0].default_value
    shader_mix.location = (0, 0)    

    # Create an output node
    shader_output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader_output.location = (300, 0)

    # Link the nodes
    material.node_tree.links.new(shader_emission.outputs['Emission'], shader_mix.inputs[1])
    material.node_tree.links.new(shader_bsdf.outputs['BSDF'], shader_mix.inputs[2])
    material.node_tree.links.new(shader_mix.outputs['Shader'], shader_output.inputs['Surface'])
    
    return material

def create_transparent_material(name, alpha_bsdf, image_texture, mix_frac=0.5):
    """ Create Material BSDF/Transparent-BSDF Mixed Shader """
    
    # Create a new material
    material = bpy.data.materials.new(name)
    material.use_nodes = True

    # Clear default nodes
    material.node_tree.nodes.clear()
    
    # Create Texture Image Node
    texture_image = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture_image.image = bpy.data.images.load(image_texture)
    texture_image.location = (-800, -200)

    # Create a Principled BSDF Shader node
    shader_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    shader_bsdf.inputs['Alpha'].default_value = alpha_bsdf 
    shader_bsdf.location = (-400, 0)
    
    # Create a Trasparent BSDF Shader node
    shader_transparent_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfTransparent')
    shader_transparent_bsdf.location = (-400, 0)
    
    # Create a Mix Shader node
    shader_mix = material.node_tree.nodes.new('ShaderNodeMixShader')
    shader_mix.inputs['Fac'].default_value = mix_frac
    shader_mix.inputs[0].default_value
    shader_mix.location = (0, 0)    

    # Create an output node
    shader_output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader_output.location = (300, 0)

    # Link the nodes
    material.node_tree.links.new(shader_mix.inputs[2], shader_transparent_bsdf.outputs['BSDF'])
    material.node_tree.links.new(shader_mix.inputs[1], shader_bsdf.outputs['BSDF'])
    material.node_tree.links.new(shader_output.inputs['Surface'], shader_mix.outputs['Shader'])
    material.node_tree.links.new(shader_bsdf.inputs['Base Color'], texture_image.outputs['Color'])
    
    return material

def apply_material_to_object(obj, material):
    """ Apply Material to Object """
        
    if obj.data.materials:
        # Assign the material to the first slot
        obj.data.materials[0] = material
    else:
        # Create a new material slot and assign the material
        obj.data.materials.append(material)
           
        
def configure_material_shadows(material): 
    """ Define how shadows are handled for material """
    
    # Store current material, and set active material to material
    current_material = bpy.context.active_object.active_material
    bpy.context.active_object.active_material = material

    # Configure shadows  
    bpy.context.active_object.active_material = hemisphere_material
    bpy.context.object.active_material.blend_method = 'BLEND'
    bpy.context.object.active_material.shadow_method = 'CLIP'
    bpy.context.object.active_material.cycles.use_transparent_shadow = False

    # Restore current_material
    bpy.context.active_object.active_material = current_material        


def create_hemisphere(radius=1.0):
    """ Create Smoothed Hemisphere """
    
    # Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
    sphere = ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    objects = data.objects
    sphere = objects['Sphere'] 
    
    bevel = sphere.modifiers.new('Bevel', 'BEVEL')
    bevel.limit_method = 'ANGLE'
    bevel.loop_slide=True
    bevel.material=-1
    bevel.profile=0.5
    bevel.offset_type='OFFSET'
    bevel.segments = 3
    bevel.width = 0.01
    bevel.harden_normals = True

    apply_subdivision(context.view_layer.objects.active)

    ops.mesh.primitive_cube_add(size=2*radius, enter_editmode=False, align='WORLD', location=(0, 0, -1*radius), scale=(1, 1, 1))

    objects = bpy.data.objects
    cube = objects['Cube'] 

    # Subtract Cube from Sphere to Create a Hemisphere
    bool_one = sphere.modifiers.new(type="BOOLEAN", name="bool hemisphere")
    bool_one.object = cube
    bool_one.operation = 'DIFFERENCE'

    context.view_layer.objects.active = sphere
    ops.object.modifier_apply(modifier='bool hemisphere')

    object_to_delete = data.objects['Cube']
    data.objects.remove(object_to_delete, do_unlink=True)

    # Correct dimensions of hemisphere
    context.view_layer.objects.active = sphere
    sphere.dimensions = 2.0*radius, 2.0*radius, 1.005*radius
    sphere.location = 0.0, 0.0, 0.0
    sphere.name = "Hemisphere (Smooth)"

    # Add sharp edges to base of hemisphere
    ob = context.view_layer.objects.active
    hemisphere_mesh = ob.data

    bm = bmesh.new()
    bm.from_mesh(hemisphere_mesh)

    EPSILON = 1.0e-5
    for vert in bm.verts:
        if -EPSILON <= vert.co.z <= EPSILON:
            vert.select = True

    # Add sharp state for all edges that are near the z-axis
    for edge in bm.edges:
        if edge.verts[0].select and edge.verts[1].select:
            edge.smooth = False

    bm.to_mesh(hemisphere_mesh)
    bm.free()
    
    hemisphere = sphere

    return hemisphere

# ------------------------------------------------------------------------------
# Base Material Definitions
# ------------------------------------------------------------------------------

# Configure Colours
slooh_gold = hex_to_gamma_corrected_blender_color('#B09C78')
slooh_bright_gold = hex_to_gamma_corrected_blender_color('#E4C490')
slooh_red = hex_to_gamma_corrected_blender_color('#DB6448') 
slooh_light_blue = hex_to_gamma_corrected_blender_color('#00A2FF')
slooh_background_blue = hex_to_gamma_corrected_blender_color('#202E40')
slooh_light_background_blue = hex_to_gamma_corrected_blender_color('#40556E')

color_white = hex_to_gamma_corrected_blender_color('#FFFFFF')
color_black = hex_to_gamma_corrected_blender_color('#000000')

Materials = {}

bsdf_material = {
    'nodes': {},
    'links': {},
    'node_data': {},
    'node_coord': {},
    'data': {}
    }

bsdf_material['nodes'] = {
    'N_PBSDF': 'ShaderNodeBsdfPrincipled', 
    'N_Out': 'ShaderNodeOutputMaterial'
    }
    
bsdf_material['links'] = {
    0: {'Out': ['N_PBSDF', 'BSDF'], 'In': ['N_Out', 'Surface']}
    }

bsdf_material['node_data'] = {
    'N_PBSDF': {
        'Base Color': 'color_bsdf',
        'Subsurface': 'subsurf',
        'Subsurface Color': 'subsurf_color', 
        'Subsurface IOR': 'subsurf_IOR',
        'Metallic': 'metal',
        'Specular': 'specular',
        'Roughness': 'rough',
        'Sheen': 'sheen',
        'Sheen Tint': 'sheen_tint',
        'Clearcoat': 'clear',
        'Clearcoat Roughness': 'clear_rough',
        'IOR': 'IOR',
        'Transmission': 'trans',
        'Transmission Roughness': 'trans_rough',
        'Emission': 'emiss_color',
        'Emission Strength': 'emiss_strength',
        'Alpha': 'alpha'
        }
    }
    
bsdf_material['node_coord'] = {
    'N_PBSDF': (-200, 0),
    'N_Out': (200, 0)
    }
    
bsdf_material['data'] = {
    'color_bsdf': color_white,
    'subsurf': 0.0,
    'subsurf_color': color_white,
    'subsurf_IOR': 1.4,
    'metal': 0.0,
    'specular': 0.5,
    'rough': 0.5,
    'sheen': 0.0,
    'sheen_tint': 0.5,
    'clear': 0.0,
    'clear_rough': 0.03,
    'IOR': 1.450,
    'trans': 0.0,
    'trans_rough': 0.0,
    'emiss_color': color_black,
    'emiss_strength': 1.0,
    'alpha': 1.0,
    'material_name': None
    }
    
obs_dome_base_material = copy.deepcopy(bsdf_material)

obs_dome_base_material['data'].update({
    'color_bsdf': color_white,
    'metal': 0.505,
    'specular': 0.5,
    'rough': 0.25,
    'emiss_color': color_white,
    'emiss_strength': 0.1,
    'material_name': 'dome_material'
    })

#print_console(bsdf_material['node_data'])
#print_console(obs_dome_base_material['node_data'])
#print_console(obs_dome_base_material)

Materials[obs_dome_base_material['data']['material_name']] = create_material(obs_dome_base_material)
    
obs_mount_material = copy.deepcopy(bsdf_material)

color_mount = hex_to_gamma_corrected_blender_color('#E7210E')
    
obs_mount_material['data'].update({
    'color_bsdf': color_mount,
    'material_name': 'mount_material'
    })
    
Materials[obs_mount_material['data']['material_name']] = create_material(obs_mount_material)
    
obs_telescope_material = copy.deepcopy(bsdf_material)

color_telescope = hex_to_gamma_corrected_blender_color('#254DA8')
    
obs_telescope_material['data'].update({
    'color_bsdf': color_telescope,
    'metal': 1.0,  
    'rough': 0.082,
    'material_name': 'telescope_material'
    })

Materials[obs_telescope_material['data']['material_name']] = create_material(obs_telescope_material)
    
obs_base_ring_material = copy.deepcopy(bsdf_material)

color_base_ring = hex_to_gamma_corrected_blender_color('#205EE7')
    
obs_base_ring_material['data'].update({
    'color_bsdf': color_base_ring,
    'rough': 0.5,
    'emiss_color': color_base_ring,
    'emiss_strength': 1.0,
    'material_name': 'base_ring_material'
    })
    
Materials[obs_base_ring_material['data']['material_name']] = create_material(obs_base_ring_material)

# ------------------------------------------------------------------------------
# Main Code - Setup Blender Scene
# ------------------------------------------------------------------------------

print_console('### Building Scene')

# Set-up dictionaries for Objects, and Materials
Objects = {}

# Configure Renderer
configure_renderer()

# Clear Scene of Objects
clear_scene()

# Create Collection for Observatory
collection = bpy.data.collections.new("Observatory")
bpy.context.scene.collection.children.link(collection)
collections['Observatory'] = collection

# Make Observatory Collection the Active Collection
layer_collection = bpy.context.view_layer.layer_collection.children[collections['Observatory'].name]
bpy.context.view_layer.active_layer_collection = layer_collection

# Import Observatory into Scene
obs_fbx_filepath = os.path.join(base_path, 'clamshell_observatory_10.fbx')
bpy.ops.import_scene.fbx( filepath = obs_fbx_filepath, global_scale = 0.085)

# Store Clamshell Observatory Objects for Later Use
Objects['Base'] = bpy.data.objects["Base"]
Objects['Base_Ring'] = bpy.data.objects["Base_Ring"]
Objects['Clamshell'] = bpy.data.objects["Clamshelll"]
Objects['Mount'] = bpy.data.objects["Mount"]
Objects['Telescope'] = bpy.data.objects["Telescope"]

print_console(Materials)

# Apply Materials to the Clamshell Observatory Components
apply_material_to_object(Objects['Base'], Materials['dome_material'])
apply_material_to_object(Objects['Base_Ring'], Materials['base_ring_material'])
apply_material_to_object(Objects['Clamshell'], Materials['dome_material'])
apply_material_to_object(Objects['Mount'], Materials['mount_material'])
apply_material_to_object(Objects['Telescope'], Materials['telescope_material'])

# Set the Collection back to the Default Collection
layer_collection = bpy.context.view_layer.layer_collection.children[collections['Collection'].name]
bpy.context.view_layer.active_layer_collection = layer_collection

# Set Scene Background Colour
color_world_background = slooh_background_blue #(0.0144438, 0.0273209, 0.0512695, 1)
set_scene_background_color(color_world_background)

# Add camera and set postion to focus on full earth view
camera = bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(3.8, 0.0, 0.85), rotation=(radians(82.0), radians(0.0), radians(90.0)), scale=(1, 1, 1))

# Set camera to Orthographic
bpy.context.object.data.type = 'ORTHO'

# Set Orthographic Scale
bpy.context.object.data.ortho_scale = 2.5

# Make Camera Active
objects = bpy.data.objects
camera = objects['Camera']
scene.camera = camera

# Set camera rotation and location
location = (3.8, 0.0, 0.93)
rotation = (82.0, 0.0, 90.0)
set_camera_location_rotation(location, rotation)

# Rotate camera about z-axis while keeping it oriented towards our scene
rotate_camera_location_and_rotation_z_axis(camera_rotation)  # Rotate camera's location and rotation by 45 degrees around the Z-axis

# Create Celestial Sphere - Hemisphere
hemisphere = create_hemisphere(radius=1.0)

# Create Transparent Material
hemisphere_material = create_transparent_material('Hemisphere_Material', 0.382, slooh_blue_texture, mix_frac=0.5)

# Apply Transparent Material
apply_material_to_object(hemisphere, hemisphere_material)

# Define how shadows are handled
configure_material_shadows(hemisphere_material)

# Smooth Shading on Hemisphere
set_smooth(hemisphere)

# Recalculate Normals Hemisphere
recalculate_normals(hemisphere.data)


def add_sun_lightsource():
    """ Add Sun Lightsource """

    # Add the Sun. Set Postion and Rotiation. Position is -1.0 on the z-axis   
    bpy.ops.object.light_add(type='SUN', radius=1, align='WORLD', location=(0, 0, -1), rotation=(0.0, 0.0, 0.0), scale=(1, 1, 1))
    
    # Sun intensity
    bpy.context.object.data.energy = 5.22
    
    # Sun angle
    bpy.context.object.data.angle = 0
    
    
def add_torus(major_radius=1.0, minor_radius=0.002, location=(0, 0, 0)):
    """ Add Ring (Torus) to Scene """
        
    # Add torus to act at line around base of hemisphere
    bpy.ops.mesh.primitive_torus_add(align='WORLD', location=location, rotation=(0, 0, 0), major_segments=100, minor_segments=50, major_radius=major_radius, minor_radius=minor_radius, abso_major_rad=1.25, abso_minor_rad=0.75)
    bpy.context.active_object.name = "Ring"
    objects = bpy.data.objects
    torus = objects['Ring'] 
    
    return torus

def add_cirle(radius=1.0, location=(0.0, 0.0, 0.0005), fill_type='TRIFAN'):
    """ Add Disk(Filled Circle) to Scene """
        
    bpy.ops.mesh.primitive_circle_add(vertices=100, radius=radius, fill_type=fill_type, enter_editmode=False, align='WORLD', location=location, scale=(1, 1, 1))
    bpy.context.active_object.name = "Disk"
    objects = bpy.data.objects
    circle = objects['Disk']   
    
    return circle

def create_glossy_colored_material(name, color_glossy_bsdf, roughness):
    """ Create Material Glossy BSDF Shader """
    
    # Create a new material
    material = bpy.data.materials.new(name)
    material.use_nodes = True

    # Clear default nodes
    material.node_tree.nodes.clear()

    # Create a Principled BSDF Shader node
    shader_glossy_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfGlossy')
    shader_glossy_bsdf.inputs['Color'].default_value = color_glossy_bsdf
    shader_glossy_bsdf.inputs['Roughness'].default_value = roughness
    shader_glossy_bsdf.location = (-0, 0) 

    # Create an output node
    shader_output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader_output.location = (200, 0)

    # Link the nodes
    material.node_tree.links.new(shader_glossy_bsdf.outputs['BSDF'], shader_output.inputs['Surface'])
    
    return material

def create_colored_emission_material(name, color_emission, emission_strenght):
    """ Create Material Emission Shader """
    
    # Create a new material
    material = bpy.data.materials.new(name)
    material.use_nodes = True

    # Clear default nodes
    material.node_tree.nodes.clear()

    # Create a Principled BSDF Shader node
    shader_emission = material.node_tree.nodes.new('ShaderNodeEmission')
    shader_emission.inputs['Color'].default_value = color_emission
    shader_emission.inputs['Strength'].default_value = emission_strenght
    shader_emission.location = (0, 0)
    
    # Create an output node
    shader_output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader_output.location = (200, 0)

    # Link the nodes
    material.node_tree.links.new(shader_emission.outputs['Emission'], shader_output.inputs['Surface'])
    
    return material

def add_star(scale=0.015, location=(0, 0, 1), name='Star'):
    """ Add Star to Scene """
        
    # Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
    bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False, align='WORLD', location=location, scale=(scale, scale, scale))
    bpy.context.active_object.name = name
    objects = bpy.data.objects
    star = objects[name]   
  
    return star

def add_glare_filter_to_compositor():
    """ Add Fog Glow (glare filter) to Compositor """
        
    bpy.context.scene.use_nodes = True

    composite_tree = bpy.context.scene.node_tree
    composite_tree_links = composite_tree.links

    render_node = composite_tree.nodes['Render Layers']
    glare_node = composite_tree.nodes.new('CompositorNodeGlare')
    output_node = composite_tree.nodes['Composite']
    viewer_node = composite_tree.nodes.new('CompositorNodeViewer')
    
    render_node.location = (-200, 0)
    glare_node.location = (0, 0)
    output_node.location = (200, -200)
    viewer_node.location = (200, 200)

    composite_tree_links.new(render_node.outputs['Image'], glare_node.inputs['Image'])
    composite_tree_links.new(glare_node.outputs['Image'], output_node.inputs['Image'])
    composite_tree_links.new(glare_node.outputs['Image'], viewer_node.inputs['Image'])

    glare_node.glare_type = 'FOG_GLOW'
    glare_node.quality = 'HIGH'
    glare_node.size = 9    


def add_hdri_world_shader(hdri_texture, color_world_background):
    """ Add HDRI Illumination to the World """
        
    # Get the environment node tree of the current scene
    scene.world.use_nodes = True
    world_node_tree = scene.world.node_tree
    tree_nodes = world_node_tree.nodes
    links = world_node_tree.links

    # Clear all nodes
    tree_nodes.clear()

    # Add Background node
    shader_background_texture = tree_nodes.new(type='ShaderNodeBackground')
    shader_background_texture.inputs['Strength'].default_value = 1.1
    shader_background_texture.location = (0,200)
    
    shader_background_color = tree_nodes.new(type='ShaderNodeBackground')
    shader_background_color.inputs['Color'].default_value = color_world_background
    shader_background_color.location = (0,-200)
    
    # Add Light Path Input node
    input_lightpath = tree_nodes.new(type='ShaderNodeLightPath')
    input_lightpath.location = (-300,-300)

    # Add Environment Texture node
    shader_environment = tree_nodes.new('ShaderNodeTexEnvironment')
    shader_environment.image = bpy.data.images.load(hdri_texture) # Relative path
    shader_environment.location = (-300,300)

    # Create a Mix Shader node
    shader_mix = tree_nodes.new('ShaderNodeMixShader')
    shader_mix.inputs['Fac'].default_value = mix_frac
    shader_mix.location = (0, 0)   

    # Add Output node
    output_world = tree_nodes.new(type='ShaderNodeOutputWorld')   
    output_world.location = (200,0)

    # Link all nodes
    links.new(input_lightpath.outputs["Is Camera Ray"], shader_mix.inputs["Fac"])
    links.new(shader_environment.outputs["Color"], shader_background_texture.inputs["Color"])
    links.new(shader_background_texture.outputs["Background"], shader_mix.inputs[1]) 
    links.new(shader_background_color.outputs["Background"], shader_mix.inputs[2]) 
    links.new(shader_mix.outputs["Shader"], output_world.inputs["Surface"]) 
    

# Notes - To Do
# (Tick - Check) Add new glossy shader for circle
# (Tick - Check) Add World HDRI Shader
# (Check) Alter observatory shader
# (Check) Check ring shader
# (Tick) Add additional stars
# (To Do) Correct Normals on Hemisphere
# (To Do) Add text for south and east (possibly north and west)
# (To Do) Add function to turn on/off text element during render
# (To Do) Check any material changes to any of the objects
# Add star paths geometry node code
# Add 


  
# Add a Sun lightsource to our sceen    
add_sun_lightsource()  

# Add (torus) ring to base of celestial hemisphere
torus = add_torus(major_radius=1.0, minor_radius=0.002, location=(0, 0, 0))

# Create material for torus
color_emission = hex_to_gamma_corrected_blender_color('#435973')
color_bsdf = hex_to_gamma_corrected_blender_color('#435973')
emission_strength = 1.7
mix_frac = 0.5
torus_material = create_colored_material('torus_material', color_bsdf, color_emission, emission_strength, mix_frac)

# Apply ring (torus) material
apply_material_to_object(torus, torus_material)

# Smooth Shading on Torus
set_smooth(torus)

# Add (filled circle) disk to our scene
circle = add_cirle(radius=1.0, location=(0.0, 0.0, 0.0005), fill_type='TRIFAN')

# Create material for (filled circle) disk
color_glossy_bsdf = hex_to_gamma_corrected_blender_color('#364E62')
roughness = 0.146
circle_material = create_glossy_colored_material('circle_material', color_glossy_bsdf, roughness)

# Apply disk (filled circle) material
apply_material_to_object(circle, circle_material)

# Smooth Shading on Circle
set_smooth(circle)

# Add stars to our scene
star_blue = add_star(scale=0.015, location=(1, 0, 0), name='Star_Blue')
star_red = add_star(scale=0.015, location=(0.7071, 0.7071, 0), name='Star_Red')
star_yellow = add_star(scale=0.015, location=(0.7071, -0.7071, 0), name='Star_Yellow')

star_objects = [star_yellow, star_red, star_blue]

# Create material for stars
color_star_blue = hex_to_gamma_corrected_blender_color('#1A5AFF')
color_star_red = hex_to_gamma_corrected_blender_color('#FF4C2E')
color_star_yellow = hex_to_gamma_corrected_blender_color('#FFEC3C')

emission_strength_star_blue = 28.3
emission_strength_star_red = 25.9
emission_strength_star_yellow = 17.0

star_blue_material = create_colored_emission_material('blue_star_material', color_star_blue, emission_strength_star_blue)
star_red_material = create_colored_emission_material('red_star_material', color_star_red, emission_strength_star_red)
star_yellow_material = create_colored_emission_material('yellow_star_material', color_star_yellow, emission_strength_star_yellow)

# Apply star materials
apply_material_to_object(star_blue, star_blue_material)
apply_material_to_object(star_red, star_red_material)
apply_material_to_object(star_yellow, star_yellow_material)

# Add Follow Constraints to Clamshell Observatory Child Objects to Track the Blue Star or Sun
bpy.context.view_layer.objects.active = Objects['Clamshell']
bpy.ops.object.constraint_add(type='LOCKED_TRACK')
bpy.context.object.constraints["Locked Track"].target = star_blue
bpy.context.object.constraints["Locked Track"].track_axis = 'TRACK_X'

bpy.context.view_layer.objects.active = Objects['Mount']
bpy.ops.object.constraint_add(type='LOCKED_TRACK')
bpy.context.object.constraints["Locked Track"].target = star_blue
bpy.context.object.constraints["Locked Track"].track_axis = 'TRACK_Y'

bpy.context.view_layer.objects.active = Objects['Telescope']
bpy.ops.object.constraint_add(type='TRACK_TO')
bpy.context.object.constraints["Track To"].target = star_blue
bpy.context.object.constraints["Track To"].track_axis = 'TRACK_Z'

# Add Glare to compositor to create glow around stars
add_glare_filter_to_compositor()

# Add HDRI image texture shader to world, but set background to matt color
color_world_background = slooh_background_blue # hex_to_gamma_corrected_blender_color('#202E40')
add_hdri_world_shader(meadow_hdri_texture, color_world_background) 


def create_text(text, font_path, location=(0, 0, 0), scale=(1, 1, 1), orientation=(0, 0, 0), name='Text', kerning=0.0):
    """ Create Text Labels for Compass Points """

    ops.object.select_all(action='DESELECT')  # Deselect all objects
    ops.object.text_add(location=location)  # Create a new text object
    text_object = context.object
    text_object.data.body = text  # Set the text content

    # Set the text object's scale
    text_object.scale = scale
    
    # Set the font of the text object
    text_object.data.font = data.fonts.load(font_path)

    # Set the text object's orientation
    euler_rotation = mathutils.Euler(orientation, 'XYZ')
    text_object.rotation_euler = euler_rotation

    # Set the kerning of the text object
    for char in text_object.data.body_format:
        char.kerning = kerning

    # Set the origin of the text object to the center of the text
    ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')

    # Set the location of the text object
    text_object.location = location

    # Set the name of the text object
    text_object.name = "Text_" + name
        
    return text_object

scale = 0.06
text = compass_lable_text # 'EAST'
name = 'South'
text_objects = {}
kerning = 1
font_name = 'Ubuntu-Regular.ttf'
font_path = os.path.join(base_path, font_name)

# Create Compass Direction Label - South
text_objects[name] = create_text(text, font_path, location=(1.51, 0, 0), scale=(scale, scale, scale), orientation=(1.43117, 0, 1.5708), name=name, kerning=kerning)
compass_points_label_material = create_colored_material('South_Text_Material', slooh_red, slooh_red, 1.0, 1.0)
apply_material_to_object(text_objects['South'], compass_points_label_material)

def rotate_object_about_z_axis(object, angle):
    """ Rotate Object around z-axis, keeping with the same orientation relative to the z-axis """

    if object is not None:
        
        # Get the current object location
        location = object.location

        # Create a rotation matrix to rotate around the Z-axis
        rotation_matrix = mathutils.Matrix.Rotation(math.radians(angle), 4, 'Z')

        # Rotate the location around the Z-axis
        rotated_location = rotation_matrix @ location

        # Set the new object location
        object.location = rotated_location

        # Rotate the objcts's rotation around its own Z-axis
        object.rotation_euler.z += math.radians(angle)

# Rotate compass label about z-axis, to South position
rotate_object_about_z_axis(text_objects['South'], compass_lable_rotation)
    
# https://blender.stackexchange.com/questions/23436/control-cycles-eevee-material-nodes-and-material-properties-using-python
# Glossy Shader https://blender.stackexchange.com/questions/143599/python-mix-shader-diffuse-bsdf-glossy-bsdf-nodes
# Glossy Diffuse Shader https://www.youtube.com/watch?v=VrsteZ3Ci3w&ab_channel=chocofur
# BPY Glossy Diffuse Shader https://gist.github.com/p2or/1ffcd6ed57bc8d857afbd3659c9a0089

#print_console(star_path_csv)
paths_df = pd.read_csv(star_path_csv)
number_of_stars = 3
#print_console(paths_df['X_01'][0])

def create_curve_from_dataframe(dataframe, index):
    """ Create Curve from Datafram """

    # Create a new curve object
    curve_data = bpy.data.curves.new(name=f"Curve_Data_{index:02}", type="CURVE")
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    curve_object = bpy.data.objects.new(name=f"Curve_{index:02}", object_data=curve_data)

    # Link the curve object to the scene
    bpy.context.collection.objects.link(curve_object)

    # Create a new spline for the curve
    spline = curve_data.splines.new(type='NURBS')
    
    # Trim Dataframe to exclude points below the X-Y plane (i.e. with negative Z values)
    dataframe_star_path = dataframe[dataframe[f'DISPLAY_{(index+1):02}']][[f'X_{(index+1):02}', f'Y_{(index+1):02}', f'Z_{(index+1):02}']].copy(index).reset_index(drop=True)

    # Set the coordinates from the dataframe
    spline.points.add(len(dataframe_star_path))
    for i, row in dataframe_star_path.iterrows():
        x, y, z = row[f'X_{(index+1):02}'], row[f'Y_{(index+1):02}'], row[f'Z_{(index+1):02}']
        spline.points[i].co = (x, y, z, 1)

    # Return the created curve object
    return curve_object

# Assuming you have a Pandas DataFrame called 'df' with 'X', 'Y', and 'Z' columns

star_path_curves = []

for index in range(number_of_stars):
    
    star_path_df = paths_df[[f'X_{(index+1):02}', f'Y_{(index+1):02}', f'Z_{(index+1):02}', f'DISPLAY_{(index+1):02}']].copy()
    star_path_curves.append( create_curve_from_dataframe(star_path_df, index) )
    

def new_GeometryNodes_group():
    """ Create Geometry Nodes Group """

    node_group = bpy.data.node_groups.new('GeometryNodes', 'GeometryNodeTree')
    
    inNode = node_group.nodes.new('NodeGroupInput')
    
    node_group.outputs.new('NodeSocketGeometry', 'Geometry')
    
    outNode = node_group.nodes.new('NodeGroupOutput')
    
    node_group.inputs.new('NodeSocketGeometry', 'Geometry')
    
    node_group.links.new(inNode.outputs['Geometry'], outNode.inputs['Geometry'])
    
    inNode.location = mathutils.Vector((-1.5*inNode.width, 0))
    outNode.location = mathutils.Vector((1.5*outNode.width, 0))
    
    return node_group

def add_circle_profile_and_material_to_curve(obj, radius, material):
    """ Setup Geometry Nodes for Object, and Add a Circular Profile to Object"""
    
    # Add Geometry Nodes modifier to the object
    modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
    
    if obj.modifiers[-1].node_group:
        node_group = obj.modifiers[-1].node_group    
    else:
        node_group = new_GeometryNodes_group()
        obj.modifiers[-1].node_group = node_group

    # Get nodes
    nodes = node_group.nodes

    # Create the necessary nodes
    group_in = nodes.get('Group Input')
    group_out = nodes.get('Group Output')
    node_circle = nodes.new(type='GeometryNodeCurvePrimitiveCircle')
    node_set_material = nodes.new(type='GeometryNodeSetMaterial')
    node_profile = nodes.new(type='GeometryNodeCurveToMesh')
    
    # Set node locations
    group_in.location = (-200, 200)
    node_circle.location = (-200, 0)
    node_profile.location = (0, 0)
    node_set_material.location = (200, 0)
    group_out.location = (400, 0)

    # Connect the nodes
    links = node_group.links
    links.new(group_in.outputs['Geometry'], node_profile.inputs['Curve'])
    links.new(node_circle.outputs['Curve'], node_profile.inputs['Profile Curve'])
    links.new(node_profile.outputs['Mesh'], node_set_material.inputs['Geometry'])
    links.new(node_set_material.outputs['Geometry'], group_out.inputs['Geometry'])
    
    # Set Radius
    node_circle.inputs[4].default_value = radius
    node_set_material.inputs['Material'].default_value = material
    
    # Set Material
    
# Create emission material for star_path curve

star_colors = [color_star_yellow, color_star_red, color_star_blue]
stars_materials_names = ['yellow_star_path_material', 'red_star_path_material', 'blue_star_path_material']
star_emission_strengths = [1.2, 1.2, 1.2]
star_materials = []

for index in range(number_of_stars):
    
    emission_color_star_path = star_colors[index]
    emission_strength_star_path = star_emission_strengths[index]
    star_materials.append( create_colored_emission_material(stars_materials_names[index], star_colors[index], star_emission_strengths[index]) )
    
for index in range(number_of_stars):

    # Add circular profile and emission material to star_path curve   
    circel_profile_radius = 0.0003
    add_circle_profile_and_material_to_curve(star_path_curves[index], circel_profile_radius, star_materials[index])

    # Apply emission material to curve object (this has no effect, but gives a place to edit the material)
    apply_material_to_object(star_path_curves[index], star_materials[index])
    
for index in range(number_of_stars):

    star_objects[index].location = paths_df[f'X_{(index+1):02}'][30], -paths_df[f'Y_{(index+1):02}'][30], paths_df[f'Z_{(index+1):02}'][30]

# ------------------------------------------------------------------------------
# Render Blender Scene
# ------------------------------------------------------------------------------

print_console('### Beginning Rendering')

# Set path for rendering files
base_path_renders = os.path.join(base_path, 'renders/')

# Set pattern string for rendered files
output_file_pattern_string = 'render%04d.jpg'

# Display number of stars being rendered
print_console(f'No. of Stars to Render: {len(star_objects)}')

# Set output format to PNG images
bpy.context.scene.render.image_settings.file_format='PNG'


def render_animation(dataset, objects, output_dir, output_file_pattern_string = 'render%d.png'):
    """ Render Animation """
      
    original_locations = []
    
    # Store current location of stars
    for object in objects:
        
        original_locations.append(object.location)
    
    # Loop through frames     
    for index_dataset in dataset.index: 
               
        # Loop through objects
        for index_objects, object in enumerate(objects):

            object.location = Vector([dataset[f'X_{(index_objects+1):02}'][index_dataset], -dataset[f'Y_{(index_objects+1):02}'][index_dataset], dataset[f'Z_{(index_objects+1):02}'][index_dataset]])
            
            # Hide star if below horizon    
            object.hide_render = not( dataset[f'DISPLAY_{(index_objects+1):02}'][index_dataset] )
            object.hide_viewport = not( dataset[f'DISPLAY_{(index_objects+1):02}'][index_dataset] )
        
        # Set filepath for renedered image
        bpy.context.scene.render.filepath = os.path.join(output_dir, (output_file_pattern_string % index_dataset))
            
        # Render animation frame
        print_console(f'Starting Render for Frame: {index_dataset}')
        bpy.ops.render.render(write_still = True)
        print_console(f'Render Complete for Frame: {index_dataset}')
    
    # Reset location of stars
    for index_object, object in enumerate(objects):
        
        object.location = original_locations[index_object]
        object.hide_render = False
        object.hide_viewport = False

render_df = paths_df[87:93].copy()

render_animation(render_df, star_objects, base_path_renders, output_file_pattern_string)

