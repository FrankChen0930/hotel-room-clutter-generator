# Version Compatibility / Update and Rollback

First pair:
- Code:0.1.0-rc.1-internal
- Asset Package:0.1.0-rc.1-internal
- Dataset:yazhi-twin-internal-static-v2.3
- SDK:Isaac6.0.0-rc.59 / Kit Python3.12.13 / USD0.25.11 on tested Windows

Preflight compares code VERSION/runtime/config, exact Asset Package version/compatibility/dataset/rights, asset_manifest SHA and every locked asset SHA. No general version range is inferred.

Update into a **new deployment directory**, copy an approved matched pair, run preflight and small static/replay QA, then point users at that directory. Preserve the old deployment and evidence. Do not in-place edit a lock/manifest, replace canonical data, force replay across changed fingerprints or silently migrate old manifests.

Rollback means choose the retained old deployment/path and its own saved manifests; it does not delete the newer version. Any future tag must map to immutable code/data manifests and evidence. Code-only fixes may still change replay identity and compatibility metadata; explicitly decide version pairing and revalidate rather than assuming old evidence transfers.

P5.2 prepares a local Git repository on main. The first commit SHA and byte inventories are recorded in the separate preparation evidence. No tag, remote repository, push or release is created in this preparation. Only README and publication/versioning/human-approval documentation change from the accepted candidate; runtime, config, tests and version remain byte-identical.
