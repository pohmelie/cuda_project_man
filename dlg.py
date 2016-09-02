import os
from cudatext import *

DEFAULT_MASKS_IGNORE = '*.zip *.7z *.tar *.gz *.rar *.exe *.dll .git .svn'

def dialog_config(op):

    id_ignore = 1
    id_recents = 3
    id_on_start = 4
    id_on_start_act = 5
    id_ok = 6

    c1 = chr(1)
    text = '\n'.join([]
        +[c1.join(['type=label', 'pos=6,6,500,0', 'cap=&File/folder masks to ignore (space-separated):'])]
        +[c1.join(['type=edit', 'pos=6,24,500,0',
            'val='+op.get('masks_ignore', DEFAULT_MASKS_IGNORE)])]
        +[c1.join(['type=label', 'pos=6,54,500,0', 'cap=&Recent projects:'])]
        +[c1.join(['type=memo', 'pos=6,74,500,180',
            'val='+'\t'.join(op.get('recent_projects', [])) ])]
        +[c1.join(['type=check', 'pos=6,186,400,0', 'cap=&Load on app start',
            'val='+('1' if op.get('on_start', False) else '0') ])]
        +[c1.join(['type=check', 'pos=28,210,400,0', 'cap=&And activate panel',
            'val='+('1' if op.get('on_start_activate', False) else '0') ])]
        +[c1.join(['type=button', 'pos=300,300,400,0', 'cap=&OK', 'props=1'])]
        +[c1.join(['type=button', 'pos=406,300,506,0', 'cap=Cancel'])]
    )

    res = dlg_custom('Project Manager options', 512, 330, text)
    if res is None:
        return

    res, text = res
    text = text.splitlines()

    if res != id_ok:
        return

    s = text[id_ignore].strip()
    while '  ' in s:
        s = s.replace('  ', ' ')
    op['masks_ignore'] = s

    s = text[id_recents].split('\t')
    op['recent_projects'] = s

    op['on_start'] = text[id_on_start]=='1'
    op['on_start_activate'] = text[id_on_start_act]=='1'

    return True


def dialog_proj_prop(prop, proj_dir):

    list_vars = prop.get('vars', '')
    list_paths = [
      'ProjMainFile='+prop.get('mainfile', ''),
      'ProjDir='+proj_dir
      ]

    id_vars = 1
    id_ok = 4

    c1 = chr(1)
    text = '\n'.join([]
        +[c1.join(['type=label', 'pos=6,6,500,0', 'cap=&Variables in form Name=Value'])]
        +[c1.join(['type=memo', 'pos=6,26,500,180',
            'val='+'\t'.join(list_vars)
            ])]
        +[c1.join(['type=label', 'pos=6,186,500,0', 'cap=&Paths, read-only (main file: change in context menu)'])]
        +[c1.join(['type=memo', 'pos=6,206,500,290', 'props=1,0,1',
            'val='+'\t'.join(list_paths)
            ])]
        +[c1.join(['type=button', 'pos=300,300,400,0', 'cap=&OK', 'props=1'])]
        +[c1.join(['type=button', 'pos=406,300,502,0', 'cap=Cancel'])]
    )

    res = dlg_custom('Project properties', 508, 330, text)
    if res is None:
        return

    res, text = res
    text = text.splitlines()

    if res != id_ok:
        return

    s = text[id_vars].split('\t')
    s = [item.strip() for item in s if '=' in item]
    prop['vars'] = s

    return True
