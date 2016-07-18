Plugin for CudaText.
Allows to manage project tree view (files and directories).
Plugin shows project panel in the side panel, with context menu.

Context menu has commands:
 - Add directory...
 - Add file...
 - New project
 - Open project...
 - Recent projects
 - Save project as...
 - Refresh
 - Remove node
 - Clear project

Tech notes:
- You can add only root nodes to tree-view. Project files store only links for root-nodes (files, dirs). File-list of folders is not saved to project. So project files are small.
- You can open project files from Open dialog, or command line. Instead of opening raw JSON content, Project panel will open. (Needs CudaText 1.3.28+)
- When you call "Remove node", node on top project level is removed, and selection inside that node is ignored.

Homepage: https://github.com/pohmelie/cuda_project_man
