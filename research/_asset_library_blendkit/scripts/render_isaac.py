"""Native D3D12 asset studio preview; capture is never automatic visual acceptance."""
import argparse
import asyncio
import os
from pathlib import Path
import sys
import traceback
from library import sha, write

def main():
    p=argparse.ArgumentParser(); p.add_argument('--usd',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scope',default='ASSET_CAPTURE_PENDING_VISUAL_REVIEW'); a=p.parse_args()
    source=a.usd.resolve(strict=True); before=sha(source); out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    for name in ('cache','data','shadercache','drivercache','texturecache','optix'): (out/name).mkdir()
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
    import omni.usd
    import omni.kit.app
    import carb
    from pxr import Usd, UsdGeom, UsdLux, Gf, Sdf
    from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file
    from isaacsim.core.utils.viewports import set_camera_view
    async def ticks(n):
        for _ in range(n): await omni.kit.app.get_app().next_update_async()
    async def capture():
        carb.settings.get_settings().set('/persistent/app/viewport/displayOptions',0)
        ctx=omni.usd.get_context(); await ctx.new_stage_async(); stage=ctx.get_stage()
        UsdGeom.SetStageUpAxis(stage,'Z'); UsdGeom.SetStageMetersPerUnit(stage,1)
        prim=stage.DefinePrim('/Asset','Xform'); prim.GetReferences().AddReference(str(source))
        await ticks(45)
        bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']).ComputeWorldBound(prim).ComputeAlignedRange()
        if bounds.IsEmpty(): raise ValueError('EMPTY_RENDER_BOUNDS')
        center=bounds.GetMidpoint(); size=bounds.GetSize(); radius=max(float(x) for x in size)
        if not radius>0: raise ValueError('ZERO_RENDER_BOUNDS')
        dome=UsdLux.DomeLight.Define(stage,'/Studio/Dome'); dome.CreateIntensityAttr(650)
        dome.CreateColorAttr(Gf.Vec3f(.92,.95,1))
        sun=UsdLux.DistantLight.Define(stage,'/Studio/Key'); sun.CreateIntensityAttr(1800); sun.CreateAngleAttr(15)
        UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(25,-35,25))
        path='/Studio/Camera'; cam=UsdGeom.Camera.Define(stage,path)
        cam.CreateFocalLengthAttr(45); cam.CreateClippingRangeAttr(Gf.Vec2f(max(.001,radius/1000),max(100,radius*100)))
        viewport=get_active_viewport(); viewport.set_active_camera(path)
        views={'front':[1.7,-2.2,1.5],'back':[-1.7,2.2,1.5]}; images=[]; cameras={}
        for name,vector in views.items():
            eye=[float(center[i])+radius*vector[i] for i in range(3)]
            target=list(map(float,center)); cameras[name]=dict(eye=eye,target=target,focal=45)
            set_camera_view(eye=eye,target=target,camera_prim_path=path,viewport_api=viewport)
            await ticks(70); dest=out/(name+'.png')
            await capture_viewport_to_file(viewport,str(dest)).wait_for_result(completion_frames=8)
            # Viewport completion can precede the asynchronous PNG file write.
            for _ in range(180):
                if dest.is_file() and dest.stat().st_size>=100:break
                await ticks(1)
            if not dest.is_file() or dest.stat().st_size<100: raise ValueError('CAPTURE_MISSING')
            images.append(dict(path=str(dest.relative_to(Path(__file__).resolve().parents[1])),sha256=sha(dest)))
        if sha(source)!=before: raise ValueError('SOURCE_CHANGED')
        stage.GetRootLayer().Export(str(out/'preview_scene.usda'))
        write(out/'render.json',dict(outcome='PASS',usd_sha256=before,images=images,cameras=cameras,
            renderer='Isaac Sim D3D12',isaac_version=Path('C:/isaac_sim/VERSION').read_text().strip(),
            scope=a.scope,visual_status='CAPTURED_PENDING_REVIEW',dynamics='NOT_EXECUTED'))
    task=asyncio.ensure_future(capture()); failed=False
    while app.is_running() and not task.done(): app.update()
    try: task.result()
    except BaseException:
        failed=True; write(out/'error.json',dict(outcome='FAIL',reason=traceback.format_exc())); traceback.print_exc()
    app.close(wait_for_replicator=False,exit_code=int(failed))

if __name__=='__main__':main()
