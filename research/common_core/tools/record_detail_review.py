"""Store observations for supplemental captures; retain unsuccessful viewpoints."""
from datetime import datetime,timezone
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.manifest import write_json_new


def record(spec_name,render_name,index,notes,unknown_views=()):
    base=CODE.parent/'_common_core_runs/work_units/WU-20/a000';case=load_json(base/spec_name)['cases'][index]
    capture=base/render_name/('case-'+str(index))/'render.json';report=load_json(capture)
    if set(notes)!={i['view'] for i in report['images']}:raise ValueError('EVERY_DETAIL_IMAGE_REQUIRES_OBSERVATION')
    images=[]
    for image in report['images']:
        unknown=image['view'] in unknown_views
        images.append(dict(**image,capture=str(capture),capture_sha256=sha256_file(capture),outcome='UNKNOWN' if unknown else 'PASS',notes=notes[image['view']],
            checks={} if unknown else {k:True for k in ['scale','floating','interpenetration','naturalness','visibility']}))
    review=dict(execution='EXECUTED',outcome='UNKNOWN' if unknown_views else 'PASS',original_index=case['original_index'],case_key=case['case_key'],
        manifest_sha256=report['manifest_sha256'],scene_sha256=report['scene_sha256'],target_state_digest=report['target_state_digest'],images=images,
        reviewer=dict(kind='AGENT',name='Codex',reviewed_utc=datetime.now(timezone.utc).isoformat()),human_acceptance='PENDING')
    out=base/'detail-reviews'/render_name;out.mkdir(parents=True,exist_ok=True);write_json_new(out/('case-'+str(index)+'.json'),review)
    print(case['case_key'],review['outcome'])
