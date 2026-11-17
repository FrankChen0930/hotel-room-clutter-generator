# Local reproducible execution

Use the installed Isaac Sim Python executable, currently
`C:/isaac_sim/kit/python/python.exe`, with `-B`. The installation's VERSION file
and captured environment identify the exact build; no package installation or
paid service is needed.

Copy `config/deployment.example.json` to a new deployment file beside its
referenced configuration files. Bind all four logical mounts to the existing
read-only local roots and set `isaac_root`. Configuration paths are relative to
the deployment file; source locators are relative to their mount. The supplied
`deployment.local.json` already binds this workstation. Missing or changed files
fail identity checks; do not update pinned hashes to suppress a failure.

PowerShell examples (absolute entry path makes caller CWD irrelevant):

```powershell
$core = 'C:/hotel_room/common_core'
$py = 'C:/isaac_sim/kit/python/python.exe'
$cfg = "$core/config/deployment.local.json"
& $py -B "$core/run_core.py" preflight --config $cfg --room hotel705
& $py -B "$core/run_core.py" generate --config $cfg --room hotel705 --scenario STAYOVER --level low --seed 706 --output 'C:/hotel_room/_common_core_runs/researcher hotel 706'
& $py -B "$core/run_core.py" generate --config $cfg --room yazhi --scenario CHECKOUT --level medium --seed 707 --output 'C:/hotel_room/_common_core_runs/researcher yazhi 707'
$manifest = 'C:/hotel_room/_common_core_runs/researcher hotel 706/attempts/a000/manifest.json'
& $py -B "$core/run_core.py" replay --config $cfg --manifest $manifest --output 'C:/hotel_room/_common_core_runs/researcher replay hotel'
& $py -B "$core/run_core.py" validate --config $cfg --manifest $manifest --tiers integrity,static,replay --output 'C:/hotel_room/_common_core_runs/researcher validate hotel'
```

Repeat replay and validate for the YAZHI manifest. Each output must be new. Keep
commands, operator/environment, exit codes and resulting manifest/state hashes.
The independent researcher signs their own operation receipt; the author cannot
sign it for them. If paths in these examples already exist, choose new run names
while keeping the requested case seeds and inputs unchanged.

Code may be copied to a new path containing spaces inside this approved workspace.
Logical source remounts and output path changes do not alter the effective state
digest when code bytes, profile, catalog, policy, source closure and case keys
are unchanged. The current approved write boundary remains `_common_core_runs`;
moving to another workstation requires that environment's authorized workspace.
Rebind sources there and verify them before generation. Cross-machine native
physics is not a promise of bitwise equality and requires a new qualification.

The code-only package's inventory contains each copied file's checksum and scope.
External source license/provenance is indexed separately as INTERNAL_EVALUATION_ONLY
or its original recorded restriction. This package grants no redistribution rights
to external assets or SDK binaries. Keep source roots and historical repositories
read-only. Local Git commits provide rollback; no push is configured or required.
