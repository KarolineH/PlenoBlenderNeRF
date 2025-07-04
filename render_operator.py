import bpy
import os
import numpy as np
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
        meta_data['w'] = helper.remove_trailing_zeros(intrinsics['w'])
        meta_data['h'] = helper.remove_trailing_zeros(intrinsics['h'])
        meta_data['k'] = helper.remove_trailing_zeros(np.tile(camera_matrix, (nr_frames, scene.nb_cameras, 1, 1)).tolist())
        meta_data['w2c'] = helper.remove_trailing_zeros(extrinsics.tolist())
        meta_data['fn'] = file_names_nested
        meta_data['cam_id'] = [[int(index) for index in range(scene.nb_cameras)] for _ in range(nr_frames)]

        helper.save_json(output_path, 'meta.json', meta_data)

    def execute(self, context):
        scene = context.scene

        # clean directory name (unsupported characters replaced) and output path
        output_dir = bpy.path.clean_name(scene.dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)
        os.makedirs(output_path, exist_ok=True)
        
        # Create log file using stored focal length from scene preparation
        helper.save_log_file(scene, scene.focal_length, output_path)
                
         # save PC as PLY file
        if scene.splats:
            helper.save_splats_ply(scene, output_path)

        # Make sure the correct frames are rendered in case this has changed
        scene.frame_end = scene.final_frame_nr
        scene.frame_start = scene.first_frame_nr

        self.write_metadata(scene, output_path)

        # Additional export options based on user flags (performed after rendering)
        if scene.export_meshes_per_frame:
            print("Starting per-frame mesh export...")
            self.report({'INFO'}, "Starting per-frame mesh export...")
            ply_path = os.path.join(output_path, 'per_frame_plys')
            if not os.path.exists(ply_path):
                os.mkdir(ply_path)
            helper.save_meshes_per_frame(scene, ply_path)
            # This should export .ply meshes for each frame of the animation
            print("Per-frame mesh export completed")
            self.report({'INFO'}, "Per-frame mesh export completed")
            
        if scene.track_vertex_trajectories:
            print("Starting vertex trajectory tracking...")
            self.report({'INFO'}, "Starting vertex trajectory tracking...")
            helper.track_vertices(scene, os.path.join(output_path, 'gt_traj.json'))
            # This should track and export trajectories of all mesh vertices
            print("Vertex trajectory tracking completed")
            self.report({'INFO'}, "Vertex trajectory tracking completed")

        # Start main rendering process
        print("Starting main rendering process...")
        self.report({'INFO'}, "Starting main rendering process...")
        self.render(scene, output_path) # RENDER SCENE
        
        # Final completion message
        print("All separate export tasks completed successfully! Please wait for the main rendering to finish...")
        self.report({'INFO'}, "All separate export tasks completed successfully! Please wait for the main rendering to finish...")
        
        return {'FINISHED'}