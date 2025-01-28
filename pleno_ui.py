import bpy

# plenoptic video ui class
class PLENO_UI(bpy.types.Panel):
    '''Plenoptic Video UI'''
    bl_idname = 'VIEW3D_PT_pleno_ui'
    bl_label = 'Plenoptic Video NeRF dataset creator (PlenoBlenderNeRF)'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PlenoBlenderNeRF'
    #bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.alignment = 'CENTER'

        layout.use_property_split = True
        layout.prop(scene, 'aabb')
        layout.prop(scene, 'splats', text='Gaussian Points (PLY file)')
        row = layout.row(align=True)
        row.prop(scene, 'coordinate_frame', toggle=True, text='NeRF', invert_checkbox=True)
        row.prop(scene, 'coordinate_frame', toggle=True, text='OpenCV')

        layout.separator()
        layout.use_property_split = True
        layout.prop(scene, 'save_path')
        layout.prop(scene, 'dataset_name')

        layout.prop(scene, 'camera')
        layout.prop(scene, 'sphere_location')
        layout.prop(scene, 'sphere_rotation')
        layout.prop(scene, 'sphere_scale')
        layout.prop(scene, 'sphere_radius')
        row = layout.row(align=True)
        row.prop(scene, 'show_sphere', toggle=True)
        
        layout.separator()
        layout.prop(scene, 'seed')
        layout.prop(scene, 'first_frame_nr')
        layout.prop(scene, 'final_frame_nr')
        layout.prop(scene, 'nb_cameras')
        layout.prop(scene, 'view_selection')

        layout.label(text='Camera distribution')
        row = layout.row(align=True)
        row.prop(scene, 'cam_distribution', toggle=True, text='per-frame', invert_checkbox=True)
        row.prop(scene, 'cam_distribution', toggle=True, text='static')

        layout.operator('object.scene_prep', text='SET UP SCENE')
        layout.operator('object.scene_reset', text='RESET SCENE')
        layout.operator('object.renderer', text='RENDER')
