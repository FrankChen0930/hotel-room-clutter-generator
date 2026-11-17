# Common Core commands

Use the Python executable from the bound local Isaac Sim SDK and the absolute
`run_core.py` path. Every command requires `--config <deployment.json>`.

| Command | Required additional arguments | Result |
|---|---|---|
| preflight | `--room` | Read-only contracts, SDK and dependency verification; no run |
| generate | `--room --scenario --level --seed --output` | New scene and sealed manifest; static/integrity/replay evidence |
| replay | `--manifest --output` | New effective-state reconstruction without sampling |
| validate | `--manifest --output [--tiers integrity,static,replay]` | New assessment, original manifest unchanged |
| batch | `--spec --output` | Explicit cases, individual results, aggregate index |

`config/batch_v1.json` contains the 36 release keys: two rooms, two scenarios,
three levels and seeds 706/707/708. Batch continues after an individual failure,
retains its exit code and never replaces a seed. A batch PASS covers generation's
static, integrity and replay layers; native support and visual acceptance are
separate assessments.

Validation tiers are `integrity,static,replay,support,visual,physics`.
`all` expands to exactly these six names. Support dispatches a bounded native
query. Visual and physics return NOT_RUN/UNKNOWN until separately captured,
reviewed or qualified against explicit targets; the command returns nonzero.
Selecting `all` never enables dynamics on the entire room.

Exit codes: 0 requested work passed; 2 parameters/schema; 3 identity/dependencies;
4 no placement solution; 5 validation or batch failure; 6 native incomplete or
requested evidence unavailable; 7 output/permission. Existing output directories,
source directories and redirected paths are rejected. Use a new output under
`_common_core_runs` for each invocation.
