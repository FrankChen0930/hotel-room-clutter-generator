# Evidence-backed progress

The existing Active Plan remains the owner of milestone status. `tools/progress.py`
adds an explicit evidence ledger and a weekly-report source; it installs no hooks.

Ingest a completed unit using `--ledger <active-plan>/ledger-evidence.jsonl
--receipt <unit>/receipt.json --status COMPLETE --commit <40-hex-local-commit>
--gate <unit>/unit-gates.json`. The receipt must contain successful commands with
matching log hashes, and unit gates must say EXECUTED/PASS. Every referenced file
is checked before recording. Receipt and gate paths stay under the new runs root;
the ledger and summary stay under the approved planning root.

The same event is idempotent. Reusing its ID with changed evidence or version is
an error. Use FAILED or INCOMPLETE for interrupted/failed receipts, retaining the
failure reason; these events never contribute a completion. The immutable receipt
remains authoritative. A changed log or receipt makes summary verification fail.

Use `--summary <new-summary.md>` to create a new report source with direct evidence
links and versions. Summaries describe the events ingested into that ledger.
Historical manual ledger entries remain intact and are not silently converted
into measured completion events. Milestone approval still requires all Roadmap
unit-specific gates; successful common tests alone do not establish acceptance.
