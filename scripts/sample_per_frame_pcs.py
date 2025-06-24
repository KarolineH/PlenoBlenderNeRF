import open3d as o3d
import numpy as np
import os

def sample_dense_pc(ply_path, out_path, size=150000):
    '''
    Sample a dense point cloud from the initial state of the scene (frame 1)
    and save it as a .npz file. The array is saved in the format [x, y, z, r, g, b].
    The default size of 150,000 points is derived from the average size in the Dynamic 3D Gaussians dataset.
    '''

    mesh = o3d.io.read_triangle_mesh(ply_path)
    pc = mesh.sample_points_uniformly(number_of_points=size)
    points = np.asarray(pc.points)
    np.savez(out_path, data=points)
    # o3d.io.write_point_cloud(os.path.join(dataset_path, 'init_pt_cld.ply'), pc)
    return

if __name__ == "__main__":
    data_dir = "/media/karo/Data1/karo/synthetic_movement_dataset"
    out_dir = os.path.join(data_dir, 'per_frame_pcs')

    for sequence in os.listdir(os.path.join(data_dir, 'per_frame_ply_exports')):
        ply_files = os.listdir(os.path.join(data_dir, 'per_frame_ply_exports', sequence))
        for ply_file in ply_files:
            ply_path = os.path.join(data_dir, 'per_frame_ply_exports', sequence, ply_file)
            out_path = os.path.join(out_dir, sequence, ply_file.replace('.ply', '.npz'))
            os.makedirs(os.path.join(out_dir, sequence), exist_ok=True)
            sample_dense_pc(ply_path, out_path, size=300000)