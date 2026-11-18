"""Offline Hotel705 public example workflow; no account, download API or private assets."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import time
from library import ROOT,read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--seeds',type=int,nargs='+',default=[706,707]);p.add_argument('--after-native-receipt',type=Path);a=p.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_]{1,80}',a.tag)
    inventory=ROOT/'config/public_source_inventory.json'
    for row in read(inventory)['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    rows=read(ROOT/'artifacts/legacy_density_pool_a001/index.json')
    for row in rows:
        path=(ROOT/row['usd_path_relative']).resolve(strict=True);assert path.is_relative_to(ROOT/'public_data')
    if a.after_native_receipt:
        write(ROOT/'reports'/('public_workflow_'+a.tag+'_progress.json'),dict(outcome='WAITING',stage='previous_native_session',receipt=str(a.after_native_receipt)))
        deadline=time.monotonic()+10800
        while not a.after_native_receipt.exists():
            if time.monotonic()>deadline:raise TimeoutError('PREVIOUS_NATIVE_SESSION_NOT_COMPLETE')
            time.sleep(2)
        assert read(a.after_native_receipt)['outcome']=='PASS'
    command=[sys.executable,'-B',str(ROOT/'scripts/run_density_physics_pipeline.py'),'--tag',a.tag,'--seeds',*map(str,a.seeds),
        '--catalog-config',str(ROOT/'config/public_hotel705'),'--hotel-native-only','--portable-source-inventory',str(inventory)]
    subprocess.run(command,cwd=ROOT,check=True)


if __name__=='__main__':main()
