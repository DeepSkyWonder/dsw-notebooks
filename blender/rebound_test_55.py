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
import rebound
import astropy

scene = context.scene

# ------------------------------------------------------------------------------
# AstroViz Class
# ------------------------------------------------------------------------------

class astroviz:
    
    Collections = {}
    Objects = {}
    Cameras = {}
    Lights = {}
    Materials = {}
    Curves = {}
    Keyframe_Datapaths = {}
    Colors = {}
    Paths = {}
    HDRI = {}
    Images = {}
    Textures = {}
    
    context = bpy.context
    data = bpy.data
    ops = bpy.ops
    scene = context.scene
    
    def __init__(self, path_config, render_config=None, camera_config=None):
        
        # Camera and Render settings
        self.render_config = {}
        self.camera_config = {}
        self.path_config = {}
        
        if render_config == None:
            render_config = {
                'device': 'GPU',
                'engine': 'CYCLES',
                'experimental': True,
                'x_res': 1920,
                'y_res': 1080,
                'render_samples': 2048,
                'preview_samples': 1024,
                'render_denoise': True,
                'preview_denoise': True,
                'noise_threshold': 0.05,
                'noise_threshold_preview': 0.01,
                'max_subdivisions': 6,
                'film_transparent': False,
                'eevee_render_samples': 64,
                'eevee_samples': 16,
                'eevee_gtao': True,
                'eevee_bloom': True
                }
                
        if camera_config == None:
            camera_config = {
                'perspective': True,
                'ortho_scale': 2.5,
                'location': (3.8, 0.0, 0.93),
                'rotation': (82.0, 0.0, 90.0),
                'scale': (1, 1, 1)       
                }

        for key in render_config:
            self.render_config[key] = render_config[key]  
            
        for key in camera_config:
            self.camera_config[key] = camera_config[key]
            
        for key in path_config:
            self.path_config[key] = path_config[key] 
        
        self.configure_render()      
        self.clear_blender()
        self.setup_slooh_colors()
        self.setup_paths()
        
    def configure_render(self):
        """ Set-up the Redering Engine (for COLAB) """    
        
        scene.cycles.device = self.render_config['device']
        prefs = bpy.context.preferences
        prefs.addons['cycles'].preferences.get_devices()
        cprefs = prefs.addons['cycles'].preferences
        print(cprefs)
        
        # Attempt to set GPU device types if available
        for compute_device_type in ('CUDA', 'OPENGL', 'OPENCL', 'NONE'):
            try:
                cprefs.compute_device_type = compute_device_type
                print('Device found',compute_device_type)
                break
            except TypeError:
                pass

        # Enable all CPU and GPU devices (no check for AMD on COLAB)
        for device in cprefs.devices:
            if not re.match('intel', device.name, re.I):
                print('Activating: ', device.name)
                device.use = True
            else:
                print(f'Activating Intel {device.type}: {device.name}')
                self.render_config['device'] = device.type
                scene.cycles.device = self.render_config['device']
                device.use = True
            
        scene.render.resolution_x = self.render_config['x_res']
        scene.render.resolution_y = self.render_config['y_res']
        
        if self.render_config['engine'] == 'CYCLES':
            
            scene.render.engine = self.render_config['engine']
            scene.render.film_transparent = self.render_config['film_transparent']
            if self.render_config['experimental']:     
                scene.cycles.feature_set = 'EXPERIMENTAL'
            scene.cycles.samples = self.render_config['render_samples']
            scene.cycles.preview_samples = self.render_config['preview_samples']
            scene.cycles.use_preview_denoising = self.render_config['render_denoise']
            scene.cycles.use_denoising = self.render_config['preview_denoise']
            scene.cycles.adaptive_threshold = self.render_config['noise_threshold']
            scene.cycles.preview_adaptive_threshold = self.render_config['noise_threshold_preview']
            scene.cycles.max_subdivisions = self.render_config['max_subdivisions']
            
        elif self.render_config['engine'] == 'BLENDER_EEVEE':
            
            scene.render.engine = self.render_config['engine']
            scene.render.film_transparent = self.render_config['film_transparent']
            scene.eevee.taa_render_samples = self.render_config['eevee_render_samples']
            scene.eevee.taa_samples = self.render_config['eevee_samples']
            context.scene.eevee.use_gtao = self.render_config['eevee_gtao']
            context.scene.eevee.use_bloom = self.render_config['eevee_bloom']
     
        return None
    
    def del_collection(self, collection):
        """ Delete collection """
        
        if collection:
            collection_name = collection.name
            
            for collection in collection.children:
                del_collection(collection)
                
            data.collections.remove(collection, do_unlink=True)
            
            if self.Collections.get(collection_name) is not None:
                del self.Collections[collection_name]
    
    def clear_blender(self):
        """ Clear and reset Blender """
        
        for ob in bpy.data.objects:
            bpy.data.objects.remove(ob)

        for bpy_data_iter in (
                bpy.data.meshes,
                bpy.data.materials,
                bpy.data.textures,
                bpy.data.images,
                bpy.data.curves,
                bpy.data.cameras,
        ):
            for id_data in bpy_data_iter:
                bpy_data_iter.remove(id_data)
                
        for collection in data.collections:
            self.del_collection(collection)
                
        #Add default collection if missing   
        if not('Collection' in  [collection.name for collection in data.collections]):
            self.create_collection('Collection')
            
        #Add default camear if missing   
        if not('Camera' in [camera.name for camera in data.cameras]):
            self.add_camera('Camera')
    
    def create_collection(self, collection_name):
        """ Create collection """
        
        collection = bpy.data.collections.new(collection_name)
        context.scene.collection.children.link(collection)
        self.Collections[collection_name] = collection
        
        return collection
    
    def set_active_collection(self, collection_name):
        """ Set active collection """
        
        layer_collection = bpy.context.view_layer.layer_collection.children[self.Collections[collection_name].name]
        bpy.context.view_layer.active_layer_collection = layer_collection       
        
        return None
    
    def set_camera_location_rotation_scale(self, camera, location, rotation, scale):
        """ Set camera location and rotation """       

        if camera is not None:
            
            # Set the camera's location
            camera.location = location

            # Set the camera's rotation
            camera.rotation_euler = [math.radians(angle) for angle in rotation]   
            
            # Set the camera's scale
            camera.scale = scale
    
    def add_camera(self, name='Camera'):
        """ Add camera to scene, and configure camera """
        
        location = self.camera_config['location']
        rotation = self.camera_config['rotation']
        scale = self.camera_config['scale']
        ortho_scale = self.camera_config['ortho_scale']
        
        # Add camera and set postion to focus on full earth view
        camera = ops.object.camera_add(enter_editmode=False, align='VIEW', \
            location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
            
        # Get the camera named 'Camera' and set it as the active camera, and store it for later
        camera = data.objects[name]
        scene.camera = camera
        self.Cameras[name] = scene.camera

        # Set perspective or orthographic
        if self.camera_config['perspective']: # What about 'PANO'
            context.object.data.type = 'PERSP'
        else:
            context.object.data.type = 'ORTHO'
            context.object.data.ortho_scale = ortho_scale
            
        # Set camera location, rotation, and scale
        self.set_camera_location_rotation_scale(camera, location, rotation, scale)
        
        return camera

    def hex_to_gamma_corrected_blender_color(self, hex_color, alpha=1.0):
        """ Convert Hex Color to Blender RGBA Gamma Corrected Color with Alpha 1.0 """
        
        def srgb2lin(s):
            """ Convert SRGB color to Linear RGB color """

            if s <= 0.0404482362771082:
                lin = s / 12.92
            else:
                lin = pow(((s + 0.055) / 1.055), 2.4)
            return lin

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
        
        return rgba
    
    def apply_material_to_object(self, obj, material):
        """ Apply Material to Object """

        if obj.data.materials:
            # Assign the material to the first slot
            obj.data.materials[0] = material
        else:
            # Create a new material slot and assign the material
            obj.data.materials.append(material)
            
    def add_color(self, name, color_hex):
        """ Add color to color dictionary """
        
        color = self.hex_to_gamma_corrected_blender_color(color_hex)
        self.Colors[name] = color
        
        return color
    
    def setup_slooh_colors(self):
        """ Add Slooh colors to color dictionary """
        
        self.add_color('slooh_gold', '#B09C78')
        self.add_color('slooh_bright_gold', '#E4C490')
        self.add_color('slooh_red', '#DB6448')
        self.add_color('slooh_light_blue', '#00A2FF')
        self.add_color('slooh_background_blue', '#202E40')
        self.add_color('slooh_light_background_blue', '#40556E')
        self.add_color('white', '#FFFFFF')
        self.add_color('black', '#000000')
        
        return None
    
    def setup_paths(self):
        """ Setup paths and folders for external files """
        
        if self.Paths.get('base_path') is None:
            self.Paths['base_path'] = self.path_config['base_path']
        
        for (folder_name, folder_path) in \
            {folder_name:folder_path for (folder_name, folder_path) in self.path_config.items() if 'folder' in folder_name}.items():
            
             self.Paths[folder_name] = os.path.join(self.Paths['base_path'], folder_path)
        
        return None
    
    def set_smooth(self, object):
        """ Enable smooth shading on an mesh object """

        for face in object.data.polygons:
            face.use_smooth = True
            
    def recalculate_normals(self, mesh):
        """ Make normals consistent for mesh """

        bm = bmesh.new()
        bm.from_mesh(mesh)

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        bm.to_mesh(mesh)
        bm.free()
        
    def bevel_and_subdivide(self, object, BEVEL=False, bevel_segments=5, bevel_width=0.01, 
        bevel_loop_slide=True, SUBDIV=True, subdivision_type='CATMULL_CLARK', 
        subdiv_quality=3, subdiv_levels=3, subdiv_render_levels=3):
        """ Apply subdivision to an object """
            
        # set active object
        current_object = context.view_layer.objects.active
        context.view_layer.objects.active = object
        
        if object.type == 'MESH':
        
            if BEVEL:
            
                bevel = object.modifiers.get("Bevel") or object.modifiers.new('Bevel', 'BEVEL')
                bevel.limit_method = 'ANGLE'
                bevel.loop_slide=True
                bevel.material=-1
                bevel.profile=0.5
                bevel.offset_type='OFFSET'
                bevel.segments = bevel_segments
                bevel.width = bevel_width
                bevel.harden_normals = True
                
            if SUBDIV :
              
                subdiv = object.modifiers.get("SubDiv") or object.modifiers.new('SubDiv', 'SUBSURF')
                subdiv.quality = subdiv_quality
                subdiv.levels = subdiv_levels
                subdiv.render_levels = subdiv_render_levels
                subdiv.subdivision_type = subdivision_type
                subdiv.use_limit_surface = True
                subdiv.uv_smooth = 'PRESERVE_CORNERS'
                subdiv.boundary_smooth = 'ALL'
                subdiv.use_creases = True
                subdiv.use_custom_normals = True
        
         # restore previous active object
        context.view_layer.objects.active = current_object
    
    def import_fbx(self, obs_fbx_filename, name, scale):
        """ Import FBX object, smooth and reculculate normals """
        
        # Import Observatory into Scene
        obs_fbx_filepath = os.path.join(self.Paths['folder_FBX'], obs_fbx_filename)
        ops.import_scene.fbx( filepath = obs_fbx_filepath, global_scale = scale)
        object = context.selected_objects[0]
        
        # Smooth and recalculate normars
        self.set_smooth(object)
        self.recalculate_normals(object.data)
        
        # Set object name
        object.name = name
        
        # Store reference for object
        self.Objects[name] = object
        
        return object
    
# ------------------------------------------------------------------------------
# Configure Blender using AstroViz
# ------------------------------------------------------------------------------
         
render_config = {
    'device': 'GPU',
    'engine': 'CYCLES',
    'experimental': True,
    'x_res': 1920,
    'y_res': 1080,
    'render_samples': 2048,
    'preview_samples': 1024,
    'render_denoise': True,
    'preview_denoise': True,
    'noise_threshold': 0.05,
    'noise_threshold_preview': 0.01,
    'max_subdivisions': 6,
    'film_transparent': False,
    'eevee_render_samples': 64,
    'eevee_samples': 16,
    'eevee_gtao': True,
    'eevee_bloom': True
    }
 
camera_config = {
    'perspective': True,
    'ortho_scale': 2.5,
    'location': (3.8, 0.0, 0.93),
    'rotation': (82.0, 0.0, 90.0),
    'scale': (1, 1, 1)       
    }
    
path_config = { \
    'base_path': '/Users/cmcewing/Documents/blender_docs/', \
    'folder_HDRI': 'HDRI/', \
    'folder_Textures': 'Textures/', \
    'folder_Images': 'Images/', \
    'folder_FBX': 'FBX/' \
    }
    
file_config = {
    'Sun_Texture': '2k_sun.jpg',
    'SloohBlue_Texture': 'slooh_blue_02.png',
    'Stars_CSV': 'star_paths_03.csv',
    'NightMeadow_HDRI': 'meadow_at_night.hdr'
    }

# Configure Renderer and Clear Scene
astrov = astroviz(path_config, render_config=render_config, camera_config=camera_config)
astrov.create_collection('Stars')
astrov.set_active_collection('Stars')

# ------------------------------------------------------------------------------
# Rebound Binary System Orbit Simulation Funcitons
# ------------------------------------------------------------------------------

def calc_G(unit = 'AU', AU_per_arsec = None):

  AU_in_metres = 1.496e+11
  solar_mass_in_kg = 1.989e+30
  year_in_seconds = 31556736 # 365.24 days in seconds

  G_metres = 6.6743e-11 # m^3 / kg s^2

  if unit == 'AU':
    G = G_metres * ( (AU_in_metres ** -3.) * (solar_mass_in_kg) * (year_in_seconds ** 2.)) # AU^3 / solar_mass year^2
  elif (unit == 'arcsec') and (AU_per_arsec != None):
    G = G_metres * ( (AU_in_metres ** -3.) * (AU_per_arsec ** -3.) * (solar_mass_in_kg) * (year_in_seconds ** 2.)) # AU^3 / solar_mass year^2
  else:
    G = G_metres # m^3 / kg s^2

  return G

def update_orbital_elements(orbital_elements, G_AU, VERBOSE):
    
    # Redefine a_AU from Period and G_AU and masses of stars using: a^3/ p^2 = G(M1 + M2) / (2pi)^2
    orbital_elements['a_AU'] = np.cbrt( (orbital_elements['P'] ** 2) * (G_AU * (orbital_elements['mass_primary'] + orbital_elements['mass_secondary'])) / ((2 * np.pi) ** 2.0) )
    if VERBOSE: print(f'Semi-major axis (secondary): {orbital_elements["a_AU"]:.2f} AU')

    # Redefine disance from a_AU and a_arcsec using: size = distance * 63241.1 * tan(angle), angle in radians, distance in lightyears, size in AU, 63241.1 = AU per lightyear
    AU_in_lightyear = 63241.1
    system_40_eridani_BC['distance'] = orbital_elements['a_AU'] / ( np.tan(np.deg2rad(orbital_elements['a_arcsec'] / 3600.0)) * (AU_in_lightyear) )
    if VERBOSE: print(f'Star System Distance: {system_40_eridani_BC["distance"]:.2f} lightyears')
    
    return orbital_elements

def simulate_star_system(orbital_elements, VERBOSE):
    
    # Define G in standard units (m^3 / kg s^2) and in units (AU^3 / solar_mass year^2)
    G_metres = calc_G()
    G_AU = calc_G(unit = 'AU')

    # Update a_AU, and distance based on a_arcsec and G_AU
    orbital_elements = update_orbital_elements(orbital_elements, G_AU, VERBOSE)

    # Define G in appropriate units for simulation (arcsec^3 / solar_mass year^2)
    AU_in_arcsec = orbital_elements['a_AU'] / orbital_elements['a_arcsec'] # Ratio at distance of star system
    G_arcsec = calc_G(unit = 'arcsec', AU_per_arsec = AU_in_arcsec)
    
    # Create simulation and set G
    sim = rebound.Simulation() 
    sim.G = G_arcsec
    
    # Setup integrator
    sim.integrator = "leapfrog"
    sim.dt = 1e-4
    
    # Add stars
    sim.add(m=orbital_elements['mass_primary'])
    sim.add(m = orbital_elements['mass_secondary'], 
        a = orbital_elements['a_arcsec'], 
        e = orbital_elements['e'], 
        inc = orbital_elements['inc'], 
        Omega = orbital_elements['Omega'], 
        omega = orbital_elements['omega'], 
        T = orbital_elements['T'])
    
    # Move simulation to the center of mass of the star system
    sim.move_to_com()
    
    # Define the simulation time step and duration
    no_of_orbits = 1
    steps_per_orbit = 250
    no_of_steps = no_of_orbits * steps_per_orbit
    orbital_period_calculated = sim.particles[1].P
    
    # Start at Epoch of periastron end at start plus one orbital period
    start_time = orbital_elements['T']
    end_time = start_time + orbital_period_calculated
    sim_times = np.linspace(start_time, end_time, no_of_steps)
    
    # Create arrays for output cartesian coordinates
    number_of_stars = sim.N
    sim_results = {}
    
    sim_results['primary'] = []
    sim_results['secondary'] = []

    x = np.zeros((number_of_stars, no_of_steps)) # coordinates for both particles
    y = np.zeros_like(x)
    z = np.zeros_like(x)
    
    # Run simulation (integrate system from start_time to end_time)

    sim_results = {'x': x, 'y': y, 'z': z}

    for time_index, time in enumerate(sim_times):

      sim.integrate(time, exact_finish_time=0)

      for star_index in range(number_of_stars):
          
          x[star_index, time_index] = sim.particles[star_index].x
          y[star_index, time_index] = sim.particles[star_index].y
          z[star_index, time_index] = sim.particles[star_index].z
          
    if VERBOSE: print(f'G: {sim.G:.4f} (AU^3 / solar_mass year^2)')
    if VERBOSE: print(f'Orbital period: {sim.particles[1].P:.2f} years')

    return sim_results, sim

# ------------------------------------------------------------------------------
# Run Star System Orbit Simulation and Generate Cartesian Coordinates
# ------------------------------------------------------------------------------

star_40_eridani_B = {
    'name': '40 Eridani B',
    'class': 'DA4',
    'type': 'White Dwarf',
    'mass': 0.573, # solar mass
    'radius': 0.014, # solar radius
    'luminosity': 0.013, # solar luminosity
    'temperature': 16500 # Kelvin
    }
    
star_40_eridani_C = {
    'name': '40 Eridani C',
    'class': 'M4.5e',
    'type': 'Red Dwarf',
    'mass': 0.2036, # solar mass
    'radius': 0.31, # solar radius
    'luminosity': 0.008, # solar luminosity
    'temperature': 3100 # Kelvin
    }

system_40_eridani_BC = {
    'name': '40 Eridani BC',
    'primary': star_40_eridani_B,
    'secondary': star_40_eridani_C,
    'period': 230.30,  # years
    'semi-major axis (AU)': 35.0, 
    'semi-major axis (arcsec)': 6.93,
    'eccentricity': 0.4294,
    'inclination': np.deg2rad(107.56), # radians
    'longitude of ascending node': np.deg2rad(151.44), # radians
    'argument of periastron': np.deg2rad(318.4), # radians
    'epoch of periastron': 1847.7, # year
    'distance': 16.340
    }

orbital_elements = {
    'system': system_40_eridani_BC,
    'name': system_40_eridani_BC['name'],
    'primary': system_40_eridani_BC['primary'],
    'secondary': system_40_eridani_BC['secondary'],
    'mass_primary': system_40_eridani_BC['primary']['mass'],
    'mass_secondary': system_40_eridani_BC['secondary']['mass'],
    'a_AU': system_40_eridani_BC['semi-major axis (AU)'],
    'a_arcsec': system_40_eridani_BC['semi-major axis (arcsec)'],
    'e': system_40_eridani_BC['eccentricity'],
    'inc': system_40_eridani_BC['inclination'],
    'Omega': system_40_eridani_BC['longitude of ascending node'],
    'omega':  system_40_eridani_BC['argument of periastron'],
    'T': system_40_eridani_BC['epoch of periastron'],
    'P': system_40_eridani_BC['period'] # This should be defined by G and a
    }
    
VERBOSE = True

sim_results, sim = simulate_star_system(orbital_elements, VERBOSE)

# ------------------------------------------------------------------------------
# Main Code - Setup Blender Scene and Animate Star System Orbit
# ------------------------------------------------------------------------------

# Setup stars

number_of_stars = 2

stars = []

for star_index in range(number_of_stars):

    # Create star
    star_surf_name = 'Star_Surface_' + f'{star_index:03}'
    astrov.import_fbx('corrected_quad_sphere.fbx', star_surf_name, 1.0)
    star_surf_object = astrov.Objects[star_surf_name]
    astrov.bevel_and_subdivide(star_surf_object, BEVEL=False, SUBDIV=True, subdivision_type='CATMULL_CLARK', 
        subdiv_quality=3, subdiv_levels=2, subdiv_render_levels=2)
    
    # Create star atmosphere
    star_atmos_name = 'Star_Atmos_' + f'{star_index:03}'
    astrov.import_fbx('corrected_quad_sphere.fbx', star_atmos_name, 1.0)
    star_atmos_object = astrov.Objects[star_atmos_name]
    astrov.bevel_and_subdivide(star_atmos_object, BEVEL=False, SUBDIV=True, subdivision_type='CATMULL_CLARK', 
        subdiv_quality=3, subdiv_levels=2, subdiv_render_levels=2)
    
    # Create empty sphere for parent object
    star_name = 'Star_' + f'{star_index:03}'
    star_object = bpy.data.objects.new(name=star_name, object_data=None)
    star_object.empty_display_type = "SPHERE"
    context.collection.objects.link(star_object)
  
    # Parent 
    star_surf_object.parent = star_object
    star_atmos_object.parent = star_object
      
    # Set star location and rotation
    star_object.location = (0.0, float(star_index) * 3.0 , 1.0)    
    rotation_degrees = (0.0, 0.0, 0.0)
    star_object.rotation_euler = [math.radians(angle) for angle in rotation_degrees]
    
    stars.append(star_object)

print(stars)
    
# Store Clamshell Observatory Objects for Later Use
#Objects['Base'] = bpy.data.objects["Base"]
#Objects['Base_Ring'] = bpy.data.objects["Base_Ring"]
#Objects['Clamshell'] = bpy.data.objects["Clamshelll"]
#Objects['Mount'] = bpy.data.objects["Mount"]
#Objects['Telescope'] = bpy.data.objects["Telescope"]

 # Makes an empty, at location, stores it in existing collection
#def make_empty(name, location, coll_name): #string, vector, string of existing coll
#    empty_obj = bpy.data.objects.new( "empty", None, )
#    empty_obj.name = name
#    empty_obj.empty_display_size = 1 
#    bpy.data.collections[coll_name].objects.link(empty_obj)
#    empty_obj.location = location
#    return empty_obj





