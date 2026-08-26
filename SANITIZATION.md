# Sanitization record

Before publication, the following substitutions were applied to the files
listed below (private infrastructure identifiers; no scientific content
was changed). Because some of these files are covered by SHA-256 freeze
records, their bytes no longer match the recorded hashes.

- Private inference endpoint hostname -> `REDACTED-PRIVATE-ENDPOINT`
- Private tailnet identifier -> `REDACTED-TAILNET`
- AWS account number -> `REDACTED-AWS-ACCOUNT`

Excluded from publication: vault-channel material unrelated to the LLM
evaluation (`vault_lote_2026-08-22/`, `vault_proposals_2026-08-22/`,
`build_vault_lote.py`, the 2026-08-22 audit bundle zip).

## Files edited

bedrock_terra/config/model_qwen3_bedrock.json
bedrock_terra/config/model_qwen3_effort_high.json
bedrock_terra/config/model_qwen3_effort_medium.json
bedrock_terra/config/model_terra_bedrock.json
bedrock_terra/config/model_terra_effort_high.json
bedrock_terra/EDCA_preexecution_amendment_record_2026-08-19.html
bedrock_terra/iam_policy_dca_bedrock.clean.json
bedrock_terra/iam_policy_dca_bedrock.json
bedrock_terra/out/abl_no_guide/run_manifest.json
bedrock_terra/out/abl_no_resolved/run_manifest.json
bedrock_terra/out/dev_qwen3_effort_medium/run_manifest.json
bedrock_terra/out/dev_qwen3_repeat_low/run_manifest.json
bedrock_terra/out/dev_qwen3/run_manifest.json
bedrock_terra/out/dev_qwen3_smoke/run_manifest.json
bedrock_terra/out/dev_terra_effort_high/run_manifest.json
bedrock_terra/out/dev_terra/run_manifest.json
bedrock_terra/out/dev_terra_smoke/run_manifest.json
bedrock_terra/out/reserved_qwen3_repeat/run_manifest.json
bedrock_terra/out/reserved_qwen3/run_manifest.json
bedrock_terra/out/reserved_terra/run_manifest.json
release_qa1b/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/config/model_kimi_gpuedge.json
release_qa1b/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/validation/freeze_record_v0_5_1_qa1b.json
release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c/config/model_kimi_gpuedge.json
release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c/validation/freeze_record_v0_5_1_qa1b.json
release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c/validation/freeze_record_v0_5_1_qa1c.json
reserved_run_2026-08-15/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/config/model_kimi_gpuedge.json
reserved_run_2026-08-15/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/results/reserved_2026-08-15/run_manifest.json
reserved_run_2026-08-15/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/validation/freeze_record_v0_5_1_qa1b.json
