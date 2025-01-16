import bpy
import os
import shutil

class RenderScene(bpy.types.Operator):
    '''Plenoptic Video Scene Rendering Operator'''
    bl_idname = 'object.renderer'
    bl_label = 'Plenoptic Video Renderer'

    def render(self, scene, output_path):
        scene.rendering = True
        scene.render.filepath = os.path.join(output_path, '') # training frames path
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True, write_still=True) # render scene
        return 'FINISHED'

    def execute(self, context):
        scene = context.scene
        # clean directory name (unsupported characters replaced) and output path
        #TODO: Make sure all meta data, point clouds are written to file at the beginning of rendering
        #TODO: Make sure the user-specified end frame number is set correctly just before rendering, make sure rendering stops at the correct frame

        output_dir = bpy.path.clean_name(scene.dataset_name)
        output_path = os.path.join(scene.save_path, output_dir)
        os.makedirs(output_path, exist_ok=True)

        self.render(scene, output_path) # RENDER SCENE
        return {'FINISHED'}

        # compress dataset and remove folder (only keep zip)
        # shutil.make_archive(output_path, 'zip', output_path) # output filename = output_path
        # shutil.rmtree(output_path)