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

#---------------------------------------------------
# Configure Blender
#---------------------------------------------------

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
    
    def __init__(self, render_config=None):
        
        # Render settings
        self.render_config = {}
        
        if render_config == None:
            render_config = {
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

#---------------------------------------------------
# Run Star System Orbit Simulation and Generate XYZ
#---------------------------------------------------

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

# Define G in standard units (m^3 / kg s^2) and in units (AU^3 / solar_mass year^2)
G_metres = calc_G()
G_AU = calc_G(unit = 'AU')

# Redefine a_AU from Period and G_AU and masses of stars using: a^3/ p^2 = G(M1 + M2) / (2pi)^2
orbital_elements['a_AU'] = np.cbrt( (orbital_elements['P'] ** 2) * (G_AU * (orbital_elements['mass_primary'] + orbital_elements['mass_secondary'])) / ((2 * np.pi) ** 2.0) )
print(f'Semi-major axis (secondary): {orbital_elements["a_AU"]:.2f} AU')

# Redefine disance from a_AU and a_arcsec using: size = distance * 63241.1 * tan(angle), angle in radians, distance in lightyears, size in AU, 63241.1 = AU per lightyear
AU_in_lightyear = 63241.1
system_40_eridani_BC['distance'] = orbital_elements['a_AU']/ ( np.tan(np.deg2rad(orbital_elements['a_arcsec'] / 3600.0)) * (AU_in_lightyear) )
print(f'Star System Distance: {system_40_eridani_BC["distance"]:.2f} lightyears')

# Define G in appropriate units for simulation (arcsec^3 / solar_mass year^2)
AU_in_arcsec = orbital_elements['a_AU'] / orbital_elements['a_arcsec'] # Ratio at distance of star system
G_arcsec = calc_G(unit = 'arcsec', AU_per_arsec = AU_in_arcsec)


def simulate_star_system(orbital_elements, G):
    
    sim = rebound.Simulation()
    
    sim.G = G
    
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
    
    # Star at Epoch of periastron end at start plus one orbital period
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

    return sim_results, sim

sim_results, sim = simulate_star_system(orbital_elements, G_arcsec)

print(f'G: {sim.G:.4f} (AU^3 / solar_mass year^2)')
print(f'Orbital period: {sim.particles[1].P:.2f} years')