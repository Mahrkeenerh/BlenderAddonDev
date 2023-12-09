'''
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import bpy
from bpy.app.handlers import persistent

from . import main


bl_info = {
    "name" : "Addon Dev",
    "author" : "Mahrkeenerh",
    "description" : "Easy addon-dev live reloading",
    "blender" : (3, 0, 0),
    "version" : (1, 0, 0),
    "location" : "Python Console",
    "category" : "Development"
}


@persistent
def on_load_handler(args):
    print(args)
    def load_all_addons() -> None:
        """Load all addons"""

        all_addons = bpy.context.scene.addev_addons

        for addon in all_addons:
            if not addon.include:
                continue

            path = addon.path
            main.load_addon(path)

    def unload_all_addons() -> None:
        """Unload all addons"""

        addons_garbage_string = bpy.context.preferences.addons['addon_dev'].preferences.addons_garbage
        paths = addons_garbage_string.split("|")

        if paths == [""]:
            return

        for path in paths:
            main.unload_addon(path)

    unload_all_addons()
    load_all_addons()
    main.update_garbage_list()


class ADDEV_MenuPopout_Operator(bpy.types.Operator):
    bl_idname = "addev.menu_popout"
    bl_label = "Addon Dev Popout"
    bl_description = "Open the addon dev popout"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        for i in range(len(bpy.context.scene.addev_addons)):
            addon = bpy.context.scene.addev_addons[i]

            row = self.layout.row()
            row.prop(addon, 'include', text='')
            module_name, raw_name = main.get_module_names(addon.path)
            row.label(text=module_name)
            remove_op = row.operator('addev.remove_addon', text='', icon_value=33)
            remove_op.index = i
            reload_op = row.operator('addev.reload_addon', text='', icon_value=692)
            reload_op.index = i

        self.layout.separator()

        row = self.layout.row()
        row.operator('addev.add_new_addon', text='Add', icon_value=706)
        row.operator('addev.add_single_py_addon', text='Add single .py', icon_value=706)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)


def addon_dev_header(self, context):
    # if serpens is installed, also show clear console button
    if 'blender_visual_scripting_addon' in bpy.context.preferences.addons:
        row = self.layout.row(align=True)
        row.operator("sn.clear_console", text="", icon="TRASH")
        row.operator("wm.console_toggle", text="Console", icon="CONSOLE")
    else:
        self.layout.operator('wm.console_toggle', text='Console', icon='CONSOLE')

    self.layout.operator('addev.menu_popout', text='Addon Dev')
    self.layout.operator('addev.reload_all_addons', text='Update All', icon_value=692)


def create_keymap():
    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps.new(name='Window', space_type='EMPTY')
    kmi = km.keymap_items.new(
        'addev.reload_all_addons',
        'R',
        'PRESS',
        ctrl=True,
        alt=False,
        shift=True
    )


def remove_keymap():
    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps['Window']
    kmi = km.keymap_items['addev.reload_all_addons']
    km.keymap_items.remove(kmi)


class ADDEV_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = 'addon_dev'
    addons_garbage: bpy.props.StringProperty(
        name='addons_garbage',
        description='Addons to garbage collect at next start',
        options={'HIDDEN'}
    )

    def draw(self, context):
        kc = bpy.context.window_manager.keyconfigs.addon
        km = kc.keymaps['Window']
        kmi = km.keymap_items['addev.reload_all_addons']
        self.layout.prop(kmi, 'type', text='Update All Addons', full_event=True)


def register():
    bpy.app.handlers.load_post.append(on_load_handler)

    main.register()

    bpy.utils.register_class(ADDEV_MenuPopout_Operator)
    bpy.types.CONSOLE_HT_header.append(addon_dev_header)
    create_keymap()
    bpy.utils.register_class(ADDEV_AddonPreferences)


def unregister():
    bpy.app.handlers.load_post.remove(on_load_handler)

    main.unregister()
   
    bpy.utils.unregister_class(ADDEV_MenuPopout_Operator)
    bpy.types.CONSOLE_HT_header.remove(addon_dev_header)
    remove_keymap()
    bpy.utils.unregister_class(ADDEV_AddonPreferences)
