"""Recover only missing exported texture names from exact preparation-pinned bytes."""
from pathlib import Path
import shutil
from library import ROOT,read,write,sha
from inspect_usd import inspect
from hotel_metadata import enrich

if __name__=='__main__':
    master=read(ROOT/'config/batch_001_processing_jobs.json');cohort=read(ROOT/'config/batch002_priority_jobs.json');results=[]
    for job in cohort['jobs']:
        raw=ROOT/job['conversion_dir'];report=raw/'integrity.json'
        if not report.exists() or read(report)['outcome']=='PASS':continue
        failed=read(report)
        if failed['errors']!=['UNRESOLVED_DEPENDENCIES']:continue
        prep=read(ROOT/job['prepare_dir']/'preparation.json');pins={Path(x['path']).name:x for x in prep.get('texture_locator_repairs',[])}
        repairs=[]
        for missing in failed['unresolved']:
            relative=Path(missing);target=(raw/relative).resolve()
            assert target.is_relative_to(raw/'textures')
            relative=target.relative_to(raw)
            pin=pins[relative.name];source=ROOT/pin['path'];assert source.is_file() and sha(source)==pin['sha256']
            if target.exists():assert sha(target)==pin['sha256']
            repairs.append((relative,source,pin['sha256']))
        assert repairs
        out=raw.parent/'recover_expand002';shutil.copytree(raw,out)
        for relative,source,expected in repairs:
            dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);assert sha(dest)==expected
        conversion=read(raw/'conversion.json');assert sha(out/'asset.usdc')==conversion['usd_sha256']
        conversion['dependency_recovery']=dict(original_conversion=dict(path=str((raw/'conversion.json').relative_to(ROOT)),sha256=sha(raw/'conversion.json')),
            repairs=[dict(target=str(relative),preparation_file=str(source.relative_to(ROOT)),sha256=expected,pixel_bytes_unchanged=True) for relative,source,expected in repairs])
        conversion['outputs']=[dict(path=str(p.relative_to(out)),sha256=sha(p)) for p in out.rglob('*') if p.is_file() and p.name not in {'conversion.json','integrity.json'}]
        write(out/'conversion.json',conversion);integrity=inspect(out/'asset.usdc');assert integrity['outcome']=='PASS';write(out/'integrity.json',integrity)
        job['conversion_dir']=str(out.relative_to(ROOT)).replace('\\','/');write(ROOT/'config'/('job_'+job['base_id']+'.json'),job)
        master['jobs']=[job if x['base_id']==job['base_id'] else x for x in master['jobs']]
        registry=read(ROOT/'registry/assets.json');a=next(x for x in registry['assets'] if x['source']['asset_base_id']==job['base_id'])
        a.update(last_completed_stage='CONVERTED',dimensions_m=integrity['dimensions_m'],geometry_identity=conversion['geometry_identity'],state_id=job['state_id'],
            usd=dict(path=str((out/'asset.usdc').relative_to(ROOT)),sha256=sha(out/'asset.usdc')),
            physics=dict(mode='STATIC_ONLY',mass_kg=None,collision_proxy=None),blockers=['ACTUAL_NATIVE_VISUAL_STATIC_SUPPORT_REPLAY_PENDING','EXTRACTABLE_GENERATOR_RIGHTS_UNCLEARED'])
        for kind in ('conversion','integrity'):
            p=out/(kind+'.json');a['evidence'][kind]=dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
        p=ROOT/'config'/('job_'+job['base_id']+'.json');a['processing_job']=dict(path=str(p.relative_to(ROOT)),sha256=sha(p));enrich(a);write(ROOT/'registry/assets.json',registry)
        results.append(dict(asset_id=a['asset_id'],recovered=len(repairs),outcome='CONVERTED_INTEGRITY_PASS'))
    write(ROOT/'config/batch_001_processing_jobs.json',master);write(ROOT/'config/batch002_priority_jobs.json',cohort)
    write(ROOT/'reports/pinned_export_texture_recovery.json',dict(results=results,scope='Missing filename recovery from exact pinned original image bytes; fresh native review required'))
    print('PINNED_EXPORT_TEXTURE_RECOVERY_PASS',len(results))
