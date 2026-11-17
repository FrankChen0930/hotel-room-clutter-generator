"""Rehash the declared closure; do not inspect unrelated repository files."""
import json
from pathlib import Path
import sys

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from common_core.contracts import load_json, verify_source


def verify() -> dict:
    workspace = CODE.parent
    bindings = {
        'room_hotel': workspace / '_hotel705_reference/release_v1.0.0/hotel705-random-clutter',
        'room_yazhi': workspace / 'YAZHI-TWIN',
        'hotel_helpers': workspace / '_hotel705_pilot',
        'toolkit': workspace / '_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator',
    }
    lock = load_json(CODE / 'config/source_lock.json')
    records = [*lock['helpers'], *lock.get('assets', [])]
    for room in lock['rooms'].values():
        if room['unresolved'] or not room['closure_verified']:
            raise ValueError('UNRESOLVED_SOURCE_CLOSURE')
        records.extend(room['closure'])
        records.append(room['root'])
    checked = set()
    for record in records:
        root = bindings[record['mount']].resolve()
        path = (root / record['path']).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError('SOURCE_PATH_ESCAPE')
        verify_source(path, record['sha256'])
        checked.add(str(path))
    return {'execution': 'EXECUTED', 'outcome': 'PASS', 'files_checked': len(checked),
            'scope': 'declared room closure and selected helper bytes only'}


if __name__ == '__main__':
    print(json.dumps(verify()))
