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

# Set-up the Redering Engine
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
        
        
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 1280
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.feature_set = 'EXPERIMENTAL'
bpy.context.scene.cycles.adaptive_threshold = 0.05
bpy.context.scene.cycles.max_subdivisions = 6



star_path_data = "/content/drive/MyDrive/blender/star_path.csv" # Substitute with your local path
slooh_blue_texture = "/Users/cmcewing/Documents/blender_docs/slooh_blue_02.png"

# Delete all existing items in scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Add a unit cube, translated in -1 in the z-direction
bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, -1), scale=(1, 1, 1))

# Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
bpy.ops.object.modifier_add(type='SUBSURF')
bpy.context.object.modifiers["Subdivision"].quality = 6
bpy.context.object.modifiers["Subdivision"].levels = 6
bpy.context.object.modifiers["Subdivision"].render_levels = 6
bpy.ops.object.modifier_apply(modifier="Subdivision")

# Subtract Cube from Sphere to Create a Hemisphere
objects = bpy.data.objects

cube = objects['Cube']
sphere = objects['Sphere'] 

bool_one = sphere.modifiers.new(type="BOOLEAN", name="bool 1")
bool_one.object = cube
bool_one.operation = 'DIFFERENCE'

bpy.context.view_layer.objects.active = sphere
bpy.ops.object.modifier_apply(modifier='bool 1')

object_to_delete = bpy.data.objects['Cube']
bpy.data.objects.remove(object_to_delete, do_unlink=True)

# Correct dimensions of hemisphere
bpy.context.view_layer.objects.active = sphere
bpy.context.object.dimensions = 2.0, 2.0, 1.0

# Add sharp edges to base of hemisphere
ob = context.view_layer.objects.active
me = ob.data

bm = bmesh.new()
bm.from_mesh(me)

EPSILON = 1.0e-5
for vert in bm.verts:
    if -EPSILON <= vert.co.z <= EPSILON:
        vert.select = True

# Add sharp state for all edges that are near the z-axis
for edge in bm.edges:
    if edge.verts[0].select and edge.verts[1].select:
        edge.smooth = False

bm.to_mesh(me)
bm.free()

# Add torus to act at line around base of hemisphere
bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), major_segments=100, minor_segments=50, major_radius=1, minor_radius=0.002, abso_major_rad=1.25, abso_minor_rad=0.75)
bpy.context.active_object.name = "Torus"
objects = bpy.data.objects
torus = objects['Torus'] 
bpy.context.view_layer.objects.active = torus

# Create material for torus
material = bpy.data.materials.new(name="TorusMaterial")
# Use nodes
material.use_nodes = True

# Add Principled BSDF node and connect to Material Output node
bsdf = material.node_tree.nodes["Principled BSDF"]
output = material.node_tree.nodes["Material Output"]
#bsdf.inputs['Base Color'].default_value = (0.233, 0.437, 0.779, 1.0)
bsdf.inputs['Base Color'].default_value = (0.0559, 0.10025, 0.172, 1)

torus.data.materials.append(material)

# Store Torus for later
bpy.context.active_object.name = "Torus"
objects = bpy.data.objects
torus = objects['Torus'] 

# Add camera and set postion to focus on full earth view
bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(3.8, 0.0, 0.85), rotation=(radians(82.0), radians(0.0), radians(90.0)), scale=(1, 1, 1))

# Set background color of scene
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.0144438, 0.0273209, 0.0512695, 1)

# Create a material for the hemisphere
bpy.context.view_layer.objects.active = sphere
bpy.ops.object.shade_smooth
material = bpy.data.materials.new(name="HemisphereMaterial")
# Use nodes
material.use_nodes = True

# Add Principled BSDF node and connect to Material Output node
bsdf = material.node_tree.nodes["Principled BSDF"]
output = material.node_tree.nodes["Material Output"]

bpy.context.view_layer.objects.active = sphere
ob = context.view_layer.objects.active

ob.data.materials.append(material)

bpy.context.object.active_material.blend_method = 'BLEND'
bpy.context.object.active_material.shadow_method = 'CLIP'
bpy.context.object.active_material.cycles.use_transparent_shadow = False


# Configure BSDF
#bsdf.inputs['Base Color'].default_value = (0.8, 0.05, 0.05, 1.0)
bsdf.inputs['Alpha'].default_value = 0.382 
#bsdf.inputs['Roughness'].default_value = 0.2
#bsdf.inputs['Specular'].default_value = 0.5
#bsdf.inputs['Transmission'].default_value = 0.5

# Make hemisphere transparent using a mix-shader and a BSDF transparency node
mix = material.node_tree.nodes.new('ShaderNodeMixShader')
trans_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfTransparent')
texture_image = material.node_tree.nodes.new('ShaderNodeTexImage')
texture_image.image = bpy.data.images.load(slooh_blue_texture)

material.node_tree.links.new(mix.inputs[2], trans_bsdf.outputs['BSDF'])
material.node_tree.links.new(mix.inputs[1], bsdf.outputs['BSDF'])
material.node_tree.links.new(output.inputs['Surface'], mix.outputs['Shader'])
material.node_tree.links.new(bsdf.inputs['Base Color'], texture_image.outputs['Color'])

# Add the Sun. Postion and Rotiation set.    
bpy.ops.object.light_add(type='SUN', radius=1, align='WORLD', location=(0, 0, -1), rotation=(0.0, 0.0, 0.0), scale=(1, 1, 1))
# Sun intensity
#bpy.context.object.data.energy = 0.4
bpy.context.object.data.energy = 5.22
# Sun angle
bpy.context.object.data.angle = 0


#bpy.ops.mesh.primitive_circle_add(vertices=100, radius=1, fill_type='TRIFAN', enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
bpy.ops.mesh.primitive_circle_add(vertices=100, radius=1, fill_type='NGON', enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
bpy.ops.object.shade_smooth
objects = bpy.data.objects
circle = objects['Circle'] 
bpy.context.view_layer.objects.active = circle

# Create material for torus
material = bpy.data.materials.new(name="CircleMaterial")
# Use nodes
material.use_nodes = True

# Add Principled BSDF node and connect to Material Output node
bsdf = material.node_tree.nodes["Principled BSDF"]
output = material.node_tree.nodes["Material Output"]
bsdf.inputs['Base Color'].default_value = (0.0101472, 0.410078, 0.8, 1)
bsdf.inputs['Alpha'].default_value = 0.259091 

circle.data.materials.append(material)


# Create Stars

# Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False, align='WORLD', location=(1, 0, 0), scale=(0.015, 0.015, 0.015))
bpy.context.active_object.name = "Star_01"
objects = bpy.data.objects
star_01 = objects['Star_01'] 
bpy.context.view_layer.objects.active = star_01

# Create material for torus
material = bpy.data.materials.new(name="Stare 01 Material")
material.use_nodes = True

# Add Emission node and connect to Material Output node (Remove default BSDF node)
bsdf = material.node_tree.nodes["Principled BSDF"]
output = material.node_tree.nodes["Material Output"]

nodes = material.node_tree.nodes
nodes.remove(bsdf)

emission = material.node_tree.nodes.new('ShaderNodeEmission')

material.node_tree.links.new(output.inputs['Surface'], emission.outputs['Emission'])

emission.inputs['Color'].default_value = (0.0105395, 0.10343, 1, 1)
emission.inputs['Strength'].default_value = 28.3 

star_01.data.materials.append(material)

# Set-up glare in compositor
bpy.context.scene.use_nodes = True

composite_tree = bpy.context.scene.node_tree
composite_tree_links = composite_tree.links

render_node = composite_tree.nodes['Render Layers']
glare_node = composite_tree.nodes.new('CompositorNodeGlare')
output_node = composite_tree.nodes['Composite']
viewer_node = composite_tree.nodes.new('CompositorNodeViewer')

composite_tree_links.new(render_node.outputs['Image'], glare_node.inputs['Image'])
composite_tree_links.new(glare_node.outputs['Image'], output_node.inputs['Image'])
composite_tree_links.new(glare_node.outputs['Image'], viewer_node.inputs['Image'])

glare_node.glare_type = 'FOG_GLOW'
glare_node.quality = 'HIGH'
glare_node.size = 9

# Make Camera Active
objects = bpy.data.objects
camera = objects['Camera']
scene.camera = camera

# Create a test dataset
data = [[1, 1, 0, 0], [2, 0, 1, 0], [3, 0, 0, 1], [4, 1, 0, 0]]
  
# Create the pandas DataFrame
paths_df = pd.DataFrame(data, columns=['Name', 'X', 'Y', 'Z'])

# Rendering Setup

#output_dir = '/content/drive/MyDrive/blender/'
output_dir = '/Users/cmcewing/Documents/blender_docs/renders/'

output_file_pattern_string = 'render%d.jpg'
step = 1

#bpy.context.scene.render.image_settings.file_format='PNG'
#bpy.context.scene.render.filepath = os.path.join(output_dir, (output_file_pattern_string % step))
#bpy.ops.render.render(write_still = True)

bpy.context.view_layer.objects.active = star_01

def rotate_and_render(dataset, output_dir, output_file_pattern_string = 'render%d.jpg', subject = bpy.context.object):
  original_location = subject.location
  for step in range(len(dataset)):
    subject.location = Vector([dataset['X'][step], dataset['Y'][step], dataset['Z'][step]])
    bpy.context.scene.render.filepath = os.path.join(output_dir, (output_file_pattern_string % step))
    bpy.ops.render.render(write_still = True)
  subject.location = original_rotation

rotate_and_render(paths_df, output_dir, output_file_pattern_string)