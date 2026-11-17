"""Reserve a fresh intake directory atomically, keeping all earlier attempt evidence."""
from pathlib import Path
import re

def reserve_attempt(sources, requested='intake_user_001'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', requested):
        raise ValueError('SIMPLE_ATTEMPT_REQUIRED')
    sources=Path(sources); sources.mkdir(parents=True,exist_ok=True)
    match=re.fullmatch(r'(.*?)([0-9]+)',requested)
    prefix=match[1] if match else requested+'_'
    start=int(match[2]) if match else 1
    width=len(match[2]) if match else 3
    for index in range(10000):
        name=requested if index==0 else prefix+str(start+index).zfill(width)
        out=sources/name
        try:
            out.mkdir()
            return out
        except FileExistsError:
            continue
    raise RuntimeError('ATTEMPT_NAME_RANGE_EXHAUSTED')
