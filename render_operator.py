
        # TODO: Make a reset button? Maybe seperate out into two objects (executes), one that sets up the scene, one that does the render. So you can reset and redo without having to wait for render.
        # TODO: Do the render
        # TODO: save and reset
        # TODO: Move functions into sensible order, move some to the helper module

        #     # rendering
        #     if scene.render_frames:
        #         output_train = os.path.join(output_path, 'train')
        #         os.makedirs(output_train, exist_ok=True)
        #         scene.rendering = (False, False, True)
        #         scene.frame_end = scene.frame_start + scene.cos_nb_frames - 1 # update end frame
        #         scene.render.filepath = os.path.join(output_train, '') # training frames path
        #         bpy.ops.render.render('INVOKE_DEFAULT', animation=True, write_still=True) # render scene

        # # if frames are rendered, the below code is executed by the handler function
        # if not any(scene.rendering):
        #     # reset camera settings
        #     if not scene.init_camera_exists: helper.delete_camera(scene, CAMERA_NAME)
        #     if not scene.init_sphere_exists:
        #         objects = bpy.data.objects
        #         objects.remove(objects[EMPTY_NAME], do_unlink=True)
        #         scene.show_sphere = False
        #         scene.sphere_exists = False

        #     scene.camera = scene.init_active_camera

        #     # compress dataset and remove folder (only keep zip)
        #     shutil.make_archive(output_path, 'zip', output_path) # output filename = output_path
        #     shutil.rmtree(output_path)