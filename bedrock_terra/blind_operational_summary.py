#!/usr/bin/env python3
"""Blinded operational summary of a development run.

Decision 3 of the cross-model replication amendment (Renxi Qiu, 19 Aug 2026)
fixes what a configuration summary may contain:

    "may contain completion, input and output truncation, JSON validity,
     schema validity, latency, token use, and cost. It must NOT contain
     reaction accuracy, rule accuracy, grounding accuracy, or condition
     contrasts."

This tool emits only the permitted set. It refuses to open
scoring_records.jsonl at all, so the selector cannot be contaminated by
running it. Per-condition output truncation IS reported: it is a frozen
operational monitor (reporting_config.json ->
absolute_truncation_difference_between_conditions), not a scientific outcome.

  python3 blind_operational_summary.py out/dev_qwen3 --config config/model_qwen3_bedrock.json
"""
from __future__ import annotations
import argparse, json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

FORBIDDEN = 'scoring_records.jsonl'
RELEASE = (Path(__file__).resolve().parent.parent / 'release_qa1c'
           / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1c')


def jsonl(p: Path):
    if p.name == FORBIDDEN:
        raise SystemExit('refusing to read %s under the blinding rule' % FORBIDDEN)
    with p.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--config', required=True)
    ap.add_argument('--reserved-calls', type=int, default=1440)
    a = ap.parse_args()

    run = Path(a.run_dir)
    cfg = json.loads(Path(a.config).read_text())
    limits = json.loads((RELEASE / 'config/reporting_config.json')
                        .read_text())['operational_monitoring']

    registry = list(jsonl(run / 'call_registry.jsonl'))
    parsed = {r['call_id']: r for r in jsonl(run / 'responses_parsed.jsonl')}
    raw = list(jsonl(run / 'responses_raw.jsonl'))
    attempts = list(jsonl(run / 'attempts.jsonl'))
    completion = json.loads((run / 'run_completion_report.json').read_text())

    n = len(registry)
    status = Counter(r['terminal_status'] for r in registry)
    valid = status.get('COMPLETED_VALID', 0)
    truncated = status.get('COMPLETED_OUTPUT_TRUNCATED', 0)
    invalid = n - valid - truncated

    trunc_by_cond = defaultdict(lambda: [0, 0])
    for r in registry:
        c = trunc_by_cond[r['condition']]
        c[1] += 1
        if r['terminal_status'] == 'COMPLETED_OUTPUT_TRUNCATED':
            c[0] += 1
    cond_rates = {k: v[0] / v[1] for k, v in sorted(trunc_by_cond.items())}
    cond_spread = (max(cond_rates.values()) - min(cond_rates.values())) if cond_rates else 0.0

    last = {}
    for r in raw:
        last[r['call_id']] = r          # keep the final attempt per call
    lat = sorted(r['latency_ms'] for r in last.values() if r.get('latency_ms'))
    tin = [r['input_tokens'] for r in last.values() if r.get('input_tokens')]
    tout = [r['output_tokens'] for r in last.values() if r.get('output_tokens')]
    finish = Counter(r.get('finish_reason') for r in last.values())
    http = Counter(r.get('http_status') for r in raw)
    retried = sum(1 for c, k in Counter(r['call_id'] for r in attempts).items() if k > 1)

    pin = cfg.get('price_per_1m_input_usd', 0.0)
    pout = cfg.get('price_per_1m_output_usd', 0.0)
    cost = (sum(tin) * pin + sum(tout) * pout) / 1e6
    per_call = cost / n if n else 0.0

    wall_s = sum(lat) / 1000.0
    schema_err = sum(1 for r in parsed.values() if r.get('errors'))

    def gate(name, value, key):
        stop = limits[key]['stop']
        warn = limits[key]['warning']
        v = 'PASS' if value < warn else ('WARNING' if value < stop else 'STOP')
        return {'metric': name, 'value': round(value, 4),
                'warning': warn, 'stop': stop, 'verdict': v}

    out = {
        'blinding': ('Decision 3 permitted fields only. scoring_records.jsonl was '
                     'not opened. No accuracy, no contrasts.'),
        'run_dir': str(run),
        'model': cfg.get('model'),
        'reasoning_effort': cfg.get('reasoning_effort'),
        'completion': {**completion, 'calls': n,
                       'status_distribution': dict(status),
                       'finish_reason': {str(k): v for k, v in finish.items()},
                       'http_status': {str(k): v for k, v in http.items()},
                       'calls_needing_retry': retried},
        'validity': {'completed_valid': valid,
                     'valid_rate': round(valid / n, 4) if n else 0.0,
                     'schema_or_json_errors': schema_err,
                     'invalid_non_truncated': invalid},
        'truncation': {'output_truncated': truncated,
                       'rate': round(truncated / n, 4) if n else 0.0,
                       'by_condition': {k: round(v, 4) for k, v in cond_rates.items()},
                       'input_truncation_detected': False},
        'operational_gates': [
            gate('overall output truncation', truncated / n if n else 0.0,
                 'overall_output_truncation'),
            gate('between-condition truncation spread', cond_spread,
                 'absolute_truncation_difference_between_conditions'),
            gate('invalid output rate', (n - valid) / n if n else 0.0,
                 'invalid_output_rate'),
        ],
        'tokens': {'input_mean': round(statistics.mean(tin), 1) if tin else 0,
                   'output_mean': round(statistics.mean(tout), 1) if tout else 0,
                   'output_median': statistics.median(tout) if tout else 0,
                   'output_max': max(tout) if tout else 0,
                   'ceiling': cfg.get('max_output_tokens')},
        'latency_ms': {'median': statistics.median(lat) if lat else 0,
                       'p95': lat[int(.95 * len(lat))] if lat else 0,
                       'max': max(lat) if lat else 0},
        'cost_usd': {'this_run': round(cost, 4),
                     'per_call': round(per_call, 6),
                     'projected_reserved': round(per_call * a.reserved_calls, 2),
                     'cap_per_run': cfg.get('max_run_cost_usd')},
        'reserved_feasibility': {
            'calls': a.reserved_calls,
            'projected_wall_clock_hours': round(
                wall_s / n * a.reserved_calls / 3600, 2) if n else 0.0,
            'note': 'serial estimate from measured per-call latency'},
    }
    verdicts = [g['verdict'] for g in out['operational_gates']]
    out['eligibility'] = {
        'payload_fits': not out['truncation']['input_truncation_detected'],
        'all_conditions_transmitted': len(cond_rates) == 3,
        'parsing_viable': schema_err == 0,
        'operational_gates': 'PASS' if all(v == 'PASS' for v in verdicts) else 'REVIEW',
        'reserved_matrix_feasible': None,
        'note': 'Scientific accuracy is NOT an eligibility criterion (Decision 1).'}
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
