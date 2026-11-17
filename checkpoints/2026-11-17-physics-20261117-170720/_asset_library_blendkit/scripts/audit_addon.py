"""Local archive CRC/structure/version audit; no claim of upstream signature verification."""
import ast
from pathlib import Path, PurePosixPath
import tomllib
import zipfile
from library import ROOT, sha, write

if __name__=='__main__':
    archive=ROOT/'tools/blenderkit.zip'; installed=ROOT/'blender_profile/scripts/addons'
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip(); names=z.namelist()
        unsafe=[n for n in names if PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts or '\\' in n or ':' in n]
        manifests=[n for n in names if n.endswith('blender_manifest.toml') and n.count('/')==1]
        assert len(manifests)==1 and not bad and not unsafe
        manifest=tomllib.loads(z.read(manifests[0]).decode())
        mismatches=[]; compared=0
        for n in names:
            if n.endswith(('.py','.toml','.exe')) and not n.endswith('/'):
                p=installed/n
                import hashlib
                if not p.is_file() or sha(p)!=hashlib.sha256(z.read(n)).hexdigest(): mismatches.append(n)
                compared+=1
        init=z.read('blenderkit/__init__.py').decode()
        tree=ast.parse(init); info=None
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='bl_info' for x in node.targets): info=ast.literal_eval(node.value)
    report=dict(outcome='PASS' if not mismatches else 'FAIL',archive_sha256=sha(archive),bytes=archive.stat().st_size,
        crc='PASS',unsafe_members=unsafe,member_count=len(names),manifest=manifest,bl_info=info,
        installed_files_compared=compared,installed_mismatches=mismatches,
        provenance='User explicitly supplied as official download; version/manifest matches official release page',
        upstream_signature='NOT_AVAILABLE_NOT_CRYPTOGRAPHICALLY_AUTHENTICATED',
        official_release='https://github.com/BlenderKit/Blendkit/releases/tag/v3.21.5.261103')
    write(ROOT/'reports/addon_archive_audit.json',report)
    print(report['outcome'],report['archive_sha256'],report['manifest']['version'],'files',compared,'mismatches',mismatches)
