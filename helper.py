import bpy
import os
import math
import shutil
import json
import datetime
import numpy as np
from bpy.app.handlers import persistent

SPHERE_NAME = 'PlenoSphere'

def is_power_of_two(x):
    return math.log2(x).is_integer()

# assert messages
def asserts(scene):
    camera = scene.camera
    dataset_name = scene.dataset_name
    error_messages = []

    if not camera.data.type == 'PERSP':
        error_messages.append('Only perspective cameras are supported!')
    if dataset_name == '':
        error_messages.append('Dataset name cannot be empty!')
    if any(x == 0 for x in scene.sphere_scale):
        error_messages.append('The sampling sphere cannot be flat! Change its scale to be non-zero in all axes.')
    if not is_power_of_two(scene.aabb):
        error_messages.append('AABB scale needs to be a power of two!')
    if scene.save_path == '':
        error_messages.append('Save path cannot be empty!')
    return error_messages

# camera intrinsics
def get_camera_intrinsics(scene, camera):
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

    return camera_intr_dict

def get_camera_extrinsics(scene, camera_list):

    camera_extrinsics = []

    if scene.cam_distribution:
        # if cameras are static, only one set of extrinsics is needed
        repetitions = 1
    else:
        repetitions = scene.final_frame_nr - scene.first_frame_nr + 1

    for rep in range(repetitions): # iterate over frames
        bpy.context.scene.frame_set(rep+1) # set the context to the current frame
        frame_extrinsics = []

        for camera in camera_list:
            name = camera[1]
            cam_obj = scene.objects[name]
            cam_data = np.array(cam_obj.matrix_world)
            if scene.coordinate_frame: 
                cam_data = convert_blender_to_opencv(cam_data) # convert from NeRF/Blender to OpenCV/COLMAP coordinate frame
            w2c = np.linalg.inv(cam_data) #! invert to get the w2c matrix, not the c2w matrix
            frame_extrinsics.append(listify_matrix(w2c))
        camera_extrinsics.append(frame_extrinsics)
    
    if scene.cam_distribution:
        camera_extrinsics = np.tile(camera_extrinsics, (scene.final_frame_nr - scene.first_frame_nr + 1, 1, 1, 1))
    
    return camera_extrinsics

def remove_trailing_zeros(obj):
    """Ensures numbers that can be integers are written as integers."""
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return int(obj) if obj.is_integer() else obj
    elif isinstance(obj, list):  # Recursively process lists
        return [remove_trailing_zeros(item) for item in obj]
    return obj

def convert_blender_to_opencv(pose):
    '''
    Convert a camera(!) pose from Blender to OpenCV coordinate frame.
    Accounting for the differences in both the local camera frame definition and also the global world coordinate frame convention.
    '''
    # Step 1: Flip y and z for each camera's orientation, keep locations the same
    camera_rotation_action = np.diag([1, -1, -1, 1])
    flipped = pose @ camera_rotation_action
    # Step 2: Rotate the camera position AND rotation about global x (clockwise), so by -90 degrees
    rotation_about_x = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    rotated = rotation_about_x @ flipped
    # Step 3: Rotate the camera position AND rotation about global z (counter-clockwise), so by +90 degrees 
    # rotation_about_z = np.array([[0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    rotation_about_y = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]])
    rotated = rotation_about_y @ rotated
    return rotated

def rotate_ply_to_opencv(ply_path):
    '''
    Rotate a PLY file from Blender to the OpenCV world coordinate frame.
    '''
    with(open(ply_path, 'r')) as f: 
        lines = f.readlines()

    for i,line in enumerate(lines): # find the number of points and the start index
        if 'element vertex' in line:
            num_points = int(line.split()[-1])
        if 'end_header' in line:
            start_index = i + 1
            break

    # Identify which lines to alter
    old_lines = lines[start_index:start_index+num_points]
    coordinates = np.array([line.split()[:3] for line in old_lines], dtype=np.float64)
    normals = np.array([line.split()[3:6] for line in old_lines], dtype=np.float64)

    # Step 1: Rotate all vertices and normals about x (clockwise), so by -90 degrees
    rotation_about_x = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    rotated = (rotation_about_x @ coordinates.T).T
    rotated_normals = (rotation_about_x @ normals.T).T

    # Step 2: Rotate all vertices and normals about y (counter-clockwise), so by +90 degrees
    rotation_about_y = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    rotated = (rotation_about_y @ rotated.T).T
    rotated_normals = (rotation_about_y @ rotated_normals.T).T

    # Format the new lines to match the old ones
    new_lines = [' '.join([str(coord) for coord in rotated[i]] + [str(norm) for norm in rotated_normals[i]]) + ' ' + ' '.join(old_lines[i].split()[6:]) + '\n' for i in range(num_points)]
    new_lines = [str.replace(line, '0.0 ', '0 ') for line in new_lines]
    # And save the file with the new lines
    lines[start_index:start_index+num_points] = new_lines
    with open(ply_path, 'w') as f:
        f.writelines(lines)
    return

def create_sphere(context):
    scene = context.scene
    if SPHERE_NAME not in scene.objects.keys() and not scene.sphere_exists:
        bpy.ops.object.empty_add(type='SPHERE')
        empty = context.active_object
        empty.name = SPHERE_NAME
        empty.location = scene.sphere_location
        empty.rotation_euler = scene.sphere_rotation
        empty.scale = scene.sphere_scale
        empty.empty_display_size = scene.sphere_radius
        scene.sphere_exists = True
        bpy.data.objects[SPHERE_NAME].hide_set(True) # hidden by default upon creation

def visualize_sphere(self, context):
    scene = context.scene
    if SPHERE_NAME not in scene.objects.keys() and not scene.sphere_exists:
        create_sphere(context)

    if SPHERE_NAME in scene.objects.keys() and scene.sphere_exists:
        if bpy.data.objects[SPHERE_NAME].hide_get():
            bpy.data.objects[SPHERE_NAME].hide_set(False)
        else:
            bpy.data.objects[SPHERE_NAME].hide_set(True)
    return

def save_log_file(scene, focal_length, directory):
    now = datetime.datetime.now()

    logdata = {
        'PlenoBlenderNeRF Version': scene.plenoblendernerf_version,
        'Date and Time' : now.strftime("%d/%m/%Y %H:%M:%S"),
        'AABB': scene.aabb,
        'Save Path': scene.save_path
    }

    logdata['Sphere Location'] = str(list(scene.sphere_location))
    logdata['Sphere Rotation'] = str(list(scene.sphere_rotation))
    logdata['Sphere Scale'] = str(list(scene.sphere_scale))
    logdata['Sphere Radius'] = scene.sphere_radius
    logdata['Lens'] = str(focal_length) + ' mm'
    logdata['Seed'] = scene.seed
    logdata['Number of Frames'] = scene.frame_end - scene.frame_start + 1
    logdata['Number of Cameras'] = scene.nb_cameras
    logdata['View Selection'] = scene.view_selection
    logdata['Dataset Name'] = scene.dataset_name
    logdata['Camera Distribution'] = 'Static uniform' if scene.cam_distribution else 'Random per-frame'
    logdata['Camera Coordinate Frame'] = 'OpenCV/COLMAP' if scene.coordinate_frame else 'NeRF/Blender'

    save_json(directory, filename='log.txt', data=logdata)
    return

# export vertex colors for each visible mesh
def save_splats_ply(scene, directory):

    bpy.context.scene.frame_set(scene.first_frame_nr) # set the context to the first frame!

    TMP_VERTEX_COLORS = 'plenoblendernerf_vertex_colors_tmp'
    # create temporary vertex colors
    for obj in scene.objects:
        if obj.type == 'MESH':
            if not obj.data.vertex_colors:
                obj.data.vertex_colors.new(name=TMP_VERTEX_COLORS)

    if bpy.context.object is None or bpy.context.active_object is None:
        bpy.context.view_layer.objects.active = bpy.data.objects[0]

    init_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')

    init_active_object = bpy.context.active_object
    init_selected_objects = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')

    # select only visible meshes
    for obj in scene.objects:
        if obj.type == 'MESH' and is_object_visible(obj):
            obj.select_set(True)

    # save ply file
    bpy.ops.wm.ply_export(filepath=os.path.join(directory, 'points3d.ply'), export_normals=True, export_colors='SRGB', export_attributes=False, export_triangulated_mesh=True, ascii_format=True)
    if scene.coordinate_frame:
        bpy.ops.wm.ply_export(filepath=os.path.join(directory, 'points3d(in_nerf_coordinate_frame).ply'), export_normals=True, export_attributes=False, ascii_format=True)
        rotate_ply_to_opencv(os.path.join(directory, 'points3d.ply'))

    # remove temporary vertex colors
    for obj in scene.objects:
        if obj.type == 'MESH' and is_object_visible(obj):
            if obj.data.vertex_colors:
                obj.data.vertex_colors.remove(obj.data.vertex_colors[TMP_VERTEX_COLORS])

    bpy.context.view_layer.objects.active = init_active_object
    bpy.ops.object.select_all(action='DESELECT')

    # reselect previously selected objects
    for obj in init_selected_objects:
        obj.select_set(True)

    bpy.ops.object.mode_set(mode=init_mode)
    return
    
# check whether an object is visible in render
def is_object_visible(obj):
    if obj.hide_render:
        return False

    for collection in obj.users_collection:
        if collection.hide_render:
            return False
    return True

def save_json(directory, filename, data, indent=4):
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=indent)

        # function from original nerf 360_view.py code for blender
def listify_matrix(matrix):
    matrix_list = []
    for row in matrix:
        matrix_list.append(list(row))
    return matrix_list

## two way property link between sphere and ui (property and handler functions)
# https://blender.stackexchange.com/questions/261174/2-way-property-link-or-a-filtered-property-display

def properties_ui_upd(self, context):
    can_scene_upd(self, context)

@persistent
def properties_desgraph_upd(scene):
    can_properties_upd(scene)

def properties_ui(self, context):
    scene = context.scene

    if SPHERE_NAME in scene.objects.keys():
        upd_off()
        bpy.data.objects[SPHERE_NAME].location = scene.sphere_location
        bpy.data.objects[SPHERE_NAME].rotation_euler = scene.sphere_rotation
        bpy.data.objects[SPHERE_NAME].scale = scene.sphere_scale
        bpy.data.objects[SPHERE_NAME].empty_display_size = scene.sphere_radius
        upd_on()

# if empty sphere modified outside of ui panel, edit panel properties
def properties_desgraph(scene):
    if scene.show_sphere and SPHERE_NAME in scene.objects.keys():
        upd_off()
        scene.sphere_location = bpy.data.objects[SPHERE_NAME].location
        scene.sphere_rotation = bpy.data.objects[SPHERE_NAME].rotation_euler
        scene.sphere_scale = bpy.data.objects[SPHERE_NAME].scale
        scene.sphere_radius = bpy.data.objects[SPHERE_NAME].empty_display_size
        upd_on()


    if SPHERE_NAME not in scene.objects.keys() and scene.sphere_exists:
        scene.show_sphere = False
        scene.sphere_exists = False

def empty_fn(self, context): pass

can_scene_upd = properties_ui
can_properties_upd = properties_desgraph

def upd_off():  # make sub function to an empty function
    global can_scene_upd, can_properties_upd
    can_scene_upd = empty_fn
    can_properties_upd = empty_fn
def upd_on():
    global can_scene_upd, can_properties_upd
    can_scene_upd = properties_ui
    can_properties_upd = properties_desgraph

def organise_folder_structure(directory):
    ''' 
    Organise the output folder structure.
    Follows the structure from Dynamic 3D Gaussians.
    '''
    # find all files ending in png jpg jpeg
    file_extension = bpy.context.scene.render.image_settings.file_format.lower()
    img_files = sorted([name for name in os.listdir(directory) if name.lower().endswith(file_extension)])

    if not img_files:
        return
    else:
        for image in img_files:
            frame_str, camera_str = image.split('.')[0].split('_')
            frame_num = int(frame_str)
            camera_num = int(camera_str)

            # Create camera folder if it doesn't exist
            camera_folder = os.path.join(directory, 'ims', str(camera_num))
            os.makedirs(camera_folder, exist_ok=True)

            current_path = os.path.join(directory, image)
            new_path = os.path.join(camera_folder, f"{frame_num:06d}.{file_extension}")
            shutil.move(current_path, new_path)
    return

# reset properties back to intial
@persistent
def post_render(scene):
    if scene.rendering: # execute this function only when rendering with addon

        organise_folder_structure(scene.render.filepath) # organise folder structure into subfolders

        dataset_name = scene.dataset_name
        # do some clean up of the scene here if you want
        scene.rendering = False
        scene.render.filepath = scene.init_output_path # reset filepath

        # clean directory name (unsupported characters replaced) and output path
        output_dir = bpy.path.clean_name(dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)

        # compress dataset and remove folder (only keep zip) #!Paused for now, keep the uncompressed version
        # shutil.make_archive(output_path, 'zip', output_path) # output filename = output_path
        # shutil.rmtree(output_path)

# set initial property values (bpy.data and bpy.context require a loaded scene)
@persistent
def set_init_props(scene):
    filepath = bpy.data.filepath
    filename = bpy.path.basename(filepath)
    default_save_path = filepath[:-len(filename)] # remove file name from blender file path = directoy path

    scene.save_path = default_save_path
    scene.init_frame_step = scene.frame_step
    scene.init_output_path = scene.render.filepath

    bpy.app.handlers.depsgraph_update_post.remove(set_init_props)