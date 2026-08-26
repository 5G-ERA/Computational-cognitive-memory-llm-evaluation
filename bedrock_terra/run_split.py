#!/usr/bin/env python3
"""Execute a named split through the FROZEN runner and scorer.

Deliberately does not reimplement any scoring. It executes the release's own
scripts/api_runner_qa1.py verbatim, injecting only the Bedrock adapter in place
of OpenAICompatibleAdapterQA1 via sys.modules. Nothing in the release is
modified and no scoring logic is duplicated, so the numbers are produced by
exactly the code that produced the sealed Kimi results.

  python3 run_dev_split.py --config config/model_terra_bedrock.json --output out/dev_terra
"""
from __future__ import annotations
import argparse, json, sys, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELEASE = (HERE.parent / 'release_qa1c'
           / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1c')

ap = argparse.ArgumentParser()
ap.add_argument('--config', required=True)
ap.add_argument('--output', required=True)
ap.add_argument('--limit', type=int)
ap.add_argument('--split', default='development', choices=['development','reserved'])
a = ap.parse_args()

sys.dont_write_bytecode = True
# Only the release goes on sys.path: `adapters` must resolve to ITS package, or
# the frozen runner cannot find adapters.mock_adapter. The Bedrock adapter is
# loaded by file path instead, so the two packages never collide.
# Python auto-adds this script's own directory to sys.path. Our adapters/ has an
# __init__.py, making it a REGULAR package that shadows the release's namespace
# package of the same name - which is why `adapters.mock_adapter` was unfindable.
# Drop our directory from the path entirely.
sys.path = [q for q in sys.path if q and Path(q).resolve() != HERE]
sys.path.insert(0, str(RELEASE / 'scripts'))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    'dca_bedrock_adapter', HERE / 'adapters' / 'bedrock_openai_adapter.py')
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
BedrockOpenAIAdapter, BudgetExceeded = _mod.BedrockOpenAIAdapter, _mod.BudgetExceeded

import adapters as _release_adapters          # the release's own package
shim = types.ModuleType('adapters.openai_compatible_adapter_qa1')
shim.OpenAICompatibleAdapterQA1 = BedrockOpenAIAdapter
sys.modules['adapters.openai_compatible_adapter_qa1'] = shim

runner = RELEASE / 'scripts/api_runner_qa1.py'
sys.argv = ['api_runner_qa1.py', '--config', a.config,
            '--split', a.split, '--output', a.output]
if a.limit:
    sys.argv += ['--limit', str(a.limit)]

print('runner congelado : %s' % runner)
print('adaptador        : BedrockOpenAIAdapter (inyectado)')
print('split            : %s\n' % a.split)

try:
    exec(compile(runner.read_text(), str(runner), 'exec'),
         {'__name__': '__main__', '__file__': str(runner)})
except BudgetExceeded as e:
    print('\n%s' % e); sys.exit(2)
except SystemExit as e:
    sys.exit(e.code)
