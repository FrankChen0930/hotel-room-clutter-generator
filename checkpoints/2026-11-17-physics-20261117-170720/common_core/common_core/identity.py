"""Content identity; never imports or writes source files."""
import hashlib
import json
import random
import re
from pathlib import Path

def sha256_file(path: Path) -> str:
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_json(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def content_digest(data) -> str:
    return hashlib.sha256(canonical_json(data)).hexdigest()


def validate_seed(seed: int) -> int:
    if type(seed) is not int or not -(2**31) <= seed < 2**31:
        raise ValueError('SEED_SIGNED32')
    return seed


def rng_seed(seed: int, namespace: str, stable_id: str, attempt_ordinal: int = 0) -> int:
    validate_seed(seed)
    if not isinstance(namespace, str) or not namespace or not isinstance(stable_id, str) or not stable_id:
        raise ValueError('RNG_STREAM_ID')
    if type(attempt_ordinal) is not int or attempt_ordinal < 0:
        raise ValueError('RNG_ATTEMPT_ORDINAL')
    payload = ['cc-rng-v1', seed, namespace, stable_id, attempt_ordinal]
    return int.from_bytes(hashlib.sha256(canonical_json(payload)).digest()[:16], 'big')


def rng_for(seed: int, namespace: str, stable_id: str, attempt_ordinal: int = 0) -> random.Random:
    return random.Random(rng_seed(seed, namespace, stable_id, attempt_ordinal))


def stable_request_id(role: str, asset_family: str, ordinal: int) -> str:
    if any(not isinstance(s, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', s)
           for s in (role, asset_family)) or type(ordinal) is not int or ordinal < 0:
        raise ValueError('REQUEST_ID_COMPONENT')
    return f'{role}/{asset_family}/{ordinal}'


def input_fingerprint(*, room_hash: str, catalog_hash: str, policy_hash: str,
                      source_closure_hash: str, code_hash: str, seed: int,
                      scenario: str, level: str) -> str:
    """Logical identities only: deployment paths are deliberately absent."""
    validate_seed(seed)
    return content_digest(dict(room_hash=room_hash,catalog_hash=catalog_hash,
        policy_hash=policy_hash,source_closure_hash=source_closure_hash,code_hash=code_hash,
        seed=seed,scenario=scenario,level=level))


def state_digest(manifest: dict) -> str:
    """Hash effective state only, excluding run paths, evidence and proposals."""
    inputs = manifest['inputs']
    logical_inputs = {key: inputs[key] for key in ['seed','scenario','level','code_hash',
        'profile_hash','catalog_hash','policy_hash','source_closure_hash']}
    objects = [{key: obj[key] for key in ['instance_id','request_id','asset_id',
        'state_sha256','origin','source_object_id','native_prim','effective']}
        for obj in manifest['objects']]
    return content_digest(dict(inputs=logical_inputs,requests=manifest['requests'],
        objects=sorted(objects,key=lambda item:item['instance_id'])))
