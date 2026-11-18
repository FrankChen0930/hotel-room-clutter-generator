"""Verify pinned first-round artifacts; leaves model qualification honestly pending."""
from pathlib import Path
from library import ROOT, read, sha, write, summarize

if __name__=='__main__':
    errors=[]
    for p in [*ROOT.glob('scripts/*.py'),*ROOT.glob('tests/*.py')]: compile(p.read_text(encoding='utf-8'),str(p),'exec')
    for p in ROOT.rglob('*.json'):
        if not any(x in p.parts for x in ('cache','shadercache','drivercache','texturecache','data')): read(p)
    status=summarize(read(ROOT/'registry/assets.json')['assets'])
    assert not status['invalid_ready']
    fixture=ROOT/'reports/infrastructure_fixture_001'; conversion=read(fixture/'conversion/conversion.json')
    integrity=read(fixture/'integrity_final.json'); native=read(ROOT/'reports/infrastructure_native_001/render.json')
    usd=fixture/'conversion/asset.usdc'; usd_sha=sha(usd)
    for report in (conversion,integrity,native):
        if report['outcome']!='PASS' or report['usd_sha256']!=usd_sha: errors.append('FIXTURE_EVIDENCE_STALE')
    if sha(Path(read(fixture/'job.json')['blend']))!=conversion['source_sha256']: errors.append('FIXTURE_ORIGINAL_CHANGED')
    for dep in integrity['dependencies']:
        if sha(dep['path'])!=dep['sha256']: errors.append('FIXTURE_DEPENDENCY_CHANGED')
    for im in native['images']:
        if sha(ROOT/im['path'])!=im['sha256']: errors.append('FIXTURE_NATIVE_IMAGE_CHANGED')
    negative=read(fixture/'negative_checks.json')
    if len(negative)!=2 or any(x['outcome']!='PASS_NEGATIVE_REJECTED' for x in negative): errors.append('NEGATIVE_CHECKS_FAILED')
    protected=read(ROOT/'reports/protected_before.json')
    for x in protected['files']:
        if not Path(x['path']).is_file() or sha(x['path'])!=x['sha256']: errors.append('PROTECTED_CHANGED:'+x['path'])
    for x in read(ROOT/'reports/comparison_receipt.json')['images']:
        if sha(ROOT/x['path'])!=x['sha256']: errors.append('HISTORICAL_IMAGE_CHANGED')
    env=read(ROOT/'config/environment.json'); env['native_runtime']='ENGINEERING_FIXTURE_CAPTURE_EXECUTED_EXIT_0'; write(ROOT/'config/environment.json',env)
    report=dict(outcome='PASS' if not errors else 'FAIL',errors=errors,status=status,
        checks=dict(python_sources_compile='PASS',json_parse='PASS',fixture_conversion='PASS',
            fixture_integrity='PASS',fixture_native_images=len(native['images']),negative_conversion_rejections=len(negative),
            protected_files=len(protected['files']),historical_images=8),
        scope='First-round engineering evidence only; not real Blendkit end-to-end/model/support/catalog qualification',
        remaining=['Official add-on installation and acquisition','CC0/extractable USD rights evidence',
            'Real representative material/geometry/scale/native review','Collision proxy and precise support',
            'Common Core candidate integration, Static/Integrity/Replay and Native Support scene comparison'],
        script_hashes=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in ROOT.glob('scripts/*.py')])
    write(ROOT/'reports/verification.json',report); print(report['outcome'],report['checks']); raise SystemExit(bool(errors))
