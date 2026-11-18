"""Minimal WU-00 contracts; expanded by WU-01. No SDK imports."""
import json, re
from pathlib import Path
from .identity import sha256_file
from .contract_validation import REQUIRED, VALIDATORS, fields, finite

def load_json(path: Path) -> dict:
    def bad_constant(value): raise ValueError('NONFINITE: '+value)
    def unique_pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('DUPLICATE_JSON_KEY: '+key)
            result[key] = value
        return result
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'),parse_constant=bad_constant,
                    object_pairs_hook=unique_pairs)
    if not isinstance(data,dict): raise ValueError('JSON_OBJECT_REQUIRED')
    finite(data)
    return data

def verify_source(path: Path, expected: str) -> None:
    if sha256_file(path)!=expected: raise ValueError('SOURCE_HASH_MISMATCH: '+str(path))

def validate_contract(data: dict, kind: str) -> dict:
    if not isinstance(data,dict): raise ValueError('JSON_OBJECT_REQUIRED')
    majors={'RoomProfile':'1','Catalog':'1','Policy':'1','Manifest':'3'}
    if kind not in majors: raise ValueError('CONTRACT_KIND')
    version=data.get('schema_version','')
    if not isinstance(version,str) or not re.fullmatch(majors[kind]+r'\.\d+',version):
        raise ValueError('SCHEMA_VERSION: '+str(version))
    fields(data, REQUIRED[kind])
    finite(data)
    VALIDATORS[kind](data)
    return data
