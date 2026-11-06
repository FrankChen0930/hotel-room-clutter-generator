# CLI / Configuration / Output Structure

Entrypoint: installed Kit Python -I -B toolkit/randomize.py. For PowerShell use the README native route or process-scoped launcher; no permanent Execution Policy change.

| Option | Meaning |
|---|---|
| --seed INTEGER | signed32-bit seed; required unless --replay |
| --task-mode checkout\|stayover | checkout default; real task-specific selection/ownership |
| --output PATH / --output-dir PATH | aliases; exact NEW directory below deployment/local-test-outputs/, existing parent required |
| --asset-package PATH | independent package root with asset_manifest.json and assets/ |
| --isaac-root PATH | installed SDK root matching the executable |
| --config PATH | local JSON overrides only assets_dir and isaac_root; path inside code-repo or local-test-outputs |
| --preflight | environment/asset/version/closure verification only; no output or SimulationApp |
| --replay PATH | saved scene_manifest.json inside code-repo or local-test-outputs; no resampling |
| --physics none\|qualified | only none is supported; qualified exits21 |

--help works without loading USD. Optimized Python -O is refused because existing geometry checks retain assertions. Network paths, URL references and symlink/junction paths are not supported. Config assets_dir is relative to code-repo; explicit path options and output paths use caller CWD. Use absolute arguments from an unrelated CWD.

Example override file:

~~~json
{"assets_dir":"../asset-package/assets","isaac_root":"C:/isaac_sim"}
~~~

Code/Asset compatibility, policy, geometry thresholds and physics mode cannot be relaxed through --config. Unsupported keys are rejected. The retained read-only policies under toolkit/config/ are included in replay fingerprints.

Successful run:

~~~text
new-run/
  scene.usda
  scene_manifest.json
  run_report.json
  validation.json
  dependency_manifest.json
  generated/<TASK>/seed_<n>_preview.usda
  generated/<TASK>/seed_<n>_manifest.json
  refined/<TASK>/seed_<n>_preview.usda
  01_PREPARED.json
  02_GENERATED.json
  03_COMPLETE.json
~~~

Manifest records code/asset versions, seed, task, asset SHA, pose/support, ownership/action, configuration fingerprint and honest scope. Preserve generator physics NOT_RUN; do not interpret a collision proxy as qualification. After a failed claim, failure.json preserves phase/reason. No --force, automatic retry or same-output reuse.

| Exit | Meaning |
|---:|---|
|0|requested static/preflight stage succeeded; read report limitations|
|2|invalid arguments/config/local-path form|
|10|unsupported/missing SDK/Python/optimized mode|
|11|missing/tampered asset or replay/config identity failure|
|12|unsafe/existing output, replay/config path or reparse path|
|13|Code/Asset/dataset/manifest/rights version mismatch|
|20|geometry/support/policy/unaccepted-state rejection|
|21|Physics disabled in this release|
|40|unexpected generation/readback failure; retain evidence|

CLI JSON errors give phase, exit code and reason. Native exit and report status must both be checked; producing one USD is not sufficient.
