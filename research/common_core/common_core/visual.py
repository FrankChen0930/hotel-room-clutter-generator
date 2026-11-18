"""Verify explicit image reviews against native capture and exact sealed state."""
from pathlib import Path
import struct
from .contracts import load_json
from .identity import sha256_file
from .paths import RUN_ROOT


def verify_review(path,manifest_path):
    path=Path(path).resolve(strict=True);manifest_path=Path(manifest_path).resolve(strict=True)
    review=load_json(path);manifest=load_json(manifest_path)
    def require(condition,reason):
        if not condition:raise ValueError('VISUAL_'+reason)
    require(path.is_relative_to(RUN_ROOT.resolve()),'REVIEW_PATH')
    require(review.get('execution')=='EXECUTED' and review.get('outcome')=='PASS','REVIEW_STATUS')
    require(review['manifest_sha256']==sha256_file(manifest_path) and review['target_state_digest']==manifest['scene']['state_digest'] and
            review['scene_sha256']==manifest['scene']['sha256'],'STATE_IDENTITY')
    require(sha256_file(manifest_path.parent/'scene.usda')==review['scene_sha256'],'SCENE_HASH')
    require(review['reviewer']['kind'] in ['AGENT','HUMAN'] and review['reviewer']['name'] and review['reviewer']['reviewed_utc'],'REVIEWER')
    require(len(review['images'])>=2 and len({i['view'] for i in review['images']})>=2,'VIEW_COUNT')
    capture_cache={}
    for image in review['images']:
        capture=Path(image['capture']).resolve(strict=True)
        require(capture.is_relative_to(RUN_ROOT.resolve()),'CAPTURE_PATH')
        if capture not in capture_cache:
            require(sha256_file(capture)==image['capture_sha256'],'CAPTURE_HASH')
            report=load_json(capture)
            require(report['execution']=='EXECUTED' and report['manifest_sha256']==review['manifest_sha256'] and
                report['target_state_digest']==review['target_state_digest'] and report['scene_sha256']==review['scene_sha256'],'CAPTURE_IDENTITY')
            capture_cache[capture]=report
        else:require(sha256_file(capture)==image['capture_sha256'],'CAPTURE_HASH')
        report=capture_cache[capture];target=(capture.parent/image['path']).resolve(strict=True)
        require(target.is_relative_to(capture.parent),'IMAGE_PATH')
        require(any(i['path']==image['path'] and i['view']==image['view'] and i['sha256']==image['sha256'] for i in report['images']),'CAPTURE_IMAGE')
        require(sha256_file(target)==image['sha256'],'IMAGE_HASH')
        with target.open('rb') as stream:header=stream.read(24)
        require(len(header)==24 and header[:8]==b'\x89PNG\r\n\x1a\n' and header[12:16]==b'IHDR' and
                min(struct.unpack('>II',header[16:24]))>=256,'IMAGE_ENCODING')
        require(image['outcome']=='PASS' and all(image['checks'].get(k) is True for k in
                ['scale','floating','interpenetration','naturalness','visibility']),'IMAGE_REVIEW')
    return dict(path=str(path),sha256=sha256_file(path),reviewer=review['reviewer'],images=review['images'])
