""" Create Animation of Stars Transiting """

# Import Libraries
import re
import os
import bpy
import bmesh
import numpy as np
import pandas as pd
from bpy import context, data, ops
from math import sin, cos, radians, pi, atan, tan
from mathutils import Vector as Vector

# Store the Sceen Context
scene = context.scene

# Configure Paths
star_path_data = "/content/drive/MyDrive/blender/star_path.csv" # Substitute with your local path
slooh_blue_texture = "/Users/cmcewing/Documents/blender_docs/slooh_blue_02.png"

# Set-up the Redering Engine
def configure_renderer(scene=scene):
    
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


# Delete all existing items in scene.
def clear_scene(ops=ops):
    
    ops.object.select_all(action='SELECT')
    ops.object.delete(use_global=False)
    
def add_subdivision(object):
    
    context.view_layer.objects.active = object    
    ops.object.modifier_add(type='SUBSURF')
    context.object.modifiers["Subdivision"].quality = 6
    context.object.modifiers["Subdivision"].levels = 6
    context.object.modifiers["Subdivision"].render_levels = 6
    ops.object.modifier_apply(modifier="Subdivision")
    
# Create Smoothed Hemisphere
def create_hemisphere(radius=1.0):

    # Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
    ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    add_subdivision(context.view_layer.objects.active)
    
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

    return sphere

# Create Smoothed Cylinder
def create_cylinder(radius=1.0, depth=1.0):

    # Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
    ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=depth, enter_editmode=False, align='WORLD', location=(0, 0, -0.5*depth), scale=(1, 1, 1))

    objects = data.objects
    cylinder = objects['Cylinder'] 

    # Correct dimensions of hemisphere
    cylinder.dimensions = 2.0*radius, 2.0*radius, 1.0*depth
    cylinder.name = "Cylinder (Smooth)"

    # Add sharp edges to bases of cylinder
    cylinder_mesh = cylinder.data

    bm = bmesh.new()
    bm.from_mesh(cylinder_mesh)

    EPSILON = 1.0e-5
    for vert in bm.verts:
        if -EPSILON <= vert.co.z <= EPSILON:
            vert.select = True
        
    for vert in bm.verts:
        if -EPSILON <= (vert.co.z + 1.0*depth) <= EPSILON:
            vert.select = True

    # Add sharp state for all edges that are near the z-axis
    for edge in bm.edges:
        if edge.verts[0].select and edge.verts[1].select:
            edge.smooth = False

    bm.to_mesh(cylinder_mesh)
    bm.free()

    return cylinder

# Setup scene

configure_renderer()
clear_scene()

hemisphere = create_hemisphere(radius=1.0)
cylinder = create_cylinder(radius=1.0, depth=1.0)






