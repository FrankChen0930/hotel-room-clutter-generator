"""Author the baked dielectric tint into standard USD Preview Surface specular workflow."""
from pathlib import Path
import shutil
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdShade,Sdf,Gf
from library import ROOT,read,write,sha
base='6d5257a4-4fdf-421d-92b9-e77f941f5187';folder=ROOT/'artifacts'/base
raw=folder/'convert_a000';out=folder/'specular_a000';out.mkdir(exist_ok=False)
conversion=read(raw/'conversion.json');assert conversion['outcome']=='PASS'
prep=read(folder/'prepare_a000/preparation.json');assert prep['outcome']=='PASS'
for p in raw.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.usd','.usda','.usdc','.png','.jpg','.jpeg','.exr'}:
        dest=out/p.relative_to(raw);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
dest=out/'textures/specular_tint.png';dest.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/prep['texture']['path'],dest)
asset=out/'asset.usdc';stage=Usd.Stage.Open(str(asset));count=0
for prim in list(stage.Traverse()):
    shader=UsdShade.Shader(prim)
    if not shader or shader.GetIdAttr().Get()!='UsdPreviewSurface':continue
    parent=prim.GetPath().GetParentPath()
    uv=UsdShade.Shader.Define(stage,parent.AppendChild('SpecularUV'));uv.CreateIdAttr('UsdPrimvarReader_float2')
    uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st');uv.CreateOutput('result',Sdf.ValueTypeNames.Float2)
    tex=UsdShade.Shader.Define(stage,parent.AppendChild('BakedSpecularTint'));tex.CreateIdAttr('UsdUVTexture')
    tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('textures/specular_tint.png'))
    tex.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB')
    tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result')
    tex.CreateInput('scale',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(prep['f0'],prep['f0'],prep['f0'],1))
    tex.CreateOutput('rgb',Sdf.ValueTypeNames.Float3)
    shader.CreateInput('useSpecularWorkflow',Sdf.ValueTypeNames.Int).Set(1)
    shader.CreateInput('specularColor',Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(),'rgb')
    count+=1
assert count==1
stage.GetRootLayer().Save()
conversion.update(usd_sha256=sha(asset),original_source_sha256=prep['source_sha256'],source_preparation=dict(path=str((folder/'prepare_a000/preparation.json').relative_to(ROOT)),sha256=sha(folder/'prepare_a000/preparation.json')),
    specular_mapping=dict(f0=prep['f0'],ior=prep['source_ior'],workflow='specular',texture_sha256=sha(dest),
        specification='https://openusd.org/25.11/spec_usdpreviewsurface.html',scope='Standard PBR approximation; visual acceptance pending'))
write(out/'conversion.json',conversion)
print('SECOND_BACKPACK_USD_SPECULAR_MAPPED',sha(asset))
