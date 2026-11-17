import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from common_core.identity import sha256_file
from common_core.visual import verify_review


class VisualIdentityTests(unittest.TestCase):
    def test_capture_state_review_and_image_bytes_must_match(self):
        # Encoded unit fixture only. This does not establish real visual acceptance.
        root=Path(__file__).resolve().parents[2]/'_common_core_runs'
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            base=Path(temporary);scene=base/'scene.usda';scene.write_text('fixture')
            manifest=base/'manifest.json';manifest.write_text(json.dumps(dict(scene=dict(state_digest='a'*64,sha256=sha256_file(scene)))))
            def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
            data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\x80'*768)*256))+chunk(b'IEND',b'')
            images=[]
            for view in ['front','top']:
                path=base/(view+'.png');path.write_bytes(data);images.append(dict(path=path.name,view=view,sha256=sha256_file(path)))
            identity=dict(manifest_sha256=sha256_file(manifest),scene_sha256=sha256_file(scene),target_state_digest='a'*64)
            capture=base/'render.json';capture.write_text(json.dumps(dict(**identity,execution='EXECUTED',images=images)))
            review=dict(**identity,execution='EXECUTED',outcome='PASS',reviewer=dict(kind='AGENT',name='UNIT_FIXTURE',reviewed_utc='fixture'),
                images=[dict(**i,capture=str(capture),capture_sha256=sha256_file(capture),outcome='PASS',checks={k:True for k in ['scale','floating','interpenetration','naturalness','visibility']}) for i in images])
            path=base/'review.json';path.write_text(json.dumps(review));self.assertIn('sha256',verify_review(path,manifest))
            review['execution']='RECORDED';path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError,'REVIEW_STATUS'):verify_review(path,manifest)
            review['execution']='EXECUTED';review['target_state_digest']='b'*64;path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError,'STATE_IDENTITY'):verify_review(path,manifest)
            review['target_state_digest']='a'*64;path.write_text(json.dumps(review));(base/'front.png').write_bytes(data+b'changed')
            with self.assertRaisesRegex(ValueError,'IMAGE_HASH'):verify_review(path,manifest)
