"""Capture real assets sequentially in one Isaac session; capture never implies visual acceptance."""
import argparse
import asyncio
import os
from pathlib import Path
import traceback
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--jobs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    jobs=read(args.jobs)['jobs'];out=args.output.resolve()
    if not 1<=len(jobs)<=16 or not out.is_relative_to(ROOT):raise ValueError('BOUNDED_WORKLINE_BATCH_REQUIRED')
    out.mkdir(parents=True,exist_ok=False)
    for name in ('cache','data','shadercache','drivercache','texturecache','optix'):(out/name).mkdir()
    os.environ['OPTIX_CACHE_PATH']=str(out/'optix')
    from isaacsim import SimulationApp
    app=SimulationApp(dict(headless=True,width=768,height=768,active_gpu=0,multi_gpu=False,
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
    from pxr import Usd,UsdGeom,UsdLux,Gf
    from omni.kit.viewport.utility import get_active_viewport,capture_viewport_to_file
    from isaacsim.core.utils.viewports import set_camera_view
    async def ticks(n):
        for _ in range(n):await omni.kit.app.get_app().next_update_async()
    async def capture(job):
        source=Path(job['usd']).resolve(strict=True);before=sha(source);folder=out/job['asset_id'];folder.mkdir()
        ctx=omni.usd.get_context();await ctx.new_stage_async();stage=ctx.get_stage()
        UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
        prim=UsdGeom.Xform.Define(stage,'/Asset').GetPrim();prim.GetReferences().AddReference(str(source))
        await ticks(40)
        bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']).ComputeWorldBound(prim).ComputeAlignedRange()
        if bounds.IsEmpty():raise ValueError('EMPTY_ASSET_BOUNDS')
        center=bounds.GetMidpoint();radius=max(map(float,bounds.GetSize()))
        if not radius>0:raise ValueError('ZERO_DIMENSIONS')
        dome=UsdLux.DomeLight.Define(stage,'/Studio/Dome');dome.CreateIntensityAttr(650);dome.CreateColorAttr(Gf.Vec3f(.92,.95,1))
        sun=UsdLux.DistantLight.Define(stage,'/Studio/Key');sun.CreateIntensityAttr(1800);sun.CreateAngleAttr(15)
        UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(25,-35,25))
        camera='/Studio/Camera';cam=UsdGeom.Camera.Define(stage,camera);cam.CreateFocalLengthAttr(45)
        cam.CreateClippingRangeAttr(Gf.Vec2f(.001,100))
        viewport=get_active_viewport();viewport.set_active_camera(camera)
        carb.settings.get_settings().set('/persistent/app/viewport/displayOptions',0)
        images=[];cameras={}
        for name,vector in {'front':[1.7,-2.2,1.5],'back':[-1.7,2.2,1.5]}.items():
            eye=[float(center[i])+radius*vector[i] for i in range(3)];target=list(map(float,center))
            set_camera_view(eye=eye,target=target,camera_prim_path=camera,viewport_api=viewport)
            cameras[name]=dict(eye=eye,target=target,focal=45)
            await ticks(65);dest=folder/(name+'.png')
            await capture_viewport_to_file(viewport,str(dest)).wait_for_result(completion_frames=8)
            for _ in range(180):
                if dest.is_file() and dest.stat().st_size>100:break
                await ticks(1)
            if not dest.is_file() or dest.stat().st_size<=100:raise ValueError('NATIVE_PNG_MISSING')
            images.append(dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest)))
        if sha(source)!=before:raise ValueError('SOURCE_CHANGED')
        report=dict(outcome='PASS',usd_sha256=before,asset_id=job['asset_id'],images=images,cameras=cameras,
            scope='Actual native asset capture only; local visual review and scene support/physics qualification are separate',review_status='PENDING_VISUAL_INSPECTION')
        write(folder/'render.json',report);return report
    async def run():
        rows=[]
        for job in jobs:
            try:report=await capture(job)
            except Exception:
                report=dict(outcome='FAIL',asset_id=job['asset_id'],reason=traceback.format_exc());write(out/(job['asset_id']+'_error.json'),report)
            rows.append(dict(asset_id=job['asset_id'],outcome=report['outcome']));print('NATIVE_ASSET_CAPTURE',job['asset_id'],report['outcome'],flush=True)
        write(out/'batch_result.json',dict(outcome='CAPTURE_BATCH_EXECUTED',results=rows,scope='No automatic quality or rights promotion'))
    task=asyncio.ensure_future(run());failed=False
    while app.is_running() and not task.done():app.update()
    try:task.result()
    except BaseException:failed=True;write(out/'fatal_error.json',dict(reason=traceback.format_exc()))
    app.close(wait_for_replicator=False,exit_code=int(failed))

if __name__=='__main__':main()
