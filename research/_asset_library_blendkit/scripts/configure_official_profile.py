"""Configure only the existing workspace profile; never reads or exports credentials."""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,write
if 'blenderkit' not in bpy.context.preferences.addons:
    bpy.ops.preferences.addon_enable(module='blenderkit')
prefs=bpy.context.preferences.addons['blenderkit'].preferences
prefs.global_dir=str(ROOT/'sources/official_cache'); prefs.directory_behaviour='GLOBAL'; prefs.client_port='5152'
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.context.preferences.filepaths.temporary_directory=str(ROOT/'blender_profile/temp')
(ROOT/'blender_profile/temp').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_userpref()
write(ROOT/'reports/official_profile.json',dict(outcome='PASS',addon='blenderkit',global_dir=prefs.global_dir,
    directory_behaviour=prefs.directory_behaviour,client_port=prefs.client_port,credentials='NOT_READ',
    profile=str(ROOT/'blender_profile'),scope='Workspace-isolated preferences only'))
print('ISOLATED_PROFILE_CONFIGURED')
