"""Selected actual runtime metadata only; no environment-variable dump."""
from copy import deepcopy
import csv
from functools import lru_cache
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from .identity import sha256_file


@lru_cache(maxsize=2)
def _environment(isaac_root):
    from pxr import Usd
    root=Path(isaac_root).resolve(strict=True);gpu=dict(execution='NOT_RUN',outcome='UNKNOWN',devices=[])
    executable=shutil.which('nvidia-smi')
    if executable:
        try:
            process=subprocess.run([executable,'--query-gpu=name,driver_version,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
            if process.returncode==0:
                gpu=dict(execution='EXECUTED',outcome='PASS',devices=[dict(name=row[0].strip(),driver_version=row[1].strip(),memory_mib=int(row[2].strip())) for row in csv.reader(process.stdout.splitlines()) if len(row)==3])
        except (OSError,ValueError,subprocess.TimeoutExpired):gpu['reason']='LOCAL_GPU_METADATA_UNAVAILABLE'
    binaries={}
    for pattern in ['omni.physx-*/bin/omni.physx.plugin.dll','omni.physics.tensors-*/bin/omni.physics.tensors.plugin.dll']:
        for path in sorted((root/'extscache').glob(pattern)):binaries[path.relative_to(root).as_posix()]=sha256_file(path)
    return dict(python=sys.version,python_executable=str(Path(sys.executable).resolve()),python_executable_sha256=sha256_file(Path(sys.executable)),
        usd=list(Usd.GetVersion()),isaac_root=str(root),isaac_build=(root/'VERSION').read_text().strip(),
        os=platform.platform(),architecture=platform.machine(),cpu=platform.processor(),gpu=gpu,physics_binary_hashes=binaries)


def runtime_environment(isaac_root=None):
    root=Path(isaac_root) if isaac_root is not None else Path(sys.executable).resolve().parents[2]
    return deepcopy(_environment(str(root.resolve())))
