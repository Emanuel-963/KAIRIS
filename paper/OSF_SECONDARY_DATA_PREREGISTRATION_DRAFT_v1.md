# KAIRIS external validation — OSF Secondary Data Preregistration draft v1

**Draft date:** 11 November 2026  
**Recommended OSF template:** Secondary Data Preregistration  
**Submission status:** draft only; not yet registered  
**Analysis status:** locked; no KAIRIS agent has been executed on the 42-case
external cohort  
**Primary analysis:** deterministic, without LLM, memory retrieval or supervised
examples

This document is a paste-ready scientific draft for the OSF registration form.
It contains no reviewer identities, affiliations or private declarations.

## 1. Title

External validation of KAIRIS: a preregistered multiperspective analysis of an
existing electrochemical impedance spectroscopy cohort

## 2. Description and research aims

KAIRIS (Kramers–Kronig-Assessed Impedance, Relaxation, and Integrated
Spectroscopy) is a deterministic-first protocol that integrates spectral
admissibility, distribution of relaxation times (DRT), Golden Spectral Field
(GSF), Electrochemical Spectral Cartography (ESC), and rule-based synthesis.

The confirmatory study asks whether the frozen KAIRIS implementation can process
an independent experimental EIS cohort with complete, auditable artifacts and,
when its admissibility and response-mapping rules permit classification, how
closely its dominant-response classification agrees with the exact
pre-adjudication consensus of two blinded specialists.

The study is designed to estimate performance and characterize abstention and
domain limitations. It is not designed to prove a unique equivalent circuit or
causal electrochemical mechanism.

## 3. Existing data and prior access

The study uses an existing public cohort associated with:

- repository DOI: `10.17605/OSF.IO/XRAV8`;
- dataset DOI: `10.17632/r9snmwyzkv.1`;
- related article DOI: `10.1038/s41598-026-35621-3`;
- license: CC BY 4.0;
- source institution: University of Zagreb, Faculty of Chemical Engineering and
  Technology.

The public source describes welded 316L stainless steel measured at open-circuit
potential using a three-electrode paste-electrolyte cell in aerated 0.1 M NaCl.
The cohort contains 42 spectra, each with 36 frequencies from 0.01 Hz to 100 kHz,
distributed across eight surface-region/treatment subgroups and two reference
passivity groups.

Before preregistration, the investigators knew the public article, sample count,
frequency grid, source subgroup names and the existence of low/high passivity
reference groups. The canonical table was downloaded, its SHA-256 was recorded,
and a deterministic representation conversion was performed to produce opaque
case identifiers. No Lin–KK, DRT, GSF, ESC or KAIRIS orchestrator output has been
generated for these 42 cases. No threshold, endpoint or mapping was selected from
KAIRIS results on this cohort.

The source labels are experimental-condition labels, not ground truth for an
equivalent circuit, a DRT peak count, a GSF regime or an ESC geometry.

## 4. Data source and integrity

The canonical source file is `raw/input_data.csv`, SHA-256:

```text
01c85092b46a68a832124d7327157b6327a0d440ea3b66ba277694432edfb8b3
```

The source stores `log10(|Z|)` and positive capacitive phase magnitude. The
frozen conversion is:

```text
|Z| = 10**log10(|Z|)
Re(Z) = |Z| cos(phase)
-Im(Z) = |Z| sin(phase)
```

The conversion verifies the source hash, frequency correspondence, finite
values and unique source identifiers. It creates 42 long-form CSV files with
opaque identifiers and a public hash manifest. The case-to-condition key remains
under coordinator control and is excluded from Git and the preregistration
bundle.

## 5. Study population, sample size and stopping rule

All 42 spectra in the canonical public table will be included. There is no
sequential sampling or optional stopping. The sample size is fixed by the full
eligible public cohort.

The study is explicitly estimation-focused. With 42 cases, uncertain
within-source physical dependence, and no untouched external pilot effect size,
no minimum accuracy, superiority margin or non-inferiority margin is declared.
The primary scientific endpoint will be reported with uncertainty rather than
converted into an arbitrary pass/fail threshold.

## 6. Unit of analysis and dependence

One complete frequency-resolved spectrum is one analysis case. Public metadata
do not resolve for every row whether spectra share a coupon, weld or acquisition
site. Therefore, the conservative frozen fallback is grouped bootstrap
resampling of the ten source subgroups, not resampling of individual frequency
points or treating all 42 rows as demonstrably independent.

The bootstrap uses 2,000 draws, seed `20261105`, and 95% percentile intervals.
The limitation that subgroup resampling does not prove physical independence
will be reported.

## 7. Inclusion and exclusion rules

Planned inclusion is all 42 source spectra. Pre-analysis exclusion is permitted
only for:

1. source checksum mismatch;
2. duplicate source identifier;
3. missing or non-finite magnitude/phase value;
4. irrecoverable mismatch between magnitude and phase frequencies;
5. documented corruption relative to the public repository.

Lin–KK failure, unusual morphology, module nonconvergence, DRT–GSF disagreement,
or disagreement with a specialist is an outcome, not an exclusion criterion.
A failed case remains in case accounting with its explicit reason.

## 8. Blinding and human reference

Reviewer A and Reviewer B receive the same 42 opaque cases, raw converted EIS
values, Nyquist/Bode figures, frozen instructions and annotation schema. They do
not receive source subgroup names, the coordinator key, KAIRIS outputs or each
other's decisions before both first-round files are locked and hashed.

The primary human reference for dominant response is exact pre-adjudication
agreement between Reviewer A and Reviewer B. Reviewer R may replace an
unavailable primary reviewer under the frozen activation rule or adjudicate
remaining disagreements after agreement statistics have been calculated, but
cannot perform both roles in the same review round.

Reviewer identities, affiliations, ORCIDs, relationships and conflict
declarations are stored privately and are not part of the public repository or
this registration bundle.

## 9. Human variables

The frozen annotation fields are:

- spectrum quality: `acceptable`, `questionable`, `unusable`;
- dominant response: `kinetic`, `diffusive`, `pseudocapacitive`, `mixed`,
  `inductive`, `undetermined`;
- apparent process count: integer 0–5 or `undetermined`;
- intercalation-pseudocapacitive compatibility: `yes`, `no`, `uncertain`;
- confidence: integer 1–5;
- proposed exclusion: `yes` or `no`, with mandatory reason for `yes`;
- optional reviewer comment.

Missing answers are not imputed. An administrative query may identify an
accidental omission but may not suggest a scientific response.

## 10. KAIRIS execution conditions

The run must start from the frozen analysis code commit and configuration
identified in `EXTERNAL_VALIDATION_FREEZE_RECORD.json`, with a clean Git tree,
the exact tag `external-validation-plan-v1.0`, a new empty output directory and
no reuse of results.

The executor forces:

```text
llm_enabled = false
llm_memory_enabled = false
supervised_learning_enabled = false
overwrite = false
```

Execution remains mechanically locked until source integrity, reviewer
materials, private administrative sign-offs, code/config identity, Git tag, OSF
registration and explicit post-registration coordinator unlock all pass.

## 11. Primary endpoint P1 — integrity and provenance

P1 is a binary engineering/reproducibility gate. Required thresholds are:

- all 42 cases accounted for: 100%;
- pipeline completion: 100%;
- consolidated JSON and HTML for each completed case: 100%;
- input hash agreement for each completed case: 100%;
- complete provenance for each completed case: 100%;
- partial artifact count: 0;
- silent failure count: 0.

A documented execution failure makes P1 fail but remains reported; it is never
silently excluded.

## 12. Primary endpoint P2 — dominant-response agreement

The P2 denominator comprises cases with exact Reviewer A/Reviewer B
pre-adjudication agreement in one of four evaluable classes: `kinetic`,
`diffusive`, `pseudocapacitive`, or `mixed`.

The frozen deterministic KAIRIS mapping is:

| DRT regime | GSF regime | Additional condition | P2 class |
|---|---|---|---|
| `kinetic_dominated` | `resistive` | Lin–KK valid | `kinetic` |
| `diffusion_dominated` | `diffusive` | Lin–KK valid | `diffusive` |
| `diffusion_dominated` | `pseudocapacitive` | diagnostic equals `intercalation_pseudocapacitive` and Lin–KK valid | `pseudocapacitive` |
| `mixed` | `mixed` | Lin–KK valid | `mixed` |
| any other combination | any | — | `undetermined` |

P2 metrics are macro-F1 and balanced accuracy over human classes represented in
the denominator, class-wise precision/recall/F1, confusion matrix and KAIRIS
abstention fraction, with grouped 95% bootstrap intervals.

A KAIRIS abstention remains in the P2 denominator and is never counted as
correct. Human disagreement, `undetermined`, or a missing required human rating
creates no human consensus and is counted separately rather than scored as a
KAIRIS error.

## 13. Secondary endpoints

Secondary analyses include:

1. pre-adjudication raw agreement, Cohen kappa and ordinal weighted kappa;
2. P2 metrics after adjudication, clearly labelled secondary;
3. sensitivity, specificity, predictive values and abstention for the explicit
   `intercalation_pseudocapacitive` diagnostic when a human yes/no reference is
   available;
4. GSF descriptors `alpha_mean`, `alpha_std`, `I_crit`, `f_Icrit`, and
   `kphi_mean`;
5. DRT descriptors peak count, resolution status, R∞ status, and `R_ct`;
6. a secondary ordered-reference sensitivity analysis expecting HI-REF > LO-REF
   for `log10(|Z|)` at 0.01 Hz and `R_ct`, reporting group medians, median
   difference, Cliff's delta, and all 70 allocations of four versus four
   reference cases.

The reference contrast is not causal ground truth and cannot promote an
exploratory descriptor to a primary endpoint.

## 14. ESC policy

ESC groups G1–G3 are descriptive. G4 is excluded from scientific contrasts
because the public cohort does not provide the sample-specific paste-cell
geometry needed to justify the configured conductivity/geometry reference. No
visual geometry or ESC reference can select a mechanism, exclude a case, or
determine success.

## 15. Missing data, nonconvergence and abstention

- no missing human value is imputed;
- no missing KAIRIS output is imputed;
- human disagreement and human indetermination are reported as lack of human
  consensus;
- Lin–KK invalidity, required-module failure, an unmapped DRT–GSF combination,
  or generic DRT–GSF inconsistency produces KAIRIS abstention;
- module nonconvergence remains a reported outcome and contributes to P1;
- denominators are printed for every metric.

## 16. Multiplicity and inference

P1 is an integrity gate and P2 is an estimation endpoint without a
null-hypothesis success test; therefore no primary multiplicity adjustment is
applied. Any secondary family reporting hypothesis-test p-values uses Holm
adjustment within that declared family and reports raw and adjusted values.
Exploratory analyses are labelled as such and emphasize effect estimates and
intervals rather than dichotomous p-value decisions.

## 17. Planned robustness and sensitivity reporting

The confirmatory report will preserve runtime, memory, platform, package
versions, input hashes, effective configuration, code commit, Git cleanliness,
Lin–KK and local smoothness as distinct outcomes, DRT convergence and peak
descriptors, GSF and ESC domains of interpretation, module disagreements and all
inconclusive cases.

Comparisons with independent Lin–KK and DRT implementations, module ablations,
regularization sensitivity, noise, frequency truncation and point-density
sensitivity are supporting analyses. They do not alter P1 or P2 and cannot be
used to choose a more favorable confirmatory output after results are opened.

## 18. Deviations and exploratory work

Any change after registration is entered in `DEVIATIONS_LOG_v1.md` with date,
rationale, timing relative to result access, affected endpoint, and expected
impact. Unplanned analyses will be labelled exploratory. Unfavorable outcomes do
not authorize threshold changes, endpoint substitution, case removal or
selection of a preferred module result.

## 19. Files and immutable identities

The registration bundle contains the external addendum, executable plan,
protocol configuration, freeze record, reviewer instructions, de-identified
reviewer roles, source/preparation metadata, public blind manifest, analysis
scripts, deviation log and a SHA-256 manifest.

Frozen analysis code commit:

```text
94a03c366b0d26ec8f2e05befed0660fb2ff0f1d
```

Frozen tag:

```text
external-validation-plan-v1.0
```

The full repository may continue to evolve, but confirmatory execution uses the
frozen identity above. Later changes do not silently replace registered files.

## 20. Current administrative status at draft creation

Two panel members have accepted participation. Conflict declarations are still
outstanding, and the full three-role administrative gate has not passed. This
draft and bundle may be prepared in parallel, but registration submission and
analysis unlock remain pending the complete private records required by the
frozen protocol.

## 21. Registration visibility recommendation

The scientific plan can be registered publicly if authorship and reviewer
privacy are already protected. If the investigators need to protect unpublished
methodological detail or support blinded peer review, an embargoed registration
is appropriate. The selected visibility and embargo end date, if any, must be
recorded in the final registration record. Reviewer identities and private
declarations are excluded under either option.

## 22. Planned reporting

The manuscript will distinguish:

- retrospective development evidence from 198 known spectra;
- confirmatory external evidence from the 42 registered cases;
- human pre-adjudication agreement;
- secondary adjudicated analyses;
- exploratory analyses and all protocol deviations.

Results will be reported regardless of whether P1 passes, whether P2 estimates
are high or low, or whether individual modules disagree.

