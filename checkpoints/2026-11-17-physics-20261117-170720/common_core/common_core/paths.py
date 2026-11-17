"""Write boundary for all new scene and assessment outputs."""
from pathlib import Path

def workspace_root():
    # A code-only copy may live inside a new run bundle. Keep the approved
    # workspace boundary instead of deriving a nested writable root from it.
    for parent in Path(__file__).resolve().parents:
        if (parent/'_common_core_runs').is_dir() and (parent/'_common_core_planning').is_dir():return parent
    raise RuntimeError('APPROVED_WORKSPACE_MISSING')


RUN_ROOT=workspace_root()/'_common_core_runs'


def reject_source_output(path, bindings):
    target=Path(path).resolve()
    for value in bindings.values():
        source=Path(value).resolve()
        if target.is_relative_to(source) or source.is_relative_to(target):raise ValueError('OUTPUT_SOURCE_OVERLAP')


def guard_new_output(path: Path) -> Path:
    path=Path(path).absolute()
    for component in [path,*path.parents]:
        try:info=component.lstat()
        except FileNotFoundError:continue
        if component.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('OUTPUT_REPARSE_REDIRECT')
    resolved=path.resolve()
    root=RUN_ROOT.resolve()
    if not resolved.is_relative_to(root) or resolved==root:raise ValueError('OUTPUT_OUTSIDE_RUN_ROOT')
    if resolved.exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
    return resolved
