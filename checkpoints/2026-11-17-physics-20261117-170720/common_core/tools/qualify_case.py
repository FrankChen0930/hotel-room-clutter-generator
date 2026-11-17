"""Create or verify a separate immutable exact-case qualification record."""
import argparse
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.contracts import load_json
from common_core.room import load_inputs
from common_core.qualification import qualify,verify
from common_core.paths import guard_new_output
from common_core.manifest import write_json_new

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('--room',required=True)
    parser.add_argument('--case-dir',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--verify',type=Path)
    parser.add_argument('--visual-review',type=Path)
    args=parser.parse_args();inputs=load_inputs(args.config,args.room)
    if args.verify:
        verify(load_json(args.verify),inputs);print('EXACT_QUALIFICATION_VERIFIED')
    else:
        if args.case_dir is None or args.output is None:parser.error('--case-dir and --output required')
        record=qualify(args.case_dir,inputs,args.visual_review);out=guard_new_output(args.output);out.mkdir(parents=True)
        write_json_new(out/'qualification.json',record);print(record['fingerprint'])
