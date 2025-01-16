import bpy
import os
from . import helper

class RenderScene(bpy.types.Operator):
    '''Plenoptic Video Scene Rendering Operator'''
    bl_idname = 'object.renderer'
    bl_label = 'Plenoptic Video Renderer'

    def render(self, scene, output_path):
        scene.rendering = True
        scene.render.filepath = os.path.join(output_path, '') # frames path
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True, write_still=True) # render scene
        return 'FINISHED'
    
    def write_metadata(self, scene, output_path):
        intrinsics = helper.get_camera_intrinsics(scene, scene.camera) # intrinsics are the same for all cameras
        extrinsics = helper.get_camera_extrinsics(scene, scene['cam_handles'])

        # helper.save_json(output_path, 'transforms.json', output_data)

    def execute(self, context):
        scene = context.scene

        # clean directory name (unsupported characters replaced) and output path
        output_dir = bpy.path.clean_name(scene.dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)
        os.makedirs(output_path, exist_ok=True)
                
         # save PC as PLY file
        if scene.splats:
            helper.save_splats_ply(scene, output_path)

        # Make sure the correct frames are rendered in case this has changed
        scene.frame_end = scene.final_frame_nr
        scene.frame_start = scene.first_frame_nr

        #TODO: Write meta data, in the correct format
        #TODO: Update the extrinsics fetching code

        self.render(scene, output_path) # RENDER SCENE

        #TODO: Pack the images into folders by camera and frame
        #ims/0/0000000.png
        #ims/cam/frame.png
        return {'FINISHED'}