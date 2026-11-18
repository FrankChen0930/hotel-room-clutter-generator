# Delivery scope

The existing toolkit is retained. `research/` adds an independent room-input, seeded-placement, bounded-physics-feedback, settled-USD, native-render and replay workflow. Original furniture layout stays fixed.

## Directly usable examples

Extract all of `downloads/hotel705_examples.zip`. In Isaac Sim use **File > Open** for `clean_room.usda` or `scenes/*.usda`. Keep `assets/` and relative paths intact. These are complete multi-root stages, not individual props to insert by defaultPrim reference. Six regular stages contain settled generated-object poses; six `_dynamic.usda` counterparts contain tested rigid-body settings.

All13 entry stages were actually relocated to another directory. Composed prims, attributes (including mesh geometry, materials, transforms and physics), time samples, relationships, asset bytes, units and defaultPrim were compared to their exact tested sources. All comparisons passed. Relative-path USD recoding changes hashes; `delivery_map.json` links original evidence to delivered files, and `relocation_verification.json` records equivalence. This is not an additional dynamics simulation.

## Public versus local pools

Public examples use **five original Hotel705 prop source records**, with limited diversity and repeated instances. Full local-library README previews show a separate102-independent-asset Blendkit research pool;3 appearance variants do not increase that count. Both sets use706:15/32/77 and707:13/49/73 instances. Public examples do not reproduce the richer local pool's bed/pillow/chair clutter. No Blendkit model/texture payload is distributed.

673 candidate identities,369 acquired sources,134 converted sources and102 independently accepted assets are different gates. `docs/asset_sources.json` contains curated source IDs/authors/URLs/versions/hashes/rights. Model originals, raw provider metadata, Add-on, caches, credentials, SDKs and the paper PDF are excluded.

## Evidence and limits

Each of six exact public sample scenes and six local-library scenes completed30seconds at120Hz (3600native steps), with49 original dynamic bodies and31 joints plus all generated props. Fixed walls/furniture supply collision support. Checks cover final-two-second stability, maximum12cm generated displacement, support-region retention and native expected contacts, plus Static/Integrity/Replay and actual image review. The clean-room wrapper completed its own49-body/31-joint30second native acceptance. The independent packaged-input runtime also generated and simulated six cases.

This is fixed-form/rigid-proxy stability for exact cases, not calibrated physical parameters, arbitrary-seed certification, cloth deformation or robot manipulation. Individual new assets remain STATIC_ONLY. Original36 formal two-room generation cases and302 protected source files remain locally intact; not all historical cases are bundled.

## Reproduction

Tested:Windows,Isaac Sim6.0.0-rc.59 built-in Python,Direct3D12 rendering,CPU PhysX,RTX5070Ti Laptop GPU. From repository root:

```powershell
& "C:\isaac_sim\kit\python\python.exe" -B research\_asset_library_blendkit\scripts\run_public_workflow.py --tag my_hotel705_run --seeds 706 707
```

Adjust the executable path for a different installation. Included native-room input/config/texture dependencies use relative paths and SHA pins; no Blendkit login or network model API is required. Use a fresh tag. Failures are retained. New results are under `research/_asset_library_blendkit/runs/`. Captures remain pending actual visual review until inspected; the workflow does not auto-accept images.

Optional asset-acquisition/local research scripts require legally acquired inputs and configuration; the public entrypoint above is the supported included workflow. No SDK is distributed. Proof summaries are under `docs/evidence/`.

## Repository and publishing scope

This repository distributes scenes, code, source attribution and scene/code verification evidence. Personal progress presentations and slide-review artifacts are excluded. Code/model rights are scoped in the root rights documents; no blanket open-source license is selected.

Publication is a normal non-force push to existing `main`. The desktop publisher records success only when GitHub confirms the exact pushed HEAD. A prepared local commit is not a verified push.
