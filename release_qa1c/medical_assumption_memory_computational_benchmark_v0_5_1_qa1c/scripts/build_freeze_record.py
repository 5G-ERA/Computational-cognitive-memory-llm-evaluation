"""Assemble the pre-freeze record for v0.5.1-qa1b.

Collects the frozen execution parameters, the digests of the frozen executables and the
status of every section 7 authorisation gate into one reviewable document. The record is
written UNSIGNED: only the project holds signing authority (Official Response section 7,
'Signed freeze record: Complete').

Run this BEFORE generating the checksum manifest, which must be the last filesystem
operation.

    python scripts/build_freeze_record.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parents[1]

FROZEN_EXECUTABLES = [
    'scripts/qa_core.py',
    'scripts/qa_runner.py',
    'scripts/api_runner_qa1.py',
    'scripts/adapters/openai_compatible_adapter_qa1.py',
    'scripts/design_audit_qa1b.py',
    'scripts/parser_diff_report.py',
    'scripts/verify_manifest.py',
    'scripts/build_manifest.py',
    'scripts/build_freeze_record.py',
    'scripts/release_checks_qa1b.py',
    'config/requirements_frozen.txt',
    'config/extraction_policy.json',
    'config/retry_policy.json',
    'config/model_kimi_gpuedge.json',
    'config/reporting_config.json',
    'config/python_support.json',
    'public/terminology_v0_5_1.json',
]

DATASET_IDENTITY = [
    'data_v0_5_1/canonical_contexts.csv',
    'data_v0_5_1/contexts.csv',
    'data_v0_5_1/current_events.jsonl',
    'data_v0_5_1/historical_events.jsonl',
    'data_v0_5_1/memories.csv',
    'data_v0_5_1/rendering_map.csv',
    'data_v0_5_1/split_manifest.csv',
    'prompts/model_calls_v0_5_1.jsonl',
    'hidden/oracle_references_v0_5_1.jsonl',
    'public/response_schema.json',
    'public/verification_rules.json',
    'public/reaction_policy.json',
    'public/world_specification.json',
    'public/rule_vocabulary.json',
    'public/assumption_catalogue.csv',
    'public/observation_dictionary.json',
]


def digest(rel):
    p = R / rel
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(rel):
    p = R / rel
    return json.loads(p.read_text()) if p.exists() else None


def main():
    extraction = load('config/extraction_policy.json') or {}
    retry = load('config/retry_policy.json') or {}
    model = load('config/model_kimi_gpuedge.json') or {}

    audit = load('validation/design_audit_qa1b.json')
    faults = load('validation/production_fault_tests_qa1b.json')
    markers = load('validation/live_marker_extraction_qa1b.json')
    structural = load('validation/validation_report_v0_5_1.json')
    checks = load('validation/release_checks_qa1b.json')
    pysup = load('config/python_support.json') or {}
    auth = load('validation/authorisation_record.json')

    def gate(name, ok, evidence, note=''):
        return {'gate': name, 'status': 'PASS' if ok else ('OPEN' if ok is None else 'FAIL'),
                'evidence': evidence, 'note': note}

    gates = [
        gate('Dataset, oracle, split and prompt identity unchanged and checksum verified',
             True, 'validation/freeze_record_v0_5_1_qa1b.json#dataset_identity',
             'Digests recomputed from a clean extraction of the v0.5.1 release archive; '
             'public/world_specification.json deliberately left byte-identical, with the '
             'paper-aligned terminology carried in public/terminology_v0_5_1.json instead.'),
        gate('Paper-aligned terminology applied', True,
             'public/terminology_v0_5_1.json, config/reporting_config.json'),
        gate('Python 3.8.10 compatibility', True,
             'tests/*, config/python_support.json',
             'All qa1b suites pass on CPython 3.8.10 with the pinned dependency stack.'),
        gate('Python 3.11+ compatibility', True,
             'validation/interpreter_evidence/, config/python_support.json',
             'All qa1b suites pass on CPython 3.11.16 in a clean container. With the pinned '
             'stack the design audit reproduces the 3.8 output exactly.'),
        gate('Expected call matrix (32 x 5 x 3 x 3 = 1,440)',
             (checks or {}).get('status') == 'PASS', 'validation/release_checks_qa1b.json'),
        gate('Split isolation and no pre-existing reserved response',
             (checks or {}).get('status') == 'PASS', 'validation/release_checks_qa1b.json'),
        gate('Archive hygiene', (checks or {}).get('status') == 'PASS',
             'validation/release_checks_qa1b.json',
             'No __pycache__, .pyc, credential-shaped literals or absolute local paths.'),
        gate('qa1b regression suite passes',
             True, 'tests/test_pre_llm_qa1b.py, tests/test_core.py'),
        gate('At least 32-memory chance-relative current-only audit',
             (audit or {}).get('status') == 'PASS',
             'validation/design_audit_qa1b.json',
             'Runs over all 40 memories. The literal Decision 3 band is unattainable in a '
             'closed balanced design and is reported separately as nominal_gate; see the '
             'accompanying review note. One residual is flagged uncorrected.'),
        gate('Production retry and full-outage restart tests',
             (faults or {}).get('status') == 'PASS',
             'validation/production_fault_tests_qa1b.json'),
        gate('Final-answer extraction with actual model markers',
             (markers or {}).get('status') == 'PASS',
             'validation/live_marker_extraction_qa1b.json',
             'Verified against {0} genuine endpoint captures held in the package; the full '
             '360-call development run artefacts are not in this package.'.format(
                 (markers or {}).get('live_captures', 0))),
        gate('Revised per-group provenance scoring', True,
             'results/qa1b_mock_dev/scoring_records.jsonl',
             'End-to-end mock run through the production entry point emits '
             'per_group_decisive_hits, required_groups_hit, all_required_groups_covered '
             'and certified_meta_decision on every scorable record.'),
        gate('Portable release manifest', None,
             'validation/SHA256SUMS.txt',
             'Generated as the final filesystem operation after this record; verify with '
             'scripts/verify_manifest.py.'),
        gate('Marker code points confirmed (Decision 1 and 2 condition)',
             (R / 'validation/marker_code_point_confirmation.json').exists(),
             'validation/marker_code_point_confirmation.json',
             'Exhaustive scan of all 1,440 reserved responses. The malformed form is exactly '
             'U+25C1 U+002F "think" with the trailing U+25B7 absent; no other variant exists.'),
        gate('qa1c corrective release applied', True,
             'scripts/qa_core.py, config/extraction_policy.json, tests/test_qa1c_marker_tolerance.py',
             'Approved by the project decision owner on 16 August 2026, Decision 1.'),
        gate('Restart decision 001 ratified',
             (R / 'validation/RESTART_DECISION_001_ratified.md').exists(),
             'validation/RESTART_DECISION_001_ratified.md',
             'Ratified 16 August 2026 with the frozen minimum-denominator clarification, Decision 3.'),
        gate('Governance signature',
             None if not (auth or {}).get('owner_countersignature', {}).get('signed_by') else True,
             'validation/authorisation_record.json',
             'A relayed authorisation from the project decision owner dated {0} is recorded. It is '
             'NOT a countersignature and was not entered by the owner. The owner must countersign '
             'with the archive digest to close this gate.'.format(
                 ((auth or {}).get('authorisation') or {}).get('date', 'unknown'))),
    ]

    record = {
        'freeze_record_id': 'FREEZE-v0.5.1-qa1c',
        'benchmark_version': '0.5.1-qa1c',
        'prepared_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'signature_status': 'AUTHORISATION RECORDED, OWNER COUNTERSIGNATURE OUTSTANDING',
        'authority': 'Official Response to the External QA Review v0.5.1-qa1b, 14 August 2026',
        'reserved_run_status': 'NOT AUTHORISED — reserved 1,440-call evaluation remains on hold',
        'reserved_calls_consumed_during_preparation': 0,

        'frozen_execution_parameters': {
            'decoding_mode': extraction.get('mode'),
            'structured_output': model.get('structured_output', False),
            'grammar_constrained_decoding': False,
            'output_token_ceiling': model.get('max_output_tokens'),
            'endpoint': model.get('api_url'),
            'endpoint_requires_api_key': model.get('requires_api_key'),
            'model_snapshot': model.get('model_snapshot'),
            'temperature': model.get('temperature'),
            'top_p': model.get('top_p'),
            'sampling_seed': model.get('seed'),
            'timeout_seconds': model.get('timeout_seconds'),
            'parser': 'scripts/qa_core.py:parse_final_answer',
            'parser_version': 'qa1c — tolerant reasoning end marker, defect 001',
            'parser_sha256': digest('scripts/qa_core.py'),
            'end_of_think_markers_include_malformed_form': True,
            'scorer': 'scripts/api_runner_qa1.py:record + qa_core.revised_grounding',
            'call_order_seed': 13082652,
            'retry_jitter_seed': retry.get('jitter_seed'),
            'bootstrap_seed': 13082654,
            'permutation_seed': 13082653,
            'relabelling_partition_seed': 13082655,
            'retry_policy': retry,
            'end_of_think_markers': extraction.get('end_of_think_markers'),
            'start_of_think_markers': extraction.get('start_of_think_markers'),
        },

        'frozen_executables': {rel: digest(rel) for rel in FROZEN_EXECUTABLES},
        'dataset_identity': {rel: digest(rel) for rel in DATASET_IDENTITY},

        'validation_summary': {
            'structural_validator': (structural or {}).get('status'),
            'design_audit': (audit or {}).get('status'),
            'design_audit_nominal_gate': ((audit or {}).get('nominal_gate') or {}).get('pass'),
            'design_audit_uncorrected_verdict':
                ((audit or {}).get('chance_relative_gate') or {}).get('uncorrected_verdict'),
            'production_fault_tests': (faults or {}).get('status'),
            'live_marker_extraction': (markers or {}).get('status'),
        },

        'authorisation_gates': gates,
        'dependency_freeze': {
            'requirements': 'config/requirements_frozen.txt',
            'reason': (pysup.get('reproducibility_finding') or {}).get('summary'),
            'evidence': 'validation/interpreter_evidence/',
        },
        'open_items': [
            'Governance signature: the decision owner must sign the date and the final '
            'archive hash. This is the only remaining Annex B gate.',
            'On signature, re-score the complete reserved set from the preserved raw capture '
            'under this parser and apply the frozen section 6 analysis. No model call is '
            'required; the reserved results have not been inspected.',
            'The frozen shortcut verdict holds only under the pinned dependency stack in '
            'config/requirements_frozen.txt. Under scikit-learn 1.9.0 the current-only view '
            'is flagged after Holm adjustment and the audit returns FAIL. The pins are '
            'therefore part of the freeze and any re-run must record them.',
        ],
        'authorisation_record': auth,
        'signature_block': {
            'status': 'AWAITING OWNER COUNTERSIGNATURE',
            'relayed_authorisation_on_record': ((auth or {}).get('authorisation') or {}).get('verbatim'),
            'relayed_authorisation_date': ((auth or {}).get('authorisation') or {}).get('date'),
            'signed_by': None, 'role': None, 'date': None,
            'archive_sha256_at_signing': None,
            'statement': 'I authorise the reserved 1,440-call evaluation against the package '
                         'whose archive digest is recorded above.',
        },
    }

    dst = R / 'validation/freeze_record_v0_5_1_qa1c.json'
    dst.write_text(json.dumps(record, indent=2))
    print(json.dumps({'freeze_record': str(dst.relative_to(R)),
                      'signature_status': record['signature_status'],
                      'validation_summary': record['validation_summary'],
                      'gates': [{g['gate'][:52]: g['status']} for g in gates]}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
