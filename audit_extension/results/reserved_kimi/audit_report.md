# Experiment 1 audit extension — audit report

Run label: **reserved_kimi**  
Parent release: v0.5.1-qa1c  
Ontology: AUDIT-ONT-1.2  
Memory groups: 32  Expected calls: 1440

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
| L1_IO | B0_LLM_ALONE        | 480      | 96.25%         | 96.25%                  | 74.58%                               | 0.00%         |
| L1_IO | M0_OPEN_LOOP_MEMORY | 480      | 95.00%         | 95.00%                  | 79.38%                               | 0.00%         |
| L1_IO | B1_VERIFIED_MEMORY  | 480      | 96.67%         | 96.67%                  | 78.33%                               | 0.00%         |
| L2_M0 | M0_OPEN_LOOP_MEMORY | 480      | 100.00%        | 100.00%                 | 100.00%                              | 0.00%         |
| L2_B1 | B1_VERIFIED_MEMORY  | 480      | 100.00%        | 100.00%                 | 84.79%                               | 0.00%         |
| L2_B0 | B0_LLM_ALONE        | 480      | 0.00%          | 0.00%                   | 0.00%                                | 0.00%         |

### Reading: LITERAL (SENSITIVITY ONLY)

| level | condition           | expected | audit coverage | functional auditability | trace reconstructibility / coherence | critical rate |
|-------|---------------------|----------|----------------|-------------------------|--------------------------------------|---------------|
| L1_IO | B0_LLM_ALONE        | 480      | 96.25%         | 96.25%                  | 74.58%                               | 0.00%         |
| L1_IO | M0_OPEN_LOOP_MEMORY | 480      | 95.00%         | 95.00%                  | 79.38%                               | 0.00%         |
| L1_IO | B1_VERIFIED_MEMORY  | 480      | 96.67%         | 96.67%                  | 78.33%                               | 0.00%         |
| L2_M0 | M0_OPEN_LOOP_MEMORY | 480      | 100.00%        | 100.00%                 | 0.00%                                | 0.00%         |
| L2_B1 | B1_VERIFIED_MEMORY  | 480      | 100.00%        | 0.00%                   | 0.00%                                | 100.00%       |
| L2_B0 | B0_LLM_ALONE        | 480      | 0.00%          | 0.00%                   | 0.00%                                | 0.00%         |

## 2. Contrasts (protocol section 13, equations 6-8)

Paired memory-clustered bootstrap, 10,000 resamples, two-sided 95% percentile interval.
Percentage points. **No contrast in this table is confirmatory.** Per decision A2 the
Level 1 differences are instrument-integrity endpoints; per decision A4 equation (7) is
withdrawn from the confirmatory set and the Level 2 result is carried by
`audit_release_integrity.csv`, not by this table.

### Reading: SCOPED

| contrast                            | role                 | point      | 95% interval     | clusters | usable resamples |
|-------------------------------------|----------------------|------------|------------------|----------|------------------|
| delta_IO_B1_minus_B0                | INSTRUMENT_INTEGRITY | +3.75      | [-1.46, +8.75]   | 32       | 10000            |
| delta_IO_M0_minus_B0                | INSTRUMENT_INTEGRITY | +4.79      | [+0.00, +9.38]   | 32       | 10000            |
| delta_Trace_B1_minus_M0             | WITHDRAWN            | -15.21     | [-18.33, -12.08] | 32       | 10000            |
| delta_Critical_B1_minus_M0          | DESCRIPTIVE          | +0.00      | [+0.00, +0.00]   | 32       | 10000            |
| delta_IO_B1_minus_B0_permutation    | ROBUSTNESS           | p = 0.1836 | |obs| = 3.75     | 32       |                  |
| delta_Trace_B1_minus_M0_permutation | ROBUSTNESS           | p = 0.0001 | |obs| = 15.21    | 32       |                  |

### Reading: LITERAL

| contrast                            | role                 | point      | 95% interval       | clusters | usable resamples |
|-------------------------------------|----------------------|------------|--------------------|----------|------------------|
| delta_IO_B1_minus_B0                | INSTRUMENT_INTEGRITY | +3.75      | [-1.46, +8.75]     | 32       | 10000            |
| delta_IO_M0_minus_B0                | INSTRUMENT_INTEGRITY | +4.79      | [+0.00, +9.38]     | 32       | 10000            |
| delta_Trace_B1_minus_M0             | WITHDRAWN            | +0.00      | [+0.00, +0.00]     | 32       | 10000            |
| delta_Critical_B1_minus_M0          | DESCRIPTIVE          | +100.00    | [+100.00, +100.00] | 32       | 10000            |
| delta_IO_B1_minus_B0_permutation    | ROBUSTNESS           | p = 0.1836 | |obs| = 3.75       | 32       |                  |
| delta_Trace_B1_minus_M0_permutation | ROBUSTNESS           | p = 1.0000 | |obs| = 0.00       | 32       |                  |

## 3. Parent-domain prevalence (descriptive)

| reading | level | domain | findings |
|---------|-------|--------|----------|
| BOTH    | L1_IO | E0     | 151      |
| BOTH    | L1_IO | E1     | 217      |
| BOTH    | L1_IO | E2     | 16       |
| BOTH    | L1_IO | E4     | 871      |
| BOTH    | L2_B1 | E3     | 73       |
| LITERAL | L2_B1 | E2     | 1440     |
| LITERAL | L2_B1 | E3     | 960      |
| LITERAL | L2_B1 | E4     | 480      |
| LITERAL | L2_B1 | E5     | 480      |
| LITERAL | L2_M0 | E1     | 480      |
| LITERAL | L2_M0 | E3     | 2880     |
| LITERAL | L2_M0 | E5     | 480      |

## 4. Root causes (primary code only, protocol section 11)

| reading | level | condition           | primary code                    | cases |
|---------|-------|---------------------|---------------------------------|-------|
| LITERAL | L1_IO | B0_LLM_ALONE        | E0_OUTPUT_TRUNCATED             | 18    |
| LITERAL | L1_IO | B0_LLM_ALONE        | E0_SCHEMA_INVALID               | 16    |
| LITERAL | L1_IO | B0_LLM_ALONE        | E1_CURRENT_GROUNDS_MISSING      | 48    |
| LITERAL | L1_IO | B0_LLM_ALONE        | E1_HISTORICAL_GROUNDS_MISSING   | 35    |
| LITERAL | L1_IO | B0_LLM_ALONE        | E2_SOURCE_MISATTRIBUTION        | 5     |
| LITERAL | L1_IO | B0_LLM_ALONE        | E4_INFLUENCE_UNEXPLAINED        | 208   |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E0_OUTPUT_TRUNCATED             | 18    |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E0_SCHEMA_INVALID               | 16    |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E1_CURRENT_GROUNDS_MISSING      | 48    |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E1_HISTORICAL_GROUNDS_MISSING   | 35    |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E2_SOURCE_MISATTRIBUTION        | 5     |
| SCOPED  | L1_IO | B0_LLM_ALONE        | E4_INFLUENCE_UNEXPLAINED        | 208   |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E0_OUTPUT_TRUNCATED             | 16    |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E0_SCHEMA_INVALID               | 10    |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E1_CURRENT_GROUNDS_MISSING      | 38    |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E1_HISTORICAL_GROUNDS_MISSING   | 35    |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E2_SOURCE_MISATTRIBUTION        | 5     |
| LITERAL | L1_IO | B1_VERIFIED_MEMORY  | E4_INFLUENCE_UNEXPLAINED        | 279   |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E0_OUTPUT_TRUNCATED             | 16    |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E0_SCHEMA_INVALID               | 10    |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E1_CURRENT_GROUNDS_MISSING      | 38    |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E1_HISTORICAL_GROUNDS_MISSING   | 35    |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E2_SOURCE_MISATTRIBUTION        | 5     |
| SCOPED  | L1_IO | B1_VERIFIED_MEMORY  | E4_INFLUENCE_UNEXPLAINED        | 279   |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E0_OUTPUT_TRUNCATED             | 24    |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E0_SCHEMA_INVALID               | 9     |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E1_CURRENT_GROUNDS_MISSING      | 28    |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E1_HISTORICAL_GROUNDS_MISSING   | 32    |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E2_SOURCE_MISATTRIBUTION        | 6     |
| LITERAL | L1_IO | M0_OPEN_LOOP_MEMORY | E4_INFLUENCE_UNEXPLAINED        | 225   |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E0_OUTPUT_TRUNCATED             | 24    |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E0_SCHEMA_INVALID               | 9     |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E1_CURRENT_GROUNDS_MISSING      | 28    |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E1_HISTORICAL_GROUNDS_MISSING   | 32    |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E2_SOURCE_MISATTRIBUTION        | 6     |
| SCOPED  | L1_IO | M0_OPEN_LOOP_MEMORY | E4_INFLUENCE_UNEXPLAINED        | 225   |
| LITERAL | L2_B1 | B1_VERIFIED_MEMORY  | E2_CAPABILITY_MISATTRIBUTION    | 480   |
| SCOPED  | L2_B1 | B1_VERIFIED_MEMORY  | E3_CURRENT_USE_GROUNDS_MISSING  | 38    |
| SCOPED  | L2_B1 | B1_VERIFIED_MEMORY  | E3_TRACE_OUTPUT_DISCONNECTED    | 35    |
| LITERAL | L2_M0 | M0_OPEN_LOOP_MEMORY | E3_PROSPECTIVE_TRACE_INCOMPLETE | 480   |

## 5. Matched M0 to B1 trace-status transitions

| reading | M0 status     | B1 status              | cases |
|---------|---------------|------------------------|-------|
| LITERAL | NONCONFORMANT | NONCONFORMANT_CRITICAL | 480   |
| SCOPED  | CONFORMANT    | CONFORMANT             | 407   |
| SCOPED  | CONFORMANT    | NONCONFORMANT          | 73    |

## 6. Release integrity (decision A4: the Level 2 result)

Level 2 reported once for the release, one row per memory, under the normative
SCOPED reading. Protocol equation (7) is withdrawn from the confirmatory set.

| memory     | M0 trace coherence | B1 trace coherence       | B1 structural status           | partial prospective field stability |
|------------|--------------------|--------------------------|--------------------------------|-------------------------------------|
| MEM51-0009 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0010 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0011 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0012 | CONFORMANT         | CONFORMANT|NONCONFORMANT | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0013 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0014 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0015 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0016 | CONFORMANT         | CONFORMANT|NONCONFORMANT | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0017 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0018 | CONFORMANT         | CONFORMANT               | -                              | STABLE                              |
| MEM51-0019 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0020 | CONFORMANT         | CONFORMANT|NONCONFORMANT | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0021 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0022 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0023 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0024 | CONFORMANT         | CONFORMANT|NONCONFORMANT | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0025 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0026 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0027 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0028 | CONFORMANT         | CONFORMANT               | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0029 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0030 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0031 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0032 | CONFORMANT         | CONFORMANT               | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0033 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0034 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0035 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0036 | CONFORMANT         | CONFORMANT|NONCONFORMANT | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |
| MEM51-0037 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0038 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0039 | CONFORMANT         | CONFORMANT|NONCONFORMANT | -                              | STABLE                              |
| MEM51-0040 | CONFORMANT         | CONFORMANT|NONCONFORMANT | UNRESOLVED_BY_CONDITION_DESIGN | STABLE                              |

Memories: 32. B1 structural statuses: - 24, UNRESOLVED_BY_CONDITION_DESIGN 8. Partial prospective field stability: STABLE 32.

Partial prospective field stability covers three of the five operands of
protocol equation (1); per decision B6 it does not establish that no silent
prospective rewrite occurred.

## 7. Existing-data reproducibility (protocol section 14)

Representation stability over 32 memories: prospective invariant **True**, resolved invariant **True**.

Cross-rendering response consistency (presentation stability, not repeated-call reproducibility):

| condition           | canonical contexts | reaction agreement | rule agreement | citation set exact | citation Jaccard |
|---------------------|--------------------|--------------------|----------------|--------------------|------------------|
| B0_LLM_ALONE        | 158                | 80.38%             | 78.48%         | 24.68%             | 0.577            |
| B1_VERIFIED_MEMORY  | 157                | 83.44%             | 82.17%         | 15.92%             | 0.543            |
| M0_OPEN_LOOP_MEMORY | 157                | 72.61%             | 68.79%         | 15.92%             | 0.511            |

## 8. Reporting boundary

Prediction accuracy and audit results are joined only after both analyses are frozen
(protocol section 15). This report contains no accuracy figure and no join.

