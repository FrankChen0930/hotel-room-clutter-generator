"""Run by the independent researcher; author preparation is not acceptance."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import subprocess
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--operator',required=True)
    parser.add_argument('--independent-operator',action='store_true',required=True)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--reference-index',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();operator=args.operator.strip()
    if not operator:parser.error('A real independent operator must identify themselves')
    reference=load_json(args.reference_index);out=guard_new_output(args.output);out.mkdir(parents=True)
    config=args.config.resolve(strict=True);commands=[];results=[];started=datetime.now(timezone.utc).isoformat()
    def run(name,argv):
        command=[sys.executable,'-B',str(CODE/'run_core.py'),argv[0],'--config',str(config),*argv[1:]]
        process=subprocess.run(command,cwd=out,capture_output=True,text=True)
        log=out/(name+'.txt');log.write_text(process.stdout+process.stderr,encoding='utf-8')
        commands.append(dict(command=command,exit_code=process.returncode,log=log.name,sha256=sha256_file(log)))
        return process.returncode
    for room,scenario,level,seed in [('hotel705','STAYOVER','low',706),('yazhi','CHECKOUT','medium',707)]:
        key=f'{room}_{scenario}_{level}_{seed}';expected=next(c for c in reference['cases'] if c['case_key']==key)
        output=out/(room+' generated');code=run(room+'-generate',['generate','--room',room,'--scenario',scenario,'--level',level,'--seed',str(seed),'--output',str(output)])
        if code:
            results.append(dict(case_key=key,outcome='FAIL',reason='GENERATION_FAILED'));continue
        manifest_path=output/'attempts/a000/manifest.json';manifest=load_json(manifest_path)
        replay=run(room+'-replay',['replay','--manifest',str(manifest_path),'--output',str(out/(room+' replay'))])
        validation=run(room+'-validate',['validate','--manifest',str(manifest_path),'--output',str(out/(room+' validation'))])
        same=manifest['scene']['state_digest']==expected['state_digest']
        results.append(dict(case_key=key,outcome='PASS' if replay==validation==0 and same else 'FAIL',
            manifest=str(manifest_path),manifest_sha256=sha256_file(manifest_path),state_digest=manifest['scene']['state_digest'],reference_state_digest=expected['state_digest'],same_state_digest=same,environment=manifest['environment']))
    passed=len(results)==2 and all(r['outcome']=='PASS' for r in results)
    write_json_new(out/'researcher-receipt.json',dict(execution='EXECUTED',outcome='PASS' if passed else 'FAIL',operator=dict(name=operator,kind='HUMAN_DECLARED',independent_declaration=args.independent_operator),
        started_utc=started,ended_utc=datetime.now(timezone.utc).isoformat(),config_sha256=sha256_file(config),reference_index_sha256=sha256_file(args.reference_index),commands=commands,cases=results,
        scope='Independent operator declaration and actual commands; operator authenticity/acceptance must be confirmed by the recipient, never author-signed'))
    raise SystemExit(0 if passed else 5)
