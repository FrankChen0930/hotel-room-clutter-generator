"""Verify current expansion evidence, distinct counts and protected baseline hashes."""
import re
from pathlib import Path
from library import ROOT,read,write,sha,artifact_ok,gate_errors,summarize

def main():
    files=[*ROOT.glob('scripts/*.py'),*ROOT.glob('tests/*.py')]
    for path in files:compile(path.read_text(encoding='utf-8'),str(path),'exec')
    registry=read(ROOT/'registry/assets.json');status=summarize(registry['assets']);assert not status['invalid_ready']
    accepted=[a for a in registry['assets'] if a.get('local_qualification',{}).get('outcome')=='PASS']
    for a in accepted:
        assert not gate_errors(a,scope='local'),a['asset_id']
        assert artifact_ok(a['local_qualification']['scene_manifest'])
        manifest=ROOT/a['local_qualification']['scene_manifest']['path']
        room_review=read(manifest.parents[2]/'scene_visual_review.json')
        assert room_review['outcome']=='PASS' and room_review['manifest_sha256']==sha(manifest)
        assert room_review['images'] and all(artifact_ok(im) for im in room_review['images'])
        assert not a['deformation_solved'] and a['physics']['mode']=='STATIC_ONLY'
        assert a['quality_decision']=='accepted' and not a['appearance_family'].startswith('pending_')
        conversion=read(ROOT/a['evidence']['conversion']['path'])
        for field in ['preparation','original_conversion']:
            assert artifact_ok(conversion[field]),(a['asset_id'],field)
        prep=read(ROOT/conversion['preparation']['path']);raw=read(ROOT/conversion['original_conversion']['path'])
        assert prep['prepared_sha256']==raw['source_sha256']
    scene=read(ROOT/'registry/latest_local_scene.json');run=Path(scene['manifest']).parents[2]
    assert read(run/'local_qualification.json')['outcome']=='PASS'
    assert read(run/'scene_visual_review.json')['outcome']=='PASS'
    for im in read(run/'scene_visual_review.json')['images']:assert artifact_ok(im)
    for x in read(ROOT/'reports/protected_before.json')['files']:assert sha(x['path'])==x['sha256'],x['path']
    for x in read(ROOT/'reports/comparison_receipt.json')['images']:
        image=(ROOT/x['path']).resolve()
        assert image.is_relative_to(ROOT.parent) and sha(image)==x['sha256']
    for x in read(ROOT/'reports/batch001_gallery_receipt.json')['images']:assert artifact_ok(x)
    log=ROOT/'reports/batch002_expansion_tests.log';data=log.read_bytes();tests=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8')
    assert '\nOK' in tests;count=int(re.search(r'Ran (\d+) tests',tests)[1])
    result=dict(outcome='PASS_LOCAL_EXPANSION_CHECKPOINT',status=status,tests=count,compiled_files=len(files),protected_files=302,
        local_accepted_asset_ids=[a['asset_id'] for a in accepted],latest_scene=scene,
        scope='Actual local evidence only; not generator/public/deformable/manipulation rights or physics qualification; overall 125 target incomplete')
    write(ROOT/'reports/expansion_verification.json',result);write(ROOT/'reports/status.json',status)
    print('LOCAL_EXPANSION_VERIFIED',dict(candidates=status['candidates'],acquired=status['acquired'],converted=status['converted'],local_ready=status['local_technical_ready'],tests=count))

if __name__=='__main__':main()
