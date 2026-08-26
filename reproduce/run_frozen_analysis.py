#!/usr/bin/env python3
"""Run the frozen Experiment 1 analysis pipeline from this repository.

`bedrock_terra/analysis_dev_arm.py` is the frozen analysis entry point,
but it locates the signed statistical module (`analysis_section6.py`)
through an absolute path from the original execution machine. This
wrapper redirects that path to the byte-identical copy stored in this
repository (`analysis/analysis_section6.py`, same SHA-256) and changes
nothing else: parsing, scoring, seal handling, clustered bootstrap
(10,000 replicates, seed 13082654) all run exactly as frozen.

It re-derives the reserved results from the raw terminal captures — no
model calls, no network. Requires numpy.

Usage:
    python3 reproduce/run_frozen_analysis.py out/reserved_qwen3 qwen3
    python3 reproduce/run_frozen_analysis.py out/reserved_terra terra

(run paths are relative to bedrock_terra/, as in the frozen tooling; an
output JSON path may be given as a third argument)
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    run, arm = sys.argv[1], sys.argv[2]

    spec = importlib.util.spec_from_file_location(
        'analysis_dev_arm', ROOT / 'bedrock_terra' / 'analysis_dev_arm.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    frozen_copy = ROOT / 'analysis' / 'analysis_section6.py'
    mod.FROZEN_ANALYSIS = frozen_copy
    print(f'FROZEN_ANALYSIS redirected to in-repo copy: {frozen_copy}')

    argv = ['analysis_dev_arm.py', '--run', run, '--arm', arm]
    if len(sys.argv) > 3:
        argv += ['--output', sys.argv[3]]
    import os
    os.chdir(ROOT / 'bedrock_terra')
    sys.argv = argv
    return mod.main()


if __name__ == '__main__':
    sys.exit(main())
