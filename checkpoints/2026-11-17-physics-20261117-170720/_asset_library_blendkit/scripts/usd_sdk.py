"""Use installed Isaac bindings without starting or modifying Isaac."""
import os
from pathlib import Path
import sys
HANDLES=[]

def load(root=Path('C:/isaac_sim')):
    if Path(sys.executable).resolve() != (root/'kit/python/python.exe').resolve():
        raise RuntimeError('USE_INSTALLED_ISAAC_PYTHON')
    libs=list((root/'extscache').glob('omni.usd.libs-*'))
    if len(libs)!=1: raise RuntimeError('AMBIGUOUS_USD_SDK')
    sys.path.insert(0,str(libs[0]))
    for p in (libs[0]/'bin',root/'kit'):
        if os.name=='nt': HANDLES.append(os.add_dll_directory(str(p)))
    from pxr import Usd
    return Usd
