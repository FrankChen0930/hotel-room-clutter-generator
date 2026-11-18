"""Retry previously blocked rigid sources once with the validated BUMP-only recipe."""
import argparse,copy,re
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--cohort',required=True);p.add_argument('--limit',type=int,default=12);a=p.parse_args()
    assert re.fullmatch(r'rigid\d{3}',a.cohort) and 1<=a.limit<=16
    out=ROOT/'config'/(a.cohort+'_jobs.json');assert not out.exists()
    master=read(ROOT/'config/batch_001_processing_jobs.json');records={x['source']['asset_base_id']:x for x in read(ROOT/'registry/assets.json')['assets']}
    retries=[]
    for index,old in enumerate(list(master['jobs'])):
        record=records[old['base_id']]
        if record['status']=='REJECTED' or record.get('local_qualification',{}).get('outcome')=='PASS':continue
        if record['category'] not in {'electronics','toiletry','personal','food','paper','luggage'} or record.get('object_form') in {'soft-like','S0-like'}:continue
        if old.get('allow_bump_only_normal_bake'):continue
        converted=ROOT/old['conversion_dir']/'integrity.json'
        if converted.exists() and read(converted)['outcome']=='PASS':continue
        log=ROOT/'artifacts'/old['base_id']/(Path(old['prepare_dir']).name+'.log')
        if not log.exists() or 'MATERIAL_DISPLACEMENT_REQUIRES_EXPLICIT_GEOMETRY_RECIPE' not in log.read_text(encoding='utf-8',errors='replace'):continue
        base=old['base_id'];archive=ROOT/'config/processing_job_history'/(base+'_before_'+a.cohort+'.json')
        assert not archive.exists();write(archive,old)
        job=copy.deepcopy(old);job.update(prepare_dir=f'artifacts/{base}/prepare_{a.cohort}_bump_retry_a000',
            conversion_dir=f'artifacts/{base}/convert_{a.cohort}_bump_retry_a000',tag=a.cohort+'_'+base[:8],
            allow_bump_only_normal_bake=True,allow_simple_surface_recipes=True,allow_generated_bake_uv=True,
            bump_bake_resolution=1024,previous_job=dict(path=str(archive.relative_to(ROOT)),sha256=sha(archive)),
            retry_reason='Validated source BUMP-only height-to-normal mapping; true geometry displacement remains blocked')
        master['jobs'][index]=job;retries.append(job);write(ROOT/'config'/('job_'+base+'.json'),job)
        if len(retries)>=a.limit:break
    write(ROOT/'config/batch_001_processing_jobs.json',master);write(out,dict(jobs=retries,scope='Single new-capability attempt; prior failures and source bytes retained'))
    print('BUMP_ONLY_REAL_SOURCE_RETRIES_QUEUED',len(retries))

if __name__=='__main__':main()
