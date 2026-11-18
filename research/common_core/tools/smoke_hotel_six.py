"""Run the initial Hotel six-case slice with fresh CLI outputs and receipts."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--room',default='hotel705');args=parser.parse_args()
    out=guard_new_output(args.output);out.mkdir(parents=True);results=[]
    for scenario in ['STAYOVER','CHECKOUT']:
        for level in ['low','medium','high']:
            key=scenario.lower()+'_'+level
            command=[sys.executable,'-B',str(CODE/'run_core.py'),'generate','--config',str(CODE/'config/deployment.local.json'),
                     '--room',args.room,'--scenario',scenario,'--level',level,'--seed','706','--output',str(out/key)]
            process=subprocess.run(command,cwd=CODE.parent,capture_output=True,text=True)
            (out/(key+'.log')).write_text(process.stdout+process.stderr,encoding='utf-8')
            results.append(dict(key=key,command=command,exit_code=process.returncode))
            print(json.dumps(results[-1]),flush=True)
    write_json_new(out/'six_case_results.json',results)
    raise SystemExit(0 if all(r['exit_code']==0 for r in results) else 5)
