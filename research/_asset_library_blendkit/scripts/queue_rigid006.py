"""Second rigid-priority cohort, selecting individual props rather than display sets."""
from library import ROOT, read, write

PREFIXES = '''62c5deaf 0797f129 7a798f79 24c47184 02bdb24a 541b0c87
138fa842 15b4839d 2453a855 c7495586 abcc784e 6e0a7c7a
13bb2552 ea6af6a1'''.split()

def main():
    records=read(ROOT/'registry/assets.json')['assets']
    master=read(ROOT/'config/batch_001_processing_jobs.json'); jobs=[]; blocked=[]
    for prefix in PREFIXES:
        a=next(a for a in records if a['source']['asset_base_id'].startswith(prefix))
        base=a['source']['asset_base_id']
        existing=next((j for j in master['jobs'] if j['base_id']==base),None)
        if existing: jobs.append(existing); continue
        assert a['source'].get('original_file') and a['status']!='REJECTED'
        probe=read(ROOT/'reports'/(base+'_batch001_probe.json'))
        if probe['libraries'] or any(o['type']=='CURVE' for o in probe['objects']):
            blocked.append(dict(asset_id=a['asset_id'],reason='External source library or curve requires explicit dependency recipe',libraries=probe['libraries']))
            continue
        meshes=[o['name'] for o in probe['objects'] if o['type']=='MESH' and not o['hidden'] and not o['hide_render']]
        note='Complete visible source mesh selection; fixed configuration only'
        if prefix=='24c47184':
            meshes=['Soap dispenser']; note='One complete dispenser, excluding the duplicate second dispenser'
        if prefix=='15b4839d':
            meshes=['KickstandSupport_3','SurfaceTablet_3']; note='Complete tablet and attached kickstand; detached pen excluded explicitly'
        job=dict(base_id=base,source=a['source']['original_file'],meshes=meshes,
                 prepare_dir=f'artifacts/{base}/prepare_rigid006_a000',conversion_dir=f'artifacts/{base}/convert_rigid006_a000',
                 dimension_bounds_m=dict(min=[.003,.003,.001],max=[.65,.65,.65]),
                 allow_base_color_bake=True,allow_multi_material_bake=True,max_texture_dimension=2048,
                 source_root_rotation_deg=[0,0,0],state_id='source_fixed_form',supports=['bench'],
                 replace_request_ids=['quality/s0_towel/1'],tag='rigid006_'+prefix,selection_note=note)
        assert meshes
        master['jobs'].append(job); jobs.append(job)
        write(ROOT/'config'/('job_'+base+'.json'),job)
    write(ROOT/'config/batch_001_processing_jobs.json',master)
    write(ROOT/'config/rigid006_jobs.json',dict(jobs=jobs,blocked=blocked,scope='Rigid-priority candidates; fixed geometry does not establish articulation or dynamics'))
    print('RIGID_CANDIDATES_QUEUED',len(jobs))

if __name__=='__main__': main()
