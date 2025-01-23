import json
import numpy as np
import os
import open3d as o3d

'''
# ! This is script intended for debugging purposes.
Run this as a stand-alone script to plot the exported camera poses and point clouds in the same frame.
'''

def plot_3d_scene(dataset_path):
    metadata = json.load(open(os.path.join(dataset_path, 'train_meta.json')))
    pc = get_cam_pc(metadata)
    scene = get_scene_cloud(dataset_path)
    frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
    o3d.visualization.draw_geometries([scene, pc, frame])

def get_cam_pc(metadata):
    pc = o3d.geometry.PointCloud()
    mats = np.array([np.linalg.inv(mat) for mat in np.array(metadata['w2c'])[0]]) # ! Invert the matrices to plot c2w (= camera poses) instead of w2c
    pc.points = o3d.utility.Vector3dVector(mats[:,:3,-1])
    pc.normals = o3d.utility.Vector3dVector(mats[:,:3,-2])
    return pc

def get_scene_cloud(dataset_path):
    data = np.load(os.path.join(dataset_path, 'init_pt_cld.npz'))['data']
    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(data[:,:3])
    pc.colors = o3d.utility.Vector3dVector(data[:,3:6])
    return pc

def compare_two_scenes(path_1, path_2):
    metadata_1 = json.load(open(os.path.join(path_1, 'train_meta.json')))
    metadata_2 = json.load(open(os.path.join(path_2, 'train_meta.json')))
    pc_1 = get_cam_pc(metadata_1)
    pc_1.paint_uniform_color([1, 0, 0])
    pc_2 = get_cam_pc(metadata_2)
    pc_2.paint_uniform_color([0, 0, 1])
    scene_1 = get_scene_cloud(path_1)
    scene_2 = get_scene_cloud(path_2)
    frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1) # size can be adjusted, but 1 = 1 meter
    o3d.visualization.draw_geometries([scene_1, scene_2, pc_1, pc_2, frame])


if __name__ == '__main__':
    
    path1= '/media/karo/Data1/karo/Other_NeRF_Datasets/Dynamic3DGaussians_Set/data/juggle'
    path2 = '/media/karo/Data1/karo/synthetic_movement_dataset/scenes/rotation'

    plot_3d_scene(path1)
    compare_two_scenes(path1, path2)