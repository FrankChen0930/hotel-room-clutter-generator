"""Absolute-path entry point, independent of the caller's working directory."""
from common_core.cli import main

if __name__=='__main__':
    raise SystemExit(main())
