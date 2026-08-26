# Medical Assumption Memory Computational Benchmark v0.4.2

## Purpose

Given a disclosed synthetic medicines-support world, test whether verified cognitive memory improves an external LLM's recovery of oracle-defined reactions.

## Conditions

- B0: public rules plus raw longitudinal and current evidence
- M0: B0 plus a prospective assumption and expected consequence
- B1: M0 plus verified relational cognitive memory

## Quick start

```bash
python scripts/validate.py
python tests/test_core.py
python scripts/api_runner.py --config config/model_config.example.json --split development --output results/my_run
python scripts/calculate_metrics.py --run results/my_run --output results/my_run/metrics.json
python scripts/bootstrap_kpis.py --run results/my_run --output results/my_run/bootstrap.json
```

The example configuration uses the mock oracle adapter to verify the complete execution and scoring pipeline. Set `provider` to `openai_compatible`, provide an API URL, and export the configured API-key environment variable for an external endpoint.

Correctness is computational, not medical.
