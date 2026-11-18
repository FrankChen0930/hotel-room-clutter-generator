"""Queue conservative single-visible-mesh sources after actual Blender probing."""
from library import ROOT,read,write

def main():
    registry=read(ROOT/'registry/assets.json');master=read(ROOT/'config/batch_001_processing_jobs.json');known={j['base_id'] for j in master['jobs']};added=[];deferred=[]
    for a in registry['assets']:
        base=a['source']['asset_base_id'];probe_path=ROOT/'reports'/(base+'_batch001_probe.json')
        if base in known or not a.get('batch_id','').startswith('batch_') or not a['source'].get('version_id') or a['status']=='REJECTED' or not probe_path.exists():continue
        probe=read(probe_path);meshes=[o for o in probe['objects'] if o['type']=='MESH' and not any(o[k] for k in ('hidden','hide_render','hide_viewport'))]
        if len(meshes)!=1 or probe['libraries']:
            deferred.append(dict(asset_id=a['asset_id'],reason='MULTI_MESH_OR_EXTERNAL_LIBRARY_RECIPE_REVIEW'));continue
        if 'flaming skull' in a['name'].lower():
            a['blockers']=['WORN_TORSO_FORM_REQUIRES_RESTING_STATE_REVIEW'];deferred.append(dict(asset_id=a['asset_id'],reason=a['blockers'][0]));continue
        job=dict(base_id=base,source=a['source']['original_file'],meshes=[meshes[0]['name']],
            prepare_dir='artifacts/'+base+'/prepare_batch001',conversion_dir='artifacts/'+base+'/convert_batch001',
            dimension_bounds_m=dict(min=[.005,.005,.001],max=[1.2,1.2,1.5]),allow_base_color_bake=True,max_texture_dimension=2048,
            state_id='source_fixed_form',supports=['floor_luggage','floor_bedside'],tag='batch001_'+base[:8])
        if a['category'] in {'electronics','paper'}:job['supports']=['bench','desk']
        elif a['category']=='toiletry':job['supports']=['minibar','bench']
        elif a['category']=='towel':job['supports']=['bench','floor_bedside']
        path=ROOT/'config'/('job_'+base+'.json')
        if path.exists():raise ValueError('EXISTING_JOB_REQUIRES_REVIEW:'+base)
        write(path,job);master['jobs'].append(job);added.append(a['asset_id'])
    write(ROOT/'registry/assets.json',registry);write(ROOT/'config/batch_001_processing_jobs.json',master)
    write(ROOT/'reports/batch001_source_queue_latest.json',dict(added=added,deferred=deferred,scope='Conversion candidacy only; actual native review and support gates remain required'))
    print('NEW_SINGLE_MESH_JOBS',len(added),'DEFERRED',len(deferred))

if __name__=='__main__':main()
