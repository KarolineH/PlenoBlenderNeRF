import bpy

# plenoptic video ui class
class PLENO_UI(bpy.types.Panel):
    '''Plenoptic Video UI'''
    bl_idname = 'VIEW3D_PT_pleno_ui'
    bl_label = 'Plenoptic Video PLENO'
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
        layout.prop(scene, 'logs')
        layout.prop(scene, 'splats', text='Gaussian Points (PLY file)')

        layout.separator()
        layout.label(text='File Format')

        row = layout.row(align=True)
        row.prop(scene, 'nerf', toggle=True, text='NGP', invert_checkbox=True)
        row.prop(scene, 'nerf', toggle=True)

        layout.separator()
        layout.use_property_split = True
        layout.prop(scene, 'save_path')

        layout.prop(scene, 'camera')
        layout.prop(scene, 'sphere_location')
        layout.prop(scene, 'sphere_rotation')
        layout.prop(scene, 'sphere_scale')
        layout.prop(scene, 'sphere_radius')
        layout.prop(scene, 'focal')
        layout.prop(scene, 'seed')

        layout.prop(scene, 'nb_cameras')
        layout.prop(scene, 'upper_views', toggle=True)
        layout.prop(scene, 'outwards', toggle=True)

        layout.use_property_split = False
        layout.separator()
        layout.label(text='Preview')

        row = layout.row(align=True)
        row.prop(scene, 'show_sphere', toggle=True)

        layout.separator()
        layout.use_property_split = True
        layout.prop(scene, 'pleno_dataset_name')

        layout.separator()
        layout.operator('object.plenoptic_video', text='PLAY PLENO')