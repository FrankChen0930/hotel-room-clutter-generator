"""Render controlled-local candidate with the same pinned V0.2 camera definitions."""
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
worker=core/'tools/launch_render.py'
sys.argv=[str(worker),'--batch',str(run/'render_batch.json'),'--output',str(run/'native_render'),'--timeout','300']
runpy.run_path(str(worker),run_name='__main__')
