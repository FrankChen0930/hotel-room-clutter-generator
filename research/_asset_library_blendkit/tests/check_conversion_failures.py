"""Exercise actual Blender exporter preflight rejection against the engineering fixture."""
from pathlib import Path
import json
import os
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from library import ROOT, read, write

if __name__=='__main__':
    fixture=ROOT/'reports/infrastructure_fixture_001'; original=read(fixture/'job.json')
    results=[]
    cases=[('bad_sha','source_sha256','0'*64,'SOURCE_SHA_MISMATCH'),
           ('bad_size','dimension_bounds_m',dict(min=[2,2,2],max=[3,3,3]),'DIMENSIONS_OUT_OF_CATEGORY_BOUNDS')]
    env={**os.environ,'BLENDER_USER_RESOURCES':str(ROOT/'blender_profile'),
        'BLENDER_USER_CONFIG':str(ROOT/'blender_profile/config'),'BLENDER_USER_SCRIPTS':str(ROOT/'blender_profile/scripts')}
    for name,key,value,reason in cases:
        job=dict(original); job[key]=value; job['output']=str(fixture/name)
        jp=fixture/(name+'.job.json'); write(jp,job)
        proc=subprocess.run(['C:/Program Files/Blender Foundation/Blender 5.2/blender.exe',
            '--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
            '--python',str(ROOT/'scripts/convert_blender.py'),'--',str(jp)],capture_output=True,text=True,timeout=45,env=env)
        (fixture/(name+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8')
        report=read(fixture/name/'conversion.json')
        assert proc.returncode!=0 and report['outcome']=='FAIL' and reason in report['reason'],report
        assert not (fixture/name/'asset.usdc').exists()
        results.append(dict(case=name,outcome='PASS_NEGATIVE_REJECTED',reason=reason,exit_code=proc.returncode))
    write(fixture/'negative_checks.json',results); print(results)
