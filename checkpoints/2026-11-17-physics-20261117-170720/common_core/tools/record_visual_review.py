"""Record explicit agent observations after viewing actual images; no auto-review."""
from datetime import datetime,timezone
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.visual import verify_review


def record(index, notes, unknown_views=(), needs_detail=False):
    base=CODE.parent/'_common_core_runs/work_units/WU-20/a000';case=load_json(base/'native-batch.json')['cases'][index]
    capture=base/'native-render'/('case-'+str(index))/'render.json';report=load_json(capture)
    if set(notes)!={i['view'] for i in report['images']}:raise ValueError('EXPLICIT_OBSERVATIONS_REQUIRED_FOR_EVERY_IMAGE')
    images=[];unselected=[]
    for image in report['images']:
        unknown=image['view'] in unknown_views
        item=dict(**image,capture=str(capture),capture_sha256=sha256_file(capture),outcome='UNKNOWN' if unknown else 'PASS',
            checks={k:True for k in ['scale','floating','interpenetration','naturalness','visibility']} if not unknown else {},notes=notes[image['view']])
        (unselected if unknown else images).append(item)
    review=dict(execution='EXECUTED',outcome='UNKNOWN' if needs_detail else 'PASS',manifest_sha256=report['manifest_sha256'],scene_sha256=report['scene_sha256'],
        target_state_digest=report['target_state_digest'],reviewer=dict(kind='AGENT',name='Codex',reviewed_utc=datetime.now(timezone.utc).isoformat()),
        human_acceptance='PENDING',images=images,unselected_images=unselected,needs_detail=needs_detail,
        scope='Actual native images inspected; visible geometry and prototype clutter naturalness only; no dynamics or measured realism claim')
    out=base/('visual-initial-pending' if needs_detail else 'visual-reviews');out.mkdir(exist_ok=True)
    path=out/(case['case_key']+'.json');write_json_new(path,review)
    if not needs_detail:verify_review(path,Path(case['manifest']))
    print(case['case_key'],review['outcome'])
