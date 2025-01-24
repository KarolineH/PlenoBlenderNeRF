import bpy

# global addon script variables
SPHERE_NAME = 'PlenoSphere'
TMP_VERTEX_COLORS = 'plenoblendernerf_vertex_colors_tmp'

class ResetScene(bpy.types.Operator):
    '''Plenoptic Video Scene Reset Operator'''
    bl_idname = 'object.scene_reset'
    bl_label = 'Plenoptic Video Scene Reset'
    default_cam_handles = ['left', 'right']

    def execute(self, context):
        '''
        Reset the scene so that the scene can be set-up again from the GUI.
        '''
        camera_list = sorted([obj.name for obj in bpy.data.objects if obj.type == 'CAMERA']) # names of all camera objects
        view_names = context.scene.render.views.keys() # names of all render views registered for multiview rendering
        
        # remove all cameras from the multiview rendering menu (except the first one)
        for view in view_names[1:]:
            obj = context.scene.render.views.get(view)
            if view in self.default_cam_handles:
                obj.camera_suffix = ""
            else:
                context.scene.render.views.remove(obj) # remove all render views except the first two that are normally there by default
        
        new_template_cam = context.scene.objects[camera_list[0]]
        new_template_cam.name = 'Camera'
        context.scene.camera = new_template_cam # keep the first camera as a new template
        context.scene.render.use_multiview = False # disable multiview rendering again

        for camera in camera_list[1:]:
            bpy.data.objects.remove(bpy.data.objects[camera], do_unlink=True)
        return {'FINISHED'}
    
    #TODO: Check if any of the new variable need resetting here