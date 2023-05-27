import bpy

C = bpy.context
D = bpy.data
O = bpy.ops
S = C.scene

import math
import mathutils
import os

base_path = '/Users/cmcewing/Documents/blender_docs/'

def hex_to_blender_color(hex_color, alpha=1.0):
    # Remove the '#' symbol from the HEX color string
    hex_color = hex_color.lstrip('#')

    # Convert the HEX color to RGB values
    rgb = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    # Add an alpha value of 1.0 to the final color
    rgba = rgb + (alpha,)

    return rgba

slooh_gold = hex_to_blender_color('#978261')
#slooh_bright_gold = hex_to_blender_color('#E4C490')
slooh_bright_gold = hex_to_blender_color('#F3DE6D')
slooh_red = hex_to_blender_color('#DB6448')
slooh_light_blue = hex_to_blender_color('#00A2FF')
slooh_background_blue = hex_to_blender_color('#202E40')
slooh_light_background_blue = hex_to_blender_color('#40556E')

print(slooh_gold)


def create_text(text, font_path, location=(0, 0, 0), scale=(1, 1, 1), orientation=(0, 0, 0), name='Text', kerning=0.0):
    O.object.select_all(action='DESELECT')  # Deselect all objects
    O.object.text_add(location=location)  # Create a new text object
    text_object = C.object
    text_object.data.body = text  # Set the text content

    # Set the text object's scale
    text_object.scale = scale
    
    # Set the font of the text object
    text_object.data.font = D.fonts.load(font_path)

    # Set the text object's orientation
    euler_rotation = mathutils.Euler(orientation, 'XYZ')
    text_object.rotation_euler = euler_rotation
    

    # Set the kerning of the text object
    for char in text_object.data.body_format:
        char.kerning = kerning

    # Set the origin of the text object to the center of the text
    O.object.origin_set(type='ORIGIN_CENTER_OF_MASS')

    # Set the location of the text object
    text_object.location = location

    # Set the name of the text object
    text_object.name = "Text_" + name
        
    return text_object

scale = 0.05
text = 'SOUTH'
name = 'South'
text_objects = {}
kerning = 1
font_name = 'Ubuntu-Regular.ttf'
font_path = os.path.join(base_path, font_name)

# Example usage
text_objects[name] = create_text(text, font_path, location=(1.3, 0, 0), scale=(scale, scale, scale), orientation=(1.43117, 0, 1.5708), name=name, kerning=kerning)

def create_colored_material(name, color):
    # Create a new material
    material = D.materials.new(name)
    material.use_nodes = True

    # Clear default nodes
    material.node_tree.nodes.clear()

    # Create a principled BSDF node
    principled_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    principled_bsdf.location = (0, 0)

    # Set the base color of the material
    principled_bsdf.inputs['Base Color'].default_value = color

    # Create an output node
    material_output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    material_output.location = (400, 0)

    # Link the nodes
    material.node_tree.links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

    return material

def apply_material_to_object(obj, material):
    if obj.data.materials:
        # Assign the material to the first slot
        obj.data.materials[0] = material
    else:
        # Create a new material slot and assign the material
        obj.data.materials.append(material)


material = create_colored_material("Slooh_Gold_Material", slooh_bright_gold)
apply_material_to_object(text_objects['South'], material)



def set_camera_location_rotation(location, rotation):
    # Get the active camera
    camera = bpy.context.scene.camera

    if camera is not None:
        # Set the camera's location
        camera.location = location

        # Set the camera's rotation
        camera.rotation_euler = [math.radians(angle) for angle in rotation]

# Example usage
location = (3.8, 0.0, 0.85)
rotation = (82.0, 0.0, 90.0)
set_camera_location_rotation(location, rotation)



#cam = bpy.data.objects['Camera']
#up = cam.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 1.0, 0.0))
#cam_direction = cam.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 0.0, -1.0))



def rotate_camera_location_and_rotation_z_axis(angle):
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

# Example usage
rotate_camera_location_and_rotation_z_axis(180)  # Rotate camera's location and rotation by 45 degrees around the Z-axis


def rotate_object_about_z_axis(object, angle):

    if object is not None:
        # Get the current camera location
        location = object.location

        # Create a rotation matrix to rotate around the Z-axis
        rotation_matrix = mathutils.Matrix.Rotation(math.radians(angle), 4, 'Z')

        # Rotate the location around the Z-axis
        rotated_location = rotation_matrix @ location

        # Set the new camera location
        object.location = rotated_location

        # Rotate the camera's rotation around its own Z-axis
        object.rotation_euler.z += math.radians(angle)
        
rotate_object_about_z_axis(text_objects['South'], 180.0)

import bpy
import pandas as pd
import bmesh
import numpy as np

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

paths_df = pd.DataFrame(paths_vecs, columns=['X', 'Y', 'Z'])

def create_curve_from_dataframe(dataframe):
    # Create a new curve object
    curve_data = bpy.data.curves.new(name="Curve", type="CURVE")
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    curve_object = bpy.data.objects.new(name="CurveObject", object_data=curve_data)

    # Link the curve object to the scene
    bpy.context.collection.objects.link(curve_object)

    # Create a new spline for the curve
    spline = curve_data.splines.new(type='NURBS')

    # Set the coordinates from the dataframe
    spline.points.add(len(dataframe))
    for i, row in dataframe.iterrows():
        x, y, z = row['X'], row['Y'], row['Z']
        spline.points[i].co = (x, y, z, 1)

    # Return the created curve object
    return curve_object

# Assuming you have a Pandas DataFrame called 'df' with 'X', 'Y', and 'Z' columns
curve_object = create_curve_from_dataframe(paths_df)

#    mesh = bpy.data.meshes.new_from_object(obj)
#    new_obj = bpy.data.objects.new(obj.name, mesh)
#    new_obj.matrix_world = obj.matrix_world
#    bpy.context.collection.objects.link(new_obj)
    
#    bpy.ops.object.convert(target='MESH')
    
    
    
#import bpy-building-blocks

