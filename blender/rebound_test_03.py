import bpy
import bmesh
import math
import mathutils
import os
from bpy import context, data, ops
import rebound

scene = context-scene

class astroviz:
    
    Collections = {}
    Objects = {}
    Cameras = {}
    Lights = {}
    Materials = {}
    Curves = {}
    

    def __init__(self, render_config):
        
        # Render settings
        self.render_config = {}
        
        if render_config['x_res'] == None:
            self.render_config['x_res'] = 1920
        else:
            self.render_config['x_res'] = render_config['x_res']
            
        if render_config['y_res'] == None:
            self.render_config['y_res'] = 1080
        else:
            self.render_config['y_res'] = render_config['y_res']
        
        if render_config['engine'] == None:
            self.render_config['engine'] = "eevee"
        else:
            self.render_config['engine'] = render_config['engine']
            
        configure_render()
        
    def configure_render(self):
        
        
        return None
    
render_config = {
    engine: 'eevee',
    x_res: 1920,
    y_res: 1080
    }
    
astrov = astroviz(render_config)
