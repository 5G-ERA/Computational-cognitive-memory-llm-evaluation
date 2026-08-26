# Cognitive Memory Benchmark v0.5.1-qa1 patch

This overlay aligns v0.5.1 terminology with *A Computational Theory of Cognitive Memory* and applies the external API QA corrections found during the completed Kimi-Dev-72B development run.

## Canonical condition names

- B0_LLM_ALONE: Raw longitudinal evidence
- M0_OPEN_LOOP_MEMORY: Pre-specified consequence mapping
- B1_VERIFIED_MEMORY: Cognitive memory

The condition IDs remain unchanged for compatibility.

## Included corrections

- free-reasoning end-of-think final JSON extraction
- separate COMPLETED_OUTPUT_TRUNCATED status
- retry, attempt audit, restart, and completeness logic
- revised chance-relative current-only gate with at least 32 memories
- revised decisive-evidence grounding and certified meta-decision accuracy
- portable relative checksum generation
- protocol and terminology map

## Apply to an extracted v0.5.1 package

```bash
python patch/scripts/apply_qa1_patch.py /path/to/extracted/v0.5.1
```

Then run the target package's structural validator and the qa1 test suite before freezing the reserved run.
