# Experiment 1 audit extension — audit report

Run label: **dev_terra**  
Parent release: v0.5.1-qa1c  
Ontology: AUDIT-ONT-1.2  
Memory groups: 8  Expected calls: 360

Decision performance is not read anywhere in this report. The audit pipeline cannot open
the hidden reaction, the hidden rule, the correctness label or the scoring records; the
oracle guard in scripts/auditlib.py exits rather than read them.

**Terminology.** Per decision B10, *audit conformity* is reserved for theory equation
(36), the lifecycle certificate test, and is not used here. The Level 1 outcome is
**Input-output trace reconstructibility**; the Level 2 outcome is
**Cognitive-trace coherence**; the section 13 reconstructibility metric is
**Functional auditability**.

**Readings.** Per decision A5, **SCOPED is normative** and LITERAL is a declared
sensitivity that must never appear as a headline figure. SCOPED excludes canonical fields
the parent release does not record; LITERAL counts them as missing components.

**Mandatory caveats.**

- Memory-clustered bootstrap intervals under-cover at these cluster counts. The parent release's own coverage study puts 8-cluster coverage near 89.6 percent and 32-cluster coverage near 92.5 percent against a nominal 95 percent. Every audit interval carries the same disclosure the decision results carry.
- Level 1 sits at a ceiling by construction on this parent release and is reported as an instrument-integrity endpoint.
- No independent reimplementation of the audit was produced. Protocol section 17 was removed for Experiment 1 by decision E1-G1 of 22 August 2026, so every figure reported here rests on a single implementation. Fixture agreement, canonicalisation tests and the oracle-independence clean-room test constrain that implementation, but none of them establishes independence from one implementer's reading of the contracts.
- The audit is deterministic by design and takes no human input at any stage. It therefore does not assess substantive citation relevance, material scope overreach beyond its frozen pattern, omitted limitations, or the adequacy of free-text explanation. Those properties are out of scope, not unmeasured pending work. What is reported is exactly what a frozen contract can decide from the retained artefacts.

## 1. Condition metrics (protocol section 13)

### Reading: SCOPED (NORMATIVE)

| level | condition           | expected | audit coverage | functional auditability | trace reconstructibility / coherence | critical rate |
|-------|---------------------|----------|----------------|-------------------------|--------------------------------------|---------------|
| L1_IO | B0_LLM_ALONE        | 120      | 100.00%        | 100.00%                 | 99.17%                               | 0.00%         |
| L1_IO | M0_OPEN_LOOP_MEMORY | 120      | 100.00%        | 100.00%                 | 99.17%                               | 0.00%         |
| L1_IO | B1_VERIFIED_MEMORY  | 120      | 100.00%        | 100.00%                 | 100.00%                              | 0.00%         |
| L2_M0 | M0_OPEN_LOOP_MEMORY | 120      | 100.00%        | 100.00%                 | 100.00%                              | 0.00%         |
| L2_B1 | B1_VERIFIED_MEMORY  | 120      | 100.00%        | 100.00%                 | 100.00%                              | 0.00%         |
| L2_B0 | B0_LLM_ALONE        | 120      | 0.00%          | 0.00%                   | 0.00%                                | 0.00%         |

### Reading: LITERAL (SENSITIVITY ONLY)

| level | condition           | expected | audit coverage | functional auditability | trace reconstructibility / coherence | critical rate |
|-------|---------------------|----------|----------------|-------------------------|--------------------------------------|---------------|
| L1_IO | B0_LLM_ALONE        | 120      | 100.00%        | 100.00%                 | 99.17%                               | 0.00%         |
| L1_IO | M0_OPEN_LOOP_MEMORY | 120      | 100.00%        | 100.00%                 | 99.17%                               | 0.00%         |
| L1_IO | B1_VERIFIED_MEMORY  | 120      | 100.00%        | 100.00%                 | 100.00%                              | 0.00%         |
| L2_M0 | M0_OPEN_LOOP_MEMORY | 120      | 100.00%        | 100.00%                 | 0.00%                                | 0.00%         |
| L2_B1 | B1_VERIFIED_MEMORY  | 120      | 100.00%        | 0.00%                   | 0.00%                                | 100.00%       |
| L2_B0 | B0_LLM_ALONE        | 120      | 0.00%          | 0.00%                   | 0.00%                                | 0.00%         |

## 2. Contrasts (protocol section 13, equations 6-8)

Paired memory-clustered bootstrap, 10,000 resamples, two-sided 95% percentile interval.
Percentage points. **No contrast in this table is confirmatory.** Per decision A2 the
Level 1 differences are instrument-integrity endpoints; per decision A4 equation (7) is
withdrawn from the confirmatory set and the Level 2 result is carried by
`audit_release_integrity.csv`, not by this table.

### Reading: SCOPED

| contrast                            | role                 | point      | 95% interval   | clusters | usable resamples |
|-------------------------------------|----------------------|------------|----------------|----------|------------------|
| delta_IO_B1_minus_B0                | INSTRUMENT_INTEGRITY | +0.83      | [+0.00, +2.50] | 8        | 10000            |
| delta_IO_M0_minus_B0                | INSTRUMENT_INTEGRITY | +0.00      | [-2.50, +2.50] | 8        | 10000            |
| delta_Trace_B1_minus_M0             | WITHDRAWN            | +0.00      | [+0.00, +0.00] | 8        | 10000            |
| delta_Critical_B1_minus_M0          | DESCRIPTIVE          | +0.00      | [+0.00, +0.00] | 8        | 10000            |
| delta_IO_B1_minus_B0_permutation    | ROBUSTNESS           | p = 1.0000 | |obs| = 0.83   | 8        |                  |
| delta_Trace_B1_minus_M0_permutation | ROBUSTNESS           | p = 1.0000 | |obs| = 0.00   | 8        |                  |

### Reading: LITERAL

| contrast                            | role                 | point      | 95% interval       | clusters | usable resamples |
|-------------------------------------|----------------------|------------|--------------------|----------|------------------|
| delta_IO_B1_minus_B0                | INSTRUMENT_INTEGRITY | +0.83      | [+0.00, +2.50]     | 8        | 10000            |
| delta_IO_M0_minus_B0                | INSTRUMENT_INTEGRITY | +0.00      | [-2.50, +2.50]     | 8        | 10000            |
| delta_Trace_B1_minus_M0             | WITHDRAWN            | +0.00      | [+0.00, +0.00]     | 8        | 10000            |
| delta_Critical_B1_minus_M0          | DESCRIPTIVE          | +100.00    | [+100.00, +100.00] | 8        | 10000            |
| delta_IO_B1_minus_B0_permutation    | ROBUSTNESS           | p = 1.0000 | |obs| = 0.83       | 8        |                  |
| delta_Trace_B1_minus_M0_permutation | ROBUSTNESS           | p = 1.0000 | |obs| = 0.00       | 8        |                  |

## 3. Parent-domain prevalence (descriptive)

| reading | level | domain | findings |
|---------|-------|--------|----------|
| BOTH    | L1_IO | E1     | 2        |
| BOTH    | L1_IO | E4     | 360      |
| LITERAL | L2_B1 | E2     | 360      |
| LITERAL | L2_B1 | E3     | 240      |
| LITERAL | L2_B1 | E4     | 120      |
| LITERAL | L2_B1 | E5     | 120      |
| LITERAL | L2_M0 | E1     | 120      |
| LITERAL | L2_M0 | E3     | 720      |
| LITERAL | L2_M0 | E5     | 120      |

## 4. Root causes (primary code only, protocol section 11)

| reading | level | condition           | primary code                    | cases |
|---------|-------|---------------------|---------------------------------|-------|
| LITERAL | L1_IO | B0_LLM_ALONE        | E1_CURRENT_GROUNDS_MISSING      | 1     |
| LITERAL | L1_IO | B0_LLM_ALONE        | E4_INFLUENCE_UNEXPLAINED        | 119   |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E1_CURRENT_GROUNDS_MISSING      | 1     |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E4_INFLUENCE_UNEXPLAINED        | 119   |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E4_INFLUENCE_UNEXPLAINED        | 120   |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E4_INFLUENCE_UNEXPLAINED        | 120   |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E1_CURRENT_GROUNDS_MISSING      | 1     |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E4_INFLUENCE_UNEXPLAINED        | 119   |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E1_CURRENT_GROUNDS_MISSING      | 1     |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E4_INFLUENCE_UNEXPLAINED        | 119   |
| LITERAL | L2_B1 | B1_VERIFIED_MEMORY  | E2_CAPABILITY_MISATTRIBUTION    | 120   |
| LITERAL | L2_M0 | M0_OPEN_LOOP_MEMORY | E3_PROSPECTIVE_TRACE_INCOMPLETE | 120   |

## 5. Matched M0 to B1 trace-status transitions

| reading | M0 status     | B1 status              | cases |
|---------|---------------|------------------------|-------|
| LITERAL | NONCONFORMANT | NONCONFORMANT_CRITICAL | 120   |
| SCOPED  | CONFORMANT    | CONFORMANT             | 120   |

## 6. Release integrity (decision A4: the Level 2 result)

Level 2 reported once for the release, one row per memory, under the normative
SCOPED reading. Protocol equation (7) is withdrawn from the confirmatory set.

| memory     | M0 trace coherence | B1 trace coherence | B1 structural status           | partial prospective field stability |
|------------|--------------------|--------------------|--------------------------------|-------------------------------------|
| MEM51-0001 | CONFORMANT         | CONFORMANT         | -                              | STABLE                              |
| MEM51-0002 | CONFORMANT         | CONFORMANT         | -                              | STABLE                              |
| MEM51-0003 | CONFORMANT         | CONFORMANT         | -                              | STABLE                              |
| MEM51-0004 | CONFORMANT         | CONFORMANT         | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0005 | CONFORMANT         | CONFORMANT         | -                              | STABLE                              |
| MEM51-0006 | CONFORMANT         | CONFORMANT         | -                              | STABLE                              |
| MEM51-0007 | CONFORMANT         | CONFORMANT         | -                              | STABLE                              |
| MEM51-0008 | CONFORMANT         | CONFORMANT         | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |

Memories: 8. B1 structural statuses: - 6, UNRESOLVED_BY_CONDITION_DESIGN 2. Partial prospective field stability: STABLE 8.

Partial prospective field stability covers three of the five operands of
protocol equation (1); per decision B6 it does not establish that no silent
prospective rewrite occurred.

## 7. Existing-data reproducibility (protocol section 14)

Representation stability over 8 memories: prospective invariant **True**, resolved invariant **True**.

Cross-rendering response consistency (presentation stability, not repeated-call reproducibility):

| condition           | canonical contexts | reaction agreement | rule agreement | citation set exact | citation Jaccard |
|---------------------|--------------------|--------------------|----------------|--------------------|------------------|
| B0_LLM_ALONE        | 40                 | 95.00%             | 95.00%         | 85.00%             | 0.931            |
| B1_VERIFIED_MEMORY  | 40                 | 97.50%             | 97.50%         | 82.50%             | 0.947            |
| M0_OPEN_LOOP_MEMORY | 40                 | 100.00%            | 100.00%        | 82.50%             | 0.936            |

## 8. Reporting boundary

Prediction accuracy and audit results are joined only after both analyses are frozen
(protocol section 15). This report contains no accuracy figure and no join.

