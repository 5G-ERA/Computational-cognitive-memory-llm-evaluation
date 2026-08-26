"""Verify every digest in validation/SHA256SUMS.txt from the extracted package root.

Covers the section 6 requirement 'verify every digest from the extracted package root'.
Paths in the manifest are relative, so verification succeeds wherever the package is
extracted. Reports missing files, changed digests and files present but unlisted.

    python scripts/verify_manifest.py            # verify
    python scripts/verify_manifest.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
MANIFEST = R / 'validation/SHA256SUMS.txt'
EXCLUDE_DIRS = {'__pycache__', '.git', '.ipynb_checkpoints'}
EXCLUDE_SUFFIX = {'.pyc', '.pyo'}


def iter_files(root):
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.suffix in EXCLUDE_SUFFIX:
            continue
        if rel.as_posix() == 'validation/SHA256SUMS.txt':
            continue
        yield rel, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    if not MANIFEST.exists():
        print('MISSING MANIFEST: {0}'.format(MANIFEST))
        return 2

    listed = {}
    for line in MANIFEST.read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split('  ', 1)
        listed[rel] = digest

    on_disk = dict(iter_files(R))
    missing = sorted(set(listed) - {k.as_posix() for k in on_disk})
    unlisted = sorted({k.as_posix() for k in on_disk} - set(listed))
    changed = []
    for rel, p in on_disk.items():
        key = rel.as_posix()
        if key in listed:
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if got != listed[key]:
                changed.append({'path': key, 'expected': listed[key], 'actual': got})

    out = {
        'manifest': str(MANIFEST.relative_to(R)),
        'package_root': str(R),
        'entries_listed': len(listed),
        'files_on_disk': len(on_disk),
        'missing': missing,
        'unlisted': unlisted,
        'changed': changed,
        'status': 'PASS' if not (missing or unlisted or changed) else 'FAIL',
    }
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print('manifest entries : {0}'.format(out['entries_listed']))
        print('files on disk    : {0}'.format(out['files_on_disk']))
        print('missing          : {0}'.format(len(missing)))
        print('changed          : {0}'.format(len(changed)))
        print('unlisted         : {0}'.format(len(unlisted)))
        for m in missing[:20]:
            print('  MISSING  {0}'.format(m))
        for c in changed[:20]:
            print('  CHANGED  {0}'.format(c['path']))
        for u in unlisted[:20]:
            print('  UNLISTED {0}'.format(u))
        print(out['status'])
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
