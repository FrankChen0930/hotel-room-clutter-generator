"""Offline source registry and fail-closed eligibility. No network or credential handling."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
STAGES = ['DISCOVERED', 'ACQUIRED', 'CONVERTED', 'VISUAL_ACCEPTED', 'GENERATION_READY']

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def local(path):
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT): raise ValueError('PATH_OUTSIDE_LIBRARY')
    return p

def validate(records):
    ids = set()
    for a in records:
        aid = a['source']['asset_base_id']; UUID(aid)
        if aid in ids: raise ValueError('DUPLICATE_SOURCE_ID')
        ids.add(aid)
        u = urlparse(a['source']['url'])
        if u.scheme != 'https' or u.hostname not in {'www.blendkit.com','www.blenderkit.com'}:
            raise ValueError('UNSUPPORTED_SOURCE')
        if aid not in u.path: raise ValueError('SOURCE_URL_ID_MISMATCH')
        if a['status'] not in STAGES + ['BLOCKED','REJECTED']: raise ValueError('INVALID_STATUS')
        if a['last_completed_stage'] not in STAGES: raise ValueError('INVALID_COMPLETED_STAGE')
        if a['status'] in STAGES and a['status'] != a['last_completed_stage']:
            raise ValueError('STAGE_STATUS_MISMATCH')

def artifact_ok(ref):
    try:
        p = local(ref['path'])
        return p.is_file() and sha(p) == ref['sha256']
    except (KeyError, TypeError, ValueError, OSError): return False

def acquired(a):
    s = a['source']
    valid=bool(s.get('version_id') and s.get('acquisition_method') == 'OFFICIAL_ADDON'
                and artifact_ok(s.get('original_file') or {}) and artifact_ok(s.get('receipt') or {}))
    raw=s.get('original_download_files') or []
    valid=valid and bool(raw) and all(artifact_ok(ref) for ref in raw)
    if not valid: return False
    receipt=read(local(s['receipt']['path']))
    return (receipt.get('asset_base_id')==s['asset_base_id'] and receipt.get('version_id')==s['version_id']
            and receipt.get('original_sha256')==s['original_file']['sha256'])

def gate_errors(a, scope='generator'):
    if scope not in {'local','generator'}: raise ValueError('UNKNOWN_QUALIFICATION_SCOPE')
    errors = []
    if not acquired(a): errors.append('SOURCE_OR_ACQUISITION_EVIDENCE_MISSING')
    r = a['rights']
    if scope=='local':
        if not (r.get('internal_use') is True and r.get('local_test_scope')=='CONTROLLED_WORKSPACE_NO_DISTRIBUTION'
                and artifact_ok(r.get('local_test_evidence'))):
            errors.append('LOCAL_TECHNICAL_TEST_NOT_AUTHORIZED')
    elif not (r.get('internal_use') is True and r.get('extractable_usd') is True
            and r.get('decision') == 'CLEARED' and artifact_ok(r.get('decision_evidence', {}))):
        errors.append('EXTRACTABLE_USD_RIGHTS_UNCLEARED')
    if not a.get('geometry_identity'): errors.append('GEOMETRY_IDENTITY_MISSING')
    if not a.get('appearance_family'): errors.append('APPEARANCE_FAMILY_MISSING')
    usd = a.get('usd', {})
    if not artifact_ok(usd): errors.append('USD_MISSING_OR_CHANGED')
    for name in ('conversion','integrity','static','native_render','visual','support','catalog','replay'):
        ref = a.get('evidence', {}).get(name, {})
        if not artifact_ok(ref):
            errors.append(name.upper() + '_EVIDENCE_MISSING'); continue
        report = read(local(ref['path']))
        if report.get('outcome') != 'PASS' or report.get('usd_sha256') != usd.get('sha256'):
            errors.append(name.upper() + '_NOT_PASS_OR_STALE')
        if name == 'visual' and not report.get('reviewer'): errors.append('VISUAL_REVIEWER_MISSING')
        if name == 'native_render' and not all(artifact_ok(x) for x in report.get('images', [])):
            errors.append('NATIVE_IMAGE_CHANGED')
        if name == 'native_render' and not report.get('images'): errors.append('NATIVE_IMAGE_MISSING')
        if name == 'integrity':
            dependencies=report.get('dependencies', [])
            if not dependencies: errors.append('DEPENDENCY_LOCK_MISSING')
            for dep in dependencies:
                if not artifact_ok(dep): errors.append('DEPENDENCY_MISSING_OR_CHANGED')
    if a.get('physics', {}).get('mode') not in {'STATIC_ONLY','DYNAMIC_QUALIFIED'}:
        errors.append('PHYSICS_MODE_MISSING')
    return errors

def summarize(records):
    validate(records)
    ready = []; seen = set(); invalid = {}; local_identities=set(); local_ready=[]
    for a in records:
        if acquired(a) and not a.get('variant_of') and not gate_errors(a,scope='local'):
            if a['geometry_identity'] not in local_identities:local_ready.append(a)
            local_identities.add(a['geometry_identity'])
        if a['status'] != 'GENERATION_READY': continue
        errors = gate_errors(a)
        identity = a.get('geometry_identity')
        if a.get('variant_of'): errors.append('VARIANT_NOT_INDEPENDENT_NOT_COUNTED')
        if identity in seen: errors.append('DUPLICATE_GEOMETRY_NOT_COUNTED')
        if errors: invalid[a['asset_id']] = errors
        else: seen.add(identity); ready.append(a)
    return dict(updated_utc=datetime.now(timezone.utc).isoformat(), target=[120,130],
        candidates=len(records), acquired=sum(acquired(a) for a in records),
        converted=sum(artifact_ok(a.get('usd', {})) and artifact_ok(a.get('evidence',{}).get('conversion',{}))
            and read(local(a['evidence']['conversion']['path'])).get('outcome')=='PASS' for a in records),
        generation_ready=len(ready), public_starter=sum(a['rights'].get('redistribution') is True for a in ready),
        local_technical_ready=len(local_identities),
        status_counts=dict(Counter(a['status'] for a in records)),
        category_candidates=dict(Counter(a['category'] for a in records)),
        category_ready=dict(Counter(a['category'] for a in ready)),
        category_local_technical_ready=dict(Counter(a['category'] for a in local_ready)),
        license_counts=dict(Counter(a['rights']['license'] for a in records)),
        rights_clear_internal_acquired=sum(acquired(a) and a['rights'].get('internal_use') is True for a in records),
        rights_clear_extractable_generator=sum(acquired(a) and a['rights'].get('extractable_usd') is True and artifact_ok(a['rights'].get('decision_evidence')) for a in records),
        verified_cc0_acquired=sum(acquired(a) and a['rights'].get('license')=='CC0' for a in records),
        hotel_suitable_visually_accepted=sum(a.get('hotel_suitability',{}).get('decision')=='accepted' for a in records),
        hotel_suitable_semantic_candidates=sum(a.get('hotel_suitability',{}).get('decision')=='candidate' for a in records),
        robotics_distribution=dict(Counter(a.get('robotics_relevance','UNREVIEWED') for a in records)),
        batch_milestones=[10,25,50,75,125],
        blocked=[dict(asset_id=a['asset_id'], reasons=a.get('blockers', [])) for a in records if a['status']=='BLOCKED'],
        invalid_ready=invalid, scope='New Blendkit library only; no historical assets or fixtures counted')

def main():
    p=argparse.ArgumentParser(); p.add_argument('command', choices=['status','check']); args=p.parse_args()
    records=read(ROOT/'registry/assets.json')['assets']; result=summarize(records)
    write(ROOT/'reports/status.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(bool(result['invalid_ready']))

if __name__=='__main__': raise SystemExit(main())
