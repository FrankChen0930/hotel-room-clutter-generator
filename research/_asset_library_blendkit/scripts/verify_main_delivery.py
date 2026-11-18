"""Review the exact prospective Git payload without reading credential stores."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();repo=a.checkout.resolve()
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    assert git('branch','--show-current').decode().strip()=='main'
    assert git('remote','get-url','origin').decode().strip()=='https://github.com/FrankChen0930/hotel-room-clutter-generator.git'
    paths=sorted(set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().strip('\x00').split('\x00')))
    files=[(name,repo/name) for name in paths if (repo/name).is_file()]
    secret=re.compile(rb'(?:github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    dangerous={'.blend','.blend1','.exe','.dll','.dmp','.pdb','.pdf','.ppt','.pptx','.pem','.key','.p12','.pfx'}
    binary_assets={'.usd','.usda','.usdc','.usdz','.png','.jpg','.jpeg','.zip'}
    for name,path in files:
        assert path.stat().st_size<95*1024*1024,('GITHUB_FILE_LIMIT',name)
        assert path.suffix.lower() not in dangerous,('EXCLUDED_PAYLOAD',name)
        assert not any(part in {'blender_profile','sources','.aws','.ssh','.codex','.agents','node_modules','__pycache__'} for part in Path(name).parts),('EXCLUDED_DIRECTORY',name)
        if path.suffix.lower() in binary_assets:
            assert name.startswith('research/_asset_library_blendkit/public_data/') or name.startswith('docs/previews/') or name=='downloads/hotel705_examples.zip',('UNAPPROVED_BINARY',name)
        if path.suffix.lower() in {'.py','.ps1','.json','.md','.txt','.toml','.yaml','.yml'}:
            assert not secret.search(path.read_bytes()),('POSSIBLE_SECRET_REDACTED',name)
        if name.startswith('research/_asset_library_blendkit/scripts/') and path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8-sig'))
    public=repo/'research/_asset_library_blendkit'
    for row in read(public/'config/public_source_inventory.json')['files']:assert sha(public/row['path'])==row['sha256']
    assert read(public/'registry/assets.json')['assets']==[]
    rows=read(public/'artifacts/legacy_density_pool_a001/index.json');assert len(rows)==5
    for row in rows:assert row['source_kind']=='EXISTING_ROOM_NOT_NEW_BLENDKIT' and 'usd_path_relative' in row and 'usd_path' not in row
    status=read(repo/'docs/PACKAGE_STATUS.json');archive=repo/status['download'];assert sha(archive)==status['sha256']
    assert status['relocation']['outcome']=='PASS' and len(status['relocation']['roots'])==13
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():assert not Path(name).is_absolute() and '..' not in Path(name).parts and Path(name).suffix.lower() not in dangerous
        pkg=json.loads(z.read('package_manifest.json'));assert pkg['redistribution']=='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_PERMISSION_ONLY'
        for row in pkg['files']:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
        for row in pkg['roots']:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256'] and row['up_axis']=='Z' and row['meters_per_unit']==1
        cases=json.loads(z.read('delivery_map.json'))['cases'];assert len(cases)==6
        for row in cases:
            assert len(json.loads(z.read(f"evidence/{row['level']}_seed_{row['seed']}/manifest.json"))['objects'])==row['instances']
            assert json.loads(z.read(f"evidence/{row['level']}_seed_{row['seed']}/native_dynamics_result.json"))['native_steps']==3600
    for name in ['README.md','README.zh-TW.md']:
        text=(repo/name).read_text(encoding='utf8')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' not in link and not link.startswith('#'):assert (repo/link.split('#')[0]).is_file(),('BROKEN_README_LINK',name,link)
        assert '102' in text and '706' in text and '707' in text
    metadata=read(repo/'docs/asset_sources.json')['assets'];assert len(metadata)==673
    assert sum(x['local_technical_pass'] and not x.get('variant_of') for x in metadata)==102
    assert not any(path.suffix.lower() in {'.ppt','.pptx'} for _,path in files)
    protected=read(ROOT/'reports/protected_verification.json');assert protected['outcome']=='PASS' and protected['checked']==302
    git('diff','--check')
    write(a.receipt,dict(outcome='PASS',repository=str(repo),branch='main',files=len(files),bytes=sum(f.stat().st_size for _,f in files),largest=sorted([dict(path=n,bytes=f.stat().st_size) for n,f in files],key=lambda r:r['bytes'],reverse=True)[:8],public_source_files=len(read(public/'config/public_source_inventory.json')['files']),public_native_prop_sources=5,packaged_stage_entries=13,public_scene_cases=6,download_sha256=sha(archive),independent_local_blendkit=102,blendkit_model_payloads=0,presentation_files=0,original_protected_files=protected['checked'],scope='Prospective Git payload, file limits, credential-pattern scan, pinned public inputs, binary scope/ZIP integrity, exact native receipts, README links, catalog metadata counts, presentation exclusion and protected baseline. Remote push is separate.'))
    print('MAIN_DELIVERY_PREFLIGHT_PASS',len(files),'files',archive.stat().st_size,'ZIP bytes')

if __name__=='__main__':main()
