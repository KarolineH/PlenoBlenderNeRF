import bpy
import json
import os


''' 
Run this within the Blender to export the coordinate trajectories of all mesh vertices in the scene.
Works best if you apply subdivision modifiers to the objects first so there are dense meshes with plenty of vertices.
The output will be a JSON file containing the trajectories of each vertex across all frames where it is present.
'''

scene = bpy.context.scene
trajectories = {}

for frame in range(scene.first_frame_nr, scene.final_frame_nr + 1):
    bpy.context.scene.frame_set(frame)

    # Evaluate depsgraph to get modifiers and animations applied
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    for obj in mesh_objects:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        world_matrix = eval_obj.matrix_world

        obj_name = obj.name
        if obj_name not in trajectories:
            trajectories[obj_name] = {}

        for idx, vert in enumerate(eval_mesh.vertices):
            world_coord = world_matrix @ vert.co
            trajectories[obj_name].setdefault(idx, {})[frame] = (world_coord.x, world_coord.y, world_coord.z)

        eval_obj.to_mesh_clear()

# Save trajectories to a JSON file
current_path = '/'.join(bpy.data.filepath.split('/')[:-1])
file_name = bpy.data.filepath.split('/')[-1].split('.')[0] + '.json'
save_path = os.path.join(current_path, file_name)

with open(save_path, 'w') as f:
    json.dump(trajectories, f, indent=4)