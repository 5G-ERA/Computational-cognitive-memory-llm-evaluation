# Experiment 1 Audit Extension — second round of questions

**To:** Renxi Qiu
**Re:** Audit extension after your decisions of 22 August 2026
**Status:** all 18 decisions applied and re-verified; §19 gate NO-GO with 4 conditions unmet

Your decisions are in. Both development splits were re-audited, fixtures re-verified (15/15), the
clean-room test still passes, and the package is hashed at 131 files. The two artefacts that drove
the preflight are gone: the Qwen3 Level 1 difference moved from −11.67 [−20.00, −2.50] to
+0.00 [−2.50, +2.50], and the B1 critical rate from 25.00% to **0.00% in every condition**.

Four gate conditions remain. Two are signatures. One is Adrian's independent validator, now in
progress. **One has no owner: the human review layer.** That is what most of this asks about.

---

## Group D — The human review layer

### D1. Is the human layer in scope for this paper at all?

Measured on the development splits, before deciding anything:

| | |
|---|---|
| Automated scope-overreach detections | **0 in 720 Level 1 cases** |
| Individual citations a human would have to judge for relevance, development only | **1,210** |
| Same, extrapolated across two reserved splits | ~9,600 |
| Coders required for the reliability sample | 2, independently |

`E2_SCOPE_OVERREACH` is the only hybrid code, and its automated half never fires on this data.
So the human layer reduces, in practice, to `E1_CITATION_IRRELEVANT`: does a citation that exists,
is visible and is in-window *substantively support* the ground the response itself claims. That is
a real question, and it is also 1,210 judgements on development alone.

Three ways forward:

1. **Run it in full.** Freeze the rubric, code a development sample for reliability, then apply
   the rubric to every citation in the reserved splits. Highest cost by a wide margin.
2. **Declare deterministic-only scope.** State in the paper that this extension reports
   deterministic checks only, name the four inert codes, and withdraw the §16 gate condition as
   out of scope for this release. Cheapest, and honest, but the audit then never tests substantive
   citation relevance at all.
3. **Bounded sample.** Freeze the rubric, code a stratified development sample with two coders,
   report the rate at which human review would downgrade a case, and publish the deterministic
   figures as bounds with that measured correction. Reserved splits stay deterministic-only.

**Recommendation: (3).** It keeps the deterministic figures as declared upper bounds, adds a
measured estimate of how loose those bounds are, and costs a sample rather than 9,600 judgements.
If you prefer (2), say so plainly and the gate condition is withdrawn rather than left unmet.

### D2. Who are the two coders?

The protocol requires two independent coders, blinded to model identity, decision correctness, the
hidden oracle, paired condition responses and aggregate results.

**Adrian cannot be one of them while he is building the independent validator** — coding these
responses would expose him to the data and to the reasoning before his implementation is finished,
and that is exactly the independence the §17 test is meant to establish.

So: can you be one of the two, and who is the second? Note the protocol blinds raters to model
identity and correctness, not to the hypothesis, so being the PI does not disqualify you — but it
is worth recording the choice deliberately rather than by default.

### D3. Should an INFO code route to human review at all?

Decision A1 set `E4_INFLUENCE_UNEXPLAINED` to severity INFO, status effect NONE, detection HYBRID.
The HYBRID detection now flags **414 of 1,440 case rows** as requiring human review, for a code
that cannot change any case status.

**Recommendation: no.** A code whose status effect is NONE should not trigger the human-review
flag. Either set its detection back to DETERMINISTIC while keeping severity INFO, or make the flag
conditional on the code having a status effect. Otherwise the reported human-review workload is
inflated by a code nothing depends on.

---

## Group E — Signatures

### E1. Sign the freeze now, or after the independent validator agrees?

The freeze record is written and ready: `validation/FREEZE_audit_extension_2026-08-22.json`,
covering contracts L1-IO-1.2, L2-M0-1.2, L2-B1-1.2, CRIT-1.1, AUDIT-ONT-1.1, AGREE-1.0 and
AUDIT-TERM-1.0, with the manifest of 131 hashed files.

**Recommendation: sign after Adrian's validator agrees.** The freeze fixes the contracts, and his
validator is precisely the thing that may show a contract to be ambiguous. Signing first means any
disagreement he finds becomes an amendment to an already-frozen contract on day one; signing after
means the frozen version is the one two implementations agree on.

### E2. Delegated signature — is it acceptable, and for which records?

You have asked Adrian to sign in your name. That is workable and there is precedent in this
project, but decision A6 states literally **REQUIRES RENXI QIU SIGNATURE**, and a delegated
signature does not satisfy that wording.

The tooling records it honestly: `signed_by` always names the person who actually signed,
`on_behalf_of` names you, the mode is stamped `DELEGATED`, and the record carries an explicit
caveat that it does not satisfy the stated requirement literally. The go/no-go gate prints the mode
wherever the signature is read, so it can never later be mistaken for your own.

Confirm which you want: a delegated signature by Adrian with that caveat on the record, or your own
signature. If delegated, please also confirm it covers both the freeze and the reserved-audit
authorisation, or only one.

### E3. Which reserved runs does the C2 authorisation cover?

`validation/AUTHORISATION_reserved_audit_001.json` currently authorises nothing: the run list is
empty by design, and the gate rejects a signed authorisation with an empty list. The three
candidates are Terra reserved (1,440 calls), Qwen3 reserved (1,440), and Kimi reserved (1,440,
your decision C1: reserved-only post-freeze arm; verified auditable — all six audit inputs are
byte-identical between qa1b and qa1c).

Name the runs, and say whether the Kimi arm goes in the same pass or as a separate authorisation
after the other two.

---

## Group F — What the audit claims

### F1. What is the audit's sentence in the paper?

After your decisions the audit's result is a clean null: Level 1 trace reconstructibility sits at
97.5–100% in every condition for both models, Level 2 cognitive-trace coherence at 99.17–100%,
critical-violation rate **0.00% everywhere**, partial prospective field stability 8/8, and
equation (7) withdrawn from the confirmatory set.

That supports a modest and defensible claim: *the retained artefacts support complete
reconstruction of the pathway from visible evidence to output in every condition, with no critical
violation, under deterministic checks.* It does not support any claim that cognitive memory
audits better than raw evidence — Level 1 is at a ceiling by construction, which is what A2
already declared.

Two questions follow. Is that the claim you want? And does the audit sit in the main paper or in
the supplement, given it is now an instrument-integrity result rather than a discriminating one?

### F2. Should the terminology fix be applied to V4.7 now?

Decision B10 reserves *audit conformity* for equation (36). V4.7 currently uses the term in the
Methods for the Experiment 2 lifecycle certificate test, which is correct, but the manuscript will
need to keep that distinct from this extension's *trace reconstructibility* and *trace coherence*
wherever both appear. Do you want a drafted terminology patch for V4.7 and a drafted audit
subsection, or will you write those yourself?

---

## Reply sheet

```
D1  human layer .............. full / deterministic-only scope / bounded sample
D2  the two coders ........... ____________________ and ____________________
D3  INFO codes flag human review? .......... yes / no

E1  sign the freeze ........... now / after the validator agrees
E2  signature mode ............ delegated to Adrian / Renxi signs
    covering .................. freeze only / authorisation only / both
E3  reserved runs authorised .. terra / qwen3 / kimi  (name all that apply)
    kimi ...................... same pass / separate authorisation

F1  audit claim ............... as drafted / amend: ____________________
    placement ................. main paper / supplement
F2  V4.7 terminology patch .... draft it / I will write it
```
