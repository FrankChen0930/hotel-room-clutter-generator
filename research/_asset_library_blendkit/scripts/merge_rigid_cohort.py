"""Merge independent candidate catalogs, retaining exact shared room/source definitions."""
import copy
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    import argparse,re
    p=argparse.ArgumentParser();p.add_argument('--cohorts',nargs='+',default=['rigid005','rigid006'])
    p.add_argument('--cohort-out',default='rigid005006');args=p.parse_args()
    assert all(re.fullmatch(r'[a-zA-Z0-9_]+',name) for name in [args.cohort_out,*args.cohorts])
    cases=[c for name in args.cohorts for c in read(ROOT/'config'/(name+'_cases.json'))['cases']]
    assert cases
    out=ROOT/'config'/(args.cohort_out+'_shared');out.mkdir(exist_ok=False)
    first=Path(cases[0]['config']).parent
    cfg=read(first/'deployment.json');profile=read(first/'profile.json')
    policy=read(first/'policy.json');catalog=read(first/'catalog.json');lock=read(first/'source_lock.json')
    entries={e['asset_id']:e for e in catalog['entries']}
    dependencies={(d['mount'],d['path']):d for d in lock['assets']}
    inputs=[]
    for case in cases:
        folder=Path(case['config']).parent
        other=read(folder/'profile.json');other['profile_version']=profile['profile_version']
        assert other==profile,'Room geometry/support definitions must be identical'
        assert read(folder/'deployment.json')==cfg
        sl=read(folder/'source_lock.json');assert sl['rooms']==lock['rooms']
        for e in read(folder/'catalog.json')['entries']:
            if e['asset_id'] in entries: assert entries[e['asset_id']]==e
            entries[e['asset_id']]=e
        for d in sl['assets']:
            key=(d['mount'],d['path'])
            if key in dependencies: assert dependencies[key]==d
            dependencies[key]=d
        p=read(folder/'policy.json')
        policy['scenarios']['STAYOVER']['eligible_categories']=sorted(set(policy['scenarios']['STAYOVER']['eligible_categories'])|set(p['scenarios']['STAYOVER']['eligible_categories']))
        policy['levels']['high']['eligible_categories']=sorted(set(policy['levels']['high']['eligible_categories'])|set(p['levels']['high']['eligible_categories']))
        for category,states in p['levels']['high'].get('allowed_states',{}).items():
            policy['levels']['high'].setdefault('allowed_states',{})[category]=sorted(set(policy['levels']['high']['allowed_states'].get(category,[]))|set(states))
        inputs.append(dict(path=str(Path(case['config']).relative_to(ROOT)),sha256=sha(case['config'])))
    catalog['entries']=list(entries.values());catalog['catalog_id']=args.cohort_out+'-controlled-local-candidate'
    lock['assets']=list(dependencies.values())
    for name,value in [('deployment.json',cfg),('profile.json',profile),('policy.json',policy),('catalog.json',catalog),('source_lock.json',lock)]:write(out/name,value)
    write(out/'merge_receipt.json',dict(outcome='PASS',cases=len(cases),new_asset_ids=[c['asset_id'] for c in cases],inputs=inputs,
          scope='Identical room/profile/source checked before sharing native preparation; no pose, source or qualification changes'))
    output=ROOT/'config'/(args.cohort_out+'_cases.json')
    if output.exists():assert read(output)['cases']==cases
    else:write(output,dict(cases=cases,failures=[]))
    preview=ROOT/'config'/(args.cohort_out+'_preview_jobs.json')
    if not preview.exists():write(preview,dict(jobs=[dict(asset_id=c['asset_id'],usd=c['asset']) for c in cases]))
    print('INDEPENDENT_CANDIDATES_MERGED',len(cases))

if __name__=='__main__': main()
