"""Copy a conversion and repair extensionless texture locators without changing pixels."""
import argparse
from pathlib import Path
import shutil
from library import ROOT,read,write,sha
import usd_sdk
usd_sdk.load()
from pxr import Usd,Sdf
from inspect_usd import inspect

def extension(path):
    header=path.read_bytes()[:12]
    if header.startswith(b'\xff\xd8\xff'):return '.jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):return '.png'
    if header.startswith(b'II*\0') or header.startswith(b'MM\0*'):return '.tif'
    raise ValueError('UNKNOWN_IMAGE_MAGIC:'+str(path))

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    source=args.source.resolve();out=args.output.resolve()
    assert source.is_relative_to(ROOT) and out.is_relative_to(ROOT) and not out.exists()
    old=read(source/'conversion.json');assert old['outcome']=='PASS'
    shutil.copytree(source,out);mapping={}
    for path in (out/'textures').iterdir():
        if path.is_file() and not path.suffix:
            dest=path.with_suffix(extension(path));shutil.copy2(path,dest);assert sha(path)==sha(dest)
            mapping[path.relative_to(out).as_posix()]=dest.relative_to(out).as_posix()
    assert mapping
    stage=Usd.Stage.Open(str(out/'asset.usdc'));changed=[]
    for prim in stage.Traverse():
        for attr in prim.GetAttributes():
            value=attr.Get()
            if isinstance(value,Sdf.AssetPath) and Path(value.path).as_posix() in mapping:
                replacement=mapping[Path(value.path).as_posix()];attr.Set(Sdf.AssetPath(replacement));changed.append(dict(attribute=str(attr.GetPath()),old=value.path,new=replacement))
    assert len(changed)==len(mapping);stage.GetRootLayer().Save()
    report=inspect(out/'asset.usdc');assert report['outcome']=='PASS';write(out/'integrity.json',report)
    old.update(usd_sha256=sha(out/'asset.usdc'),derivative_of=dict(path=str((source/'conversion.json').relative_to(ROOT)),sha256=sha(source/'conversion.json')),
        texture_locator_repair=dict(changed=changed,pixel_bytes_unchanged=True,native_visual_review='REQUIRED'))
    old['outputs']=[dict(path=str(p.relative_to(out)),sha256=sha(p)) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in {'conversion.json','integrity.json'}]
    write(out/'conversion.json',old)
    print('TEXTURE_EXTENSIONS_REPAIRED',len(changed),'ACTUAL_NATIVE_REVIEW_STILL_REQUIRED')

if __name__=='__main__':main()
