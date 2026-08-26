"""Generate validation/SHA256SUMS.txt with relative paths.

Covers finding C1: temporary files are excluded and the manifest is written as the final
filesystem operation, so it can never record a state that no longer exists. Paths are
relative to the package root, so the manifest verifies from any extraction directory.

Run this LAST, after every other freeze step. Verify with scripts/verify_manifest.py.

    python scripts/build_manifest.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
MANIFEST_REL = 'validation/SHA256SUMS.txt'
EXCLUDE_DIRS = {'__pycache__', '.git', '.ipynb_checkpoints', '.pytest_cache'}
EXCLUDE_SUFFIX = {'.pyc', '.pyo', '.swp', '.tmp'}
EXCLUDE_NAMES = {'.DS_Store', 'Thumbs.db'}


def iter_files(root):
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.suffix in EXCLUDE_SUFFIX or p.name in EXCLUDE_NAMES:
            continue
        if p.name.startswith('~') or p.name.endswith('~'):
            continue
        if rel.as_posix() == MANIFEST_REL:
            continue
        yield rel, p


def main():
    rows = []
    for rel, p in iter_files(R):
        rows.append('{0}  {1}'.format(hashlib.sha256(p.read_bytes()).hexdigest(),
                                      rel.as_posix()))
    dst = R / MANIFEST_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('\n'.join(rows) + '\n')
    print('{0} entries written to {1}'.format(len(rows), MANIFEST_REL))
    print('manifest sha256: {0}'.format(hashlib.sha256(dst.read_bytes()).hexdigest()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
