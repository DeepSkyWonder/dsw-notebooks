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
from bpy import context, data, ops
from math import sin, cos, radians, pi, atan, tan
from mathutils import Vector as Vector

# Store the Sceen Context
scene = context.scene

# Configure Paths
star_path_data = "/content/drive/MyDrive/blender/star_path.csv" # Substitute with your local path
slooh_blue_texture = "/Users/cmcewing/Documents/blender_docs/slooh_blue_02.png"


# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

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
        
        
    scene.render.resolution_x = 1280
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

def vertex_circle(segments, z):
    """ Return a ring of vertices """
    verts = []

    for i in range(segments):
        angle = (math.pi*2) * i / segments
        verts.append((math.cos(angle), math.sin(angle), z))

    return verts


def face(segments, i, row):
    """ Return a face on a cylinder """

    if i == segments - 1:
        ring_start = segments * row
        base = segments * (row + 1)

        return (base - 1, ring_start, base, (base + segments) - 1)

    else:
        base = (segments * row) + i
        return (base, base + 1, base + segments + 1, base + segments)


def bottom_cap(verts, faces, segments, cap='NGON'):
    """ Build bottom caps as triangle fans """

    if cap == 'TRI':
        verts.append((0, 0, 0))
        center_vert = len(verts) - 1

        [faces.append((i, i+1, center_vert)) for i in range(segments - 1)]
        faces.append((segments - 1, 0, center_vert))

    elif cap == 'NGON':
        faces.append([i for i in range(segments)])

    else:
        print('[!] Passed wrong type to bottom cap')


def top_cap(verts, faces, segments, rows, cap='NGON'):
    """ Build top caps as triangle fans """

    if cap == 'TRI':
        verts.append((0, 0, rows - 1))
        center_vert = len(verts) - 1
        base = segments * (rows - 1)

        [faces.append((base+i, base+i+1, center_vert))
                       for i in range(segments - 1)]

        faces.append((segments * rows - 1, base, center_vert))

    elif cap == 'NGON':
        base = (rows - 1) * segments
        faces.append([i + base for i in range(segments)])

    else:
        print('[!] Passed wrong type to top cap')
        
def apply_subdivision(object):
    """ Apply subdivision to an object """
        
    # set active object
    current_object = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = object    
    
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].quality = 3
    bpy.context.object.modifiers["Subdivision"].levels = 3
    bpy.context.object.modifiers["Subdivision"].render_levels = 3
    bpy.context.object.modifiers["Subdivision"].subdivision_type = 'CATMULL_CLARK'
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

def make_cylinder(name, segments=64, rows=4, cap=None):
    """ Make a cylinder """

    data = { 'verts': [], 'edges': [], 'faces': [] }

    for z in range(rows):
        data['verts'].extend(vertex_circle(segments, z))

    for i in range(segments):
        for row in range(0, rows - 1):
            data['faces'].append(face(segments, i, row))

    if cap:
        bottom_cap(data['verts'], data['faces'], segments, cap)
        top_cap(data['verts'], data['faces'], segments, rows, cap)


    scene = bpy.context.scene
    obj = object_from_data(data, name, scene)
    recalculate_normals(obj.data)
    set_smooth(obj)

    bevel = obj.modifiers.new('Bevel', 'BEVEL')
    
    bevel.limit_method = 'ANGLE'
    bevel.loop_slide=True
    bevel.material=-1
    bevel.profile=0.5
    #bevel.offset=0.0
    bevel.offset_type='OFFSET'
    #bevel.vertex_only=False
    #bevel.clamp_overlap=False
    bevel.segments = 3
    bevel.width = 0.02
    bevel.harden_normals = True

    obj.modifiers.new('Edge Split', 'EDGE_SPLIT')

    return obj

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
    ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    apply_subdivision(context.view_layer.objects.active)
    
    objects = data.objects
    sphere = objects['Sphere'] 

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
    sphere.dimensions = 2.0*radius, 2.0*radius, 1.0*radius
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
# Main Code
# ------------------------------------------------------------------------------

# Configure Renderer
configure_renderer()

# Clear Scene of Objects
clear_scene()

# Set Scene Background Colour
color_world_background = 202E40
color_world_background = hex_to_blender_color('#202E40') #(0.0144438, 0.0273209, 0.0512695, 1)
set_scene_background_color(color_world_background)

# Create Cylinder
cylinder = make_cylinder('Cylinder', 32, 4, 'TRI')

# Size and locate Cylinder
cylinder.dimensions = 2., 2., 1.
cylinder.location[2] = -1. 
cylinder.data.use_auto_smooth = True

# Create Sphere
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, radius=1, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
sphere = bpy.context.view_layer.objects.active

#recalculate_normals(sphere.data)
#set_smooth(sphere)
#sphere.data.use_auto_smooth = True

# Combine (Union) Cylinder to Sphere to Create a Domed Cylinder
bool_obs = sphere.modifiers.new(type="BOOLEAN", name="bool obs")
bool_obs.object = cylinder
bool_obs.operation = 'UNION'

bpy.context.view_layer.objects.active = sphere
bpy.ops.object.modifier_apply(modifier='bool obs')

# Remove Cylinder
object_to_delete = cylinder
bpy.data.objects.remove(object_to_delete, do_unlink=True)

# Set Combined object as active object
bpy.context.view_layer.objects.active = sphere

# Name Object Observatory
sphere.name = "Observatory"
observatory = sphere

# Recalute Normals, Smooth, Auto Smooth
recalculate_normals(observatory.data)
set_smooth(observatory)
observatory.data.use_auto_smooth = True

# Apply Subdivision
apply_subdivision(observatory)  

# Add Material
color_emission = hex_to_blender_color('#FFA02B')
color_bsdf = hex_to_blender_color('#F46A25')
emission_strenght = 1.0
mix_frac = 0.925
obs_material = create_colored_material('obs_material', color_bsdf, color_emission, emission_strenght, mix_frac)

# Apply Material
apply_material_to_object(observatory, obs_material)

# Set origin, location, and scale of observatory (move up in z-dir by 1.0 units)
observatory.location = 0.0, 0.0, 1.0        

# Move observatory origin to 0, 0, 0
set_object_origin_to_scene_origin(observatory)

# Scale observatory and move to obs origin to 0, 0, 0
obs_scale = 0.1
observatory.scale = obs_scale, obs_scale, obs_scale
observatory.location = 0.0, 0.0, 0.0

# Add camera and set postion to focus on full earth view
bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(3.8, 0.0, 0.85), rotation=(radians(82.0), radians(0.0), radians(90.0)), scale=(1, 1, 1))

# Set camera rotation and location
location = (3.8, 0.0, 0.85)
rotation = (82.0, 0.0, 90.0)
set_camera_location_rotation(location, rotation)

# Rotate camera about z-axis while keeping it oriented towards our scene
rotate_camera_location_and_rotation_z_axis(180)  # Rotate camera's location and rotation by 45 degrees around the Z-axis

# Create Celestial Sphere - Hemisphere
hemisphere = create_hemisphere(radius=1.0)

# Create Transparent Material
hemisphere_material = create_transparent_material('Hemisphere Material', 0.382, slooh_blue_texture, mix_frac=0.5)

# Apply Transparent Material
apply_material_to_object(hemisphere, hemisphere_material)

# Define how shadows are handled
configure_material_shadows(hemisphere_material)








    
