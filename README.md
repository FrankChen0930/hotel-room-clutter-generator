# YAZHI-TWIN Randomization Toolkit

Version: **0.1.0-rc.1-internal**. P5.2 local Git preparation; not a published GitHub Release. Intended private repository: `hotel-room-clutter-generator`; remote creation and first push require separate Human authorization.

**INTERNAL_EVALUATION_ONLY / REDISTRIBUTION_NOT_CLEARED / LICENSE_PENDING_HUMAN_APPROVAL**

Generate bounded static hotel-room configurations from an existing room USD. The retained sampler supports integer seeds, CHECKOUT/STAYOVER policies, relative USD overlays, manifests, geometry/support checks and deterministic replay. No runtime physics, cloth, renderer or robot certification is included.

## Installation and layout

You need an existing Windows Isaac Sim **6.0.0-rc.59** installation with bundled Python **3.12.13 / OpenUSD0.25.11**. No installer, SDK binaries or pip environment is supplied; do not upgrade your system just to try this candidate. Other versions/machines are not certified.

Place the two separately approved local folders as siblings:

~~~text
deployment/
  code-repo/                 # this folder
  asset-package/
    asset_manifest.json
    assets/                  # 39 immutable dependency files
  local-test-outputs/         # new generated directories, never tracked
~~~

Keep the Asset Package intact. Its internal historic-looking path identifiers are preserved only to keep relative references; no original research/output folder is accessed at runtime. Code and Asset Package versions must both be **0.1.0-rc.1-internal** for this candidate.

## Quick Start: native Kit Python (recommended)

Open PowerShell, change to this code-repo folder, then:

~~~powershell
$code = (Get-Location).Path
$deployment = Split-Path $code -Parent
$isaac = 'C:\isaac_sim'                    # set your existing installation
$assets = Join-Path $deployment 'asset-package'
New-Item -ItemType Directory -Force -Path (Join-Path $deployment 'local-test-outputs') | Out-Null
$py = Join-Path $isaac 'kit\python\python.exe'
$cli = Join-Path $code 'toolkit\randomize.py'

& $py -I -B $cli --help
& $py -I -B $cli --isaac-root $isaac --asset-package $assets --seed 49 --preflight
& $py -I -B $cli --isaac-root $isaac --asset-package $assets --seed 49 --task-mode checkout --output-dir "$deployment\local-test-outputs\checkout49"
& $py -I -B $cli --isaac-root $isaac --asset-package $assets --seed 50 --task-mode checkout --output "$deployment\local-test-outputs\checkout50"
& $py -I -B $cli --isaac-root $isaac --asset-package $assets --seed 49 --task-mode stayover --output-dir "$deployment\local-test-outputs\stayover49"
~~~

These output names must not already exist. --output-dir and --output are aliases. The argument is an **exact new directory**, not a USD filename or an existing output root. Its parent must exist below deployment/local-test-outputs/. Relative output paths resolve against the caller's working directory; absolute paths are clearer. Omitting --output creates a new timestamped directory there.

The CLI also works from another CWD when absolute CLI/asset/output paths are supplied. Preflight is read-only; it starts no SimulationApp and writes no output. Ordinary WindowsApps Python is not required.

## Optional process-scoped PowerShell launcher

A machine may refuse direct .ps1 invocation. Use the native Python route above, or:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$code\toolkit\randomize.ps1" --isaac-root $isaac --asset-package $assets --seed 49 --preflight
~~~

This applies only to that child process. Never run Set-ExecutionPolicy or weaken persistent policy for this toolkit. Launcher SDK precedence: explicit --isaac-root, local --config isaac_root, YAZHI_ISAAC_ROOT, then C:\isaac_sim. Native Python must itself come from the configured installation.

## Replay and outputs

~~~powershell
& $py -I -B $cli --isaac-root $isaac --asset-package $assets --replay "$deployment\local-test-outputs\checkout49\scene_manifest.json" --output-dir "$deployment\local-test-outputs\checkout49_replay"
~~~

Saved-manifest replay restores recorded poses without resampling. Same-seed generation independently resamples deterministically. Both require matching code/config/asset identity. v0.1.0 manifests are not silently migrated into this RC.

Each successful output includes scene.usda, scene_manifest.json, validation.json, dependency_manifest.json, run_report.json, generated/refined USD layers and immutable phase receipts. Preserve the layers and Asset Package; scene.usda alone is not standalone. Failure details are printed as JSON and, after output claim, preserved in failure.json. Never reuse a failed or completed output directory.

## Scope and limitations

- Tested examples: Seed49/50 CHECKOUT and Seed49 STAYOVER. Arbitrary signed32-bit seeds may geometrically reject; the tool never quietly substitutes another seed.
- Existing conservative furniture/rigid-item sampling and Task/Ownership policies are retained. Guest belongings stay DO_NOT_TOUCH; labels are synthetic research assumptions, not hotel SOP or robot permission.
- Only retained NeatCanonical/SideDrape and Neat/Compressed pillow states. No new bedding or trash/cue algorithm.
- PHYSICS_NOT_RUN; COLLISION_NOT_CERTIFIED; HUMAN_ACCEPTANCE_PENDING. --physics qualified is explicitly refused.
- P3.5 Blender diagnostic cylinder envelope discrepancy is about **1.47 mm** against the unchanged **0.20 mm** threshold: NOT_MET. It does not overturn static USD QA, and no new rendering/certification is claimed.
- GUI, navigation, manipulation, runtime cloth, full-room dynamics and general cross-machine compatibility remain unsupported.

## Documentation and QA

[Installation](docs/installation.md) | [CLI/config/output reference](docs/cli_reference.md) | [Reproducibility](docs/reproducibility.md) | [Troubleshooting](docs/troubleshooting.md) | [Known limitations](docs/known_limitations.md) | [Version/update/rollback](docs/versioning.md) | [Publication draft](docs/publication_plan.md) | [Human decisions](docs/human_approval_checklist.md) | [Rights](RIGHTS.md).

The supplied tests use this candidate only and the installed SDK; no original research/staging/QA-builder import is needed. They create fresh sequential bounded static runs and negative fixtures under sibling QA/output directories. See tests/README.md. QA evidence and actual generated samples are delivered outside this code candidate, not committed into it.

This isolated copy is prepared for a local Git repository on `main`. No remote repository, GitHub release or upload is authorized by this preparation. The first commit SHA and Git QA evidence are recorded outside the code repository. Local technical PASS is not distribution permission.
