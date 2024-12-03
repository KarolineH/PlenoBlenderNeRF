import os
import numpy as np
import bpy
import random
import mathutils
import datetime

from . import helper

# global addon script variables
SPHERE_NAME = 'PlenoSphere'
TMP_VERTEX_COLORS = 'plenoblendernerf_vertex_colors_tmp'

class ScenePrep(bpy.types.Operator):
    '''Plenoptic Video Scene Prep Operator'''
    bl_idname = 'object.scene_prep'
    bl_label = 'Plenoptic Video Scene Prep'

    # camera intrinsics
    def get_camera_intrinsics(self, scene, camera):
        camera_angle_x = camera.data.angle_x
        camera_angle_y = camera.data.angle_y

        # camera properties
        f_in_mm = camera.data.lens # focal length in mm
        scale = scene.render.resolution_percentage / 100
        width_res_in_px = scene.render.resolution_x * scale # width
        height_res_in_px = scene.render.resolution_y * scale # height
        optical_center_x = width_res_in_px / 2
        optical_center_y = height_res_in_px / 2

        # pixel aspect ratios
        size_x = scene.render.pixel_aspect_x * width_res_in_px
        size_y = scene.render.pixel_aspect_y * height_res_in_px
        pixel_aspect_ratio = scene.render.pixel_aspect_x / scene.render.pixel_aspect_y

        # sensor fit and sensor size (and camera angle swap in specific cases)
        if camera.data.sensor_fit == 'AUTO':
            sensor_size_in_mm = camera.data.sensor_height if width_res_in_px < height_res_in_px else camera.data.sensor_width
            if width_res_in_px < height_res_in_px:
                sensor_fit = 'VERTICAL'
                camera_angle_x, camera_angle_y = camera_angle_y, camera_angle_x
            elif width_res_in_px > height_res_in_px:
                sensor_fit = 'HORIZONTAL'
            else:
                sensor_fit = 'VERTICAL' if size_x <= size_y else 'HORIZONTAL'

        else:
            sensor_fit = camera.data.sensor_fit
            if sensor_fit == 'VERTICAL':
                sensor_size_in_mm = camera.data.sensor_height if width_res_in_px <= height_res_in_px else camera.data.sensor_width
                if width_res_in_px <= height_res_in_px:
                    camera_angle_x, camera_angle_y = camera_angle_y, camera_angle_x

        # focal length for horizontal sensor fit
        if sensor_fit == 'HORIZONTAL':
            sensor_size_in_mm = camera.data.sensor_width
            s_u = f_in_mm / sensor_size_in_mm * width_res_in_px
            s_v = f_in_mm / sensor_size_in_mm * width_res_in_px * pixel_aspect_ratio

        # focal length for vertical sensor fit
        if sensor_fit == 'VERTICAL':
            s_u = f_in_mm / sensor_size_in_mm * width_res_in_px / pixel_aspect_ratio
            s_v = f_in_mm / sensor_size_in_mm * width_res_in_px

        camera_intr_dict = {
            'camera_angle_x': camera_angle_x,
            'camera_angle_y': camera_angle_y,
            'fl_x': s_u,
            'fl_y': s_v,
            'k1': 0.0,
            'k2': 0.0,
            'p1': 0.0,
            'p2': 0.0,
            'cx': optical_center_x,
            'cy': optical_center_y,
            'w': width_res_in_px,
            'h': height_res_in_px,
            'aabb_scale': scene.aabb
        }

        return {'camera_angle_x': camera_angle_x} if scene.nerf else camera_intr_dict
    
    def save_log_file(self, scene, directory):
        now = datetime.datetime.now()

        logdata = {
            'PlenoBlenderNeRF Version': scene.plenoblendernerf_version,
            'Date and Time' : now.strftime("%d/%m/%Y %H:%M:%S"),
            'AABB': scene.aabb,
            'File Format': 'NeRF' if scene.nerf else 'NGP',
            'Save Path': scene.save_path
        }

        logdata['Sphere Location'] = str(list(scene.sphere_location))
        logdata['Sphere Rotation'] = str(list(scene.sphere_rotation))
        logdata['Sphere Scale'] = str(list(scene.sphere_scale))
        logdata['Sphere Radius'] = scene.sphere_radius
        logdata['Lens'] = str(scene.focal) + ' mm'
        logdata['Seed'] = scene.seed
        logdata['Number of Frames'] = scene.nb_frames
        logdata['Number of Cameras'] = scene.nb_cameras
        logdata['Upper Views'] = scene.upper_views
        logdata['Outwards'] = scene.outwards
        logdata['Dataset Name'] = scene.dataset_name

        helper.save_json(directory, filename='log.txt', data=logdata)

    # export vertex colors for each visible mesh
    def save_splats_ply(self, scene, directory):
        # create temporary vertex colors
        for obj in scene.objects:
            if obj.type == 'MESH':
                if not obj.data.vertex_colors:
                    obj.data.vertex_colors.new(name=TMP_VERTEX_COLORS)

        if bpy.context.object is None:
            self.report({'INFO'}, 'No object active. Setting first object as active.')
            bpy.context.view_layer.objects.active = bpy.data.objects[0]

        init_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        init_active_object = bpy.context.active_object
        init_selected_objects = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')

        # select only visible meshes
        for obj in scene.objects:
            if obj.type == 'MESH' and helper.is_object_visible(obj):
                obj.select_set(True)

        # save ply file
        bpy.ops.wm.ply_export(filepath=os.path.join(directory, 'points3d.ply'), export_normals=True, export_attributes=False, ascii_format=True)

        # remove temporary vertex colors
        for obj in scene.objects:
            if obj.type == 'MESH' and helper.is_object_visible(obj):
                if obj.data.vertex_colors:
                    obj.data.vertex_colors.remove(obj.data.vertex_colors[TMP_VERTEX_COLORS])

        bpy.context.view_layer.objects.active = init_active_object
        bpy.ops.object.select_all(action='DESELECT')

        # reselect previously selected objects
        for obj in init_selected_objects:
            obj.select_set(True)

        bpy.ops.object.mode_set(mode=init_mode)

    def sample_cam_poses(self, scene, num_cameras):
        # initialise random number generators
        seeds = [(2654435761 * (scene.seed + 1)) ^ (805459861 * (num + 1)) for num in range(num_cameras)]
        rngs = [random.Random(seed) for seed in seeds] # random number generators

        # sample random angles
        thetas = np.array([rng.random() * 2 * np.pi for rng in rngs])
        phis = np.array([np.arccos(1 - 2 * rng.random()) for rng in rngs]) # ensure uniform sampling from unit sphere

        # generate the position component
        unit_xs = np.cos(thetas) * np.sin(phis) 
        unit_ys = np.sin(thetas) * np.sin(phis)
        if scene.upper_views:
            unit_zs = [abs(np.cos(phi)) for phi in phis]
        else:
            unit_zs = [np.cos(phi) for phi in phis]
        unit_vectors = np.vstack((unit_xs, unit_ys, unit_zs)).T
        points = scene.sphere_radius * np.array(scene.sphere_scale) * unit_vectors
        overall_rotation = mathutils.Euler(scene.sphere_rotation).to_matrix() # in case the sphere is rotated in the scene
        points = (np.array(overall_rotation) @ points.T).T

        # generate the rotation component
        view_vectors = np.array(scene.sphere_location) - points # view vectors from camera poses to sphere origin
        up= np.array([0, 0, 1]) # define the up vector (world Z-axis)
        return points

    def prepare_scene(self, context):
        ### Places all the cameras and sets rendering settings
        # set up multiview rendering
        scene = context.scene
        template_camera = scene.camera
        scene.render.use_multiview = True # Activates multiview or "plenoptic" rendering option
        scene.render.views_format = 'MULTIVIEW' # use multiview as opposed to stereo 3D 
        default_cam_handles = ['left', 'right', 'RenderView'] # the first three cameras added to a multiview panel are always named this
        helper.create_sphere(context) # only creates the sphere if it does not already exist

        num_cameras = scene.nb_cameras
        points = self.sample_cam_poses(scene, num_cameras)

        cam_handle_record = [] # keep a record of pairs of object names and their corresponding camera handles for multi-view rendering
        bpy.ops.scene.render_view_add() # add a first additional camera in the multi-view menu
        for i, point in enumerate(points):
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
            cam_constraint.track_axis = 'TRACK_Z' if scene.outwards else 'TRACK_NEGATIVE_Z'
            cam_constraint.up_axis = 'UP_Y'
            cam_constraint.target = bpy.data.objects[SPHERE_NAME]
            
            new_cam.name = f"{template_camera.name}_{i}"
            new_cam.data.name = f"{template_camera.name}_{i}"
            context.collection.objects.link(new_cam)
            bpy.data.cameras[new_cam.name].lens = scene.focal
            
        bpy.data.objects.remove(bpy.data.objects[template_camera.name], do_unlink=True)
        return cam_handle_record
    
    def get_camera_extrinsics(self, scene, camera_list):
        camera_extr_dict = []
        for camera in camera_list:
            name = camera[1]
            cam_obj = scene.objects[name]
            cam_data = {
                'camera_object': cam_obj.name,
                'transform_matrix': helper.listify_matrix(cam_obj.matrix_world)
            }
            camera_extr_dict.append(cam_data)
        return camera_extr_dict

    def execute(self, context):

        ''' First, check that all inputs are valid '''
        scene = context.scene
        template_camera = scene.camera
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
        Proceed with setting up the scene and rendering settings 
        and record all static information before rendering.
        '''
        output_data = self.get_camera_intrinsics(scene, template_camera)
        camera_list = self.prepare_scene(context)

        # clean directory name (unsupported characters replaced) and output path
        output_dir = bpy.path.clean_name(scene.dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)
        os.makedirs(output_path, exist_ok=True)

        if scene.logs: self.save_log_file(scene, output_path)
        if scene.splats: self.save_splats_ply(scene, output_path)

        # initial property might have changed since set_init_props update
        scene.init_output_path = scene.render.filepath

        # other intial properties
        scene.init_sphere_exists = scene.show_sphere
        output_data['cameras'] = self.get_camera_extrinsics(scene, camera_list)
        helper.save_json(output_path, 'transforms.json', output_data)
        return {'FINISHED'}
