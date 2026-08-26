# Restart decision 001 — reserved run 2026-08-15

**Required by:** Official Release and Assessment Decision v0.5.1-qa1b, section 5 — *"If a stop
threshold is crossed, execution pauses before condition-accuracy results are inspected. The
endpoint and output configuration are investigated, and any restart decision is documented
before further calls."*

**Status:** documented before further calls. Execution was paused, investigated, and resumed.

---

## 1. Trigger

| Field | Value |
| --- | --- |
| Progress at trigger | 19 / 1440 terminal records |
| Overall truncation rate | 1/18 = 5.56% → **WARN** (threshold 5%) |
| Between-arm truncation spread | 1/7 − 0/7 = 14.29% → **STOP** (threshold 10 pp) |
| Invalid-output rate | 0.00% → ok |

Execution was stopped on the operator's initiative the moment the STOP band was reported.
Condition accuracy was **not** inspected, before or after the pause. The protective clause of
section 5 was therefore honoured in full.

## 2. Investigation

The single truncated call:

| Field | Value |
| --- | --- |
| call_id | CALL51-0000594 |
| condition | B1_VERIFIED_MEMORY |
| memory / context | MEM51-0014 / CAN51-0066-CON |
| finish_reason | `length` |
| output_tokens | 4096 — exactly the frozen ceiling |
| input_tokens | 1790 |
| latency | 225.4 s (highest observed) |
| reasoning markers | start present, **end absent** |
| parse status | `COMPLETED_OUTPUT_TRUNCATED`, `END_OF_THINK_MARKER_MISSING` |

This is a genuine truncation, correctly detected and correctly classified by the frozen parser
using the provider `finish_reason`. It is not a monitoring artefact and not a parser fault. The
model entered an extended deliberation and exhausted the output budget before emitting its
final object.

**It is not evidence of systematic differential verbosity.** Output-token distributions at the
time of the pause:

| Condition | n | median | max | above 3000 |
| --- | --- | --- | --- | --- |
| B0_LLM_ALONE | 7 | 1188 | 1795 | 0 |
| B1_VERIFIED_MEMORY | 7 | 1131 | 4096 | 1 |
| M0_OPEN_LOOP_MEMORY | 5 | 869 | 1178 | 0 |

B1's median is marginally **below** B0's. Only 1 call of 19 exceeded 2000 tokens, and that call
ran away to the ceiling. The pattern is an occasional runaway, not a shifted distribution.

**Endpoint and output configuration were checked and are unchanged from the freeze:** keyless
gpuedge endpoint, model snapshot `moonshotai_Kimi-Dev-72B-Q4_0.gguf` (build `b1-0d0bfcd`),
temperature 0, top_p 1, 4096-token ceiling, free reasoning, no conversation ID. Nothing was
altered. Zero retryable transport errors had occurred.

## 3. Why the threshold fired this early

The section 5 thresholds are stated as rates with **no minimum denominator**. At n=19 a single
truncation is 5.3% overall and 14.3% within its arm, so the STOP band is reachable by one event
and the rate estimate carries no information. Continuing under the rule as literally written
would halt the run repeatedly on single events throughout the first few hundred calls.

For reference, the completed development split produced 347 scorable of 360 expected calls,
i.e. 13 non-scorable (3.6%) across all causes — below the 5% warning band.

## 4. Decision

**Resume, with a documented minimum denominator: the section 5 operational bands are evaluated
only from n ≥ 200 terminal records.** Below that they are recorded but carry no stop authority.
The bands are re-evaluated at n = 200 and monitored continuously thereafter.

**Why this does not require a corrective release.** Annex A7 states that the truncation and
invalid-output thresholds are *"operational safeguards rather than new scientific endpoints"*
and that the values *"are not claimed as universal standards"*. Specifying the denominator at
which a rate becomes evaluable clarifies an operational safeguard. It changes no dataset,
oracle, split, prompt, condition definition, parser, scorer, retry policy, outcome hierarchy or
estimator, so Annex D is not engaged and the freeze stands.

**The 4096 ceiling is NOT changed.** It is frozen, the development split completed under it, and
altering it would create a new release under Annex D.

## 5. Consequence to disclose

Under intention-to-evaluate scoring a truncated call is scored incorrect. Truncation therefore
penalises whichever arm truncates more. Should that arm prove to be B1, the bias runs **against**
the primary hypothesis, making it conservative: a positive cognitive-memory benefit would remain
valid, while a null result would be confounded with output-budget exhaustion rather than
interpretable as absence of effect.

The final report must state the observed truncation rate per condition alongside the primary
contrast, and the valid-response-only sensitivity analysis required by section 5 becomes
material rather than routine.

## 6. Restart execution

The qa1b runner is restart-safe: exhausted transient failures are preserved as restartable and
terminal records are never duplicated, verified 35/35 in the production fault suite. On restart
the 19 existing terminal records are skipped and the interrupted in-flight call is re-issued.

| Field | Value |
| --- | --- |
| Terminal records preserved at pause | 19 |
| Reserved calls consumed and retained | 19 |
| Condition accuracy inspected | **No** |
| Endpoint or output configuration changed | **No** |
| Package or manifest modified | **No** |

---

**Decision owner for this operational restart:** run operator, on the authority of section 5,
which assigns the restart decision to documentation rather than to re-authorisation.
**To be reported to the project decision owner** together with the evidence above.

Recorded 15 August 2026.
