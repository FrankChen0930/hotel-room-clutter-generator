"""Thin preflight/generate entry. Business rules live in planner/placer/validators."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from .contracts import load_json
from .identity import sha256_file
from .manifest import build_manifest,seal_manifest,write_json_new
from .paths import guard_new_output
from .room import load_inputs,prepare_room


def main(argv=None):
    parser=argparse.ArgumentParser(prog='common_core');sub=parser.add_subparsers(dest='command',required=True)
    for name in ['preflight','generate']:
        p=sub.add_parser(name);p.add_argument('--config',type=Path,required=True);p.add_argument('--room',required=True)
        if name=='generate':
            p.add_argument('--scenario',required=True);p.add_argument('--level',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('replay');p.add_argument('--config',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('validate');p.add_argument('--config',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--tiers',default='integrity,static,replay')
    p=sub.add_parser('batch');p.add_argument('--config',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv);run=None
    try:
        if sys.flags.optimize:raise ValueError('OPTIMIZED_PYTHON_UNSUPPORTED')
        if args.command in ('generate','replay','validate','batch'):run=guard_new_output(args.output)
        config=load_json(args.config);sdk=Path(config['isaac_root'])
        if run is not None:
            from .paths import reject_source_output
            anchor=args.config.resolve().parent
            reject_source_output(run,{k:anchor/v for k,v in config['bindings'].items()})
        from .sdk import load_usd
        load_usd(sdk)
        if args.command=='batch':
            from .batch import execute_batch
            return execute_batch(load_json(args.spec),args.config.resolve(),args.output,main)
        if args.command in ('replay','validate'):
            from .identity import content_digest
            candidate=load_json(args.manifest);anchor=args.config.resolve().parent
            rooms=[key for key,value in config['rooms'].items() if content_digest(load_json(anchor/value))==candidate['inputs']['profile_hash']]
            if len(rooms)!=1:raise ValueError('REPLAY_ROOM_IDENTITY')
            inputs=load_inputs(args.config,rooms[0])
            if args.command=='validate':
                from .assessment import assess_manifest,expand_tiers
                return assess_manifest(args.manifest,inputs,args.output,expand_tiers(args.tiers),args.config,rooms[0])
            from .replay import load_manifest,replay_manifest
            manifest=load_manifest(args.manifest,inputs);original=args.manifest.parent/'scene.usda'
            report=replay_manifest(manifest,args.output,inputs,original if original.exists() else None,sha256_file(args.manifest))
            print(json.dumps(report));return 0 if report['outcome']=='PASS' else 5
        inputs=load_inputs(args.config,args.room)
        if args.command=='preflight':
            print(json.dumps(dict(outcome='PASS',room=args.room,scope='contracts, SDK USD bootstrap, source and asset SHA closure; no scene created')));return 0
        from .planner import plan_requests
        from .placer import place_requests
        from .writer import write_scene
        from .validation import validate_static,validate_integrity
        plan=plan_requests(inputs,args.seed,args.scenario,args.level);room=prepare_room(inputs.profile,inputs.bindings)
        run.mkdir(parents=True,exist_ok=False);write_json_new(run/'request.json',plan)
        attempt=run/'attempts/a000';attempt.mkdir(parents=True)
        result=place_requests(plan,room,inputs.catalog);write_json_new(attempt/'sampling.json',result['sampling'])
        if result['status']!='PASS':
            write_json_new(attempt/'failure.json',result['failure']);write_json_new(run/'run_index.json',dict(status='FAILED',attempt='a000',failure=result['failure']));return 4
        scene=attempt/'scene.usda';write_scene(scene,inputs,result)
        manifest=build_manifest(inputs,plan,result,scene,run.name)
        assessment=validate_static(scene,manifest,room,inputs);validation=attempt/'validation';validation.mkdir()
        manifest['achieved']=assessment['metrics']
        integrity=validate_integrity(inputs,manifest)
        from .replay import replay_manifest
        replay=replay_manifest(manifest,attempt/'replay',inputs,scene)
        for kind,report in [('static',assessment),('integrity',integrity),('replay',replay)]:
            write_json_new(validation/(kind+'.json'),report)
            manifest['evidence_refs'].append(dict(kind=kind,uri='validation/'+kind+'.json',sha256=sha256_file(validation/(kind+'.json')),
                execution=report['execution'],outcome=report['outcome'],scope=report['scope'],
                target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(generator='1.0',code_hash=manifest['inputs']['code_hash'])))
        seal_manifest(manifest,attempt/'manifest.json')
        status='STATIC_PASS' if all(r['outcome']=='PASS' for r in (assessment,integrity,replay)) else 'FAILED'
        write_json_new(run/'run_index.json',dict(status=status,attempt='a000',manifest='attempts/a000/manifest.json',manifest_sha256=sha256_file(attempt/'manifest.json'),scope='static only'))
        print(json.dumps(dict(output=str(run),status=status,objects=len(result['objects']),errors=assessment['errors'])))
        return 0 if status=='STATIC_PASS' else 5
    except (ValueError,KeyError,OSError,RuntimeError) as exc:
        error=dict(status='INCOMPLETE',phase=args.command,reason=str(exc),exception=type(exc).__name__)
        if run is not None and run.is_dir() and not (run/'failure.json').exists():write_json_new(run/'failure.json',error)
        print(json.dumps(error),file=sys.stderr)
        if isinstance(exc,FileNotFoundError):return 3
        if isinstance(exc,PermissionError):return 7
        if 'OUTPUT_' in str(exc):return 7
        if any(tag in str(exc) for tag in ['HASH','IDENTITY','MISSING','DEPENDENCY']):return 3
        return 2
