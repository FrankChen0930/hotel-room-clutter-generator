"""Run with Blender --background --factory-startup --python; never dumps preferences."""
import bpy
import addon_utils
import json
import os
from pathlib import Path
import sys

args=sys.argv[sys.argv.index('--')+1:]
out=Path(args[0]); out.parent.mkdir(parents=True,exist_ok=True)
addons=[m.__name__ for m in addon_utils.modules() if 'blendkit' in m.__name__.lower() or 'blenderkit' in m.__name__.lower()]
properties={p.identifier:dict(type=p.type, default=str(getattr(p,'default',''))) for p in bpy.ops.wm.usd_export.get_rna_type().properties if p.identifier!='rna_type'}
report=dict(blender_version=bpy.app.version_string, executable=bpy.app.binary_path,
    addon_modules=addons, enabled=[x for x in bpy.context.preferences.addons.keys() if x in addons],
    login_status='UNKNOWN_NOT_INSPECTED_NO_ADDON' if not addons else 'UNKNOWN_NOT_INSPECTED',
    profile_env={k:os.environ.get(k) for k in ('BLENDER_USER_RESOURCES','BLENDER_USER_CONFIG','BLENDER_USER_SCRIPTS')},
    usd_export_properties=properties, python_version=sys.version,
    scope='Factory startup with isolated workspace profile; no credentials read or persisted')
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLENDER_PROBE',bpy.app.version_string,'addons',addons)
