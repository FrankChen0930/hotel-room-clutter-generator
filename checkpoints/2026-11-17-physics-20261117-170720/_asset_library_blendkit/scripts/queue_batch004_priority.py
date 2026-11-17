"""Diversify the acquired pool with toiletries and personal charging equipment."""
from library import ROOT,read,write

BASES=['abb55c86-2ca0-4650-8b7a-756b0d052f97','ad9f1563-3d0a-4240-93b2-030713a55ff0',
       '02734c70-c281-4ac1-aca7-876ec5130e22','75ae1630-d426-40c3-8531-ecc1b47dcf32',
       'a8b94094-9e18-4f2d-b0f9-868dacce557f','a758d464-0bb9-490a-a602-4d21d769d086']

def main():
    records=read(ROOT/'registry/assets.json')['assets'];master=read(ROOT/'config/batch_001_processing_jobs.json');jobs=[]
    for base in BASES:
        existing=next((j for j in master['jobs'] if j['base_id']==base),None)
        if existing:jobs.append(existing);continue
        a=next(a for a in records if a['source']['asset_base_id']==base)
        assert a['source'].get('original_file') and a['status']!='REJECTED' and not a.get('local_qualification')
        probe=read(ROOT/'reports'/(base+'_batch001_probe.json'));assert not probe['libraries']
        meshes=[o['name'] for o in probe['objects'] if o['type']=='MESH' and not o['hidden'] and not o['hide_render']]
        assert meshes
        job=dict(base_id=base,source=a['source']['original_file'],meshes=meshes,
            prepare_dir='artifacts/'+base+'/prepare_expand003',conversion_dir='artifacts/'+base+'/convert_expand003',
            dimension_bounds_m=dict(min=[.003,.003,.001],max=[.6,.6,.6]),allow_base_color_bake=True,
            allow_multi_material_bake=True,max_texture_dimension=2048,source_root_rotation_deg=[0,0,0],
            state_id='source_fixed_form',supports=['bench'],replace_request_ids=['quality/s0_towel/1'],tag='expand003_'+base[:8])
        master['jobs'].append(job);jobs.append(job);write(ROOT/'config'/('job_'+base+'.json'),job)
    write(ROOT/'config/batch_001_processing_jobs.json',master)
    write(ROOT/'config/batch004_priority_jobs.json',dict(jobs=jobs,scope='Exact acquired sources, technical candidates only; no acceptance inferred'))
    print('DIVERSE_ACQUIRED_COHORT_QUEUED',len(jobs))

if __name__=='__main__':main()
