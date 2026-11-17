"""One offline Blender process inspects newly acquired real sources; skips completed probes."""
from pathlib import Path
import runpy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha
registry=read(ROOT/'registry/assets.json');done=[]
for a in registry['assets']:
    if not a.get('batch_id','').startswith('batch_') or not a['source'].get('version_id') or a['status']=='REJECTED':continue
    source=ROOT/a['source']['original_file']['path'];output=ROOT/'reports'/(a['source']['asset_base_id']+'_batch001_probe.json')
    if output.exists():continue
    try:
        sys.argv=['probe_cached_blend.py','--',str(source),str(output)]
        runpy.run_path(str(ROOT/'scripts/probe_cached_blend.py'),run_name='__main__')
        done.append(a['asset_id'])
    except Exception as e:
        write(output.with_suffix('.error.json'),dict(outcome='BLOCKED',source_sha256=sha(source),reason=str(e)))
print('REAL_BATCH_SOURCE_PROBES',len(done),done)
