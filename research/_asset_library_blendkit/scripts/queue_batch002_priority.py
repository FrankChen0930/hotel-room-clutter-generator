"""Explicit source-backed conversion cohort; one source compound never counts as parts."""
from library import ROOT,read,write

IDS=['3394d3ed-24e7-4dfe-b1a6-d4086df20195','639cf1dc-24e8-46db-a181-6082910b72c2',
'804cce47-eb45-4dbe-bb30-4bccebc0513b','ebbe0d72-f5b0-4875-b91e-72457dbfbe09',
'bfcc4fc6-c361-4ebd-bd77-bffd40958849','eab5b1cb-c75d-4e80-a679-c9a4ea26c3b7',
'b54819e4-6551-4509-b76c-2bce9ada8cf8','0b960a0d-01f7-4038-95bf-6915f58360f1',
'0695b127-5065-438d-9f08-32c821ca3316','2574df22-31fb-4218-8e4c-f1e19fd227e7',
'edec95aa-204f-45f2-b971-6da92da3bfc3','57a63c57-0503-49d7-aa42-68c3fda0fc66',
'fabe80bb-cbd7-4f43-b4f1-40f70d96b443','faea10d7-f0e3-444e-8bcb-f054580170e7',
'fff2f538-af1e-4ce1-972e-6504d4f922b7','9bbfc887-e61a-4430-9081-d1b22ba26d61',
'5a5900a1-1529-4c5b-87f6-26b40edf787f','065fd0c4-39ce-42ac-b2b7-b1b277a58057']

if __name__=='__main__':
    registry=read(ROOT/'registry/assets.json')['assets'];master=read(ROOT/'config/batch_001_processing_jobs.json');jobs=[]
    for base in IDS:
        a=next(x for x in registry if x['source']['asset_base_id']==base)
        assert a['source'].get('version_id') and a['status']!='REJECTED' and not a.get('local_qualification')
        probe=read(ROOT/'reports'/(base+'_batch001_probe.json'));assert not probe['libraries']
        meshes=[o['name'] for o in probe['objects'] if o['type']=='MESH' and not o['hidden'] and not o['hide_render']]
        assert meshes
        if base not in {'fabe80bb-cbd7-4f43-b4f1-40f70d96b443','faea10d7-f0e3-444e-8bcb-f054580170e7'}:assert len(meshes)==1
        job=dict(base_id=base,source=a['source']['original_file'],meshes=meshes,
            prepare_dir='artifacts/'+base+'/prepare_expand001',conversion_dir='artifacts/'+base+'/convert_expand001',
            dimension_bounds_m=dict(min=[.005,.005,.001],max=[1.2,1.2,1.5]),allow_base_color_bake=True,max_texture_dimension=2048,
            state_id='source_fixed_form',supports=['floor_luggage'],tag='expand001_'+base[:8])
        if a['category'] in {'electronics','paper','toiletry','food'}:
            job.update(supports=['bench'],replace_request_ids=['quality/s0_towel/1'])
        path=ROOT/'config'/('job_'+base+'.json')
        if path.exists() and read(path)!=job:
            archive=ROOT/'config'/('job_'+base+'_before_expand001.json')
            if not archive.exists():write(archive,read(path))
        write(path,job);master['jobs']=[j for j in master['jobs'] if j['base_id']!=base]+[job];jobs.append(job)
    write(ROOT/'config/batch_001_processing_jobs.json',master)
    write(ROOT/'config/batch002_priority_jobs.json',dict(jobs=jobs,scope='Exact actual source meshes inspected; candidate conversion only. All source parts count as one, no soft physics inferred.'))
    print('PRIORITY_REAL_SOURCE_JOBS',len(jobs))
