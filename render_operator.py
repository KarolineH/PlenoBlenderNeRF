import bpy
import os
import numpy as np
import shutil
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
        intrinsics = helper.get_camera_intrinsics(scene, scene.objects[scene['cam_handles'][0][1]]) # intrinsics are the same for all cameras
        camera_matrix = np.array([[intrinsics['fl_x'], 0, intrinsics['cx']], [0, intrinsics['fl_y'], intrinsics['cy']], [0, 0, 1]])
        extrinsics = helper.get_camera_extrinsics(scene, scene['cam_handles'])
        nr_frames = scene.final_frame_nr - scene.first_frame_nr + 1

        frame_ids = [str(number+1).zfill(6) for number in range(nr_frames)]
        camera_ids = [str(cam_id) for cam_id in range(scene.nb_cameras)]
        file_names_nested = [[f"{camera_id}/{frame_id}.{scene.render.image_settings.file_format.lower()}" for camera_id in camera_ids] for frame_id in frame_ids]

        meta_data = {}
        meta_data['w'] = intrinsics['w']
        meta_data['h'] = intrinsics['h']
        meta_data['k'] = np.tile(camera_matrix, (nr_frames, scene.nb_cameras, 1, 1)).tolist()
        meta_data['w2c'] = extrinsics.tolist()
        meta_data['fn'] = file_names_nested
        meta_data['cam_id'] = [[int(index) for index in range(scene.nb_cameras)] for _ in range(nr_frames)]

        helper.save_json(output_path, 'meta.json', meta_data)

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

        self.write_metadata(scene, output_path)

        self.render(scene, output_path) # RENDER SCENE

        #TODO: Check the coordinate frame convention
        return {'FINISHED'}