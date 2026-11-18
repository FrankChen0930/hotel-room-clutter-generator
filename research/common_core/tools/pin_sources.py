"""Inspect only the declared room dependency closures and reuse helpers."""
import argparse
import json
from pathlib import Path
import sys

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from common_core.identity import sha256_file
from common_core.sdk import load_usd


def inventory(workspace: Path, sdk: Path) -> dict:
    Usd, UsdUtils = load_usd(sdk)
    roots = {
        'room_hotel': workspace / '_hotel705_reference/release_v1.0.0/hotel705-random-clutter',
        'room_yazhi': workspace / 'YAZHI-TWIN',
        'hotel_helpers': workspace / '_hotel705_pilot',
        'toolkit': workspace / '_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator',
    }
    room_paths = {'room_hotel': 'assets/room7052/7052_ver3_0925.usda',
                  'room_yazhi': 'room/usd/YAZHI_TWIN.usd'}
    result = {'schema_version': '1.0', 'rooms': {}, 'helpers': [],
              'environment': {'python': sys.version, 'executable': sys.executable,
                              'usd': list(Usd.GetVersion()),
                              'isaac_build': (sdk / 'VERSION').read_text().strip()}}

    def entry(path):
        path = Path(path).resolve(strict=True)
        for mount, root in roots.items():
            if path.is_relative_to(root.resolve()):
                return {'mount': mount, 'path': path.relative_to(root.resolve()).as_posix(),
                        'sha256': sha256_file(path), 'bytes': path.stat().st_size}
        raise ValueError('UNDECLARED_DEPENDENCY_MOUNT: ' + str(path))

    for mount, relative in room_paths.items():
        path = roots[mount] / relative
        before = sha256_file(path)
        layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(path))
        files = {Path(layer.realPath).resolve() for layer in layers if layer.realPath}
        files.update(Path(asset).resolve() for asset in assets)
        records = sorted((entry(p) for p in files), key=lambda x: (x['mount'], x['path']))
        if sha256_file(path) != before:
            raise ValueError('SOURCE_CHANGED_DURING_INSPECTION')
        result['rooms'][mount] = {'root': entry(path), 'closure': records,
                                  'unresolved': sorted(map(str, unresolved)),
                                  'closure_verified': not unresolved}
    helpers = {
        'hotel_helpers': [('roomscale/prepare.py', ['top_triangles']),
                          ('pilot.py', ['signature', 'rel']),
                          ('inspect_source.py', ['SDK bootstrap reference only'])],
        'toolkit': [('toolkit/runtime_support.py', ['hash_json', 'reject_reparse', 'contained']),
                    ('toolkit/vendor/geometry_check.py', ['extract_primitive']),
                    ('toolkit/vendor/randomize_table.py', ['matrix_list'])],
    }
    for mount, items in helpers.items():
        for relative, functions in items:
            result['helpers'].append({**entry(roots[mount] / relative), 'functions': functions,
                                      'reuse': 'read-only reference; no historical main imports'})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(CODE.parent, Path('C:/isaac_sim'))
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({key: {'files': len(value['closure']), 'unresolved': value['unresolved']}
                      for key, value in result['rooms'].items()}))
