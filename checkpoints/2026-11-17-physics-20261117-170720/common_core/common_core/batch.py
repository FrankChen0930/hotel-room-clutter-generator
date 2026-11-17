"""Explicit immutable case keys, failure isolation, and no seed substitutions."""
from pathlib import Path
from .identity import validate_seed
from .manifest import write_json_new
from .paths import guard_new_output


def validate_spec(spec):
    if spec.get('schema') != 'Batch/1' or not spec.get('cases'):raise ValueError('BATCH_SCHEMA')
    seen=set()
    for case in spec['cases']:
        key=case['case_key']
        if not isinstance(key,str) or not key or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in key):raise ValueError('BATCH_CASE_KEY')
        if key in seen:raise ValueError('BATCH_DUPLICATE_KEY')
        seen.add(key);validate_seed(case['seed'])
        if not all(isinstance(case[k],str) and case[k] for k in ['room','scenario','level']):raise ValueError('BATCH_CASE_PARAMETERS')
    return spec['cases']


def execute_batch(spec, config, output, runner):
    cases=validate_spec(spec);out=guard_new_output(output);out.mkdir(parents=True)
    write_json_new(out/'spec.json',spec);records=[]
    for case in cases:
        run=out/case['case_key']
        argv=['generate','--config',str(config),'--room',case['room'],'--scenario',case['scenario'],
              '--level',case['level'],'--seed',str(case['seed']),'--output',str(run)]
        try:exit_code=runner(argv);error=None
        except (Exception,SystemExit) as exc:exit_code=2;error=type(exc).__name__+': '+str(exc)
        records.append(dict(**case,exit_code=exit_code,outcome='PASS' if exit_code==0 else 'FAIL',
            output=case['case_key'],reason=error,scope='generation static/replay/integrity only'))
        write_json_new(out/('case-'+case['case_key']+'.json'),records[-1])
    index=dict(execution='EXECUTED',outcome='PASS' if all(r['exit_code']==0 for r in records) else 'FAIL',cases=records)
    write_json_new(out/'batch_index.json',index)
    return 0 if index['outcome']=='PASS' else 5
