import open3d as o3d
import os
import numpy as np
import json
from PIL import Image
import shutil

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

    train_metadata['w'] = remove_trailing_zeros(full_metadata['w'])
    train_metadata['h'] = remove_trailing_zeros(full_metadata['h'])
    test_metadata['w'] = remove_trailing_zeros(full_metadata['w'])
    test_metadata['h'] = remove_trailing_zeros(full_metadata['h'])

    train_metadata['k'] = remove_trailing_zeros(np.tile(np.asarray(full_metadata['k'])[0,0], (num_frames, len(train_cameras), 1, 1)).tolist())
    test_metadata['k'] = remove_trailing_zeros(np.tile(np.asarray(full_metadata['k'])[0,0], (num_frames, len(test_cameras), 1, 1)).tolist())

    test_metadata['w2c'] = remove_trailing_zeros(np.asarray(full_metadata['w2c'])[:,test_cameras,:,:].tolist())
    train_metadata['w2c'] = remove_trailing_zeros(np.asarray(full_metadata['w2c'])[:,train_cameras,:,:].tolist())

    test_metadata['fn'] = np.asarray(full_metadata['fn'])[:,test_cameras].tolist()
    train_metadata['fn'] = np.asarray(full_metadata['fn'])[:,train_cameras].tolist()

    train_metadata['cam_id'] = np.tile(np.asarray(train_cameras), (num_frames,1)).tolist()
    test_metadata['cam_id'] = np.tile(np.asarray(test_cameras), (num_frames,1)).tolist()

    with open(os.path.join(dataset_path, 'train_meta.json'), 'w') as f:
        json.dump(train_metadata, f, indent=4)
    with open(os.path.join(dataset_path, 'test_meta.json'), 'w') as f:
        json.dump(test_metadata, f, indent=4)
    return

def remove_trailing_zeros(in_obj):
    if isinstance(in_obj, int):
        return in_obj
    if isinstance(in_obj, float):
        return int(in_obj) if in_obj.is_integer() else in_obj
    if isinstance(in_obj, list):
        return [remove_trailing_zeros(item) for item in in_obj]
    return in_obj

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
    '''
    If your rendered images have an alpha channel (RGBA) and some background is visible within them,
    then this function will create a binary mask for each image. Foreground pixels are set to 255, background to 0.
    '''

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


def alpha_composite_linear(fg_img, bg_color=(0, 0, 0)):
    """
    Alpha composite an RGBA PIL image with straight alpha over a solid bg color.
    
    Args:
        fg_img: PIL Image in RGBA mode (sRGB + straight alpha)
        bg_color: tuple of 3 ints (0-255), background RGB in sRGB
    
    Returns:
        PIL Image in RGB mode with proper compositing done in linear space.
    """
    def srgb_to_linear(c):
        """Convert sRGB [0..1] to linear RGB."""
        a = 0.055
        c = np.clip(c, 0, 1)
        linear = np.where(c <= 0.04045,
                        c / 12.92,
                        ((c + a) / (1 + a)) ** 2.4)
        return linear

    def linear_to_srgb(c):
        """Convert linear RGB [0..1] to sRGB."""
        a = 0.055
        c = np.clip(c, 0, 1)
        srgb = np.where(c <= 0.0031308,
                        c * 12.92,
                        (1 + a) * (c ** (1 / 2.4)) - a)
        return srgb

    fg = np.array(fg_img).astype(np.float32) / 255.0
    alpha = fg[..., 3:4]  # shape (H,W,1)
    fg_rgb = fg[..., :3]

    # Convert fg RGB and bg color to linear
    fg_rgb_lin = srgb_to_linear(fg_rgb)
    bg_rgb = np.array(bg_color).astype(np.float32) / 255.0
    bg_rgb_lin = srgb_to_linear(bg_rgb)

    # Composite in linear space
    comp_lin = fg_rgb_lin * alpha + bg_rgb_lin * (1 - alpha)

    # Convert back to sRGB
    comp_srgb = linear_to_srgb(comp_lin)

    # Convert to uint8 image
    comp_img = (comp_srgb * 255).round().astype(np.uint8)
    return Image.fromarray(comp_img, mode="RGB")

def bg_composite(dataset_path, bg=(0,0,0)):
    '''
    Moves the original (rendered) RGBA images from the '/ims/' folder to /alpha_ims/
    and replaces the images with alpha-composited RGB versions.
    Default background colour is black (0,0,0).  
    '''
    input_img_dir = os.path.join(dataset_path, 'ims/')
    alpha_img_dir = os.path.join(dataset_path, 'alpha_ims/')

    # Walk through the input directory and replicate the structure
    for root, _, files in os.walk(input_img_dir):
        for filename in files:
            if filename.endswith(".png"):
                input_path = os.path.join(root, filename)
                relative_path = os.path.relpath(input_path, input_img_dir)
                alpha_path = os.path.join(alpha_img_dir, relative_path)
                # Ensure the output directory exists
                os.makedirs(os.path.dirname(alpha_path), exist_ok=True)

                shutil.copyfile(input_path, alpha_path)

                im = Image.open(input_path).convert("RGBA")
                comp = alpha_composite_linear(im, bg_color=bg)
                comp.save(input_path)
    print(f"Alpha-composited images saved to {input_img_dir}.")
    return

if __name__ == '__main__':

    ## ------------------------------------------------------------------  
    ''' USER INPUTS '''
    folder = '/your/dataset/location/' # This folder can contain multiple data sets generated by the add-on, each in its own subfolder
    point_cloud_size = 150000
    test_cameras = [3,9,20,31]
    ##-----------------------------------------------------------------

    for item in os.listdir(folder):
        scene_path = os.path.join(folder, item.split('.')[0])
        
        '''1) Use this function to produce crude foreground/background segmentation masks for all images, if your images have an Alpha Channel (RGBA)'''
        create_segmentation_masks(scene_path)

        '''2) Use this function to split the data set into training and testing sets. Specify the ID numbers of the cameras you want to use for testing.'''
        train_test_split(scene_path, test_cameras=test_cameras)
        
        '''3) Use this function to sample a dense point cloud from the sparse point cloud Blender outputs (first frame of your animation)'''
        sample_dense_pc(scene_path, size=point_cloud_size)

        '''4) Use this function to composite the RGBA images with a solid background colour.'''
        bg_composite(scene_path, bg=(0,0,0))