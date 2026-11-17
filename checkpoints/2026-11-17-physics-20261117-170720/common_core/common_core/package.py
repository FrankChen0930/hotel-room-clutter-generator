"""Code-only snapshot with actual-byte checksums and external source rights index."""
from pathlib import Path
import shutil
from .contracts import load_json
from .identity import sha256_file
from .manifest import write_json_new
from .paths import guard_new_output


def build_package(output):
    source=Path(__file__).resolve().parents[1];out=guard_new_output(output);out.mkdir(parents=True)
    code=out/'Common Core code';code.mkdir();inventory=[]
    for path in sorted(source.rglob('*')):
        relative=path.relative_to(source)
        if not path.is_file() or any(p in ['.git','__pycache__','.pytest_cache'] for p in relative.parts) or relative.as_posix()=='config/deployment.local.json':continue
        if path.suffix.lower() in ['.usd','.usda','.usdc','.png','.jpg','.dll','.exe']:raise ValueError('PACKAGE_EXTERNAL_BINARY_FORBIDDEN')
        target=code/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        inventory.append(dict(path=relative.as_posix(),sha256=sha256_file(target),bytes=target.stat().st_size,
            scope='COMMON_CORE_CODE_OR_CONFIGURATION; no rights to referenced external assets granted'))
    catalog=load_json(source/'config/catalog.json');rights=[]
    for entry in catalog['entries']:
        for state in entry['states']:
            rights.append(dict(asset_id=entry['asset_id'],state_id=state['state_id'],sha256=state['sha256'],
                locator=state['usd_locator_or_native_prim'],license_scope=entry.get('license_scope','ORIGINAL_SOURCE_RESTRICTIONS_APPLY'),
                provenance=entry.get('provenance'),included=False))
    lock=load_json(source/'config/source_lock.json')
    dependencies=[dict(**record,included=False,license_scope='ORIGINAL_SOURCE_RESTRICTIONS; INTERNAL_EVALUATION_ONLY; NOT_REDISTRIBUTED')
        for group in [*[r['closure'] for r in lock['rooms'].values()],lock['helpers'],lock['assets']] for record in group]
    write_json_new(out/'inventory.json',dict(schema='CodeDelivery/1',code_directory=code.name,files=inventory,assets_included=False))
    write_json_new(out/'external-rights.json',dict(states=rights,files=dependencies,sdk=dict(included=False,license_scope='LOCAL_INSTALLATION_LICENSE')))
    return out
