"""Reuse read-only proven native support dispatcher with this workline's output boundary."""
from pathlib import Path
import runpy
import sys
from library import ROOT
import usd_sdk
usd_sdk.load()
core=ROOT.parent/'common_core';sys.path.insert(0,str(core));sys.path.insert(0,str(core/'tools'))
import common_core.paths
common_core.paths.RUN_ROOT=ROOT/'runs'
run=ROOT/'runs/real_backpack_hotel705_stayover_high_706_a002'
worker=ROOT.parent/'_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z/scripts/launch_support_experiment.py'
sys.argv=[str(worker),'--batch',str(run/'support_batch.json'),'--output',str(run/'native_support'),'--timeout','240']
runpy.run_path(str(worker),run_name='__main__')
