"""Append-only assessments against a sealed authoritative manifest."""
from pathlib import Path
import subprocess
import sys
from .contracts import load_json
from .identity import sha256_file
from .manifest import write_json_new
from .paths import guard_new_output
from .replay import load_manifest,replay_manifest
from .room import prepare_room
from .validation import validate_static,validate_integrity

TIERS=('integrity','static','replay','support','visual','physics')


def expand_tiers(value):
    values=value.split(',')
    if values==['all']:return list(TIERS)
    if not values or len(values)!=len(set(values)) or any(v not in TIERS for v in values):raise ValueError('VALIDATION_TIERS')
    return values


def assess_manifest(path, inputs, output, tiers, config, room_id):
    path=Path(path).resolve(strict=True);manifest=load_manifest(path,inputs)
    scene=path.parent/'scene.usda'
    if not scene.is_file():raise ValueError('SCENE_MISSING')
    out=guard_new_output(output);out.mkdir(parents=True);results={};room=None
    code=Path(__file__).resolve().parents[1]
    for tier in tiers:
        if tier=='static':
            room=room or prepare_room(inputs.profile,inputs.bindings);report=validate_static(scene,manifest,room,inputs)
        elif tier=='integrity':report=validate_integrity(inputs,manifest)
        elif tier=='replay':report=replay_manifest(manifest,out/'replay',inputs,scene,sha256_file(path))
        elif tier=='support':
            request=out/'support-batch.json';write_json_new(request,dict(cases=[dict(room=room_id,manifest=str(path))]))
            command=[sys.executable,'-B',str(code/'tools/launch_support.py'),'--config',str(config.resolve()),'--batch',str(request),'--output',str(out/'native-support')]
            with (out/'support-launch.log').open('x',encoding='utf-8') as log:
                process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
            result=out/'native-support/result.json'
            report=load_json(result) if process.returncode==0 and result.exists() else dict(execution='INCOMPLETE',outcome='UNKNOWN',reason='NATIVE_SUPPORT_INCOMPLETE')
        else:
            report=dict(execution='NOT_RUN',outcome='UNKNOWN',reason='EXPLICIT_CAPTURE_AND_REVIEW_REQUIRED' if tier=='visual' else 'EXACT_TARGET_SELECTION_AND_QUALIFICATION_REQUIRED',
                        scope='all expands explicitly; no implicit visual approval or whole-room dynamics')
        write_json_new(out/(tier+'.json'),report)
        results[tier]=dict(execution=report['execution'],outcome=report['outcome'],uri=tier+'.json',sha256=sha256_file(out/(tier+'.json')))
    index=dict(manifest=str(path),manifest_sha256=sha256_file(path),target_state_digest=manifest['scene']['state_digest'],
        execution='EXECUTED',outcome='PASS' if all(r['outcome']=='PASS' for r in results.values()) else 'FAIL',tiers=results)
    write_json_new(out/'assessment.json',index)
    if index['outcome']=='PASS':return 0
    return 6 if any(r['outcome']=='UNKNOWN' for r in results.values()) else 5
