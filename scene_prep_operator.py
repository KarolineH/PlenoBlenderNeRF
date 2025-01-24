import os
import numpy as np
import bpy
import random
import mathutils

from . import helper

# global addon script variables
SPHERE_NAME = 'PlenoSphere'

class ScenePrep(bpy.types.Operator):
    '''Plenoptic Video Scene Prep Operator'''
    bl_idname = 'object.scene_prep'
    bl_label = 'Plenoptic Video Scene Prep'

    def sample_cam_poses(self, scene, num_cameras, num_repetitions):
        ''' 
        Sample to distribute a number of cameras uniformly on the surface of a sphere.
        Although this function samples locations randomly, it is deterministic so that with the same scene seed it will always return the same result.
        Inputs:
        - scene: the scene object containing user settings (random seed and sphere details)
        - num_cameras: the number of cameras to distribute
        - num_repetitions: the number of times to repeat the sampling, e.g. if the cameras should move to new random locations at each frame
        
        Outputs:
        - points: a numpy array of shape (num_repititions, num_cameras, 3) containing the camera position coordinates (xyz)
        '''
        # initialise random number generators
        seeds = [(2654435761 * (scene.seed + 1)) ^ (805459861 * (num + 1)) for num in range(num_cameras)]
        rngs = [random.Random(seed) for seed in seeds] # random number generators for each camera

        # sample random angles
        cam_poses = []
        for rep in range(num_repetitions):
            thetas = np.array([rng.random() * 2 * np.pi for rng in rngs]) # this is different each time it is called, but if rngs is regenerated with the same seed, the same result will be returned
            phis = np.array([np.arccos(1 - 2 * rng.random()) for rng in rngs]) # ensure uniform sampling from unit sphere

            # generate the position component
            unit_xs = np.cos(thetas) * np.sin(phis) 
            unit_ys = np.sin(thetas) * np.sin(phis)
            if scene.upper_views:
                unit_zs = [abs(np.cos(phi)) for phi in phis] # if upper views is active, only distribute on the upper hemisphere
            else:
                unit_zs = [np.cos(phi) for phi in phis]
            unit_vectors = np.vstack((unit_xs, unit_ys, unit_zs)).T
            points = scene.sphere_radius * np.array(scene.sphere_scale) * unit_vectors
            overall_rotation = mathutils.Euler(scene.sphere_rotation).to_matrix() # in case the sphere is rotated in the scene
            points = (np.array(overall_rotation) @ points.T).T
            cam_poses.append(points)

        result = np.stack(cam_poses) # numpy array of size [num_repetitions, num_cameras, 3] containing the camera position coordinates (xyz)
        return result
    
    def regular_cam_poses(self, scene, num_cameras):
        '''
        Distribute a number of cameras uniformly on the surface of a sphere.
        This function is deterministic and will always return the same result for the same input.
        Returns an array of size [num_cameras, 3] containing the camera position coordinates (xyz).
        '''
        # instead of random, distribute the cameras uniformly on a sphere
        phi = np.pi * (np.sqrt(5.) - 1.)  # golden angle in radians
        indices = np.arange(0, num_cameras, dtype=float) + 0.5  # to place the points in the middle of the bins
        if scene.upper_views:
            z = (indices/num_cameras)
        else:
            z = 1 - (indices / num_cameras) * 2  # y goes from 1 to -1
        radius = np.sqrt(1 - z * z)  # radius at y
        theta = phi * np.arange(0, num_cameras, dtype=float)  # golden angle increment
        x = np.cos(theta) * radius
        y = - np.sin(theta) * radius
        unit_vectors = np.vstack((x, y, z)).T
        points = scene.sphere_radius * np.array(scene.sphere_scale) * unit_vectors
        overall_rotation = mathutils.Euler(scene.sphere_rotation).to_matrix() # in case the sphere is rotated in the scene
        points = (np.array(overall_rotation) @ points.T).T
        result = np.expand_dims(points, axis=0) # array of size [1, num_cameras, 3] containing the camera position coordinates (xyz)
        return result

    def prepare_scene(self, context):
        ### Places all the cameras in their initial positions and sets rendering settings
        # set up multiview rendering
        scene = context.scene
        template_camera = scene.camera

        scene.render.use_multiview = True # Activates multiview or "plenoptic" rendering option
        scene.render.views_format = 'MULTIVIEW' # use multiview as opposed to stereo 3D 
        default_cam_handles = ['left', 'right', 'RenderView'] # the first three cameras added to a multiview panel are always named this
        helper.create_sphere(context) # only creates the sphere if it does not already exist

        num_cameras = scene.nb_cameras
        repetitions = scene.final_frame_nr - scene.first_frame_nr + 1
        scene.frame_end = scene.final_frame_nr
        scene.frame_start = scene.first_frame_nr
        if scene.cam_distribution:
            points = self.regular_cam_poses(scene, num_cameras)
        else:
            points = self.sample_cam_poses(scene, num_cameras, repetitions)

        cam_handle_record = [] # keep a record of pairs of object names and their corresponding camera handles for multi-view rendering
        bpy.ops.scene.render_view_add() # add a first additional camera in the multi-view menu

        # points has shape [num_repetitions, num_cameras, 3], always use the first (and sometimes only) repetition for initial camera placement
        for i, point in enumerate(points[0,:,:]):
            if i < len(default_cam_handles):
                cam_handle = default_cam_handles[i]
            else:
                bpy.ops.scene.render_view_add() # add a new camera in the multi-view menu at every iteration
                cam_handle = f"RenderView.{str(i-len(default_cam_handles)+1).zfill(3)}"
            cam_handle_record.append((cam_handle, f"{template_camera.name}_{i}"))
            bpy.context.scene.render.views[cam_handle].camera_suffix = f'_{i}'
            new_cam = template_camera.copy()
            new_cam.data = template_camera.data.copy()
            new_cam.animation_data_clear()
            new_cam.location = point

            cam_constraint = new_cam.constraints.new(type='TRACK_TO')
            cam_constraint.track_axis = 'TRACK_NEGATIVE_Z'
            cam_constraint.up_axis = 'UP_Y'
            cam_constraint.target = bpy.data.objects[SPHERE_NAME]

            new_cam.name = f"{template_camera.name}_{i}"
            new_cam.data.name = f"{template_camera.name}_{i}"
            context.collection.objects.link(new_cam)

            if points.shape[0] > 1:
                # if there are more than one repetition, keyframe the camera locations for each frame
                for rep,coord in enumerate(points[:,i,:]):
                    new_cam.location = coord
                    new_cam.keyframe_insert(data_path='location', frame=scene.first_frame_nr + rep)
            
        bpy.data.objects.remove(bpy.data.objects[template_camera.name], do_unlink=True)
        context.space_data.stereo_3d_camera = 'MONO'
        return cam_handle_record, points

    def execute(self, context):

        ''' First, check that all inputs are valid '''
        scene = context.scene
        template_camera = scene.camera
        focal_length = template_camera.data.lens
        # check if camera is selected : next errors depend on an existing camera
        if template_camera == None:
            self.report({'ERROR'}, 'Be sure to have a selected camera!')
            return {'FINISHED'}
        
        # if there is an error, print first error message
        error_messages = helper.asserts(scene)
        if len(error_messages) > 0:
           self.report({'ERROR'}, error_messages[0])
           return {'FINISHED'}

        ''' 
        Proceed with setting up the scene and rendering settings.
        '''
        #output_data = helper.get_camera_intrinsics(scene, template_camera)
        camera_list, poses = self.prepare_scene(context)
        scene['cam_handles'] = camera_list # save the camera handles for later use

        # clean directory name (unsupported characters replaced) and output path
        output_dir = bpy.path.clean_name(scene.dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)
        os.makedirs(output_path, exist_ok=True)

        #np.save(os.path.join(scene.save_path, scene.dataset_name, 'tmp_camera_poses.npy'), poses) # write the temporary array with all camera poses to a file, overwrites each time the scene is set up
        helper.save_log_file(scene, focal_length, output_path) # log file also overwrites each time the scene is set up

        # initial property might have changed since set_init_props update
        scene.init_output_path = scene.render.filepath
        # other intial properties
        scene.init_sphere_exists = scene.show_sphere
        return {'FINISHED'}