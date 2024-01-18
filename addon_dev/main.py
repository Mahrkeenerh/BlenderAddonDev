import os
import shutil
import sys

import bpy
import addon_utils
from bpy_extras.io_utils import ImportHelper


class AddonGroup(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(
        name='path',
        description='Path to addon folder/python file',
        subtype='DIR_PATH'
    )

    def on_include_update(self, context):
        if self.include:
            load_addon(self.path)
        else:
            unload_addon(self.path)

    include: bpy.props.BoolProperty(
        name='include',
        description='Enable/Disable addon',
        default=True,
        update=on_include_update
    )


def get_module_names(path: str) -> tuple[str, str]:
    """Get the module name from a path"""

    module_name = os.path.basename(path) if os.path.isdir(path) else os.path.splitext(os.path.basename(path))[0]
    raw_name = os.path.basename(path)

    return module_name, raw_name


def update_garbage_list() -> None:
    """Return the garbage string"""

    addons = bpy.context.scene.addev_addons

    paths = [i.path for i in addons]
    garbage_string = "|".join(paths)

    bpy.context.preferences.addons['addon_dev'].preferences.addons_garbage = garbage_string


def load_addon(path: str) -> str:
    """Load an addon from a path
    
    shutil copy (overwrite) to the addons folder
    delete from sys.modules
    enable addon

    return module name
    """

    is_dir = os.path.isdir(path)
    module_name, raw_name = get_module_names(path)

    full_path = os.path.join(
        bpy.utils.user_resource("SCRIPTS"),
        "addons",
        raw_name
    )

    # Check if path already exists
    if os.path.exists(full_path):
        if is_dir:
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)

    # Copy the addon to the addons folder
    if is_dir:
        shutil.copytree(path, full_path)
    else:
        shutil.copy(path, full_path)

    for name in sorted(list(sys.modules.keys())):
        if name.startswith(f"{module_name}."):
            del sys.modules[name]

    if module_name in sys.modules:
        del sys.modules[module_name]

    bpy.ops.preferences.addon_enable(module=module_name)

    update_garbage_list()

    return module_name


def unload_addon(path: str):
    """Unload an addon by path"""

    module_name, raw_name = get_module_names(path)
    is_enabled, is_loaded = addon_utils.check(module_name)

    if not is_enabled or not is_loaded:
        print("Addon not loaded", path)
        return

    bpy.ops.preferences.addon_disable(module=module_name)


class ADDEV_OT_AddNewAddon(bpy.types.Operator, ImportHelper):
    bl_idname = "addev.add_new_addon"
    bl_label = "Add New Addon"
    bl_description = "Add a new addon to the dev list"
    bl_options = {"REGISTER", "UNDO"}
    filter_glob: bpy.props.StringProperty(
        default='*.',
        options={'HIDDEN'}
    )

    def execute(self, context):
        if os.path.isdir(self.filepath):
            addon_path = os.path.normpath(self.filepath)
        else:
            addon_path = os.path.dirname(self.filepath)

        # Check if addon is already in list, or if it is already loaded
        for addon in bpy.context.scene.addev_addons:
            if addon.path == addon_path:
                self.report({'ERROR'}, message=f'ADDEV AddNewAddon: Addon already in list')
                return {"FINISHED"}

        module_name, raw_name = get_module_names(addon_path)
        is_enabled, is_loaded = addon_utils.check(module_name)

        if is_enabled or is_loaded:
            self.report({'ERROR'}, message=f'ADDEV AddNewAddon: Addon already exists')
            return {"FINISHED"}

        addon_name = load_addon(addon_path)
        bpy.context.scene.addev_addons.add().path = addon_path

        self.report({'INFO'}, message=f'Loaded: {addon_name}')
        return {"FINISHED"}


class ADDEV_OT_AddSinglePyAddon(bpy.types.Operator, ImportHelper):
    bl_idname = "addev.add_single_py_addon"
    bl_label = "Add single py Addon"
    bl_description = "Add single .py file addon to the dev list"
    bl_options = {"REGISTER", "UNDO"}
    filter_glob: bpy.props.StringProperty(
        default='*.py',
        options={'HIDDEN'}
    )

    def execute(self, context):
        addon_path = os.path.normpath(self.filepath) 

        # Check if addon is already in list, or if it is already loaded
        for addon in bpy.context.scene.addev_addons:
            if addon.path == addon_path:
                self.report({'ERROR'}, message=f'ADDEV AddSinglePyAddon: Addon already in list')
                return {"FINISHED"}

        module_name, raw_name = get_module_names(addon_path)
        is_enabled, is_loaded = addon_utils.check(module_name)

        if is_enabled or is_loaded:
            self.report({'ERROR'}, message=f'ADDEV AddSinglePyAddon: Addon already exists')
            return {"FINISHED"}

        addon_name = load_addon(addon_path)
        self.report({'INFO'}, message=f'Loaded: {addon_name}')
        return {"FINISHED"}


class ADDEV_OT_RemoveAddon(bpy.types.Operator):
    bl_idname = "addev.remove_addon"
    bl_label = "Remove Addon"
    bl_description = "Remove addon from dev list"
    bl_options = {"REGISTER", "UNDO"}
    index: bpy.props.IntProperty(
        name='index',
        description='addon index to remove from list',
        options={'HIDDEN'},
        min=0
    )

    def execute(self, context):
        if len(bpy.context.scene.addev_addons) <= self.index:
            self.report({'ERROR'}, message=f'ADDEV RemoveAddon: Index out of range')
            return {"FINISHED"}

        if bpy.context.scene.addev_addons[self.index].include:
            bpy.context.scene.addev_addons[self.index].include = False
        bpy.context.scene.addev_addons.remove(self.index)

        update_garbage_list()
        return {"FINISHED"}


class ADDEV_OT_ReloadAddon(bpy.types.Operator):
    bl_idname = "addev.reload_addon"
    bl_label = "Reload Addon"
    bl_description = "Update and reload a single addon"
    bl_options = {"REGISTER", "UNDO"}
    index: bpy.props.IntProperty(
        name='index',
        description='addon index to reload',
        options={'HIDDEN'},
        min=0
    )

    def execute(self, context):
        if len(bpy.context.scene.addev_addons) <= self.index:
            self.report({'ERROR'}, message=f'ADDEV ReloadAddon: Index out of range')
            return {"FINISHED"}

        path = bpy.context.scene.addev_addons[self.index].path
        unload_addon(path)
        load_addon(path)

        bpy.ops.preferences.addon_refresh()

        module_name, raw_name = get_module_names(path)
        self.report({'INFO'}, message=f'ADDEV: Reloaded {module_name}')

        return {"FINISHED"}


class ADDEV_ReloaAllAddons_Operator(bpy.types.Operator):
    bl_idname = "addev.reload_all_addons"
    bl_label = "Reload All Addons"
    bl_description = "Update and reload all addons"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for addon in bpy.context.scene.addev_addons:
            if not addon.include:
                continue

            unload_addon(addon.path)
            load_addon(addon.path)

        bpy.ops.preferences.addon_refresh()

        self.report({'INFO'}, message='ADDEV: Reloaded!')

        return {"FINISHED"}


def register():
    bpy.utils.register_class(AddonGroup)
    bpy.types.Scene.addev_addons = bpy.props.CollectionProperty(
        name='addons',
        description='List of addons in development',
        type=AddonGroup
    )

    bpy.utils.register_class(ADDEV_OT_AddNewAddon)
    bpy.utils.register_class(ADDEV_OT_AddSinglePyAddon)
    bpy.utils.register_class(ADDEV_OT_RemoveAddon)
    bpy.utils.register_class(ADDEV_OT_ReloadAddon)
    bpy.utils.register_class(ADDEV_ReloaAllAddons_Operator)


def unregister():
    bpy.utils.unregister_class(AddonGroup)
    del bpy.types.Scene.addev_addons

    bpy.utils.unregister_class(ADDEV_OT_AddNewAddon)
    bpy.utils.unregister_class(ADDEV_OT_AddSinglePyAddon)
    bpy.utils.unregister_class(ADDEV_OT_RemoveAddon)
    bpy.utils.unregister_class(ADDEV_OT_ReloadAddon)
    bpy.utils.unregister_class(ADDEV_ReloaAllAddons_Operator)
