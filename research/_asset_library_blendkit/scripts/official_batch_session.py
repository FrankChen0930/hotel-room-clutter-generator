"""User-run official Blendkit GUI: bounded, serialized search/download of hotel candidates."""
import argparse
import bpy
from pathlib import Path
import shutil
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha
from intake_attempts import reserve_attempt
from batch_selection import choose
from acquisition_control import decision,validate_queries
from session_cleanup import release_scene

p=argparse.ArgumentParser();p.add_argument('--attempt',default='batch_001_001');p.add_argument('--setup-check',action='store_true');p.add_argument('--config',type=Path,default=ROOT/'config/batch_001_acquisition.json');args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if not args.config.resolve().is_relative_to(ROOT/'config'):raise ValueError('WORKLINE_CONFIG_REQUIRED')
out=reserve_attempt(ROOT/'sources',args.attempt);config=read(args.config)
validate_queries(config['queries']);continuous=config.get('continuous_acquisition')
if bpy.app.background:raise ValueError('OFFICIAL_GUI_REQUIRED')
if 'blenderkit' not in bpy.context.preferences.addons:bpy.ops.preferences.addon_enable(module='blenderkit')
from blenderkit import global_vars,search,download,paths,reports,timer
prefs=bpy.context.preferences.addons['blenderkit'].preferences
if not args.setup_check:
    desired=str(ROOT/'sources/official_cache_user')
    if prefs.global_dir!=desired:prefs.global_dir=desired
    if prefs.directory_behaviour!='GLOBAL':prefs.directory_behaviour='GLOBAL'
    def prepare_user_client_port():
        if prefs.client_port=='65425':return None
        if not bpy.app.timers.is_registered(timer.client_communication_timer):return .5
        prefs.client_port='65425';return None
    if prefs.client_port!='65425':bpy.app.timers.register(prepare_user_client_port,first_interval=1)
wm=bpy.context.window_manager;wm.blenderkit_models.import_method='APPEND_OBJECTS'
ui=wm.blenderkitUI;ui.search_lock=True;ui.asset_type='MODEL';ui.free_only=True;ui.search_lock=False
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
known={a['source']['asset_base_id'] for a in read(ROOT/'registry/assets.json')['assets'] if a['source'].get('version_id')}
excluded=set(config.get('excluded_asset_ids',[]))
import uuid
for value in excluded:uuid.UUID(value)
known.update(excluded)
acquired_ids=set(known)
acquired_ids.difference_update(excluded)
source_sizes={a['source']['asset_base_id']:(ROOT/a['source']['original_file']['path']).stat().st_size for a in read(ROOT/'registry/assets.json')['assets'] if a['source'].get('version_id')}
for receipt in (ROOT/'sources').glob('batch_*_*/*/*/official_source.json'):
    value=read(receipt)
    if value.get('outcome')=='OFFICIAL_RAW_ACQUIRED':
        acquired_ids.add(value['metadata']['assetBaseId']);known.add(value['metadata']['assetBaseId'])
        source_sizes[value['metadata']['assetBaseId']]=value['original_file'].get('bytes',0)
initial_bytes=sum(source_sizes.values())
for previous in (ROOT/'sources').glob('batch_*_*/batch_status.json'):
    prior=read(previous)
    if prior.get('outcome')=='BLOCKED' and prior.get('reason')=='OFFICIAL_DOWNLOAD_TIMEOUT':
        if prior.get('selected',{}).get('assetBaseId'):known.add(prior['selected']['assetBaseId'])
state=dict(outcome='WAITING_OFFICIAL_CLIENT',attempt=out.name,completed=[],jobs=[],index=0,
    credentials='NOT_READ',operation='Official add-on search entrypoint and scene.blenderkit_download; no custom HTTP requests')
phase='WAIT';license_filter='cc_zero';started=time.monotonic();phase_started=started;last_search=0.;selected=None;scene=None;history_id=None
bootstrap=bpy.context.scene

def safe(meta):
    result={k:meta.get(k) for k in ('assetBaseId','id','displayName','name','assetType','license','isFree','canDownload','sourceAppVersion','verificationStatus','filesSize') if k in meta}
    author=meta.get('author') or {};result['author']={k:author.get(k) for k in ('id','firstName','lastName') if k in author}
    params=meta.get('dictParameters') or {};result['dimensions_metadata']={k:v for k,v in params.items() if k.startswith('dimension') or k in ('faceCount','textureResolutionMax')}
    return result
def save():write(out/'batch_status.json',state)
def stop(outcome,reason):
    state.update(outcome=outcome,reason=reason,elapsed_s=round(time.monotonic()-started,2));save()
    print('HOTEL_BATCH_STOP',outcome,reason,str(out),flush=True)
    return None
def next_job(reason):
    global phase,phase_started,license_filter,selected,scene
    state['jobs'].append(dict(job=config['queries'][state['index']],result=reason))
    state['index']+=1;license_filter='cc_zero';selected=None;phase='WAIT';phase_started=time.monotonic();save()
    if continuous and scene is not None and reason!='BLOCKED_SINGLE_ASSET_DOWNLOAD_OR_APPEND_TIMEOUT':
        state['last_cleanup']=release_scene(scene,bootstrap);scene=None;save()
def start_search(job):
    global phase,phase_started,last_search,history_id,scene
    if scene is None or scene.get('hotel_batch_job')!=state['index']:
        scene=bpy.data.scenes.new('HotelBatch_'+str(state['index']));scene['hotel_batch_job']=state['index'];bpy.context.window.scene=scene
    ui.search_lock=True;ui.search_keywords=job['query'];ui.search_license=license_filter;ui.asset_type='MODEL';ui.search_lock=False
    search.search()  # installed official add-on entrypoint, same search used by its GUI operator
    history_id=search.get_active_history_step()['id'];last_search=time.monotonic();phase_started=last_search;phase='SEARCH'
    state.update(outcome='SEARCHING',query=job['query'],license_filter=license_filter);save()
def tick():
    global phase,phase_started,license_filter,selected,scene,last_search
    try:
        now=time.monotonic()
        # Stop on authorization/rate-limit messages. Never retry through another interface.
        texts=' '.join(str(getattr(r,'text','')).lower() for r in reports.reports)
        if any(x in texts for x in ('too many requests','rate limit','http 429','http 403','http 401','status (429)','status (403)','status (401)','log in to','login required')):
            return stop('HUMAN_REQUIRED','OFFICIAL_LOGIN_PERMISSION_OR_RATE_LIMIT')
        if continuous and phase=='WAIT':
            control_path=ROOT/config.get('control_file','config/continuous_acquisition_control.json')
            if not control_path.resolve().is_relative_to(ROOT/'config'):raise ValueError('WORKLINE_CONTROL_FILE_REQUIRED')
            control=read(control_path) if control_path.exists() else {}
            extra=validate_queries(control.get('additional_queries',[]))
            config['queries']=validate_queries(read(args.config)['queries']+extra)
            records=read(ROOT/'registry/assets.json')['assets']
            ready=len({a['geometry_identity'] for a in records if a.get('local_qualification',{}).get('outcome')=='PASS' and not a.get('variant_of') and a.get('geometry_identity')})
            action=decision(continuous,control,acquired_count=len(acquired_ids),local_ready=ready,
                elapsed_s=now-started,original_bytes=initial_bytes+sum(x.get('bytes',0) for x in state.get('new_source_sizes',[])))
            state['continuous']=dict(action=action,acquired_source_ids=len(acquired_ids),reported_local_accepted=ready,query_count=len(config['queries']));save()
            if action=='PAUSED':state['outcome']='PAUSED_BY_LOCAL_CONTROL';save();return 2.
            if action!='CONTINUE':
                stop('CONTROLLED_ACQUISITION_STOP',action)
                bpy.app.timers.register(lambda:bpy.ops.wm.quit_blender() and None,first_interval=2);return None
        if state['index']>=len(config['queries']) or len(state['completed'])>=config['max_new_sources']:
            state['outcome']='OFFICIAL_BATCH_ACQUISITION_COMPLETE';save();print('HOTEL_BATCH_DONE',len(state['completed']),str(out),flush=True)
            bpy.app.timers.register(lambda:bpy.ops.wm.quit_blender() and None,first_interval=2)
            return None
        job=config['queries'][state['index']]
        if phase=='WAIT':
            if not global_vars.CLIENT_ACCESSIBLE:
                if now-phase_started>90:return stop('BLOCKED','OFFICIAL_CLIENT_TIMEOUT')
                return 1.
            if now-started<10 or now-last_search<config['minimum_search_interval_s']:return 1.
            start_search(job);return 1.
        if phase=='SEARCH':
            history=search.get_active_history_step()
            if history['id']!=history_id:return stop('BLOCKED','SEARCH_CHANGED_DURING_BATCH')
            if history.get('is_searching'):
                if now-phase_started>config['search_timeout_s']:
                    next_job('BLOCKED_SINGLE_QUERY_SEARCH_TIMEOUT');last_search=now+30;return 1.
                return 1.
            # Give official result parsing a short settling interval.
            if now-phase_started<3:return 1.
            results=search.get_search_results();index,decisions=choose(results,job['category'],known)
            write(out/(str(state['index']).zfill(2)+'_'+license_filter+'_results.json'),dict(query=job,results=[safe(r) for r in results],decisions=decisions))
            if index is None:
                if license_filter=='cc_zero':license_filter='ANY';phase='WAIT';return 1.
                next_job('NO_SUITABLE_CONFIRMED_FREE_MODEL');return 1.
            selected=dict(results[index]);known.add(selected['assetBaseId'])
            state.update(outcome='DOWNLOADING',selected=safe(selected));save()
            bpy.ops.scene.blenderkit_download(asset_index=index)
            phase='DOWNLOAD';phase_started=now;return 1.
        if phase=='DOWNLOAD':
            used=scene.get('assets used',{})
            pending=[task_id for task_id,task in download.download_tasks.items() if task.get('asset_data',{}).get('assetBaseId')==selected['assetBaseId']]
            if selected['assetBaseId'] not in used or pending:
                state['download_elapsed_s']=round(now-phase_started,1);save()
                if now-phase_started>config['download_timeout_s']:
                    for task_id in pending:bpy.ops.scene.blenderkit_download_kill(task_id=task_id)
                    next_job('BLOCKED_SINGLE_ASSET_DOWNLOAD_OR_APPEND_TIMEOUT');return 1.
                return 1.
            meta=used[selected['assetBaseId']];meta=meta.to_dict() if hasattr(meta,'to_dict') else dict(meta)
            if meta.get('isFree') is not True or meta.get('assetType')!='model':return stop('BLOCKED','FREE_MODEL_PERMISSION_CHANGED')
            cached=[Path(x).resolve() for x in paths.get_download_filepaths(meta,meta.get('resolution','blend'))]
            cached=[x for x in cached if x.is_file() and x.suffix=='.blend' and x.is_relative_to(ROOT/'sources/official_cache_user')]
            if not cached:
                if now-phase_started>config['download_timeout_s']:
                    next_job('BLOCKED_SINGLE_ASSET_ORIGINAL_CACHE_NOT_FOUND');return 1.
                return 1.
            asset_out=out/meta['assetBaseId']/meta['id'];asset_out.mkdir(parents=True,exist_ok=False)
            original=asset_out/'original.blend';shutil.copy2(cached[-1],original)
            record=dict(outcome='OFFICIAL_RAW_ACQUIRED',metadata=safe(meta),job=job,batch_id=config['batch_id'],
                original_file=dict(path=str(original.relative_to(ROOT)),sha256=sha(original),bytes=original.stat().st_size),
                cache_origin=dict(path=str(cached[-1].relative_to(ROOT)),sha256=sha(cached[-1])),
                scope='Raw original from official Client; model suitability, conversion, physics and rights qualification still pending')
            write(asset_out/'official_source.json',record)
            state['completed'].append(dict(path=str((asset_out/'official_source.json').relative_to(ROOT)),sha256=sha(asset_out/'official_source.json')))
            acquired_ids.add(meta['assetBaseId']);state.setdefault('new_source_sizes',[]).append(dict(bytes=original.stat().st_size))
            next_job('RAW_SOURCE_SAVED');return 1.
        return 1.
    except Exception:
        state['error']=traceback.format_exc();return stop('FAIL','OFFICIAL_BATCH_ERROR')

class HOTEL_BATCH_PT_Status(bpy.types.Panel):
    bl_label='飯店資產批次取得';bl_idname='HOTEL_BATCH_PT_status';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Hotel Library'
    def draw(self,context):
        self.layout.label(text='官方操作逐件取得，請保持視窗開啟。')
        self.layout.label(text='已保存：'+str(len(state['completed']))+' / '+str(config['max_new_sources']))
        self.layout.label(text=state['outcome'])
        self.layout.label(text=str(state.get('query','')))
        self.layout.label(text='完成後自動關閉；不需逐件點選。')
bpy.utils.register_class(HOTEL_BATCH_PT_Status)
save()
if args.setup_check:
    state.update(outcome='BATCH_GUI_SETUP_PASS_NO_NETWORK_REQUEST',scope='Setup check only; no search or model acquisition');save()
    bpy.app.timers.register(lambda:bpy.ops.wm.quit_blender() and None,first_interval=1)
else:bpy.app.timers.register(tick,first_interval=2)
print('HOTEL_BATCH_READY',str(out),'official serialized acquisition; no manual model selection required',flush=True)
