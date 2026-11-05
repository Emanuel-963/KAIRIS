# KAIRIS external validation addendum — version 1.0

**Status:** scientific specification complete; analysis locked pending private
acceptances, immutable code identity and OSF registration

**Draft created:** 4 November 2026

**Scientific results accessed by KAIRIS:** no

**KAIRIS agents executed on this cohort:** no

The scientific decisions are executable in
`config/external_validation_plan_v1.json`. No Lin--KK, DRT, GSF, ESC or KAIRIS
orchestrator execution is authorized until
`scripts/check_external_validation_readiness.py` reports every gate as passed.

## 1. Confirmed external source

- title: *Optimizing Unsupervised Clustering of Electrochemical Impedance
  Spectra via Normalization and Dimensionality Reduction*;
- repository DOI: `10.17605/OSF.IO/XRAV8`;
- dataset DOI: `10.17632/r9snmwyzkv.1`;
- related article DOI: `10.1038/s41598-026-35621-3`;
- originating institution: University of Zagreb, Faculty of Chemical
  Engineering and Technology;
- license: CC BY 4.0;
- system: welded 316L stainless steel in aerated 0.1 M NaCl;
- acquisition: open-circuit potential, three-electrode paste-electrolyte cell;
- cohort: 42 spectra at 36 frequencies from 0.01 Hz to 100 kHz;
- conditions: eight combinations of surface region/treatment and two reference
  passivity groups.

The source institution, system and measurements are independent of KAIRIS. The
numerical spectra have not been processed by KAIRIS and were not used to choose
its existing thresholds.

## 2. Role and limits of the cohort

This cohort will be treated as a prospective external validation set relative to
the frozen KAIRIS implementation and analysis plan. Published surface-condition
and passivity-reference labels are experimental-condition labels, not causal
ground truth for an equivalent circuit, DRT peak count, GSF regime or ESC
geometry.

The cohort must not be used for:

- fitting KAIRIS thresholds before the confirmatory execution;
- selecting a DRT regularization value after outcomes are seen;
- training, memory retrieval, few-shot examples or fine-tuning of an LLM;
- choosing the most favorable GSF or ESC output after comparison with labels;
- silently excluding spectra because their outputs are unfavorable.

## 3. Integrity and deterministic preparation

The two downloaded files and their SHA-256 values are recorded in
`data/external_confirmatory/316l_passivity_osf_xrav8/source_metadata.json`.
`raw/input_data.csv` is the canonical conversion source.

The source is a wide Bode table containing `log10(|Z|)` and the positive
capacitive phase-angle magnitude. The frozen representation conversion is:

```text
|Z| = 10**log10(|Z|)
Re(Z) = |Z| cos(phase)
-Im(Z) = |Z| sin(phase)
```

The conversion script verifies the source checksum and creates opaque case IDs.
It performs no spectral validation or scientific classification. The local
case-to-condition key remains under coordinator control and is excluded from Git.

## 4. Inclusion and exclusion

Planned inclusion: all 42 source spectra.

Permitted pre-analysis exclusions:

1. source checksum mismatch;
2. duplicate source identifier;
3. missing or non-finite magnitude/phase value;
4. irrecoverable mismatch between magnitude and phase frequencies;
5. documented corruption relative to the public repository.

Lin--KK failure, unusual morphology, nonconvergence of a downstream module,
module disagreement or disagreement with a specialist are outcomes, not
exclusion criteria.

## 5. Experimental unit and dependence

Each frequency-resolved spectrum is one analysis case. The public table contains
42 unique case rows distributed across ten source subgroups: AW-BASE 4, AW-HAZ 4,
MC-BASE 4, MC-HAZ 4, PAW-BASE 3, PAW-HAZ 4, PMC-BASE 5, PMC-HAZ 6, LO-REF 4 and
HI-REF 4. The public metadata does not resolve, for every row, whether sites or
spectra share a coupon. Therefore, the frozen conservative fallback is to
bootstrap the **ten source subgroups**, not individual frequency points or 42
rows, using 2,000 draws, seed `20261105` and 95% intervals. This does not prove
independence within or between source subgroups; the limitation must be stated.

## 6. Blinded expert review

The review panel will be recorded publicly only by blinded role. Personally
identifying information, qualifications and relationships are retained in the
coordinator's private records and are not committed to the public repository.

| Panel role | Public identifier | Assigned responsibility |
|---|---|---|
| Primary specialist A | Reviewer A | complete the entire frozen annotation form for every eligible case, independently and under blinding |
| Primary specialist B | Reviewer B | complete the same entire frozen annotation form for every eligible case, independently and under blinding |
| Reserve specialist and adjudicator | Reviewer R | replace a primary reviewer if the activation rule is met, or adjudicate only the disagreements that persist after inter-reviewer agreement has been calculated |

Any relevant academic or collaborative relationships are documented in the
private conflict declarations and summarized in the submitted article only
with the reviewers' explicit consent. The annotations
will be independent in the operational sense: separate files, no discussion, no
access to each other's decisions and no access to KAIRIS outputs before both
files are locked. The external status of this validation refers to the cohort
and its originating institution, not to the review panel.

All three reviewers will receive opaque case identifiers, raw Nyquist/Bode
views, the frozen annotation form and the same written instructions. They will
not receive KAIRIS outputs, source subgroup names or the coordinator key before
the applicable annotations or adjudications are locked. Training will use only
examples outside the 42-case external cohort and will teach the annotation
schema without revealing expected KAIRIS classifications.

The reserve specialist will be activated when a primary specialist withdraws,
does not return a complete usable form by the frozen deadline, or has more than
10% of required fields missing after one administrative completeness query. In
that replacement role, the reserve specialist must annotate the full cohort
blindly and independently. If both primary forms are usable, the reserve will
instead act only as adjudicator for disagreements that remain after agreement
statistics have been calculated. Adjudication will not erase or replace the
original disagreement dataset, and the adjudicator will not receive KAIRIS
outputs.

Detailed responsibilities and declarations are recorded in
`paper/REVIEWER_ROLES_AND_CONFLICTS_v1.md`.

The public repository contains only role identifiers. Written acceptance,
identity, affiliation, ORCID when available, relevant experience, conflict
declaration and delivery deadline stay in the ignored coordinator directory.
The public template is `paper/private_admin_signoff_template.json`; the completed
private file is a readiness gate and must never be committed.

## 7. Confirmatory questions and endpoints

### 7.1 Primary scientific question

Can the frozen deterministic KAIRIS produce complete, auditable outputs on an
independent experimental corrosion/passivity cohort and, when its spectral
admissibility and two-observable mapping permit a classification, how closely
does its dominant-response classification agree with an independent exact
pre-adjudication consensus of two blinded specialists?

The claim is deliberately about reproducibility, classification agreement and
abstention. It is not a claim that KAIRIS recovers a unique circuit or a causal
mechanism.

### 7.2 P1 — integrity and provenance gate

All 42 cases must be accounted for and complete. Every completed case must have
consolidated JSON, HTML, matching input SHA-256 and full provenance; partial
artifacts and silent failures must equal zero. A documented failure makes P1
fail, but is retained with its reason rather than silently excluded. P1 is binary
and all fraction thresholds are 100%; partial and silent failure counts must be
zero.

### 7.3 P2 — dominant-response agreement

The primary human reference is exact agreement between Reviewer A and Reviewer B
on `dominant_response` **before adjudication**, restricted to `kinetic`,
`diffusive`, `pseudocapacitive` and `mixed`. The frozen KAIRIS mapping is:

| DRT | GSF | extra condition | P2 class |
|---|---|---|---|
| `kinetic_dominated` | `resistive` | Lin-KK valid | `kinetic` |
| `diffusion_dominated` | `diffusive` | Lin-KK valid | `diffusive` |
| `diffusion_dominated` | `pseudocapacitive` | diagnostic is `intercalation_pseudocapacitive` and Lin-KK valid | `pseudocapacitive` |
| `mixed` | `mixed` | Lin-KK valid | `mixed` |
| any other combination | any | — | `undetermined` |

P2 reports macro-F1 and balanced accuracy over human classes represented in the
primary denominator, class-wise precision/recall/F1, confusion matrix and the
KAIRIS abstention fraction, with grouped 95% bootstrap intervals. A KAIRIS
abstention remains in the denominator and is never counted as correct. Human
disagreement, `undetermined` or a required missing rating creates **no human
consensus** and is counted separately rather than scored as a KAIRIS error.

This 42-case cohort is an estimation study: no minimum accuracy, superiority or
non-inferiority threshold will be introduced. The absence of an external pilot
effect size, uncertain physical dependence and likely class imbalance do not
support an honest powered threshold. This is an explicit decision, not a pending
item. Only P1 has confirmatory pass/fail gates.

### 7.4 Secondary endpoints

- pre-adjudication raw agreement, Cohen kappa and ordinal weighted kappa;
- the same P2 metrics after adjudication, labelled secondary;
- sensitivity, specificity, predictive values and abstention for the explicit
  `intercalation_pseudocapacitive` diagnostic when a human yes/no reference exists;
- frozen GSF descriptors: `alpha_mean`, `alpha_std`, `I_crit`, `f_Icrit` and
  `kphi_mean`;
- frozen DRT descriptors: peak count, resolution status, R∞ status and `R_ct`;
- a secondary ordered-reference sensitivity analysis expecting HI-REF > LO-REF
  for `log10(|Z|)` at 0.01 Hz and `R_ct`, reporting medians, median difference,
  Cliff's delta and all 70 allocations of four versus four reference cases.

The reference contrast is not causal ground truth and cannot promote an
exploratory descriptor to a primary endpoint.

### 7.5 ESC decision

ESC G1--G3 will be reported descriptively. G4 is excluded from scientific
contrasts because the public cohort does not provide the sample-specific
paste-cell geometry required to justify the conductivity/geometry reference in
the KAIRIS configuration. No visual regularity or ESC reference may select a
mechanism, exclude a case or determine study success.

### 7.6 Multiplicity

P1 is an integrity gate and P2 is estimation without a null-hypothesis success
test, so no primary multiplicity adjustment applies. Any secondary family that
reports hypothesis-test p-values will use Holm adjustment within that declared
family and report both raw and adjusted values. Exploratory work will be labelled
as such and emphasize estimates and intervals.

## 8. Planned reporting independent of pass/fail thresholds

At minimum, the study will report:

- import and completion rates with explicit failure reasons;
- Lin--KK and local smoothness outcomes without conflating them;
- DRT convergence, peak descriptors and abstentions;
- GSF and ESC descriptors with their domains of interpretation;
- module agreement/disagreement and inconclusive cases;
- agreement between the two specialists before adjudication;
- estimates, denominators and grouped 95% confidence intervals;
- runtime, memory, platform and complete provenance;
- every protocol deviation and its timing relative to result access.

## 9. Registration gate

Approval requires:

- [x] conservative dependence fallback frozen at source-subgroup level;
- [x] two primary specialists and one reserve nominated and assigned roles;
- [ ] written acceptance and conflict declarations received;
- [x] primary and secondary endpoints frozen;
- [x] success policy, denominators, abstentions and contrasts frozen;
- [x] reviewer instructions and annotation schema frozen;
- [ ] exact code commit and configuration identified;
- [ ] OSF registration submitted before KAIRIS execution;
- [ ] registration identifier and timestamp added here;
- [ ] immutable Git tag created.

Only after every applicable item is complete and the coordinator explicitly sets
`analysis_unlocked=true` may the status change to
`approved_registered_analysis_unlocked`.

The mechanical gate is:

```bash
python scripts/check_external_validation_readiness.py
```

Exit code `2` means the analysis remains locked. After the private acceptances,
freeze record, Git tag and OSF fields have been completed, the registered run is:

```bash
python scripts/run_external_validation.py \
  --output output/external_validation_316l_v1
```

The review package can be generated before scientific analysis because it
contains raw converted EIS only:

```bash
python scripts/build_external_review_pack.py \
  --destination output/external_review_pack_v1
```

After both reviewer files are locked, the primary statistical analysis is:

```bash
python scripts/analyze_blinded_reviews.py reviewer_A_form.csv reviewer_B_form.csv \
  --destination output/external_review_agreement_v1

python scripts/analyze_external_confirmation.py \
  --output output/external_validation_316l_v1 \
  --reviewer-a reviewer_A_form.csv --reviewer-b reviewer_B_form.csv \
  --mapping data/external_confirmatory/316l_passivity_osf_xrav8/coordinator/blinding_key.csv \
  --destination output/external_confirmatory_analysis_v1
```
