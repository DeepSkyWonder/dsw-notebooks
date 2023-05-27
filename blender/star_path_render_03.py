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
#data = [[1, 1, 0, 0], [2, 0, 1, 0], [3, 0, 0, 1], [4, 1, 0, 0]]
  
# Create the pandas DataFrame
#paths_df = pd.DataFrame(data, columns=['Name', 'X', 'Y', 'Z'])

paths_vecs = np.array([[-7.44269691e-01,  6.67879197e-01,  7.11177373e-05],
       [-7.50202309e-01,  6.61127402e-01,  1.03466770e-02],
       [-7.56073708e-01,  6.54164837e-01,  2.05161995e-02],
       [-7.61882015e-01,  6.46993722e-01,  3.05764432e-02],
       [-7.67625379e-01,  6.39616344e-01,  4.05242009e-02],
       [-7.73301969e-01,  6.32035053e-01,  5.03563010e-02],
       [-7.78909974e-01,  6.24252268e-01,  6.00696092e-02],
       [-7.84447608e-01,  6.16270469e-01,  6.96610288e-02],
       [-7.89913105e-01,  6.08092201e-01,  7.91275019e-02],
       [-7.95304722e-01,  5.99720071e-01,  8.84660107e-02],
       [-8.00620741e-01,  5.91156748e-01,  9.76735780e-02],
       [-8.05859467e-01,  5.82404963e-01,  1.06747268e-01],
       [-8.11019229e-01,  5.73467505e-01,  1.15684189e-01],
       [-8.16098382e-01,  5.64347224e-01,  1.24481491e-01],
       [-8.21095308e-01,  5.55047026e-01,  1.33136369e-01],
       [-8.26008414e-01,  5.45569879e-01,  1.41646065e-01],
       [-8.30836132e-01,  5.35918801e-01,  1.50007866e-01],
       [-8.35576925e-01,  5.26096871e-01,  1.58219105e-01],
       [-8.40229280e-01,  5.16107219e-01,  1.66277164e-01],
       [-8.44791714e-01,  5.05953031e-01,  1.74179476e-01],
       [-8.49262773e-01,  4.95637543e-01,  1.81923521e-01],
       [-8.53641032e-01,  4.85164045e-01,  1.89506829e-01],
       [-8.57925094e-01,  4.74535874e-01,  1.96926983e-01],
       [-8.62113594e-01,  4.63756420e-01,  2.04181618e-01],
       [-8.66205197e-01,  4.52829119e-01,  2.11268421e-01],
       [-8.70198598e-01,  4.41757454e-01,  2.18185133e-01],
       [-8.74092524e-01,  4.30544956e-01,  2.24929547e-01],
       [-8.77885733e-01,  4.19195198e-01,  2.31499516e-01],
       [-8.81577017e-01,  4.07711800e-01,  2.37892942e-01],
       [-8.85165198e-01,  3.96098422e-01,  2.44107790e-01],
       [-8.88649133e-01,  3.84358766e-01,  2.50142076e-01],
       [-8.92027710e-01,  3.72496576e-01,  2.55993878e-01],
       [-8.95299854e-01,  3.60515632e-01,  2.61661329e-01],
       [-8.98464520e-01,  3.48419755e-01,  2.67142624e-01],
       [-9.01520699e-01,  3.36212801e-01,  2.72436014e-01],
       [-9.04467418e-01,  3.23898660e-01,  2.77539812e-01],
       [-9.07303737e-01,  3.11481260e-01,  2.82452391e-01],
       [-9.10028752e-01,  2.98964559e-01,  2.87172184e-01],
       [-9.12641593e-01,  2.86352547e-01,  2.91697688e-01],
       [-9.15141429e-01,  2.73649245e-01,  2.96027458e-01],
       [-9.17527461e-01,  2.60858703e-01,  3.00160116e-01],
       [-9.19798930e-01,  2.47984998e-01,  3.04094342e-01],
       [-9.21955111e-01,  2.35032235e-01,  3.07828884e-01],
       [-9.23995317e-01,  2.22004543e-01,  3.11362551e-01],
       [-9.25918896e-01,  2.08906075e-01,  3.14694215e-01],
       [-9.27725237e-01,  1.95741008e-01,  3.17822815e-01],
       [-9.29413764e-01,  1.82513538e-01,  3.20747353e-01],
       [-9.30983937e-01,  1.69227882e-01,  3.23466897e-01],
       [-9.32435256e-01,  1.55888275e-01,  3.25980580e-01],
       [-9.33767259e-01,  1.42498972e-01,  3.28287601e-01],
       [-9.34979521e-01,  1.29064239e-01,  3.30387224e-01],
       [-9.36071655e-01,  1.15588361e-01,  3.32278780e-01],
       [-9.37043314e-01,  1.02075632e-01,  3.33961665e-01],
       [-9.37894187e-01,  8.85303623e-02,  3.35435343e-01],
       [-9.38624003e-01,  7.49568687e-02,  3.36699345e-01],
       [-9.39232530e-01,  6.13594790e-02,  3.37753267e-01],
       [-9.39719573e-01,  4.77425279e-02,  3.38596773e-01],
       [-9.40084978e-01,  3.41103566e-02,  3.39229594e-01],
       [-9.40328627e-01,  2.04673112e-02,  3.39651529e-01],
       [-9.40450444e-01,  6.81774108e-03,  3.39862444e-01],
       [-9.40450389e-01, -6.83400220e-03,  3.39862270e-01],
       [-9.40328462e-01, -2.04835664e-02,  3.39651008e-01],
       [-9.40084702e-01, -3.41266000e-02,  3.39228725e-01],
       [-9.39719187e-01, -4.77587534e-02,  3.38595556e-01],
       [-9.39232034e-01, -6.13756808e-02,  3.37751703e-01],
       [-9.38623397e-01, -7.49730409e-02,  3.36697435e-01],
       [-9.37893470e-01, -8.85464990e-02,  3.35433087e-01],
       [-9.37042487e-01, -1.02091728e-01,  3.33959063e-01],
       [-9.36070719e-01, -1.15604408e-01,  3.32275833e-01],
       [-9.34978476e-01, -1.29080234e-01,  3.30383933e-01],
       [-9.33766105e-01, -1.42514907e-01,  3.28283967e-01],
       [-9.32433993e-01, -1.55904146e-01,  3.25976604e-01],
       [-9.30982565e-01, -1.69243681e-01,  3.23462580e-01],
       [-9.29412283e-01, -1.82529260e-01,  3.20742695e-01],
       [-9.27723649e-01, -1.95756648e-01,  3.17817818e-01],
       [-9.25917201e-01, -2.08921627e-01,  3.14688880e-01],
       [-9.23993513e-01, -2.22020001e-01,  3.11356880e-01],
       [-9.21953201e-01, -2.35047593e-01,  3.07822879e-01],
       [-9.19796914e-01, -2.48000250e-01,  3.04088003e-01],
       [-9.17525339e-01, -2.60873843e-01,  3.00153445e-01],
       [-9.15139201e-01, -2.73664268e-01,  2.96020458e-01],
       [-9.12639261e-01, -2.86367447e-01,  2.91690359e-01],
       [-9.10026315e-01, -2.98979330e-01,  2.87164529e-01],
       [-9.07301196e-01, -3.11495897e-01,  2.82444412e-01],
       [-9.04464774e-01, -3.23913157e-01,  2.77531511e-01],
       [-9.01517952e-01, -3.36227151e-01,  2.72427393e-01],
       [-8.98461671e-01, -3.48433955e-01,  2.67133685e-01],
       [-8.95296903e-01, -3.60529675e-01,  2.61652075e-01],
       [-8.92024659e-01, -3.72510456e-01,  2.55984311e-01],
       [-8.88645982e-01, -3.84372479e-01,  2.50132199e-01],
       [-8.85161948e-01, -3.96111961e-01,  2.44097605e-01],
       [-8.81573668e-01, -4.07725160e-01,  2.37882453e-01],
       [-8.77882287e-01, -4.19208374e-01,  2.31488724e-01],
       [-8.74088981e-01, -4.30557942e-01,  2.24918456e-01],
       [-8.70194959e-01, -4.41770246e-01,  2.18173745e-01],
       [-8.66201463e-01, -4.52841710e-01,  2.11256741e-01],
       [-8.62109767e-01, -4.63768806e-01,  2.04169648e-01],
       [-8.57921173e-01, -4.74548049e-01,  1.96914726e-01],
       [-8.53637019e-01, -4.85176004e-01,  1.89494288e-01],
       [-8.49258669e-01, -4.95649281e-01,  1.81910700e-01],
       [-8.44787520e-01, -5.05964543e-01,  1.74166379e-01],
       [-8.40224997e-01, -5.16118500e-01,  1.66263794e-01],
       [-8.35572554e-01, -5.26107915e-01,  1.58205465e-01],
       [-8.30831674e-01, -5.35929605e-01,  1.49993960e-01],
       [-8.26003870e-01, -5.45580436e-01,  1.41631898e-01],
       [-8.21090680e-01, -5.55057333e-01,  1.33121944e-01],
       [-8.16093671e-01, -5.64357275e-01,  1.24466812e-01],
       [-8.11014435e-01, -5.73477296e-01,  1.15669260e-01],
       [-8.05854592e-01, -5.82414489e-01,  1.06732094e-01],
       [-8.00615787e-01, -5.91166004e-01,  9.76581622e-02],
       [-7.95299690e-01, -5.99729053e-01,  8.84503579e-02],
       [-7.89907996e-01, -6.08100904e-01,  7.91116165e-02],
       [-7.84442424e-01, -6.16278889e-01,  6.96449153e-02],
       [-7.78904716e-01, -6.24260401e-01,  6.00532722e-02],
       [-7.73296638e-01, -6.32042894e-01,  5.03397451e-02],
       [-7.67619977e-01, -6.39623889e-01,  4.05074309e-02],
       [-7.61876543e-01, -6.47000968e-01,  3.05594639e-02],
       [-7.56068168e-01, -6.54171778e-01,  2.04990158e-02],
       [-7.50196703e-01, -6.61134035e-01,  1.03292938e-02],
       [-7.44264020e-01, -6.67885519e-01,  5.35401313e-05]])

paths_df = pd.DataFrame(paths_vecs, columns=['X', 'Y', 'Z'])[0:3]

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
  subject.location = original_location

rotate_and_render(paths_df, output_dir, output_file_pattern_string)