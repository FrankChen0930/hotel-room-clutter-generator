"""Actual clean-room rigid stability check after native render work completes."""
import argparse
import math
from pathlib import Path
import subprocess
import sys
import time
from library import ROOT,read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',type=Path,required=True);p.add_argument('--after-native-receipt',type=Path);a=p.parse_args()
    folder=a.scene.resolve().parent;assert folder.is_relative_to(ROOT/'runs')
    assert read(folder/'geometry_preservation.json')['outcome']=='PASS'
    if a.after_native_receipt:
        write(folder/'acceptance_progress.json',dict(outcome='WAITING',stage='previous_native_session'))
        deadline=time.monotonic()+10800
        while not a.after_native_receipt.exists():
            if time.monotonic()>deadline:raise TimeoutError('PREVIOUS_NATIVE_SESSION_NOT_COMPLETE')
            time.sleep(2)
        assert read(a.after_native_receipt)['outcome']=='PASS'
    write(folder/'acceptance_progress.json',dict(outcome='RUNNING',stage='actual_30_second_native_room_simulation'))
    out=folder/'dynamics'
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/launch_room_dynamics.py'),'--scene',str(a.scene),'--output',str(out),'--mode','props_dynamic','--seconds','30'],check=True)
    result=read(out/'result.json');trajectories=read(out/'trajectory.json')['trajectories'];issues=[]
    assert result['outcome']=='DIAGNOSTIC_PASS' and result['native_steps']==3600 and result['registered_dynamic_bodies']==49 and result['authored_joints']==31
    assert len(trajectories)==49 and result['source_sha256']==sha(a.scene)
    norm=lambda v:math.sqrt(sum(x*x for x in v))
    for path,samples in trajectories.items():
        if any(norm(x['velocity'][:3])>.03 or norm(x['velocity'][3:])>.2 for x in samples if x['time_s']>=28):issues.append(path)
    assert not issues,issues
    write(folder/'clean_room_acceptance.json',dict(outcome='PASS',scene_sha256=sha(a.scene),native_result_sha256=sha(out/'result.json'),native_steps=3600,seconds=30,
        registered_dynamic_bodies=49,authored_joints=31,final_two_seconds='PASS',source_saved=False,
        scope='Exact independent clean-room physics preparation layer; original geometry/layout retained. No deformable or robot manipulation qualification.'))
    write(folder/'acceptance_progress.json',dict(outcome='PASS',stage='clean_room_actual_native_acceptance'))
    print('CLEAN_ROOM_ACTUAL_NATIVE_ACCEPTANCE_PASS',49,31,3600)


if __name__=='__main__':main()
