import os
import collections
import json
import stat
from .pathlib import Path, PurePosixPath

from cudatext import *
import cudatext_cmd


PROJECT_EXTENSION = ".cuda-proj"
DIALOG_FILTER = "CudaText projects|*"+PROJECT_EXTENSION
NODES = NODE_PROJECT, NODE_DIR, NODE_FILE = range(3)

icon_names = {
    NODE_PROJECT: "cuda-project-man-icon-project.png",
    NODE_DIR: "cuda-project-man-icon-directory.png",
    NODE_FILE: "cuda-project-man-icon-file.png",
}

NodeInfo = collections.namedtuple("NodeInfo", "caption index image level")


class Command:

    title = "Project"
    actions = (
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
    )
    options = {
        "recent_projects": [],
    }
    tree = None


    def __init__(self):

        settings_dir = Path(app_path(APP_DIR_SETTINGS))
        self.options_filename = settings_dir / "cuda_project_man.json"

        if self.options_filename.exists():

            with self.options_filename.open() as fin:

                self.options = json.load(fin)

        self.new_project()

    def init_panel(self):

        ed.cmd(cudatext_cmd.cmd_ShowSidePanelAsIs)
        app_proc(PROC_SIDEPANEL_ADD, self.title + ",-1,tree")

        self.tree = app_proc(PROC_SIDEPANEL_GET_CONTROL, self.title)
        tree_proc(self.tree, TREE_ITEM_DELETE, 0)

        base = Path(__file__).parent
        for n in NODES:

            path = base / icon_names[n]
            tree_proc(self.tree, TREE_ICON_ADD, 0, 0, str(path))

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

        for name in self.actions:

            if name == "-":

                self.add_context_menu_node(parent, "0", name)

            elif name == "Recent projects":

                sub_parent = self.add_context_menu_node(parent, "0", name)
                for path in self.options["recent_projects"]:

                    action = str.format(
                        "cuda_project_man,action_open_project,'{}'",
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

            self.project["nodes"].append(path)
            self.project["nodes"].sort(key=Command.node_ordering)
            self.action_refresh()
            if self.project_file_path:

                self.action_save_project_as(self.project_file_path)

    def new_project(self):

        self.project = dict(nodes=[])
        self.project_file_path = None

    def add_recent(self, path):

        recent = self.options["recent_projects"]
        if path in recent:

            recent.pop(recent.index(path))

        self.options["recent_projects"] = ([path] + recent)[:10]
        self.generate_context_menu()

    def action_refresh(self, parent=None, nodes=None):

        unfold = parent is None
        if parent is None:

            tree_proc(self.tree, TREE_ITEM_DELETE, 0)
            if self.project_file_path is None:

                project_name = "*Unsaved project*"

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

            path = dlg_file(True, "", "", DIALOG_FILTER)

        if path:

            with open(path) as fin:

                self.project = json.load(fin)
                self.project_file_path = Path(path)
                self.add_recent(path)
                self.action_refresh()
                self.save_options()

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
            path = dlg_file(False, "", project_path, DIALOG_FILTER)

        if path:

            path = Path(path)
            if path.suffix != PROJECT_EXTENSION:

                path = path.parent / (path.name + PROJECT_EXTENSION)

            self.project_file_path = path
            with path.open("w") as fout:

                json.dump(self.project, fout, indent=4)

            if need_refresh:

                self.add_recent(str(path))
                self.action_refresh()
                self.save_options()

    def get_info(self, index):

        return NodeInfo(*tree_proc(self.tree, TREE_ITEM_GET_PROP, index))

    def get_location_by_index(self, index):

        path = []
        while index and index not in self.top_nodes:

            path.append(self.get_info(index).caption)
            index = tree_proc(self.tree, TREE_ITEM_GET_PARENT, index)

        path.reverse()
        full_path = Path(self.top_nodes[index] / str.join("/", path))

        return full_path

    def on_panel(self, ed_self, id_control, id_event):

        if not self.tree or id_control != self.tree:

            return

        if id_event == "on_dbl_click":

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
