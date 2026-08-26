# Restart decision 001 — RATIFIED

**Ratified by the project decision owner, 16 August 2026 (Decision 3).**

The original record is `decisions/RESTART_DECISION_001.md` in the delivery folder. It is
ratified with the following frozen clarification, which now forms part of the release:

> **Frozen clarification.** Operational percentage warning and stopping thresholds are
> evaluated only after at least 200 terminal responses. Before that denominator, events are
> logged and reviewed descriptively but do not independently trigger a rate-based stop.

## Scope

This clarification applies to the section 5 operational monitoring thresholds only:

- overall output truncation (warning 5%, stop 10%)
- absolute truncation difference between conditions (warning 5 pp, stop 10 pp)
- invalid-output rate (warning 5%, stop 10%)

It does not alter the thresholds themselves, the dataset, oracle, split, prompts, condition
definitions, parser policy, retry policy, outcome hierarchy or estimator. Consistent with
Annex A7, which states that these thresholds are operational safeguards rather than scientific
endpoints and that the values are not claimed as universal standards.

## Why it was needed

The stop rule fired once during the reserved run, at 19 terminal responses, on a single
truncated reply. At that denominator one event is 5.3% overall and 14.3% within its arm, so the
stop band is reachable by a single event while the rate estimate carries no information.
Applied literally the run would have halted repeatedly through its first few hundred calls.

Execution was paused, the endpoint and output configuration were investigated and found
unchanged, the minimum denominator was documented, and the run resumed producing 1,440 unique
terminal records with no duplicates.

## Outcome across the completed run

The concern that prompted the original stop did not survive the full run. Genuine
output-budget truncation settled at 4.03% of 1,440 calls, close to the 3.6% non-scorable rate
observed on the development split, and the condition most exposed to it was the pre-specified
consequence mapping rather than cognitive memory. The between-arm spread after correction is
1.67%, inside the `ok` band. The 4,096-token ceiling was never changed.
