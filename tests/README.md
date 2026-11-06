# Candidate-only Local Acceptance

Use installed supported Kit Python, no test framework installation:

~~~powershell
& "$isaac\kit\python\python.exe" -I -B "$code\tests\acceptance.py" --isaac-root $isaac
~~~

The harness derives candidate paths from this code-repo, writes fresh evidence under sibling qa/ and new scene outputs under local-test-outputs/, and runs children sequentially from C:/Windows. It performs real USD generation/readback, no SimulationApp/PhysX/Cloth/Blender. Every native case is timeout/RSS bounded; failed receipts are retained. Do not rerun successful costly cases merely to rewrite documents.

README CLI examples correspond to docs/acceptance_commands.json, which the harness consumes. The test never imports original research or old staging/QA-builder modules. The separate preparation-only source-protection script is outside code-repo.

Negative fixtures intentionally have wrong/missing manifests or data. They are failure cases, not mocks of successful generation and not part of the Asset Package.
