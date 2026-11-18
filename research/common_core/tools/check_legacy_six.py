"""Reconstruct the six explicitly adopted legacy fixtures into new output only."""
from pathlib import Path
import argparse
import json
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.contracts import load_json
from common_core.room import load_inputs
from common_core.legacy import import_hotel_v2

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    inputs=load_inputs(CODE/'config/deployment.local.json','hotel705')
    batch=load_json(CODE.parent/'_hotel705_pilot/roomscale/active_batch.json');reports=[]
    for index,path in enumerate(batch['runs']):
        result=import_hotel_v2(Path(path)/'manifest.json',args.output/str(index),inputs)
        reports.append(result);print(json.dumps(dict(index=index,**result)),flush=True)
    if len(reports)!=6 or any(r['outcome']!='PASS' for r in reports):raise SystemExit(5)
