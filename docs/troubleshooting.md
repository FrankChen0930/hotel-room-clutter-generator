# Troubleshooting

- Direct .ps1 blocked: use native Kit Python, or powershell.exe -NoProfile -ExecutionPolicy Bypass -File ... for that child only. Do not Set-ExecutionPolicy.
- SDK missing/error10: check --isaac-root, YAZHI_ISAAC_ROOT and that the actual Python executable is from the same supported installation. The tool installs nothing.
- Asset Package missing/error11: supply --asset-package pointing to its root, not a single USD or assets/ subfolder. Preserve asset_manifest.json and all locked files.
- Version/error13: compare code VERSION and Asset Package version; obtain an approved matched pair. Do not edit the manifest/lock to bypass validation.
- Output refused/error12: use a new directory below sibling local-test-outputs/, not a filename or existing directory. Create its parent first. No overwrite/force.
- Invalid config/error2: only assets_dir/isaac_root overrides are accepted, no physics/geometry relaxation.
- Replay error11: code/config/assets or saved manifest changed. Retain the old installation/output; do not rewrite evidence or import old-v0.1.0 fingerprints.
- Geometry/error20: retain the bounded rejection/failure evidence; do not silently choose another seed or disable checks.
- Physics/error21: intentionally unsupported, not a missing optional dependency.
- Viewer texture/material issue: keep the complete relative USD/texture closure. Blender diagnostics have a known cylinder representation discrepancy; see known_limitations.md. No renderer fix is included here.

Read JSON stderr, failure.json (if output was claimed) and phase receipts. A failed output remains evidence; use a new Run for another authorized attempt.
