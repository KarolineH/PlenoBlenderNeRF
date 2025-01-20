import open3d as o3d
import os
import numpy as np
import json

def train_test_split(dataset_path, test_cameras=[]):

    full_metadata = json.load(open(os.path.join(dataset_path, 'meta.json')))
    test_metadata = {}
    train_metadata = {}

    # Since all recorded cameras share the same intrinsics, we only change the shape of the array
    num_frames = np.asarray(full_metadata['cam_id']).shape[0]
    original_num_cam = np.asarray(full_metadata['cam_id']).shape[1]
    test_cameras = sorted(test_cameras)
    train_cameras = list(range(original_num_cam))
    [train_cameras.remove(ID) for ID in test_cameras]

    train_metadata['w'] = full_metadata['w']
    train_metadata['h'] = full_metadata['h']
    test_metadata['w'] = full_metadata['w']
    test_metadata['h'] = full_metadata['h']

    train_metadata['k'] = np.tile(np.asarray(full_metadata['k'])[0,0], (num_frames, len(train_cameras), 1, 1)).tolist()
    test_metadata['k'] = np.tile(np.asarray(full_metadata['k'])[0,0], (num_frames, len(test_cameras), 1, 1)).tolist()

    test_metadata['w2c'] = np.asarray(full_metadata['w2c'])[:,test_cameras,:,:].tolist()
    train_metadata['w2c'] = np.asarray(full_metadata['w2c'])[:,train_cameras,:,:].tolist()

    test_metadata['fn'] = np.asarray(full_metadata['fn'])[:,test_cameras].tolist()
    train_metadata['fn'] = np.asarray(full_metadata['fn'])[:,train_cameras].tolist()

    train_metadata['cam_id'] = np.tile(np.asarray(train_cameras), (num_frames,1)).tolist()
    test_metadata['cam_id'] = np.tile(np.asarray(test_cameras), (num_frames,1)).tolist()

    with open(os.path.join(dataset_path, 'train_meta.json'), 'w') as f:
        json.dump(train_metadata, f)
    with open(os.path.join(dataset_path, 'test_meta.json'), 'w') as f:
        json.dump(test_metadata, f)
    return


def sample_dense_pc(dataset_path, size=150000):
    '''
    Sample a dense point cloud from the initial state of the scene (frame 1)
    and save it as a .npz file. The array is saved in the format [x, y, z, r, g, b].
    The default size of 150,000 points is derived from the average size in the Dynamic 3D Gaussians dataset.
    '''

    mesh = o3d.io.read_triangle_mesh(os.path.join(dataset_path, 'points3d.ply'))
    pc = mesh.sample_points_uniformly(number_of_points=size)
    points = np.asarray(pc.points)
    colours = np.asarray(pc.colors)
    nppc = np.append(points, colours, axis=1)
    out_file = os.path.join(dataset_path, 'init_pt_cld.npz')
    np.savez(out_file, data=nppc)
    o3d.io.write_point_cloud(os.path.join(dataset_path, 'init_pt_cld.ply'), pc)
    return

train_test_split('/home/karo/ws/PlenoBlenderNeRF/tests/dataset9', test_cameras=[2,0])
sample_dense_pc('/home/karo/ws/PlenoBlenderNeRF/tests/dataset9')