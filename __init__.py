import os
import collections
import json
import stat
from fnmatch import fnmatch
from .pathlib import Path, PurePosixPath
from .dlg import *

from cudatext import *
import cudatext_cmd

PROJECT_EXTENSION = ".cuda-proj"
PROJECT_DIALOG_FILTER = "CudaText projects|*"+PROJECT_EXTENSION
PROJECT_UNSAVED_NAME = "(Unsaved project)"

NODES = NODE_PROJECT, NODE_DIR, NODE_FILE = range(3)

global_project_info = {}

icon_names = {
    NODE_PROJECT: "cuda-project-man-icon-project.png",
    NODE_DIR: "cuda-project-man-icon-directory.png",
    NODE_FILE: "cuda-project-man-icon-file.png",
}

NodeInfo = collections.namedtuple("NodeInfo", "caption index image level")


def is_filename_mask_listed(name, mask_list):

    s = os.path.basename(name)
    for item in mask_list.split(' '):
        if fnmatch(s, item):
            return True
    return False


class Command:

    title = "Project"
    actions = {
        None: (
            "Add directory...",
            "Add file...",
            "-",
            "New project",
            "Open project...",
            "Recent projects",
            "Save project as...",
            "-",
            "Refresh",
            "Remove node",
            "Clear project",
        ),
        NODE_PROJECT: (
            "Add directory...",
            "Add file...",
            "-",
            "New project",
            "Open project...",
            "Recent projects",
            "Save project as...",
            "-",
            "Refresh",
            "Remove node",
            "Clear project",
        ),
        NODE_DIR: (
            "New file...",
            "Rename...",
            "Delete directory",
            "New directory...",
            "Find in directory...",
            "-",
            "Add directory...",
            "Add file...",
            "-",
            "New project",
            "Open project...",
            "Recent projects",
            "Save project as...",
            "-",
            "Refresh",
            "Remove node",
            "Clear project",
        ),
        NODE_FILE: (
            #"New file...",
            "Rename...",
            "Delete file",
            #"New directory...",
            #"Find in directory...",
            "-",
            "Add directory...",
            "Add file...",
            "-",
            "New project",
            "Open project...",
            "Recent projects",
            "Save project as...",
            "-",
            "Refresh",
            "Remove node",
            "Clear project",
        ),
    }
    options = {
        "recent_projects": [],
        "masks_ignore": DEFAULT_MASKS_IGNORE,
        "on_start": False,
    }
    tree = None


    def __init__(self):

        settings_dir = Path(app_path(APP_DIR_SETTINGS))
        self.options_filename = settings_dir / "cuda_project_man.json"

        if self.options_filename.exists():

            with self.options_filename.open() as fin:

                self.options = json.load(fin)

        self.new_project()

    def init_panel(self, and_activate=True):

        #already inited?
        if self.tree:
            return

        ed.cmd(cudatext_cmd.cmd_ShowSidePanelAsIs)
        app_proc(PROC_SIDEPANEL_ADD, self.title + ",-1,tree")

        self.tree = app_proc(PROC_SIDEPANEL_GET_CONTROL, self.title)
        tree_proc(self.tree, TREE_ITEM_DELETE, 0)

        base = Path(__file__).parent
        for n in NODES:

            path = base / icon_names[n]
            tree_proc(self.tree, TREE_ICON_ADD, 0, 0, str(path))

        if and_activate:
            app_proc(PROC_SIDEPANEL_ACTIVATE, self.title)

        self.action_refresh()
        self.generate_context_menu()

    def show_panel(self):

        if not self.tree:

            self.init_panel()

    @property
    def selected(self):

        return tree_proc(self.tree, TREE_ITEM_GET_SELECTED)

    def add_context_menu_node(self, parent, action, name):

        desc = str.format(
            "{};{};{};-1",
            parent,
            action,
            name,
        )
        return app_proc(PROC_MENU_ADD, desc)

    def generate_context_menu(self):

        parent = "side:" + self.title
        app_proc(PROC_MENU_CLEAR, parent)

        if self.selected is not None:

            i = self.get_info(self.selected).image

        else:

            i = None

        for name in self.actions[i]:

            if name == "-":

                self.add_context_menu_node(parent, "0", name)

            elif name == "Recent projects":

                sub_parent = self.add_context_menu_node(parent, "0", name)
                for path in self.options["recent_projects"]:

                    action = str.format(
                        "cuda_project_man,action_open_project,r'{}'",
                        path,
                    )
                    self.add_context_menu_node(sub_parent, action, path)

            else:

                action_name = name.lower().replace(" ", "_").rstrip(".")
                action = "cuda_project_man,action_" + action_name
                self.add_context_menu_node(parent, action, name)

    @staticmethod
    def node_ordering(node):

        path = Path(node)
        return path.is_file(), path.name

    def add_node(self, dialog):

        path = dialog()
        if path is not None:

            msg_status("Adding to project: "+path, True)
            self.project["nodes"].append(path)
            self.project["nodes"].sort(key=Command.node_ordering)
            self.action_refresh()
            if self.project_file_path:

                self.action_save_project_as(self.project_file_path)

    def new_project(self):

        self.project = dict(nodes=[])
        self.project_file_path = None
        self.update_global_data()

    def add_recent(self, path):

        recent = self.options["recent_projects"]
        if path in recent:

            recent.pop(recent.index(path))

        self.options["recent_projects"] = ([path] + recent)[:10]
        self.generate_context_menu()

    def action_new_file(self):

        location = Path(self.get_location_by_index(self.selected))
        if location.is_file():

            location = location.parent

        result = dlg_input("New file:", "")
        if not result:

            return

        if os.sep in result:

            msg_status("Incorrect file name")
            return

        path = location / result
        path.touch()
        self.action_refresh()

        #open new file
        self.jump_to_filename(str(path))
        file_open(str(path))

    def action_rename(self):

        location = Path(self.get_location_by_index(self.selected))
        result = dlg_input("Rename to", str(location.name))
        if not result:

            return

        new_location = location.parent / result
        location.replace(new_location)
        if location in self.top_nodes.values():

            self.action_remove_node()
            self.add_node(lambda: str(new_location))

        self.action_refresh()
        self.jump_to_filename(str(new_location))

    def action_delete_file(self):

        location = Path(self.get_location_by_index(self.selected))
        location.unlink()
        self.action_refresh()

    def action_delete_directory(self, start=None):

        location = start or Path(self.get_location_by_index(self.selected))
        for path in location.glob("*"):

            if path.is_file():

                path.unlink()

            elif path.is_dir():

                self.action_delete_directory(path)

        location.rmdir()
        if start is None:

            self.action_refresh()

    def action_new_directory(self):

        location = Path(self.get_location_by_index(self.selected))
        if location.is_file():

            location = location.parent

        result = dlg_input("New directory", "")
        if not result:

            return

        location = location / result
        location.mkdir()
        self.action_refresh()
        self.jump_to_filename(str(location))

    def action_find_in_directory(self):

        ...

    def action_refresh(self, parent=None, nodes=None):

        unfold = parent is None
        if parent is None:

            tree_proc(self.tree, TREE_ITEM_DELETE, 0)
            if self.project_file_path is None:

                project_name = PROJECT_UNSAVED_NAME

            else:

                project_name = self.project_file_path.stem

            parent = tree_proc(
                self.tree,
                TREE_ITEM_ADD,
                0,
                -1,
                project_name,
                NODE_PROJECT,
            )
            nodes = self.project["nodes"]
            self.top_nodes = {}

        for path in map(Path, nodes):

            if self.is_filename_ignored(path.name):
                continue

            index = tree_proc(
                self.tree,
                TREE_ITEM_ADD,
                parent,
                -1,
                path.name,
                NODE_DIR if path.is_dir() else NODE_FILE,
            )
            if nodes is self.project["nodes"]:

                self.top_nodes[index] = path

            if path.is_dir():

                sub_nodes = sorted(path.iterdir(), key=Command.node_ordering)
                self.action_refresh(index, sub_nodes)

        if unfold:

            tree_proc(self.tree, TREE_ITEM_UNFOLD, parent)

    def action_new_project(self):

        self.new_project()
        self.action_refresh()

    def action_open_project(self, path=None):

        if path is None:

            path = dlg_file(True, "", "", PROJECT_DIALOG_FILTER)

        if path:

            if Path(path).exists():

                with open(path) as fin:

                    self.project = json.load(fin)
                    self.project_file_path = Path(path)
                    self.add_recent(path)
                    self.action_refresh()
                    self.save_options()

                self.update_global_data()
                msg_status("Project opened: "+path)

            else:

                msg_status("Recent item not found")

    def action_add_directory(self):

        self.add_node(lambda: dlg_dir(""))

    def action_add_file(self):

        self.add_node(lambda: dlg_file(True, "", "", ""))

    def action_remove_node(self):

        index = self.selected
        while index and index not in self.top_nodes:

            index = tree_proc(self.tree, TREE_ITEM_GET_PARENT, index)

        if index in self.top_nodes:

            tree_proc(self.tree, TREE_ITEM_DELETE, index)
            path = self.top_nodes.pop(index)
            i = self.project["nodes"].index(str(path))
            self.project["nodes"].pop(i)
            if self.project_file_path:

                self.action_save_project_as(self.project_file_path)

    def action_clear_project(self):

        self.project["nodes"].clear()
        self.action_refresh()

    def action_save_project_as(self, path=None):

        need_refresh = path is None
        if path is None:

            if self.project_file_path:
                project_path = str(self.project_file_path.parent)
            else:
                project_path = ""
            path = dlg_file(False, "", project_path, PROJECT_DIALOG_FILTER)

        if path:

            path = Path(path)
            if path.suffix != PROJECT_EXTENSION:

                path = path.parent / (path.name + PROJECT_EXTENSION)

            self.project_file_path = path
            with path.open("w") as fout:

                json.dump(self.project, fout, indent=4)

            self.update_global_data()
            msg_status("Project saved")

            if need_refresh:

                self.add_recent(str(path))
                self.action_refresh()
                self.save_options()

    def update_global_data(self):
        global global_project_info
        global_project_info['filename'] = str(self.project_file_path) if self.project_file_path else ''
        global_project_info['nodes'] = self.project['nodes']

    def get_info(self, index):

        return NodeInfo(*tree_proc(self.tree, TREE_ITEM_GET_PROP, index))

    def get_location_by_index(self, index):

        path = []
        while index and index not in self.top_nodes:

            path.append(self.get_info(index).caption)
            index = tree_proc(self.tree, TREE_ITEM_GET_PARENT, index)

        path.reverse()
        full_path = Path(self.top_nodes[index] / str.join(os.sep, path))

        return full_path

    def on_panel(self, ed_self, id_control, id_event):

        if not self.tree or id_control != self.tree:

            return

        if id_event == "on_sel":

            self.generate_context_menu()

        elif id_event == "on_dbl_click":

            info = self.get_info(self.selected)
            if info.image == NODE_FILE:

                path = self.get_location_by_index(self.selected)
                file_open(str(path))

    def save_options(self):

        with self.options_filename.open(mode="w") as fout:

            json.dump(self.options, fout, indent=4)

    def menu_recents(self):

        items = self.options["recent_projects"]
        if not items:
            return

        items_nice = [os.path.basename(fn)+'\t'+os.path.dirname(fn) for fn in items]
        res = dlg_menu(MENU_LIST, '\n'.join(items_nice))
        if res is None:
            return

        self.init_panel()
        self.action_open_project(items[res])

    def new_project_open_dir(self):

        self.init_panel()
        self.action_new_project()
        self.action_add_directory()

        # unfold 1st item under root
        items = tree_proc(self.tree, TREE_ITEM_ENUM, 0)
        if not items:
            return
        items = tree_proc(self.tree, TREE_ITEM_ENUM, items[0][0])
        if not items:
            return
        tree_proc(self.tree, TREE_ITEM_UNFOLD, items[0][0])
        tree_proc(self.tree, TREE_ITEM_SELECT, items[0][0])

        app_proc(PROC_SIDEPANEL_ACTIVATE, self.title)

    def on_open_pre(self, ed_self, filename):

        if filename.endswith(PROJECT_EXTENSION):

            self.init_panel()
            self.action_open_project(filename)
            return False #block opening

    def config(self):

        if dialog_config(self.options):
            self.save_options()

    def is_filename_ignored(self, fn):

        mask_list = self.options.get("masks_ignore", DEFAULT_MASKS_IGNORE)
        return is_filename_mask_listed(fn, mask_list)

    def on_start(self, ed_self):

        if not self.options.get("on_start", False):
            return

        and_activate = self.options.get("on_start_activate", False)
        self.init_panel(and_activate)

        items = self.options.get("recent_projects", [])
        if items:
            self.action_open_project(items[0])

    def contextmenu_add_dir(self):

        self.init_panel()
        self.action_add_directory()

    def contextmenu_add_file(self):

        self.init_panel()
        self.action_add_file()

    def contextmenu_new_proj(self):

        self.init_panel()
        self.action_new_project()

    def contextmenu_open_proj(self):

        self.init_panel()
        self.action_open_project()

    def contextmenu_save_proj_as(self):

        self.init_panel()
        self.action_save_project_as()

    def contextmenu_refresh(self):

        self.init_panel()
        self.action_refresh()

    def contextmenu_remove_node(self):

        self.init_panel()
        self.action_remove_node()

    def contextmenu_clear_proj(self):

        self.init_panel()
        self.action_clear_project()

    def enum_all(self, callback):
        """
        Callback for all items.
        Until callback gets false.
        """

        items = tree_proc(self.tree, TREE_ITEM_ENUM, 0)
        if items:
            self.enum_subitems(items[0][0], callback)

    def enum_subitems(self, item, callback):
        """
        Callback for all subitems of given item.
        Until callback gets false.
        """

        items = tree_proc(self.tree, TREE_ITEM_ENUM, item)
        if items:
            for i in items:
                subitem = i[0]
                fn = str(self.get_location_by_index(subitem))
                if not callback(fn, subitem):
                    return False
                if not self.enum_subitems(subitem, callback):
                    return False
        return True

    def menu_goto(self):

        if not self.tree:
            msg_status('Project not opened')
            return

        files = []

        def callback_collect(fn, item):
            if os.path.isfile(fn):
                files.append(fn)
            return True

        self.enum_all(callback_collect)
        if not files:
            msg_status('Project is empty')
            return

        files_nice = [os.path.basename(fn)+'\t'+os.path.dirname(fn) for fn in files]
        res = dlg_menu(MENU_LIST_ALT, '\n'.join(files_nice))
        if res is None:
            return

        self.jump_to_filename(files[res])

    def jump_to_filename(self, filename):

        filename_to_find = filename

        def callback_find(fn, item):
            if fn==filename_to_find:
                tree_proc(self.tree, TREE_ITEM_SELECT, item)
                return False
            return True

        msg_status('Jumping to: '+filename)
        self.enum_all(callback_find)
