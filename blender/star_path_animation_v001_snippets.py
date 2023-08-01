import bpy
import bmesh
import math


# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

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
    bpy.data.materials["Material.002"].node_tree.nodes["Mix Shader"].inputs[0].default_value
    shader_mix.location = (0, 0)    

    # Create an output node
    shader_output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader_output.location = (300, 0)

    # Link the nodes
    material.node_tree.links.new(shader_emission.outputs['Emission'], shader_mix.inputs[1])
    material.node_tree.links.new(shader_bsdf.outputs['BSDF'], shader_mix.inputs[2])
    material.node_tree.links.new(shader_mix.outputs['Shader'], shader_output.inputs['Surface'])
    
    return material

def apply_material_to_object(obj, material):
    """ Apply Material to Object """
        
    if obj.data.materials:
        # Assign the material to the first slot
        obj.data.materials[0] = material
    else:
        # Create a new material slot and assign the material
        obj.data.materials.append(material)
        
# ------------------------------------------------------------------------------
# Main Code
# ------------------------------------------------------------------------------

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

# Add Material
color_emission = hex_to_blender_color('#FFA02B')
color_bsdf = hex_to_blender_color('#F46A25')
emission_strenght = 1.2
mix_frac = 0.925
obs_material = create_colored_material('obs_material', color_bsdf, color_emission, emission_strenght, mix_frac)

# Apply Material
apply_material_to_object(observatory, obs_material)




