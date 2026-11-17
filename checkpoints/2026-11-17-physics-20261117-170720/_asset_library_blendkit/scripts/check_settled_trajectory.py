"""Independent, strict final-window and requested-support checks on actual samples."""
import math
from library import read,write,sha

def check(attempt,surfaces):
    from generate_surface_scenes import object_prim,footprint_supported
    m=read(attempt/'manifest.json');report=read(attempt/'dynamics/result.json');data=read(attempt/'dynamics/trajectory.json')['trajectories'];issues=[];rows=[]
    norm=lambda x:math.sqrt(sum(v*v for v in x))
    for obj in m['objects']:
        path=object_prim(obj);samples=data.get(path,[]);flags=[]
        if not samples:issues.append(dict(prim=path,issues=['MISSING_BODY']));continue
        end=samples[-1]['time_s'];window=[s for s in samples if s['time_s']>=end-2];last=samples[-1]['pose_xyzw']
        lin=max(norm(s['velocity'][:3]) for s in window);ang=max(norm(s['velocity'][3:]) for s in window)
        disp=max(math.dist(s['pose_xyzw'][:3],samples[0]['pose_xyzw'][:3]) for s in samples)
        region=surfaces.specs[obj['effective']['support_id']]['region'];point=[[last[0]-.00001,last[1]-.00001],[last[0]+.00001,last[1]-.00001],[last[0],last[1]+.00001]]
        if lin>.03 or ang>.2:flags.append('NOT_SETTLED_FINAL_2S')
        if disp>.12:flags.append('DISPLACEMENT_OVER_12CM')
        if not footprint_supported(dict(status='SUPPORTED',shape='polygon',polygon=region),point,0):flags.append('LEFT_SUPPORT_REGION')
        if flags:issues.append(dict(prim=path,issues=flags))
        rows.append(dict(prim=path,window_max_linear_speed_mps=lin,window_max_angular_speed_radps=ang,max_displacement_m=disp))
    for path,samples in data.items():
        if path.startswith('/CommonCore/'):continue
        window=[s for s in samples if s['time_s']>=samples[-1]['time_s']-2]
        if any(norm(s['velocity'][:3])>.03 or norm(s['velocity'][3:])>.2 for s in window):issues.append(dict(prim=path,issues=['SOURCE_BODY_NOT_SETTLED_FINAL_2S']))
    outcome='PASS' if report['outcome']=='DIAGNOSTIC_PASS' and not issues and report['registered_dynamic_bodies']==49+len(m['objects']) and report['authored_joints']==31 else 'FAIL'
    return dict(outcome=outcome,issues=issues,body_checks=rows,trajectory_sha256=sha(attempt/'dynamics/trajectory.json'),native_result_sha256=sha(attempt/'dynamics/result.json'),scope='Full-room rigid surrogate stability, final2s, displacement and support-region retention; no soft deformation or robot interaction qualification')
