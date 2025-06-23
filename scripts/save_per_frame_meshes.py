import bpy
import os 
import numpy as np


''' 
Run this within Blender 
to export the meshes of all visible objects in the scene as PLY files for each frame.
'''

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

def is_object_visible(obj):
    if obj.hide_render:
        return False

    for collection in obj.users_collection:
        if collection.hide_render:
            return False
    return True

scene = bpy.context.scene
scene.frame_set(scene.first_frame_nr) # set the context to the first frame!

current_path = '/'.join(bpy.data.filepath.split('/')[:-1])
output_path = os.path.join(current_path, 'ply_exports', bpy.data.filepath.split('/')[-1].split('.')[0])
os.makedirs(output_path, exist_ok=True)

scene = bpy.context.scene

for frame in range(scene.first_frame_nr, scene.final_frame_nr + 1):
    scene.frame_set(frame)

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
 
    filename = f"frame_{frame:04d}.ply"
    filepath = os.path.join(output_path, filename)

    if bpy.data.filepath.split('/')[-1].split('.')[0] == 'hole_formation':
        bpy.ops.wm.ply_export(filepath=filepath, export_selected_objects=True, export_normals=True, export_colors='NONE', export_attributes=False, export_triangulated_mesh=True, ascii_format=True)
    else:
        bpy.ops.wm.ply_export(filepath=filepath, export_selected_objects=True, export_normals=True, export_colors='NONE', export_attributes=False, export_triangulated_mesh=False, ascii_format=True)
    rotate_ply_to_opencv(filepath)

    bpy.context.view_layer.objects.active = init_active_object
    bpy.ops.object.select_all(action='DESELECT')
