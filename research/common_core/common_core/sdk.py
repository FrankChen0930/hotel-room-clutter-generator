"""Load the installed SDK's USD bindings without starting SimulationApp."""
import os
from pathlib import Path
import sys

_dll_handles = []


def load_usd(isaac_root: Path):
    root = Path(isaac_root).resolve(strict=True)
    expected_python = root / 'kit/python/python.exe'
    if Path(sys.executable).resolve() != expected_python.resolve():
        raise RuntimeError('SDK_PYTHON_MISMATCH')
    libs = sorted((root / 'extscache').glob('omni.usd.libs-*'))
    if len(libs) != 1:
        raise RuntimeError('SDK_USD_LIBRARY_AMBIGUOUS: ' + str(libs))
    if str(libs[0]) not in sys.path:
        sys.path.insert(0, str(libs[0]))
        if os.name == 'nt':
            for directory in (libs[0] / 'bin', root / 'kit'):
                _dll_handles.append(os.add_dll_directory(str(directory)))
    from pxr import Usd, UsdUtils
    return Usd, UsdUtils
