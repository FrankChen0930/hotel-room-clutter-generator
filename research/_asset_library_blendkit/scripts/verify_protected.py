from pathlib import Path
from library import ROOT, read, sha, write
if __name__=='__main__':
    snapshot=read(ROOT/'reports/protected_before.json'); changed=[]
    for x in snapshot['files']:
        p=Path(x['path'])
        if not p.is_file() or sha(p)!=x['sha256']: changed.append(x['path'])
    report=dict(outcome='PASS' if not changed else 'FAIL',checked=len(snapshot['files']),changed=changed,scope=snapshot['scope'])
    write(ROOT/'reports/protected_verification.json',report); print(report); raise SystemExit(bool(changed))
