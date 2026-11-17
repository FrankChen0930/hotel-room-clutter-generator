"""WU-02 bounded read-only probe: six selected collider prims at most."""
import argparse
import json
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
from common_core.identity import sha256_file
Usd,_=load_usd(Path('C:/isaac_sim'))
from pxr import UsdPhysics
from common_core.adapters import extract_support


def probe():
    path=CODE.parent/'YAZHI-TWIN/room/usd/YAZHI_TWIN.usd'
    before=sha256_file(path);stage=Usd.Stage.Open(str(path));selected=[]
    roots=['/YAZHI_TWIN/ShellColliders/Floor','/YAZHI_TWIN/Furniture/ROUND_BLACK_TABLE',
           '/YAZHI_TWIN/Furniture/BEDSIDE_CABINET','/YAZHI_TWIN/Furniture/WOODEN_BENCH']
    for root_path in roots:
        root=stage.GetPrimAtPath(root_path)
        if not root:continue
        for prim in Usd.PrimRange(root,Usd.TraverseInstanceProxies()):
            if prim.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():
                selected.append(extract_support(stage,prim))
                if len(selected)==6:break
        if len(selected)==6:break
    after=sha256_file(path)
    if before!=after:raise ValueError('SOURCE_CHANGED')
    return dict(execution='EXECUTED',scope='six selected YAZHI collider prims maximum; no native simulation',
                source_sha256=before,source_unchanged=before==after,supports=selected,
                adapter_decision='Use analytic primitive_top for supported upright Cube/Cylinder; mesh_top requires proven convex coverage; all other geometry UNKNOWN.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=probe()
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result))
