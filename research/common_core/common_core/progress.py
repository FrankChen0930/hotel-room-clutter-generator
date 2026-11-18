"""Evidence-backed progress events and reproducible summaries; no hooks."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
from .contracts import load_json
from .identity import content_digest,sha256_file

from .paths import workspace_root
ROOT=workspace_root()


def checked_path(path, root):
    path=Path(path).absolute();root=Path(root).resolve(strict=True)
    if any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('PROGRESS_REDIRECT')
    resolved=path.resolve()
    if not resolved.is_relative_to(root):raise ValueError('PROGRESS_PATH_SCOPE')
    return resolved


def event_from_receipt(receipt_path, status, commit=None, gates=()):
    path=checked_path(receipt_path,ROOT/'_common_core_runs');receipt=load_json(path)
    if status not in ['COMPLETE','FAILED','INCOMPLETE']:raise ValueError('PROGRESS_STATUS')
    if not re.fullmatch(r'WU-\d{2}',receipt['unit_id']):raise ValueError('PROGRESS_UNIT')
    refs=[dict(path=str(path),sha256=sha256_file(path))]
    for command in receipt.get('commands',[]):
        log=checked_path(ROOT/command['evidence_ref'],ROOT/'_common_core_runs')
        if sha256_file(log)!=command['sha256']:raise ValueError('PROGRESS_LOG_HASH')
    for ref in receipt.get('evidence_refs',[]):
        evidence=checked_path(path.parent/ref['path'],ROOT/'_common_core_runs')
        if sha256_file(evidence)!=ref['sha256']:raise ValueError('PROGRESS_EVIDENCE_HASH')
    if status=='COMPLETE':
        commands=receipt.get('commands',[])
        if receipt['status']!='COMPLETE' or not commands or any(c['exit_code']!=0 for c in commands) or receipt.get('failure_reason'):
            raise ValueError('PROGRESS_COMPLETION_UNPROVEN')
        if not commit or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('PROGRESS_VERSION_REQUIRED')
        if not gates:raise ValueError('PROGRESS_UNIT_GATES_REQUIRED')
        for gate in gates:
            gate=checked_path(gate,ROOT/'_common_core_runs');report=load_json(gate)
            if report.get('execution')!='EXECUTED' or report.get('outcome')!='PASS':raise ValueError('PROGRESS_UNIT_GATE_FAILED')
            refs.append(dict(path=str(gate),sha256=sha256_file(gate)))
    return dict(event_id=receipt['event_id']+'-'+status,unit_id=receipt['unit_id'],status=status,
        receipt_sha256=sha256_file(path),code_commit=commit,evidence_refs=refs,
        failure_reason=receipt.get('failure_reason'),next_unit=receipt.get('next_unit'))


def append_event(ledger, event):
    path=checked_path(ledger,ROOT/'_common_core_planning');path.parent.mkdir(parents=True,exist_ok=True)
    existing=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line] if path.exists() else []
    for previous in existing:
        if previous['event_id']==event['event_id']:
            if previous!=event:raise ValueError('PROGRESS_EVENT_CONFLICT')
            return False
    with path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
    return True


def summary(ledger):
    path=checked_path(ledger,ROOT/'_common_core_planning')
    events=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line];latest={}
    for event in events:
        for ref in event['evidence_refs']:
            evidence=checked_path(ref['path'],ROOT/'_common_core_runs')
            if sha256_file(evidence)!=ref['sha256']:raise ValueError('PROGRESS_SUMMARY_STALE_EVIDENCE')
        latest[event['unit_id']]=event
    lines=['# Evidence-backed progress','',f'Generated UTC: {datetime.now(timezone.utc).isoformat()}','',
        '| Unit | Status | Version | Evidence |','|---|---|---|---|']
    for key,event in sorted(latest.items()):
        links=', '.join(f'[{Path(ref["path"]).name}]({Path(ref["path"]).as_posix()})' for ref in event['evidence_refs'])
        lines.append(f'| {key} | {event["status"]} | {event.get("code_commit") or "unversioned"} | {links} |')
    return '\n'.join(lines)+'\n'
