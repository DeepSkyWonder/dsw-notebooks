""" Create 3d Earth map """
import bpy
import bmesh
import numpy as np
#import pandas as pd
from bpy import context, data, ops
from math import sin, cos, radians, pi, atan, tan

scene = context.scene


EARTH_IMAGE = "/content/drive/MyDrive/blender/8081_earthmap4k.jpg" # Substitute with your local path
EARTH_BUMP = "/content/drive/MyDrive/blender/8081_earthbump4k.jpg" # Substitute with your local path

# Delete all existing items in scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Add a sphere, set quality to highest and apply shade smooth. Scale 'semi' adjusted to coordinate conversion and raised 100m above. 
bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False, align='WORLD', location=(0, 0, 100), scale=(202, 202, 202))
bpy.ops.object.modifier_add(type='SUBSURF')
bpy.context.object.modifiers["Subdivision"].quality = 6
bpy.context.object.modifiers["Subdivision"].levels = 6
bpy.context.object.modifiers["Subdivision"].render_levels = 6
bpy.ops.object.modifier_apply(modifier="Subdivision")
bpy.ops.object.shade_smooth()

bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'

bpy.context.scene.render.resolution_x = 2160
bpy.context.scene.render.resolution_y = 1440

# Create a new material
material = bpy.data.materials.new(name="EarthMaterial")
# Use nodes
material.use_nodes = True
# Add Principled BSDF
bsdf = material.node_tree.nodes["Principled BSDF"]
texImage = material.node_tree.nodes.new('ShaderNodeTexImage')
# Load image of Earth
texImage.image = bpy.data.images.load(EARTH_IMAGE)
# Set node links for color
material.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])


bsdf = material.node_tree.nodes["Material Output"]
texImage = material.node_tree.nodes.new('ShaderNodeTexImage')
# Load image of Earth bump version
texImage.image = bpy.data.images.load(EARTH_BUMP)
# Set colorspace to Non-Color
texImage.image.colorspace_settings.name = 'Non-Color'
# Add the Bump node
bump_shader = material.node_tree.nodes.new('ShaderNodeBump')
# Set node links for displacement
material.node_tree.links.new(bsdf.inputs['Displacement'], bump_shader.outputs['Normal'])
# Set node links for color from bump node
material.node_tree.links.new(bump_shader.inputs['Normal'], texImage.outputs['Color'])
# Activate the sphere object
ob = context.view_layer.objects.active
# Set Metallic to 1
bpy.data.materials["EarthMaterial"].node_tree.nodes["Principled BSDF"].inputs[4].default_value = 1
# Assign it to object
ob.data.materials.append(material)

bpy.data.materials["EarthMaterial"].node_tree.nodes["Bump"].inputs[0].default_value = 5

# Add the Sun. Postion and Rotiation set.    
bpy.ops.object.light_add(type='SUN', radius=1, align='WORLD', location=(0, 300, 250), rotation=(1.0472, 1.5708, 2.61799), scale=(1, 1, 1))
# Sun intensity
bpy.context.object.data.energy = 8
# Sun angle
bpy.context.object.data.angle = 0

# Add camera and set postion to focus on full earth view
bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(1100.0, 140.0, 60.0), rotation=(1.6109, -0.0422, 1.7157), scale=(1, 1, 1))

scene.camera = context.object

bpy.ops.file.autopack_toggle()
bpy.ops.wm.save_as_mainfile(filepath='/content/drive/MyDrive/blender/earth.blend')
