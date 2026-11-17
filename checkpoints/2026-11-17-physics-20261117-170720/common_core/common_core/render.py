"""Native render worker, adapted from pinned Hotel fixed-camera renderer.

Use through tools/launch_render.py; no imports from historical scripts.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request',type=Path,required=True);args=parser.parse_args()
    request=json.loads(args.request.read_text(encoding='utf-8'));out=args.request.parent
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from common_core.identity import sha256_file
    from common_core.manifest import write_json_new
    cases=request.get('cases',[request])
    for case in cases:
        manifest=Path(case['manifest']);scene=manifest.parent/'scene.usda'
        if sha256_file(manifest)!=case['manifest_sha256'] or sha256_file(scene)!=case['scene_sha256']:raise ValueError('RENDER_IDENTITY_MISMATCH')
    if request.get('worker_sha256') and sha256_file(__file__)!=request['worker_sha256']:raise ValueError('RENDER_WORKER_IDENTITY')
    for name in ['cache','data','shadercache','drivercache','texturecache','optix']:(out/name).mkdir()
    os.environ['OPTIX_CACHE_PATH']=str(out/'optix')
    from isaacsim import SimulationApp
    app=SimulationApp(dict(headless=True,width=request.get('width',960),height=request.get('height',600),active_gpu=0,multi_gpu=False,
        extra_args=['--d3d12','--/app/vulkan=false','--/app/d3d12=true','--/app/asyncRendering=false',
            '--/renderer/multiGpu/enabled=false','--/UJITSO/enabled=false','--/UJITSO/datastore/allowHubDataStore=false',
            '--/app/settings/persistent=false','--/app/exts/registryEnabled=false','--/log/file='+str(out/'isaac.log'),
            '--/app/userConfigPath='+str(out/'user.config.json'),'--/app/tokens/cache='+str(out/'cache'),
            '--/app/tokens/data='+str(out/'data'),'--/rtx/shaderDb/cachePath='+str(out/'shadercache'),
            '--/rtx-transient/resourcemanager/localTextureCachePath='+str(out/'texturecache'),
            '--/rtx/shaderDb/driverCachePath='+str(out/'drivercache')]))
    import carb
    import omni.usd
    import omni.kit.app
    from pxr import Gf,UsdGeom
    from omni.kit.viewport.utility import get_active_viewport,capture_viewport_to_file
    from isaacsim.core.utils.viewports import set_camera_view
    async def ticks(n):
        for _ in range(n):await omni.kit.app.get_app().next_update_async()
    async def capture_case(case,case_out):
        ctx=omni.usd.get_context();carb.settings.get_settings().set('/persistent/app/viewport/displayOptions',0)
        manifest=Path(case['manifest']);scene=manifest.parent/'scene.usda'
        if sha256_file(manifest)!=case['manifest_sha256'] or sha256_file(scene)!=case['scene_sha256']:raise ValueError('RENDER_IDENTITY_MISMATCH')
        if not await ctx.open_stage_async(str(scene)):raise RuntimeError('RENDER_STAGE_OPEN_FAILED')
        await ticks(65);stage=ctx.get_stage();stage.SetEditTarget(stage.GetSessionLayer());images=[]
        for name,cfg in case['cameras'].items():
            path='/CommonCoreReview/Camera';cam=UsdGeom.Camera.Define(stage,path)
            cam.CreateFocalLengthAttr(cfg['focal']);cam.CreateClippingRangeAttr(Gf.Vec2f(.02,100))
            viewport=get_active_viewport();viewport.set_active_camera(path)
            set_camera_view(eye=cfg['eye'],target=cfg['target'],camera_prim_path=path,viewport_api=viewport)
            await ticks(55);image=case_out/(name+'.png')
            await capture_viewport_to_file(viewport,str(image)).wait_for_result(completion_frames=8)
            for _ in range(180):
                if image.exists() and image.stat().st_size:break
                await ticks(1)
            if not image.exists() or not image.stat().st_size:raise RuntimeError('RENDER_IMAGE_MISSING')
            images.append(dict(view=name,path=image.name,sha256=sha256_file(image),camera=cfg));print('IMAGE_CAPTURED',name,flush=True)
        report=dict(execution='EXECUTED',outcome='UNKNOWN',review_status='CAPTURED_PENDING_REVIEW',
            manifest_sha256=case['manifest_sha256'],target_state_digest=case['state_digest'],scene_sha256=case['scene_sha256'],
            renderer='Direct3D12',images=images,scope='native fixed-camera images; no dynamics',source_saved=False,
            producer_identity=dict(worker_sha256=request.get('worker_sha256'),code_hash=request.get('producer_code_hash')))
        if sha256_file(scene)!=case['scene_sha256']:raise ValueError('RENDER_SCENE_CHANGED')
        write_json_new(case_out/'render.json',report)
        return dict(manifest_sha256=case['manifest_sha256'],render_ref=str((case_out/'render.json').relative_to(out)),sha256=sha256_file(case_out/'render.json'))
    async def capture():
        reports=[]
        for index,case in enumerate(cases):
            case_out=out/('case-'+str(index)) if 'cases' in request else out
            if case_out!=out:case_out.mkdir()
            reports.append(await capture_case(case,case_out));print('RENDER_CASE_COMPLETE',index,flush=True)
        if 'cases' in request:write_json_new(out/'render_index.json',dict(cases=reports,scope='capture only; visual review separate'))
    task=asyncio.ensure_future(capture());failed=False
    while app.is_running() and not task.done():app.update()
    try:task.result()
    except BaseException:
        failed=True;write_json_new(out/'error.json',dict(reason=traceback.format_exc()));traceback.print_exc()
    app.close(wait_for_replicator=False,exit_code=1 if failed else 0)


if __name__=='__main__':main()
