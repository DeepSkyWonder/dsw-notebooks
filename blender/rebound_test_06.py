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
import math
from math import sin, cos, radians, pi, atan, tan
from mathutils import Vector as Vector
import rebound

scene = context.scene

class astroviz:
    
    Collections = {}
    Objects = {}
    Cameras = {}
    Lights = {}
    Materials = {}
    Curves = {}
    
    context = bpy.context
    data = bpy.data
    ops = bpy.ops
    scene = context.scene
    
    def __init__(self, render_config):
        
        # Render settings
        self.render_config = {}
        
        if render_config = {
            'engine': 'CYCLES',
            'experimental': True,
            'x_res': 1920,
            'y_res': 1080
            }
                
        self.render_config['engine'] = render_config['engine']
        self.render_config['experimental'] = render_config['experimental']
        self.render_config['x_res'] = render_config['x_res']
        self.render_config['y_res'] = render_config['y_res']
        
            
        self.configure_render()
        
    def configure_render(self):
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
            
            
        scene.render.resolution_x = self.render_config['x_res']
        scene.render.resolution_y = self.render_config['y_res']
        scene.render.engine = self.render_config['engine']
        if self.render_config['experimental']:     
            scene.cycles.feature_set = 'EXPERIMENTAL'
        scene.cycles.adaptive_threshold = 0.05
        scene.cycles.max_subdivisions = 6
        
        return None
    
render_config = {
    'engine': 'CYCLES',
    'experimental': True,
    'x_res': 1920,
    'y_res': 1080
    }

if False:
    
    bpy.data.scenes["Scene"].render.engine
    bpy.data.scenes["Scene"].cycles.preview_adaptive_threshold
    bpy.data.scenes["Scene"].cycles.adaptive_threshold
    bpy.data.scenes["Scene"].cycles.max_subdivisions
    bpy.data.scenes["Scene"].cycles.samples
    bpy.data.scenes["Scene"].render.film_transparent = False
    

    bpy.data.scenes["Scene"].render.engine = 'BLENDER_EEVEE'
    bpy.data.scenes["Scene"].eevee.taa_render_samples = 64
    bpy.data.scenes["Scene"].eevee.taa_samples = 16
    bpy.context.scene.eevee.use_gtao = True # Ambient Occulation
    bpy.context.scene.eevee.use_bloom = True
    bpy.data.scenes["Scene"].render.film_transparent = False

astrov = astroviz(render_config)

# 40 Eridani B: White Dwarf DA4 (9.52 V)
# 0.573±0.018 Solar mass
# 0.014 Solar radius
# 0.013 Solar luminosity
# 16,500 K

# 40 Eridani C: Red Dwarf M4.5e (11.17 V)
# 0.2036±0.0064 Solar mass
# 0.31 Solar radius
# 0.008 Solar luminosity
# 3,100 K

# Period 230.30±0.68 yr
# Semi-major axis 6.930±0.050" or 35AU
# Eccentricity 0.4294±0.0027
# Inclination 107.56±0.29°
# Longitude of the node (Ω)	151.44±0.12°
# Periastron epoch (T)	1847.7±1.1
# Argument of periastron (ω) 318.4±1.1° (secondary)

# 40 Eridani AB - Distance
# 16.340 ly (16.9655281467 if a = 36.0474 AU and angular a = 6.93 arc-seconds

star_40_eridani_B = {
    'class': 'DA4',
    'type': 'White Dwarf',
    'mass': 0.573, # solar mass
    'radius': 0.014, # solar radius
    'luminosity': 0.013, # solar luminosity
    'temperature': 16500 # Kelvin
    }
    
star_40_eridani_C = {
    'class': 'M4.5e',
    'type': 'Red Dwarf',
    'mass': 0.573, # solar mass
    'radius': 0.014, # solar radius
    'luminosity': 0.013, # solar luminosity
    'temperature': 16500 # Kelvin
    }
    
system_40_eridani_BC = {
    'Primary': star_40_eridani_B,
    'Secondary': star_40_eridani_C,
    'Period': 230.30,  # years
    'Semi-major axis (AU)': 36.0474, # AU
    'Semi-major axis (arcsec)': 6.93, # arc-seconds
    'Eccentricity': 0.4294,
    'Inclination': np.deg2rad(107.56), # radians
    'Longitude of ascending node': np.deg2rad(151.44), # radians
    'Argument of periastron': np.deg2rad(318.4), # radians
    'Epoch of periastron': 1847.7, # year
    'Distance': 16.9655281467 # light-years - 16.340 ly (16.9655281467 if a = 36.0474 AU and angular a = 6.93 arc-seconds
    }

orbital_elements = {
    'mass_primary': system_40_eridani_BC['primary']['mass'],
    'mass_secondary': system_40_eridani_BC['secondary']['mass'],
    'a_AU': system_40_eridani_BC['Semi-major axis (AU)'],
    'a_arcsec': system_40_eridani_BC['Semi-major axis (arcsec)']
    'e': system_40_eridani_BC['Eccentricity'],
    'inc': system_40_eridani_BC['Inclination']
    'Omega': system_40_eridani_BC['Longitude of ascending node']
    'omeag':  system_40_eridani_BC['Argument of periastron'],
    'T': system_40_eridani_BC['Epoch of periastron'],
    'P': system_40_eridani_BC['Period'] # This should be defined by G and a
    }

def simulate_star_system(orbital_elements):
    
    sim = rebound.Simulation()
    
    # Define G in appropriate unitis for simulation
    AU_in_metres = 1.496e+11
    solar_mass_in_kg = 1.989e+30
    year_in_seconds = 31556736 # 365.24 days in seconds
    arcsec_in_AU = orbital_elements['a_AU'] / orbital_elements['a_arcsec'] # Ratio at distance of star system
    
    G_metres = 6.6743e-11 # m^3 / kg s^2
    G_AU = G_metres * ( (AU_in_metres ** -3.) * (solar_mass_in_kg) * (year_in_seconds ** 2.))# AU^3 / solar_mass year^2
    G_arcsec = G_AU * (arcsec_in_AU ** -3.) # arc_seconds^3 / solar_mass year^2
    
    sim.G = G_arcsec
    
    # Setup integrator
    sim.integrator = "leapfrog"
    sim.dt = 1e-4
    
    # Add stars
    sim.add(m=orbital_elements['mass_primary'])
    sim.add(m = orbital_elements['mass_primary'],
        a = orbital_elements['a_arcsec'],
        e = orbital_elements['a_arcsec'],
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
    
    # Star at Epoch of periastron end at start plus one orbital period
    start_time = orbital_elements['T']
    end_time = start_time + orbital_period_calculated
    sim_times = np.linspace(start_time, end_time, no_of_steps)
    
    # Create arrays for output cartesian coordinates
    number_of_stars = sim.N
    sim_results = {}
    
    for star_index in number_of_stars:
        sim_results.append({f'{star_index}': []})
    
    # Run simulation (integrate system from start_time to end_time)

    for time_index, time in enumerate(times):

      sim.integrate(time, exact_finish_time=0)

      for star_index in range(number_of_stars):
          
        sim_results[f'{star_index]}'].append{Vector(sim.particles[j].x, sim.particles[j].y, sim.particles[j].z)}
        
    return sim_results