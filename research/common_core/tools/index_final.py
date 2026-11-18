"""Verify all WU-20 evidence before recording an engineering-scenes index."""
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path(sys.executable).resolve().parents[2])
from common_core.contracts import load_json
from common_core.delivery import final_index
from common_core.manifest import write_json_new
base=CODE.parent/'_common_core_runs/work_units/WU-20/a000'
index=final_index(load_json(CODE/'config/batch_v1.json'),base/'formal36',base/'native-support',base/'visual-final',CODE/'config/deployment.local.json')
write_json_new(base/'delivery_index.json',index)
write_json_new(base/'unit-gates.json',dict(execution='EXECUTED',outcome='PASS',formal_cases=len(index['cases']),
    passed_scene_layers=['static','integrity','replay','support','visual'],seven_layers_separate=True,
    level_means=index['level_means'],limited_dynamic_scope='WU-21 pending, named targets only',
    independent_researcher_scope='WU-22 pending; author relocation is not independent acceptance',
    dedicated_s0_eight='WU-12/a002/receipt.json and unit-gates.json',delivery_index='delivery_index.json'))
print('FORMAL36_ENGINEERING_SCENES_PASS')
