"""Next exact-source cohort, including explicitly frozen compound and resting states."""
from library import ROOT,read,write

NEW=['f8573a9c-0797-4607-9416-199f8da16fd8','c46b5c9d-a0c8-4b29-a373-d361d6b1459e',
'49c3286a-b70e-47be-ac59-6782c33f7f39','b0cb1fcf-4f2f-4135-8e95-c52257d099ac',
'4027c1c0-d6f0-4926-933c-e3323cc739cb','b11895dd-c6af-4071-8011-5f8a16cb5ac7',
'aaec1a4c-775c-4367-b4ac-8557876f72cd','74fca3ee-3226-4629-afdb-3b63ca8b3049',
'50d94ec7-8e08-4464-8753-1394d82305dc','492e383d-cdeb-4bbf-a960-3a28d76d0a0c',
'9513bb5c-4dc7-49af-bbae-c878a1b396fd','af189ac3-c67d-4fe2-8156-30f4488a8a75',
'3c823376-52b6-4ce8-bd2c-30152c961b15','e0215771-cea8-4806-8424-e42ec7be7e35']
EXISTING=['eab5b1cb-c75d-4e80-a679-c9a4ea26c3b7','5a5900a1-1529-4c5b-87f6-26b40edf787f']

if __name__=='__main__':
    registry=read(ROOT/'registry/assets.json')['assets'];master=read(ROOT/'config/batch_001_processing_jobs.json');jobs=[]
    for base in EXISTING:jobs.append(next(j for j in master['jobs'] if j['base_id']==base))
    for base in NEW:
        a=next(x for x in registry if x['source']['asset_base_id']==base);assert a['source'].get('version_id') and a['status']!='REJECTED' and not a.get('local_qualification')
        probe=read(ROOT/'reports'/(base+'_batch001_probe.json'));assert not probe['libraries']
        meshes=[o['name'] for o in probe['objects'] if o['type']=='MESH' and not o['hidden'] and not o['hide_render']]
        job=dict(base_id=base,source=a['source']['original_file'],meshes=meshes,prepare_dir='artifacts/'+base+'/prepare_expand002',conversion_dir='artifacts/'+base+'/convert_expand002',
            dimension_bounds_m=dict(min=[.005,.005,.001],max=[1.2,1.2,1.5]),allow_base_color_bake=True,allow_multi_material_bake=True,max_texture_dimension=2048,
            state_id='source_fixed_form',supports=['floor_luggage'],tag='expand002_'+base[:8])
        if a['category'] in {'electronics','paper','toiletry','food'}:job.update(supports=['bench'],replace_request_ids=['quality/s0_towel/1'])
        if base=='af189ac3-c67d-4fe2-8156-30f4488a8a75':job.update(source_root_rotation_deg=[90,0,0],state_id='lying_rigid_fixed')
        if base=='3c823376-52b6-4ce8-bd2c-30152c961b15':job.update(source_root_rotation_deg=[90,0,0],state_id='s0_laid_flat_source_scan')
        p=ROOT/'config'/('job_'+base+'.json')
        if p.exists() and read(p)!=job:
            archive=ROOT/'config'/('job_'+base+'_before_expand002.json')
            if not archive.exists():write(archive,read(p))
        write(p,job);master['jobs']=[j for j in master['jobs'] if j['base_id']!=base]+[job];jobs.append(job)
    write(ROOT/'config/batch_001_processing_jobs.json',master);write(ROOT/'config/batch003_priority_jobs.json',dict(jobs=jobs,
        scope='Exact original source meshes, one compound per source; two root rotations document fixed resting normalization, no deformation/physics solution inferred.'))
    print('NEXT_REAL_SOURCE_COHORT',len(jobs))
