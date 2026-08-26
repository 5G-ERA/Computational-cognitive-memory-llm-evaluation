# Medical Assumption Memory Computational Benchmark v0.5.1

v0.5.1 replaces reaction-specific current templates with a matched, reaction-balanced design. Forty reusable memories are each paired with all five reactions. Five current template families and five neutral comparison markers are independently balanced. Marker meaning is randomly permuted per memory and is available in raw history and verified memory, requiring historical-current integration.

## Validation

- 40 memories
- 200 canonical contexts
- 40 per reaction
- 40 per template
- 8 per template-reaction cell
- 600 renderings
- 1,800 B0/M0/B1 calls
- all structural and challenge gates pass
- deterministic B1 oracle recovery: 100%
- full development mock pipeline: 100%

External API QA is the next step. Reserved execution remains on hold until retry, restart, and structured-output QA pass and the release is frozen.
