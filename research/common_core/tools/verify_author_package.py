"""Author package smoke only; never independent researcher acceptance."""
import argparse
from pathlib import Path
import subprocess
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--code',type=Path,required=True);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--reference-index',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    reference=load_json(args.reference_index);out=guard_new_output(args.output);out.mkdir(parents=True);commands=[];results=[]
    for room,scenario,level,seed in [('hotel705','STAYOVER','low',706),('yazhi','CHECKOUT','medium',707)]:
        case_key=f'{room}_{scenario}_{level}_{seed}';expected=next(c for c in reference['cases'] if c['case_key']==case_key)
        run=out/(room+' generated');manifest=run/'attempts/a000/manifest.json'
        work=[['generate','--room',room,'--scenario',scenario,'--level',level,'--seed',str(seed),'--output',str(run)],
              ['replay','--manifest',str(manifest),'--output',str(out/(room+' replay'))],
              ['validate','--manifest',str(manifest),'--output',str(out/(room+' validation'))]]
        for index,argv in enumerate(work):
            command=[sys.executable,'-B',str(args.code.resolve()/'run_core.py'),argv[0],'--config',str(args.config.resolve()),*argv[1:]]
            process=subprocess.run(command,cwd=out,capture_output=True,text=True);log=out/(room+'-'+str(index)+'.txt');log.write_text(process.stdout+process.stderr,encoding='utf-8')
            commands.append(dict(command=command,exit_code=process.returncode,log=log.name,sha256=sha256_file(log)))
            if process.returncode:raise RuntimeError('AUTHOR_PACKAGE_COMMAND_FAILED: '+str(command)+' '+process.stderr)
        actual=load_json(manifest);same=actual['scene']['state_digest']==expected['state_digest']
        if not same:raise ValueError('AUTHOR_PACKAGE_FINAL_STATE_MISMATCH')
        results.append(dict(case_key=case_key,state_digest=actual['scene']['state_digest'],reference_state_digest=expected['state_digest'],same=same,manifest_sha256=sha256_file(manifest)))
    write_json_new(out/'author-repro.json',dict(execution='EXECUTED',outcome='PASS',operator=dict(kind='AUTHOR_AGENT',name='Codex'),independent_acceptance=False,
        scope='Final code-only package, actual remounted source copies, path with spaces and different CWD; independent researcher remains required',commands=commands,cases=results))
    print('AUTHOR_FINAL_PACKAGE_REPRO_PASS; INDEPENDENT_HANDOFF_PENDING')
