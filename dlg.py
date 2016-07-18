import os
from cudatext import *

DEFAULT_EXT_IGNORE = 'zip 7z tar gz rar exe'

def dialog_config(op):

    id_ignore = 1
    id_ok = 2
    
    c1 = chr(1)
    text = '\n'.join([]
        +[c1.join(['type=label', 'pos=6,6,500,0', 'cap=File extensions to ignore (space-separated):'])]
        +[c1.join(['type=edit', 'pos=6,24,500,0', 'val='+op.get('ext_ignore', DEFAULT_EXT_IGNORE)])]
        +[c1.join(['type=button', 'pos=300,200,400,0', 'cap=OK', 'props=1'])]
        +[c1.join(['type=button', 'pos=406,200,506,0', 'cap=Cancel'])]
    )
    
    res = dlg_custom('Project Manager options', 512, 230, text)
    if res is None: 
        return
        
    res, text = res
    text = text.splitlines()
    
    if res != id_ok:
        return
        
    op['ext_ignore'] = text[id_ignore]

    return True
