"""Optional installer, unexecuted until official ZIP is available."""
import bpy
import addon_utils
from pathlib import Path
import sys
import zipfile

archive=Path(sys.argv[sys.argv.index('--')+1]).resolve(strict=True)
with zipfile.ZipFile(archive) as z:
    names=z.namelist()
    if any(Path(x).is_absolute() or '..' in Path(x).parts for x in names): raise ValueError('UNSAFE_ARCHIVE')
    if not any('blenderkit' in x.lower() or 'blendkit' in x.lower() for x in names): raise ValueError('NOT_BLENDKIT_ARCHIVE')
bpy.ops.preferences.addon_install(filepath=str(archive))
mods=[m.__name__ for m in addon_utils.modules(refresh=True) if m.__name__ in {'blenderkit','blendkit'}]
if len(mods)!=1: raise ValueError('OFFICIAL_ADDON_MODULE_NOT_FOUND_OR_EXTENSION_LAYOUT_REQUIRES_UI')
bpy.ops.preferences.addon_enable(module=mods[0]); bpy.ops.wm.save_userpref()
print('ISOLATED_ADDON_ENABLED',mods[0])
