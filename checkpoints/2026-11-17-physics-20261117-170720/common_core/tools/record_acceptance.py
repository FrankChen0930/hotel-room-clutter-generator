"""Development receipt writer. Run only after checking a unit's specific gates.

This captures fresh common checks; it does not decide Roadmap acceptance or
replace the later product progress/ledger component.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

CODE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE))
from common_core.identity import sha256_file


def record(unit, attempt, next_unit, reuse_tests=None):
    started=datetime.now(timezone.utc).isoformat()
    run=CODE.parent/'_common_core_runs/work_units'/unit/attempt
    run.mkdir(parents=True,exist_ok=True)
    if (run/'receipt.json').exists():raise ValueError('IMMUTABLE_RECEIPT_EXISTS')
    commands=[[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],
              [sys.executable,'-B','tools/verify_source_lock.py'],
              ['git','-c','safe.directory='+CODE.as_posix(),'diff','--check']]
    results=[]
    for i,command in enumerate(commands):
        log=run/f'acceptance-{i}.txt'
        reuse=None
        if i==0 and reuse_tests is not None:
            proof_path=Path(reuse_tests).resolve(strict=True);proof=json.loads(proof_path.read_text(encoding='utf-8'))
            current={p.relative_to(CODE.parent).as_posix():sha256_file(p) for folder in ['common_core','tests'] for p in sorted((CODE/folder).glob('*.py'))}
            expected={Path(key).as_posix():value for key,value in proof['files'].items()}
            if proof['exit_code']!=0 or current!=expected:raise ValueError('TEST_REUSE_CODE_OR_TESTS_CHANGED')
            source=proof_path.parent/proof['test_log'];raw=source.read_bytes()
            decoded=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8')
            if '\nOK' not in decoded or 'FAILED (' in decoded:raise ValueError('TEST_REUSE_NOT_PASS')
            with log.open('xb') as stream:stream.write(raw)
            exit_code=0;reuse=dict(proof=str(proof_path),proof_sha256=sha256_file(proof_path),original_log_sha256=sha256_file(source),
                rationale='Exact core and test file inventory unchanged since actual successful suite; native/unit gates separately executed for this unit')
        else:
            result=subprocess.run(command,cwd=CODE,capture_output=True,text=True)
            with log.open('x',encoding='utf-8') as stream:stream.write(result.stdout+result.stderr)
            exit_code=result.returncode
        results.append(dict(command=command,exit_code=exit_code,reused_verified_tests=reuse,
                            evidence_ref=log.relative_to(CODE.parent).as_posix(),sha256=sha256_file(log)))
        if exit_code:raise RuntimeError('ACCEPTANCE_COMMAND_FAILED: '+str(command)+'\n'+result.stderr)
    files={p.relative_to(CODE).as_posix():sha256_file(p) for p in CODE.rglob('*')
           if p.is_file() and '.git' not in p.relative_to(CODE).parts and '__pycache__' not in p.parts}
    receipt=dict(event_id=unit+'-'+attempt,unit_id=unit,status='COMPLETE',started_utc=started,
        ended_utc=datetime.now(timezone.utc).isoformat(),input_identity=dict(source_lock_sha256=files['config/source_lock.json'],approval='D-01_2026-11-14'),
        changed_files=files,commands=results,exit_codes=[r['exit_code'] for r in results],
        evidence_refs=[dict(path=p.name,sha256=sha256_file(p)) for p in sorted(run.iterdir()) if p.is_file()],
        failure_reason=None,next_unit=next_unit,
        limits=['Completion also requires the recorded unit-specific Roadmap gates; common tests alone do not establish native/render/scene acceptance.'])
    with (run/'receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps({'receipt':str(run/'receipt.json'),'exit_codes':receipt['exit_codes']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',required=True);parser.add_argument('--attempt',default='a000');parser.add_argument('--next',required=True)
    parser.add_argument('--reuse-tests',type=Path)
    args=parser.parse_args()
    if not args.unit.startswith('WU-') or not args.unit[3:].isdigit() or '/' in args.attempt or '\\' in args.attempt or '..' in args.attempt:
        raise ValueError('INVALID_UNIT_OR_ATTEMPT')
    record(args.unit,args.attempt,args.next,args.reuse_tests)
