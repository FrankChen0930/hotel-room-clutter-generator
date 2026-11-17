"""Verify current real-model evidence without rerunning expensive immutable native captures."""
import re
from pathlib import Path
from library import ROOT,read,write,sha,artifact_ok,summarize,gate_errors

def main():
    files=[*ROOT.glob('scripts/*.py'),*ROOT.glob('tests/*.py')]
    for p in files:compile(p.read_text(encoding='utf-8'),str(p),'exec')
    registry=read(ROOT/'registry/assets.json');status=summarize(registry['assets']);assert not status['invalid_ready']
    qualified=[a for a in registry['assets'] if a.get('local_qualification',{}).get('outcome')=='PASS']
    for a in qualified:
        assert not gate_errors(a,scope='local')
        assert 'EXTRACTABLE_USD_RIGHTS_UNCLEARED' in gate_errors(a)
    case=read(ROOT/'registry/latest_local_scene.json');run=Path(case['manifest']).parents[2];attempt=Path(case['manifest']).parent
    reports=[attempt/'static.json',attempt/'integrity.json',attempt/'replay.json',run/'native_support/case-0.json',
        run/'native_support/result.json',run/'native_support/process.json',run/'native_render/process.json',
        run/'local_qualification.json',run/'scene_visual_review.json']
    for p in reports:assert read(p)['outcome']=='PASS',str(p)
    native=read(run/'native_render/case-0/render.json')
    assert native['manifest_sha256']==sha(case['manifest']) and native['scene_sha256']==sha(case['scene'])
    for im in native['images']:assert sha(run/'native_render/case-0'/im['path'])==im['sha256']
    for im in read(ROOT/'reports/comparison_receipt.json')['images']:assert sha(ROOT/im['path'])==im['sha256']
    protected=read(ROOT/'reports/protected_before.json')
    for p in protected['files']:assert sha(p['path'])==p['sha256'],p['path']
    log=ROOT/'reports/real_model_tests_final.log';raw=log.read_bytes();tests=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8')
    count=int(re.search(r'Ran (\d+) tests',tests)[1]);assert '\nOK' in tests
    write(ROOT/'reports/status.json',status)
    result=dict(outcome='PASS_CONTROLLED_LOCAL_REAL_MODEL_DELIVERY',status=status,tests_passed=count,
        source_files_compiled=len(files),protected_files_checked=len(protected['files']),
        scene_quality=read(run/'scene_quality_summary.json'),
        evidence=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in reports+[log]],
        remaining=['Second acquired source geometry/material screening and conversion','Diverse official CC0 candidate acquisition',
            'Extractable generator/public rights clarification','Broader material/batch/dynamic qualification'],
        scope='One actual Blendkit model locally qualified, second acquired and next semantic batch started; library target remains incomplete')
    write(ROOT/'reports/current_delivery_verification.json',result)
    print(result['outcome'],dict(tests=count,protected=result['protected_files_checked'],acquired=status['acquired'],converted=status['converted'],local_ready=status['local_technical_ready'],generation_ready=status['generation_ready']))

if __name__=='__main__':main()
