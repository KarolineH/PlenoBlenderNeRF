import bpy
from . import helper, pleno_ui, scene_prep_operator, reset_operator, render_operator

# blender info
bl_info = {
    'name': 'PlenoBlenderNeRF',
    'description': 'Create plenoptic videos for dynamic NeRF dataset creation within Blender',
    'author': 'Karoline Heiwolt',
    'version': (0, 0, 1),
    'blender': (4, 3, 0),
    'location': '3D View > N panel > PlenoBlenderNeRF',
    'doc_url': 'https://github.com/KarolineH/PlenoBlenderNeRF',
    'category': 'Object',
}

# global addon variables
VERSION = '.'.join(str(x) for x in bl_info['version'])

# addon properties
PROPS = [
    # global controllable properties
    ('aabb', bpy.props.IntProperty(name='AABB', description='AABB scale as defined in Instant NGP', default=4, soft_min=1, soft_max=128) ),
    ('splats', bpy.props.BoolProperty(name='Gaussian Points', description='Whether to export a points3d.ply file for Gaussian Splatting', default=True) ),
    ('save_path', bpy.props.StringProperty(name='Save Path', description='Path to the output directory in which the synthetic dataset will be stored', subtype='DIR_PATH') ),

    # global automatic properties
    ('init_frame_step', bpy.props.IntProperty(name='Initial Frame Step') ),
    ('init_output_path', bpy.props.StringProperty(name='Initial Output Path', subtype='DIR_PATH') ),
    ('rendering', bpy.props.BoolProperty(name='Rendering', description='Whether this addon is rendering', default=False) ),
    ('plenoblendernerf_version', bpy.props.StringProperty(name='BlenderNeRF Version', default=VERSION) ),

    #pleno controllable properties
    ('dataset_name', bpy.props.StringProperty(name='Dataset Name', description='Name of the Pleno dataset : the data will be stored under <save path>/<name>', default='dataset') ),
    ('sphere_location', bpy.props.FloatVectorProperty(name='Location', description='Center position of the training sphere', unit='LENGTH', update=helper.properties_ui_upd) ),
    ('sphere_rotation', bpy.props.FloatVectorProperty(name='Rotation', description='Rotation of the training sphere', unit='ROTATION', update=helper.properties_ui_upd) ),
    ('sphere_scale', bpy.props.FloatVectorProperty(name='Scale', description='Scale of the training sphere in xyz axes', default=(1.0, 1.0, 1.0), update=helper.properties_ui_upd) ),
    ('sphere_radius', bpy.props.FloatProperty(name='Radius', description='Radius scale of the training sphere', default=4.0, soft_min=0.01, unit='LENGTH', update=helper.properties_ui_upd) ),
    ('seed', bpy.props.IntProperty(name='Seed', description='Random seed for sampling views on the training sphere', default=0) ),
    ('nb_cameras', bpy.props.IntProperty(name='Cameras', description='Number of fixed cameras placed on the sphere', default=30, soft_min=1) ),
    ('first_frame_nr', bpy.props.IntProperty(name='Start Frame Number', description='First frame of the animation to render', default=1, soft_min=1) ),
    ('final_frame_nr', bpy.props.IntProperty(name='End Frame Number', description='Last frame of the animation to render', default=48, soft_min=1) ),
    ('show_sphere', bpy.props.BoolProperty(name='Preview Sphere', description='Whether to show the training sphere from which random views will be sampled', default=False, update=helper.visualize_sphere) ),
    ('upper_views', bpy.props.BoolProperty(name='Upper Views', description='Whether to sample views from the upper hemisphere of the training sphere only', default=True) ),
    ('cam_distribution', bpy.props.BoolProperty(name='Random per-frame', description='Whether to place cameras in fixed uniformly sampled or random per-frame positions', default=False)),
    ('coordinate_frame', bpy.props.BoolProperty(name='Coordinate Frame Convention', description='Whether to use the NeRF/Blender or OpenCV/COLMAP camera coordinate frame convention', default=True)),

    # Pleno automatic properties
    ('sphere_exists', bpy.props.BoolProperty(name='Sphere Exists', description='Whether the sphere exists', default=False) ),
    ('init_sphere_exists', bpy.props.BoolProperty(name='Init sphere exists', description='Whether the sphere initially exists', default=False) ),
]

# classes to register / unregister
CLASSES = [
    pleno_ui.PLENO_UI,
    scene_prep_operator.ScenePrep,
    reset_operator.ResetScene,
    render_operator.RenderScene
]

# load addon
def register():
    for (prop_name, prop_value) in PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.app.handlers.render_complete.append(helper.post_render)
    bpy.app.handlers.render_cancel.append(helper.post_render)
    bpy.app.handlers.depsgraph_update_post.append(helper.properties_desgraph_upd)
    bpy.app.handlers.depsgraph_update_post.append(helper.set_init_props)

# deregister addon
def unregister():
    for (prop_name, _) in PROPS:
        delattr(bpy.types.Scene, prop_name)

    bpy.app.handlers.render_complete.remove(helper.post_render)
    bpy.app.handlers.render_cancel.remove(helper.post_render)
    bpy.app.handlers.depsgraph_update_post.remove(helper.properties_desgraph_upd)
    # bpy.app.handlers.depsgraph_update_post.remove(helper.set_init_props)

    for cls in CLASSES:
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()