# Hotel Room Clutter Generation — research checkpoint

Checkpoint:2026-11-17. See PROJECT_STATUS.json for precise scope and counts.

This repository snapshot contains Common Core V1 source, Blendkit library/physics pipeline source and tests, source/license metadata, planning records and selected evidence summaries. It is not a self-contained asset distribution or a complete binary workspace backup.

## Current results

- Common Core V1: LOCAL_RC_COMPLETE; protected baseline and36 formal cases retained locally.
- Blendkit:384 candidates,187 acquired,48 converted,42 locally accepted;0 GENERATION_READY and0 publicly cleared Starter assets. These gates are distinct.
- Seed706 Low/Medium/High:15/32/72 instances; Seed707:13/49/73. Counts are instances, not independent source models.
- Six exact full-room CPU PhysX nominal runs:30s,3600 steps,49 original dynamic bodies and31 source joints plus all generated props. Two additional High mass/COM trials passed. These are rigid surrogates with estimated parameters.
- Soft-object physics validation is deferred by user decision. Cloth/bags/pillows remain fixed visual forms; no deformable simulation or robot manipulation qualification is claimed.
-30 native captures reviewed locally,49 regression tests passed,302 protected files unchanged.

## Layout and prerequisites

Keep common_core/ and _asset_library_blendkit/ as siblings. Python scripts target the existing Windows Blender and Isaac Sim6.0.0-rc.59 environment. See source for current SDK paths. Native runs require separately and legally acquired room/asset inputs and local deployment bindings; those dependencies are intentionally absent here. This source snapshot alone cannot reproduce the full room render.

Pure engineering checks on the original SDK environment:

```powershell
& C:\isaac_sim\kit\python\python.exe -B -m unittest discover -s _asset_library_blendkit/tests -p 'test_*.py'
```

With local legal assets/configuration available, the complete independent candidate entry is _asset_library_blendkit/scripts/run_density_physics_pipeline.py --tag NEW_TAG --seeds 706 707 (pass706 and707 as separate arguments). Review actual images before handoff. Never infer public redistribution or flexible-object qualification from a local physics PASS.

## Rights and omissions

No original Blendkit .blend, converted USD, texture, Hotel705/YAZHI source asset, SDK, add-on, login profile, raw cache or paper PDF is included. Obtain dependencies legally through their original sources. Source/license metadata is in metadata/asset_sources.json; unknown extractable-USD/redistribution rights stay unknown. No blanket license is assigned to third-party materials or to this checkpoint.

Some source scripts reference intentionally excluded local run/config artifacts. Evidence JSONs here are summaries and hashes, not claims that the omitted runtime artifacts are bundled. Source attribution and binary qualification gates remain independent.
