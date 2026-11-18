"""Run in actual Blender GUI. Uses installed official add-on operations, no network API clone."""
import argparse
from pathlib import Path
import sys
import time
import traceback
import os
import bpy
import addon_utils
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT, write

parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--timeout',type=int,default=60); parser.add_argument('--query',default='towel')
parser.add_argument('--license',choices=['cc_zero','ANY'],default='cc_zero'); parser.add_argument('--quit',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]); out=args.output.resolve()
if not out.is_relative_to(ROOT) or out.exists(): raise ValueError('NEW_WORKSPACE_PROBE_REQUIRED')
out.mkdir(parents=True); started=time.monotonic(); searched=False
report=dict(outcome='RUNNING',gui_not_background=not bpy.app.background,query=args.query,license_filter=args.license,
    pid=os.getpid(),authentication='NOT_READ',operator='view3d.blenderkit_search',source='Installed official Blendkit add-on',results=[])

def save(): write(out/'status.json',report)
def finish(outcome,reason=None):
    report.update(outcome=outcome,reason=reason,elapsed_s=round(time.monotonic()-started,2)); save()
    try:
        bpy.ops.screen.screenshot(filepath=str(out/'blender_gui.png'))
        report['screenshot']='blender_gui.png'; save()
    except Exception as e: report['screenshot_error']=type(e).__name__; save()
    if args.quit: bpy.app.timers.register(lambda: bpy.ops.wm.quit_blender() and None,first_interval=1)
    return None

try:
    if bpy.app.background: raise ValueError('ACTUAL_GUI_REQUIRED')
    if 'blenderkit' not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module='blenderkit')
    prefs=bpy.context.preferences.addons['blenderkit'].preferences
    prefs.global_dir=str(ROOT/'sources/official_cache')
    prefs.directory_behaviour='GLOBAL'
    prefs.client_port='5152'
    bpy.context.preferences.filepaths.use_scripts_auto_execute=False
    from blenderkit import global_vars,search
    report['addon_version']=list(global_vars.VERSION)
    report['official_cache']=prefs.global_dir
    # Configure built-in UI fields under search lock to avoid multiple update-triggered searches.
    ui=bpy.context.window_manager.blenderkitUI
    ui.search_lock=True; ui.asset_type='MODEL'; ui.free_only=True; ui.search_license=args.license
    ui.search_keywords=args.query; ui.search_lock=False
    save()
    def tick():
        global searched
        try:
            report['client_accessible']=bool(global_vars.CLIENT_ACCESSIBLE)
            report['gui_view3d_areas']=sum(a.type=='VIEW_3D' for w in bpy.context.window_manager.windows for a in w.screen.areas)
            if global_vars.CLIENT_ACCESSIBLE and not searched:
                bpy.ops.view3d.blenderkit_search(keywords=args.query); searched=True
                report['official_search_invoked']=True
            if searched:
                results=search.get_search_results()
                # Whitelist descriptive metadata only: never dump API keys, signed URLs or file descriptors.
                fields=('assetBaseId','id','displayName','name','assetType','license','isFree','canDownload','sourceAppVersion','verificationStatus','description')
                safe=[]
                for r in results:
                    item={k:r.get(k) for k in fields if k in r}
                    author=r.get('author') or {}
                    item['author']={k:author.get(k) for k in ('id','firstName','lastName','aboutMe') if k in author}
                    safe.append(item)
                report['results']=safe
                if safe: return finish('PASS_OFFICIAL_GUI_SEARCH')
            save()
            elapsed=time.monotonic()-started
            if elapsed>=args.timeout: return finish('BLOCKED','OFFICIAL_CLIENT_OR_SEARCH_TIMEOUT')
            return 1.0
        except Exception:
            report['error']=traceback.format_exc(); return finish('FAIL','OFFICIAL_GUI_OPERATOR_ERROR')
    bpy.app.timers.register(tick,first_interval=3)
except Exception:
    report['error']=traceback.format_exc(); finish('FAIL','GUI_SETUP_ERROR')
