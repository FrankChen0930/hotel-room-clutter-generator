"""User-run official GUI intake. Human selects one free model; no custom download API."""
import argparse
import bpy
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,write,sha
from intake_attempts import reserve_attempt
from asset_dependencies import linked_asset_datablocks

p=argparse.ArgumentParser();p.add_argument('--attempt',default='intake_user_001');p.add_argument('--query',default='backpack');p.add_argument('--setup-check',action='store_true')
p.add_argument('--auto-recommended',action='store_true')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if not args.attempt.replace('_','').replace('-','').isalnum():raise ValueError('SIMPLE_ATTEMPT_REQUIRED')
out=reserve_attempt(ROOT/'sources',args.attempt)
args.attempt=out.name
print('HOTEL_LIBRARY_ATTEMPT',args.attempt,str(out),flush=True)
if bpy.app.background:raise ValueError('USER_GUI_REQUIRED')
if 'blenderkit' not in bpy.context.preferences.addons:bpy.ops.preferences.addon_enable(module='blenderkit')
from blenderkit import global_vars,search,download,paths
prefs=bpy.context.preferences.addons['blenderkit'].preferences
# Keep the user-run official client distinct from the agent's restricted probe client.
# Setup-only checks retain the probe cache/port and never occupy the user's client port.
desired_cache=str(ROOT/'sources'/('official_cache' if args.setup_check else 'official_cache_user'))
if prefs.global_dir!=desired_cache:prefs.global_dir=desired_cache
if prefs.directory_behaviour!='GLOBAL':prefs.directory_behaviour='GLOBAL'
desired_port='5152' if args.setup_check else '65425'
# Client restart callbacks need their official communication timer registered first.
def configure_client_port():
    from blenderkit import timer
    if prefs.client_port==desired_port:return None
    if not bpy.app.timers.is_registered(timer.client_communication_timer):return .5
    prefs.client_port=desired_port
    return None
if prefs.client_port!=desired_port:bpy.app.timers.register(configure_client_port,first_interval=1)
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
scene=bpy.data.scenes.new('HotelLibraryOfficialIntake');bpy.context.window.scene=scene
wm=bpy.context.window_manager;wm.blenderkit_models.import_method='APPEND_OBJECTS'
ui=wm.blenderkitUI;ui.search_lock=True;ui.asset_type='MODEL';ui.free_only=True;ui.search_license='ANY' if args.auto_recommended else 'cc_zero';ui.search_keywords=args.query;ui.search_lock=False
state=dict(outcome='WAITING_USER_OFFICIAL_FREE_MODEL',attempt=args.attempt,query=args.query,
    credentials='NOT_READ',download='HUMAN_SELECTION_IN_OFFICIAL_UI',source_count=0)
write(out/'session.json',state)
started=time.monotonic();searched=False;last_snapshot=None;auto_requested=False
# This exact model appeared as Free/canDownload in the user's actual official GUI search.
# Download at most one model and recheck its current Free permission before invoking the official operator.
recommended_id='fa971768-8e7e-49dd-93e5-c225b578899e'
state['mode']='AUTO_ONE_RECOMMENDED_FREE_MODEL_LOCAL_TEST' if args.auto_recommended else 'MANUAL_SELECTION'

def plain(v):return v.to_dict() if hasattr(v,'to_dict') else dict(v)
def safe_metadata(d):
    result={k:d.get(k) for k in ('assetBaseId','id','displayName','name','assetType','license','isFree','canDownload','sourceAppVersion','verificationStatus') if k in d}
    author=d.get('author') or {};result['author']={k:author.get(k) for k in ('id','firstName','lastName') if k in author}
    params=d.get('dictParameters') or {};result['dimensions_metadata']={k:v for k,v in params.items() if k.startswith('dimension') or k in ('faceCount','textureResolutionMax')}
    return result

class HOTEL_LIBRARY_PT_Intake(bpy.types.Panel):
    bl_label='飯店資產取得：操作步驟';bl_idname='HOTEL_LIBRARY_PT_intake'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Hotel Library'
    def draw(self,context):
        lay=self.layout
        if state['outcome']=='OFFICIAL_MODEL_SAVED_PENDING_INTAKE':
            lay.label(text='已保存模型，可以關閉並回覆「完成」。',icon='CHECKMARK')
            return
        if state['outcome'].startswith(('FAIL','BLOCKED')):
            lay.label(text='取得流程遇到問題，請回報目前畫面。',icon='ERROR')
            lay.label(text=state.get('reason',state['outcome']))
            return
        if args.auto_recommended:
            lay.label(text='正在自動搜尋並下載一個免費背包，請稍候。')
            lay.label(text='Royalty Free：僅進行受控本機技術測試。')
            lay.label(text='保存完成後可關閉 Blender，回覆「完成」。')
            return
        lay.label(text='1. 點空白處關閉 Blender 啟動畫面。')
        lay.label(text='2. 在上方 Blendkit 搜尋列找背包等用品。')
        lay.label(text='3. 將一個標示 Free 的模型拖進中央。')
        lay.label(text='4. 等待下載；模型與資料會自動保存。')
        lay.separator()
        lay.label(text='沒有結果：按下方按鈕放寬授權篩選。')
        lay.label(text='僅做本機測試；不要選 Full 或購買訂閱。')
        lay.operator('view3d.blenderkit_search',text='重新搜尋').keywords=ui.search_keywords
        lay.operator('hotel_library.search_any_license',text='找不到？顯示其他授權的候選')

class HOTEL_LIBRARY_OT_SearchAny(bpy.types.Operator):
    bl_idname='hotel_library.search_any_license';bl_label='顯示其他授權的候選'
    def execute(self,context):
        ui.search_lock=True;ui.search_license='ANY';ui.search_lock=False
        bpy.ops.view3d.blenderkit_search(keywords=ui.search_keywords)
        return {'FINISHED'}
bpy.utils.register_class(HOTEL_LIBRARY_OT_SearchAny)
bpy.utils.register_class(HOTEL_LIBRARY_PT_Intake)
for window in wm.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            # Blender 5.2 exposes active_panel_category as read-only. Keep the
            # sidebar open; the user can click the Hotel Library tab.

def tick():
    global searched,last_snapshot,auto_requested
    try:
        state['client_accessible']=bool(global_vars.CLIENT_ACCESSIBLE)
        if global_vars.CLIENT_ACCESSIBLE and not searched:
            bpy.ops.view3d.blenderkit_search(keywords=args.query);searched=True
        current_results=search.get_search_results()
        results=[safe_metadata(r) for r in current_results]
        if results!=last_snapshot:
            write(out/'visible_search_results.json',dict(source='Official GUI current search page; human controls queries/pages',results=results))
            last_snapshot=results
        used=scene.get('assets used',{})
        if args.auto_recommended and not auto_requested and not used:
            for index,r in enumerate(current_results):
                if r.get('assetBaseId')!=recommended_id:continue
                if r.get('isFree') is not True or r.get('canDownload') is not True or r.get('assetType')!='model':
                    state['outcome']='BLOCKED_RECOMMENDED_MODEL_NOT_CURRENTLY_FREE_DOWNLOADABLE'
                    write(out/'session.json',state);return None
                auto_requested=True
                state.update(outcome='DOWNLOADING_RECOMMENDED_FREE_MODEL',download='OFFICIAL_OPERATOR_SINGLE_FREE_MODEL',recommended_asset_base_id=recommended_id)
                write(out/'session.json',state)
                bpy.ops.scene.blenderkit_download(asset_index=index)
                break
        state['source_count']=len(used)
        if len(used)>1:
            state['outcome']='BLOCKED_MULTIPLE_MODELS_REQUIRE_SINGLE_ASSET_REVIEW';write(out/'session.json',state);return None
        if len(used)==1 and not download.download_tasks:
            data=plain(next(iter(used.values())))
            if data.get('isFree') is not True or data.get('assetType')!='model':
                state['outcome']='BLOCKED_NOT_CONFIRMED_FREE_MODEL';write(out/'session.json',state);return None
            objects=list(scene.objects)
            if not any(o.type=='MESH' for o in objects):return 2.0
            linked=linked_asset_datablocks(objects)
            if linked:
                state.update(outcome='BLOCKED_ASSET_LINKED_DEPENDENCIES',linked_datablocks=linked,
                    reason='模型仍有外部連結；已保留官方快取，交由離線處理。')
                write(out/'session.json',state);return None
            col=bpy.data.collections.new('HotelLibrarySource');scene.collection.children.link(col)
            for obj in objects:
                if obj.name not in col.objects:col.objects.link(obj)
            bpy.ops.file.pack_all()
            blend=out/'download.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
            raw=[]
            for filename in paths.get_download_filepaths(data,data.get('resolution','blend')):
                original=Path(filename).resolve()
                if original.is_file() and original.is_relative_to(Path(prefs.global_dir).resolve()):
                    raw.append(dict(path=str(original.relative_to(ROOT)),sha256=sha(original),bytes=original.stat().st_size))
            state.update(outcome='OFFICIAL_MODEL_SAVED_PENDING_INTAKE',collection=col.name,
                blend=str(blend.relative_to(ROOT)),source_sha256=sha(blend),metadata=safe_metadata(data),
                official_download_files=raw,original_download_hash_status='PINNED' if raw else 'PENDING_LOCATE_OFFICIAL_CACHE',
                elapsed_s=round(time.monotonic()-started,2),scope='Official model obtained; all conversion/quality/tool/public rights remain pending')
            write(out/'downloaded_source.json',state);write(out/'session.json',state)
            print('HOTEL_LIBRARY_OFFICIAL_SOURCE_SAVED',str(blend),flush=True)
            return None
        write(out/'session.json',state)
        # Stop only the watcher after thirty minutes; never force-close a user's GUI.
        if time.monotonic()-started>1800:
            state['outcome']='WATCHER_TIMEOUT_NO_MODEL';write(out/'session.json',state);return None
        return 2.0
    except Exception:
        state.update(outcome='FAIL',error=traceback.format_exc());write(out/'session.json',state);return None
if args.setup_check:
    state.update(outcome='SESSION_SETUP_PASS_NO_MODEL',gui_not_background=not bpy.app.background,
        official_addon_enabled='blenderkit' in bpy.context.preferences.addons,
        import_method=wm.blenderkit_models.import_method,scope='GUI setup test only; no search/download/model acceptance')
    write(out/'session.json',state)
    bpy.app.timers.register(lambda:bpy.ops.wm.quit_blender() and None,first_interval=1)
else:bpy.app.timers.register(tick,first_interval=4)
print('HOTEL_LIBRARY_INTAKE_READY: '+('自動取得免費背包中，請稍候，不需點選其他模型。' if args.auto_recommended else '請在官方 Blendkit 選一個 Free 模型；下載後自動保存。'),flush=True)
