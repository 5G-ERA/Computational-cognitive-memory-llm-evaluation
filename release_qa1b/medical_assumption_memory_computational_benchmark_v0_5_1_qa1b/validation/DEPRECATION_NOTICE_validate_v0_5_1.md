# Deprecation notice — scripts/validate_v0_5_1.py

**Authority:** Official Release and Assessment Decision v0.5.1-qa1b, 15 August 2026, section 10.

`scripts/validate_v0_5_1.py` is retained **byte-identical** to the v0.5.1 release so that
recipients can verify the underlying data structure has not been silently altered. It remains
the authoritative **structural** validator.

Its shortcut output is **NOT authoritative**. Specifically the keys

    current_only_gate, assumption_only_gate, memory_only_gate,
    b0_bow_gate, nontext_near_prior

in `validation/validation_report_v0_5_1.json` use the retired one-sided macro-F1 threshold on
the eight-memory development split. That threshold was shown to be unsuitable for this
benchmark's closed balanced design: under grouped cross-validation the training and held-out
cell counts are complementary, so a zero-information probe is driven below the nominal class
prior without carrying transferable information.

**Authoritative shortcut and release-validity assessment:** `scripts/design_audit_qa1b.py`,
output `validation/design_audit_qa1b.json`.

Do not cite the legacy shortcut keys as a current decision rule.
