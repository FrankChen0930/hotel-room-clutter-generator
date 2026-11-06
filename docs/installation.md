# Installation / Requirements

1. Obtain permission for both code and the independent Asset Package. These local preparation files are not cleared for redistribution.
2. Supply an existing licensed Windows Isaac6.0.0-rc.59 installation. The first candidate is tested only with its Kit Python3.12.13 and USD0.25.11. No downloads, pip installation, driver change or runtime update is performed by this package.
3. Put code-repo/ and asset-package/ beside each other; create local-test-outputs/ beside them. Do not flatten the assets/ tree or rename its internal referenced layers.
4. Set the exact SDK path through native Python invocation plus --isaac-root, or YAZHI_ISAAC_ROOT / launcher flag. A file named python.exe is not sufficient: it must be the configured Kit Python and supply the expected bundled USD extension.
5. Run --help and read-only --preflight before generation. Wrong version, ABI, missing extension, bad asset manifest, version mismatch or missing data must fail visibly. Never auto-download missing assets.

Default assets_dir is ../asset-package/assets, relative to code-repo. --asset-package explicitly selects another package root (the directory containing asset_manifest.json and assets/). Dataset identity, version, file set, rights metadata and SHA must still match the closed compatibility lock. Sibling layout is recommended for portable output references; a different drive can make relative USD references impossible and is not certified.

Blender is not needed for this release's static runtime. Original research, old staging outputs and QA builders are not runtime dependencies. No simulation/cloth/renderer entrypoint is shipped.

New folders are required for another code or asset version. Do not overwrite an old installation or an old Run while updating.
