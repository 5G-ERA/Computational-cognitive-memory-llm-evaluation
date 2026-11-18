# Experiment 2 — Robotic embodiment transfer as a test of CCM constitution and scalability

**Scope and status, as of 2026-11-18.**

> **Read this first.** This document states the *design* of Experiment 2
> and *where the evidence stands*. The experiment is in progress. No
> comparative result between C2.5 and C3 is claimed here. Statements
> under "Expected" are hypotheses to be tested, not findings. The
> records, tools and robot stacks of Experiment 2 are not yet in this
> repository (see [What is not here yet](#what-is-not-here-yet)).

Experiment 1 (this repository) evaluates cognitive memory in an LLM
meta-decision benchmark. Experiment 2 asks the same question on robots:
can knowledge about a task be constituted as **Computational Cognitive
Memory (CCM)** and reused when the deployment changes, without training
a new model for each body?

## 1. Motivation

Cognitive knowledge for crossing an unstructured doorway was first
collected with a TurtleBot Waffle. That initial knowledge (C1)
associated crossing success principally with robot speed and available
clearance. Reusing this consequence relation directly on other
embodiments (Robotnik Summit XL, Unitree G1) produced failures, because
embodiment, sensing and operating conditions had changed. Preserving
the original consequence was not enough to determine how the existing
crossing capabilities should participate under the new conditions.

Experiment 2 tests whether the crossing knowledge can be constituted as
CCM and reused across deployment scenarios, instead of training a
separate model per embodiment.

## 2. The three conditions

All three use an external LLM. They differ in how the reconstruction is
organised.

| Condition | Computational organisation |
|---|---|
| **C2** — unstructured external reconstruction | The LLM reconstructs the crossing decision without an explicit DCA interface or a declared DCC capability–role structure. |
| **C2.5** — consequence-preserving reconstruction | The LLM uses Contextual Span and the observations (speed, clearance, angle, pose) to classify successful and unsuccessful crossing. The classified relation between observations and outcome is then preserved. A strong baseline that does not constitute full CCM. |
| **C3** — DCA-scoped reconstruction | The LLM process is scoped by the full DCA interface. It establishes an additional *pre-crossing* cognitive role, followed by the *crossing* role. DCC represents the capability–role relations and supports switching between the roles. |

In C3 each role requires its own DCA composition:

```
r1 = pre-crossing        I_cog(r1) = < C_ctx(r1), C_loc(r1), C_auth(r1) >
r2 = crossing            I_cog(r2) = < C_ctx(r2), C_loc(r2), C_auth(r2) >
```

### From DCA to DCC

1. **Contextual Span** classifies the simulation observations (speed,
   clearance, angle, pose).
2. **Semantic Locality** uses these distinctions to establish
   *pre-crossing* as a new cognitive concept.
3. **Authority Partitioning** calibrates what the concept can establish
   and how it can participate.
4. The resulting concept is transferred into **DCC** as a persistent
   pre-crossing cognitive role.
5. Under simulation-to-real and cross-embodiment change, the DCC role is
   **maintained, not recreated**. Authority Partitioning is re-applied
   to calibrate the role against the new embodiment, evidence and
   operating conditions.

Cognitive Scalability is therefore expected to come from preserving the
DCC role while recalibrating its authorised participation — not from
training an embodiment-specific model, and not from reconstructing the
cognitive role from the beginning.

## 3. Stages and expected results

| Stage | Change introduced | Expected (hypothesis) |
|---|---|---|
| **2.1** CCM constitution, Summit XL in simulation | none (origin) | C2 performs poorly. C2.5 and C3 both reconstruct successful and unsuccessful crossing accurately. The difference between them is structural, not yet behavioural. |
| **2.2a** Simulation → physical Summit XL | sensing, physical interaction, environment | C3 reconstructs better than C2.5: preserving a consequence relation formed in simulation is less robust than reconstructing the role-conditioned participation basis. |
| **2.2b** Summit XL → Unitree G1, initial role space | embodiment, sensing, capability expression | No clear difference between C2.5 and C3: the initial DCC role space does not represent a task-relevant factor (lighting). This would mark an *adequacy boundary*, not a failure of the reconstruction principle. |
| **2.2c** Unitree G1, role space extended for lighting | the role space, not the model | C3 reconstructs better than C2.5 once the role space is adequate for the declared deployment class. |

C2 is excluded from the transfer analysis (2.2) if its performance in
simulation is inadequate.

### Claims the experiment is designed to test

1. **DCA-scoped LLM reconstruction is conditioned by DCC role
   specification.** Pre-crossing and crossing require different
   contextual, semantic and authority compositions; a DCC role switch
   induces the corresponding change in DCA composition.
2. **DCC adequacy bounds reconstruction.** An advantage of C3 is
   expected only when the declared role space represents the
   task-relevant factors. DCC must be adequate for the declared
   deployment class; it need not represent every possible future
   condition.
3. **CCM enables stable capability reuse without additional
   embodiment-specific optimisation.** The crossing capabilities already
   exist in each robot. CCM does not create or improve them. It supplies
   the computational object — externally reconstructible participation —
   through which they are interpreted, assigned to cognitive roles and
   reused.

The decisive evidence is not performance in the original simulation. It
is reconstruction under simulation-to-real and cross-embodiment
variation, once the role space is adequate.

## 4. What is evaluated, and what is not

- **Reconstruction target:** successful / unsuccessful crossing,
  reconstructed from what is known at the pre-crossing point. The
  observed outcome of the crossing is the reference label.
- **Decision point:** a *frozen record* taken at the aligned
  pre-crossing point, before entering the doorway. A frozen record is
  valid only when the robot was stationary at the intended decision
  point and the record passes timing, freshness, synchronisation and
  integrity checks. Each record carries a manifest (context, pair, cut
  and traversal identifiers, alignment and freeze times, component
  timestamps, file hashes).
- **Same records for every condition.** C2.5 and C3 are run on the same
  frozen records and receive the same observations, including direction
  and light level. The only difference is the role structure.
- **Not evaluated:** the motion routine. Crossing time, clearance
  margins and speed are not results of this experiment. Motion-routine
  performance is not concept-reconstruction performance.
- **Counts are reported separately:** attempted, aligned, frozen, valid,
  classified.
- **Phases are disjoint:** development → calibration → held-out
  comparison. Calibration does not optimise the observed advantage of
  one condition over another; held-out records are not opened until the
  calibration and the scoring rule are fixed.

### Design decisions fixed so far

- **Direction** (A→B / B→A through the same doorway) stays inside the
  pre-crossing role as two calibrations of the same role. The role space
  is extended only for lighting.
- Rule written before looking at the data: if C3 remains unstable on the
  G1 after per-direction calibration, direction is reported as a second
  adequacy boundary.
- The Summit XL and G1 tracks run in parallel. The G1 does not import
  Summit-specific thresholds, clearances or authority rules.

## 5. Where the evidence stands (2026-11-18)

| Stage | Evidence available | What can be said |
|---|---|---|
| 2.1 Summit XL, simulation | Development batches recorded under earlier protocol versions. | Not yet evaluated under the condition definitions of Section 2. |
| 2.2a Physical Summit XL | 4 manifest-valid frozen records at the pre-crossing point, all in one direction (A→B); 3 crossed, 1 did not. | Acquisition is repeatable and non-interfering. Too few records, and too little outcome variation, for any C2.5-versus-C3 statement. |
| 2.2b Unitree G1, initial role space | 15 pre-crossing records cut from continuous recordings (the robot did not stop at the point) plus 4 kept unopened; two development calibration rounds (pooled and per direction). | Development only. The records show a direction-dependent blind fraction and a non-stationary pre-crossing point. No advantage of C3 can be claimed. |
| 2.2c Unitree G1, lighting | Two attempts in darkness that never reached the pre-crossing point: no record. | No evidence yet. |

Mechanisms in place:

- Physical Summit XL: non-interfering freeze at the pre-crossing point,
  with manifest check.
- Unitree G1: a stop at the pre-crossing point (zero command until the
  robot has been still and aligned for a set time, then a frozen marker)
  was implemented on 2026-11-17 and has been tested in the digital twin
  only. Records taken before it are development records "without stop".
- Passage envelope measured by hand: free doorway width 0.743 m; Summit
  XL 0.620 m wide; G1 0.570 m hand to hand, standing still.

One development comparison has been run on 14 physical records (Summit
XL and G1 together, 2026-11-16), under earlier output definitions. All
records had the same expected outcome, so it could not measure
discrimination between conditions.

## 6. Next steps

1. G1 sessions with the stop, per direction, under normal and reduced
   light, split into a calibration block and a held-out block.
2. Per-direction calibration of the pre-crossing role on the calibration
   block.
3. Scoring rule and outcome scale fixed in writing before the held-out
   block is opened.
4. C2.5 and C3 on the same records, with the initial role space and with
   the light-conditioned role added.
5. More physical Summit XL records with outcome variation, and their
   simulation counterparts, for stage 2.2a.

## What is not here yet

The Experiment 2 frozen records, manifests, held-out blocks, prompts and
analysis code are not in this repository. They will be added with their
freeze records when the corresponding stage is locked, following the
same practice as Experiment 1 ([`SANITIZATION.md`](SANITIZATION.md)).
