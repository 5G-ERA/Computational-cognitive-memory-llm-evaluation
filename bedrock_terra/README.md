# Bedrock arm — pre-flight overlay (v0.5.1)

Working overlay for adding Bedrock arms to the frozen v0.5.1 benchmark.
**`release_qa1c/` is never written to.** Everything here reads it read-only.

Arms proposed: **GPT-5.6 Terra** (frontier) and **Qwen3 Next 80B** (open-weight,
carries the frozen `temperature: 0` determinism clause).

## Run order

```bash
export AWS_BEARER_TOKEN_BEDROCK='<long-term Bedrock API key>'

# 1. Validate the request shape with no network and no key
python3 probe_bedrock.py --config config/model_terra_bedrock.json --dry-run

# 2. Measure (~15 calls, a few cents, DEVELOPMENT split only)
python3 probe_bedrock.py --config config/model_terra_bedrock.json

# 3. Resolve the Qwen3 model id from probe P0 output, write it into
#    config/model_qwen3_bedrock.json, then repeat
python3 probe_bedrock.py --config config/model_qwen3_bedrock.json
```

Results land in `out/probe_<config>.json` (full evidence) and
`out/probe_<config>.md` (table for the note to Renxi).

## What the probes settle

| Probe | Question | Consequence if it fails |
|---|---|---|
| P0 | Which model ids does this account serve? | Wrong id → 404; also the version pin for the freeze record |
| P1 | Is the `system` message respected? (gate A1) | Silently dropped → 0% JSON, the exact gpuedge defect |
| P2 | Is `response_format` accepted? (gate A2) | AWS docs say structured outputs are unsupported for Terra; expect ignore/reject, which **preserves** the frozen `structured_output: false` |
| P3 | Are `temperature` / `top_p` / `seed` accepted? | Rejected → the frozen determinism clause needs a declared amendment for that arm |
| P4 | Which output-ceiling field bites? | `max_tokens` ignored → the 4096 ceiling silently disappears; output is billed at 10x quota burndown |
| P5 | How does reasoning come back? | Marker list in `extraction_policy.json` is Kimi-specific and must be re-derived per arm (this is defect 001's root cause) |
| P6 | Statelessness across calls | State leakage invalidates the independence assumption |
| P7 | Is `reasoning_effort` accepted, at what token cost? | A **new** frozen parameter with no Kimi analogue. Judge the measured output distribution against `baseline_kimi.json`: the frozen 4096 ceiling already truncated **4.0% (58/1440)** of Kimi calls, so an arm that reasons more will truncate more |
| P8 | Does a real dev call survive the frozen parser? | End-to-end confirmation before spending the split |

## Files

- `config/model_terra_bedrock.json` — Terra arm. Fields left `null` /
  `PENDING_PROBE` are deliberately unset; the probes resolve them. Do not fill
  them in by hand.
- `config/model_qwen3_bedrock.json` — Qwen3 arm. Model id intentionally not
  hard-coded: it was never verified against a live listing.
- `adapters/bedrock_openai_adapter.py` — drop-in for
  `OpenAICompatibleAdapterQA1` (same `Cls(cfg)` / `invoke(call)` contract, so
  `scripts/api_runner_qa1.py` takes it unchanged). Configurable ceiling field,
  opt-in sampling params, and reasoning kept **out** of `assistant_text`.
- `probe_bedrock.py` — the probes above.

## Decisions for Renxi — fill in from measured results, do not pre-empt

| # | Decision | Depends on |
|---|---|---|
| 1 | Determinism: preserve on Qwen3, declare amendment on Terra? | P3 |
| 2 | `reasoning_effort` value to freeze | P7 + a dev sweep judged on **JSON validity and truncation rate**, never on B1−B0 |
| 3 | One primary per arm (two pre-registered replications) vs pooled with model as a factor | statistical, not measurable |
| 4 | Global CRIS routing for both arms — any Bedfordshire residency requirement? | governance |

Decision 2 carries the same hazard as defect D3 in benchmark v3.2: choosing a
knob on a criterion aligned with our own hypothesis. Judge it on validity and
truncation only, and record how it was chosen.

## Not in scope here

The Kimi reserved result stays as published: sealed, signed, positive
(B1−B0 = +9.79 pp, 95% CI [5.00, 14.79]). These arms are pre-registered
replications, not a replacement.
