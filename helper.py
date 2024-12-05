import bpy
import os
import math
import shutil
import json
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

    if not scene.nerf and not is_power_of_two(scene.aabb):
        error_messages.append('AABB scale needs to be a power of two!')
    if scene.save_path == '':
        error_messages.append('Save path cannot be empty!')
    if scene.splats and scene.render.image_settings.file_format != 'PNG':
        error_messages.append('Gaussian Splatting requires PNG file extensions!')
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

    return {'camera_angle_x': camera_angle_x} if scene.nerf else camera_intr_dict

def get_camera_extrinsics(scene, camera_list):
    camera_extr_dict = []
    for camera in camera_list:
        name = camera[1]
        cam_obj = scene.objects[name]
        cam_data = {
            'camera_object': cam_obj.name,
            'transform_matrix': listify_matrix(cam_obj.matrix_world)
        }
        camera_extr_dict.append(cam_data)
    return camera_extr_dict

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

# reset properties back to intial
@persistent
def post_render(scene):
    if scene.rendering: # execute this function only when rendering with addon
        dataset_name = scene.dataset_name
        # do some clean up of the scene here if you want
        scene.rendering = False
        scene.render.filepath = scene.init_output_path # reset filepath

        # clean directory name (unsupported characters replaced) and output path
        output_dir = bpy.path.clean_name(dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)

        # compress dataset and remove folder (only keep zip)
        shutil.make_archive(output_path, 'zip', output_path) # output filename = output_path
        shutil.rmtree(output_path)

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