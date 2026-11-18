"""Assemble reviewed views only; unresolved required details block acceptance."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.visual import verify_review

base=CODE.parent/'_common_core_runs/work_units/WU-20/a000';out=base/'visual-final'
if out.exists():raise ValueError('IMMUTABLE_FINAL_VISUAL_EXISTS')
cases=load_json(base/'native-batch.json')['cases'];prepared=[]
details=[(path,load_json(path)) for path in sorted((base/'detail-reviews').rglob('case-*.json'))]
for index,case in enumerate(cases):
    originals=[base/folder/(case['case_key']+'.json') for folder in ['visual-reviews','visual-initial-pending']]
    path=next(p for p in originals if p.exists());original=load_json(path);review=deepcopy(original)
    review['prior_review_refs']=[dict(path=str(path),sha256=sha256_file(path))]
    selected=[]
    for detail_path,detail in details:
        if detail['original_index']!=index:continue
        if any(detail[k]!=original[k] for k in ['manifest_sha256','scene_sha256','target_state_digest']):raise ValueError('DETAIL_STATE_IDENTITY')
        review['prior_review_refs'].append(dict(path=str(detail_path),sha256=sha256_file(detail_path)))
        selected.extend(i for i in detail['images'] if i['outcome']=='PASS')
        review.setdefault('unselected_images',[]).extend(i for i in detail['images'] if i['outcome']!='PASS')
    for missing in original.get('unselected_images',[]):
        if missing['view']=='overview':continue
        if not any(i['view'].startswith(missing['view']+'_') for i in selected):raise ValueError('UNRESOLVED_DETAIL: '+case['case_key']+'/'+missing['view'])
    review['images'].extend(selected);review.update(outcome='PASS',needs_detail=False)
    review['reviewer']['reviewed_utc']=datetime.now(timezone.utc).isoformat()
    review['scope']='Actual original and supplemental views inspected; selected view union covers target supports. Unusable/cropped/occluded originals retained. Agent review only, Human pending.'
    prepared.append((case,review))
out.mkdir();count=0
for case,review in prepared:
    target=out/(case['case_key']+'.json');write_json_new(target,review);verify_review(target,Path(case['manifest']));count+=len(review['images'])
print('FINAL_VISUAL_CASES',len(prepared),'SELECTED_IMAGES',count)
