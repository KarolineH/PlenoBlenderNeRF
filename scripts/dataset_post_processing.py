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
        json.dump(train_metadata, f, indent=4)
    with open(os.path.join(dataset_path, 'test_meta.json'), 'w') as f:
        json.dump(test_metadata, f, indent=4)
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
    nppc = np.append(nppc, np.ones([size,1]), axis=1) # Add a column of ones as segmentation mask
    out_file = os.path.join(dataset_path, 'init_pt_cld.npz')
    np.savez(out_file, data=nppc)
    o3d.io.write_point_cloud(os.path.join(dataset_path, 'init_pt_cld.ply'), pc)
    return

def create_segmentation_masks(dataset_path):
    from PIL import Image

    input_img_dir = os.path.join(dataset_path, 'ims/')
    output_img_dir = os.path.join(dataset_path, 'seg/')

    def process_image(input_path, output_path):
        # Open the image
        img = Image.open(input_path).convert("RGBA")
        # Extract the alpha channel (transparency)
        alpha = img.split()[-1]
        # Create a binary mask (255 for white, 0 for black)
        binary_mask = Image.eval(alpha, lambda a: 255 if a > 0 else 0)
        # Save the mask
        binary_mask.save(output_path)

    # Walk through the input directory and replicate the structure
    for root, _, files in os.walk(input_img_dir):
        for file in files:
            if file.endswith(".png"):
                input_path = os.path.join(root, file)
                relative_path = os.path.relpath(input_path, input_img_dir)
                output_path = os.path.join(output_img_dir, relative_path)
                # Ensure the output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # Process the image
                process_image(input_path, output_path)


if __name__ == '__main__':
    dataset_path = '/media/karo/Data1/karo/synthetic_movement_dataset/DATA/rotation'
    # create_segmentation_masks(dataset_path)
    train_test_split(dataset_path, test_cameras=[3,9,20,31])
    sample_dense_pc(dataset_path)