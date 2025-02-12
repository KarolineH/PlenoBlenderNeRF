# PlenoBlenderNeRF
Blender add-on for recording plenoptic (multi-view) videos in NeRF/3DGS format of dynamic/animated scenes within Blender. 
If you have any comments or requests, please submit an issue. 

## Functionality
This add-on automatically sets up a 360° multi-camera array to render your animated scenes from multiple views. It also records the complete meta-data required for NeRF/Gaussian Splatting data sets (camera intrinsics, extrinsics, initial point cloud...).
You can choose to keep all cameras static across the frames of your animation, or randomly re-distribute all cameras at each single frame.
The add-on currently supports three different 360° camera setups, where all cameras are facing inwards towards the centre of the scene.
- Cameras placed on a full sphere
- Cameras placed on the upper hemisphere
- Cameras placed on a sphere, but excluding poses on the top 5% and bottom 30% of the sphere (similar to the [Panoptic Studio dataset](https://www.cs.cmu.edu/~hanbyulj/panoptic-studio/))

## Installation
1. Download this repository as a **ZIP** file
2. Open Blender (4.0.0 or above)
3. In Blender, head to **Edit > Preferences > Add-ons**, and select **Install From Disk** under the drop icon
4. Select the downloaded **ZIP** file
5. After installation, the add-on GUI is located in the sidebar menu. Press 'n' key to toggle the sidebar.


## Usage
1. Design your desired scene, including animations. Make sure to set all relevant Blender settings, including camera parameters, rendering engine, frame rate, output format etc., just as you would for an individual render.
2. Navigate to the PlenoBlenderNeRF add-on GUI in the sidebar.
3. Tip: Make sure the "Preview Sphere" switch in the PlenoBlenderNeRF add-on GUI is toggled ON so you can see more easily how each of the other parameters affects camera placement.  
4. Set all parameters in the PlenoBlenderNeRF add-on GUI. I recommend you play around with the settings a little bit.
  Changes are only adopted once you press the "SET UP SCENE" button. Hit "RESET SCENE" every time you want to make some more changes in the GUI.

     ![preview](https://github.com/user-attachments/assets/9e3c9615-9b1d-46cc-b603-cd7c25d535c5)  

  - AABB Parameter: The aabb scale parameter is used in [InstantNGP](https://github.com/NVlabs/instant-ngp), if you don't intend to use InstantNGP, feel free to ignore this one.
  - Gaussian Points: Tick this to also export a point cloud of the first frame. This will be needed if you intend to use any Gaussian Splatting methods.
  - NeRF/OpenCV Toggle: This toggle switches the output data format between the **OpenCV/COLMAP** camera coordinate frame convention and the **NeRF/Blender** frame convention. (E.g. [Dynamic 3D Gaussians](https://github.com/JonathonLuiten/Dynamic3DGaussians) uses the OpenCV camera coordinate system, while the standard for NeRF methods is the Blender coordinate system)
  - Save Path: Select a target directory for your data output.
  - Dataset Name: Specify a name for your output directory. Make sure to change this each time you render to avoid overwriting data.
  - Camera: Select a template camera object. This pre-selects the initial camera object by default. You can either edit this camera object to suit your scene or add your own and select it here via drag-and-drop. The selected camera object will serve as a template, which is duplicated for each additional camera in the plenoptic setup.
  - Location, Rotation, Scale: Use this to control the placement of the (invisible) sphere on whose surface your cameras will be placed. Use the Scale settings only if you need to scale differently along different axes — otherwise, change the radius settings instead.
  - Radius: The radius of the (invisible) sphere on whose surface your cameras will be placed.
  - Preview Sphere: Toggle this on to preview the invisible sphere on whose surface your cameras will be placed. This will not show in your renders.
  - Seed: There is some randomness in the *"per-frame"* camera placement procedure. However, this process is deterministic as long as you keep the seed constant. Change it if you want to see some different camera pose distributions.
  - Start Frame Number: The first frame of your animation (typically = 1).
  - End Frame Number: The last frame of your animation.
  - Cameras: The number of cameras/different views from which you want to render your scene. Each camera will render each frame.
  - View Selection: Full = Cameras will be placed on the full sphere surface; Upper = Cameras will be placed on the upper hemisphere; Mid-section = Cameras will be placed on the sphere but omitting the top 5% and bottom 30% of the sphere surface.
  - Camera distribution toggle: Toggle between static cameras (once generated, each camera will remain static across the animation/across frames) and per-frame (each camera will randomly be re-positioned for each frame of the animation).
5. Once you are happy with the settings, make sure to **hit RESET SCENE and then SET UP SCENE again**, so that all of your changes in the GUI are definitely applied before rendering.
(6. Recommended: Play back your animation one last time, also switch into Camera View in Blender to check if you are happy with the camera placement.
7. Hit 'RENDER'

## Optional Python post-processing functions:
8. Download the /scripts/ folder from this repo (either clone the repo or extract the subfolder from the zip file).
Navigate to the scripts folder, then install the requirements by running 
`pip install -r requirements.txt`
9. Find the file **scripts/dataset_post_processing.py** which was created with the input requirements of [Dynamic 3D Gaussians](https://github.com/JonathonLuiten/Dynamic3DGaussians) in mind. It has three main functions:
  - If you rendered your images with an alpha channel (in Blender, set Output format to png with RGBA color) you can use this to create foreground/background segmentation masks for all of your rendered images
  - You can use this to split your data into a training and test set. It creates separate train_meta.json and test_meta.json meta data files.
  - You can use this to sample a dense point cloud in .npz format from the original sparse point cloud in .ply format that Blender outputs.
10. Edit the file path at the bottom of the script to point to your rendered data sets.
    Consider changing the two variables
    - point_cloud_size: Number of points sampled for the dense point cloud.
    - test_cameras: Choose which cameras to use for testing only.
Then run:
  `python dataset_post_processing.py`
 
## Output
Your output should contain:
- **/ims/** Image folder, images are number by frame and organised in one folder per camera.
- **log.txt** A record of your PlenoBlenderNeRF settings.
- **meta.json** Meta-data for each image, including camera intrinsics and extrinsics. The format follows the requirements of [Dynamic 3D Gaussians](https://github.com/JonathonLuiten/Dynamic3DGaussians).
- **points3d.ply** A sparse point cloud sampled from the meshes in the first frame of your animation.

After the optional post-processing you will find these additional outputs:
- **test_meta.json** & **train_meta.json**, Separate meta-data files splitting the data into training and test sets.
- **/seg/** Binary segmentation mask folder, following the same structure as the image folder
- **init_pt_cld.npz** and **init_pt_cld.ply** Dense PointClouds sampled from the first frame of the animation. Default size is 150,000 points. You can change this in the post-processing script.

## Acknowledgement
This project started out as a fork from [BlenderNeRF](github.com/maximeraafat/BlenderNeRF), go check out their work as well.
