"""Queue existing legally acquired rigid-prop candidates without replacing prior jobs."""
from library import ROOT, read, write

PREFIXES = '''b6a5ddf7 2995530d e069557e ef1e03b4 e68dc9f3
763ccff2 5adb5d73 5821b9c6 0f4a02a2 7d8b68ac 2ac12d0a
6acb3764 db279e5a f872b90b 7aeed32f 74719338 50ddf85d
5ef51f42 2980324e 69386254 bb3c2b28 50a58d84 f50cffc7 612e8be1'''.split()

def main():
    records = read(ROOT/'registry/assets.json')['assets']
    master = read(ROOT/'config/batch_001_processing_jobs.json')
    jobs = []
    for prefix in PREFIXES:
        record = next(a for a in records if a['source']['asset_base_id'].startswith(prefix))
        base = record['source']['asset_base_id']
        existing = next((j for j in master['jobs'] if j['base_id'] == base), None)
        if existing:
            jobs.append(existing)
            continue
        assert record['source'].get('original_file') and record['status'] != 'REJECTED'
        assert record.get('local_qualification', {}).get('outcome') != 'PASS'
        probe = read(ROOT/'reports'/(base+'_batch001_probe.json'))
        assert not probe['libraries']
        assert not any(o['type'] == 'CURVE' for o in probe['objects']), 'Do not silently omit cables'
        meshes = [o['name'] for o in probe['objects']
                  if o['type'] == 'MESH' and not o['hidden'] and not o['hide_render']]
        assert meshes
        job = dict(base_id=base, source=record['source']['original_file'], meshes=meshes,
                   prepare_dir=f'artifacts/{base}/prepare_rigid005_a000',
                   conversion_dir=f'artifacts/{base}/convert_rigid005_a000',
                   dimension_bounds_m=dict(min=[.003,.003,.001], max=[.6,.6,.6]),
                   allow_base_color_bake=True, allow_multi_material_bake=True,
                   max_texture_dimension=2048, source_root_rotation_deg=[0,0,0],
                   state_id='source_fixed_form', supports=['bench'],
                   replace_request_ids=['quality/s0_towel/1'], tag='rigid005_'+prefix)
        master['jobs'].append(job)
        jobs.append(job)
        write(ROOT/'config'/('job_'+base+'.json'), job)
    write(ROOT/'config/batch_001_processing_jobs.json', master)
    write(ROOT/'config/rigid005_jobs.json', dict(jobs=jobs,
        scope='Rigid-first fixed-form technical candidates; no dynamics or visual acceptance inferred',
        local_pool_target=150, soft_physics_deferred=True))
    print('RIGID_CANDIDATES_QUEUED', len(jobs))

if __name__ == '__main__':
    main()
