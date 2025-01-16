
TMP_VERTEX_COLORS = 'plenoblendernerf_vertex_colors_tmp'

    def save_log_file(self, scene, focal_length, directory):
        now = datetime.datetime.now()

        logdata = {
            'PlenoBlenderNeRF Version': scene.plenoblendernerf_version,
            'Date and Time' : now.strftime("%d/%m/%Y %H:%M:%S"),
            'AABB': scene.aabb,
            'File Format': 'NeRF' if scene.nerf else 'NGP',
            'Save Path': scene.save_path
        }

        logdata['Sphere Location'] = str(list(scene.sphere_location))
        logdata['Sphere Rotation'] = str(list(scene.sphere_rotation))
        logdata['Sphere Scale'] = str(list(scene.sphere_scale))
        logdata['Sphere Radius'] = scene.sphere_radius
        logdata['Lens'] = str(focal_length) + ' mm'
        logdata['Seed'] = scene.seed
        logdata['Number of Frames'] = scene.frame_end - scene.frame_start + 1
        logdata['Number of Cameras'] = scene.nb_cameras
        logdata['Upper Views'] = scene.upper_views
        logdata['Outwards'] = scene.outwards
        logdata['Dataset Name'] = scene.dataset_name

        helper.save_json(directory, filename='log.txt', data=logdata)

    # export vertex colors for each visible mesh
    def save_splats_ply(self, scene, directory):
        # create temporary vertex colors
        for obj in scene.objects:
            if obj.type == 'MESH':
                if not obj.data.vertex_colors:
                    obj.data.vertex_colors.new(name=TMP_VERTEX_COLORS)

        if bpy.context.object is None:
            self.report({'INFO'}, 'No object active. Setting first object as active.')
            bpy.context.view_layer.objects.active = bpy.data.objects[0]

        init_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        init_active_object = bpy.context.active_object
        init_selected_objects = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')

        # select only visible meshes
        for obj in scene.objects:
            if obj.type == 'MESH' and helper.is_object_visible(obj):
                obj.select_set(True)

        # save ply file
        bpy.ops.wm.ply_export(filepath=os.path.join(directory, 'points3d.ply'), export_normals=True, export_attributes=False, ascii_format=True)

        # remove temporary vertex colors
        for obj in scene.objects:
            if obj.type == 'MESH' and helper.is_object_visible(obj):
                if obj.data.vertex_colors:
                    obj.data.vertex_colors.remove(obj.data.vertex_colors[TMP_VERTEX_COLORS])

        bpy.context.view_layer.objects.active = init_active_object
        bpy.ops.object.select_all(action='DESELECT')

        # reselect previously selected objects
        for obj in init_selected_objects:
            obj.select_set(True)

        bpy.ops.object.mode_set(mode=init_mode)