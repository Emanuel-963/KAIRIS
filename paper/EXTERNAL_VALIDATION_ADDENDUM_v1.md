# KAIRIS external validation addendum — draft v1

**Status:** draft; not approved, not tagged and not registered

**Draft created:** 4 November 2026

**Scientific results accessed by KAIRIS:** no

**KAIRIS agents executed on this cohort:** no

This document must be completed, approved and registered before any execution of
Lin--KK, DRT, GSF, ESC or the KAIRIS orchestrator on the external cohort.

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

Each frequency-resolved spectrum is one analysis case. Before registration, the
coordinator must confirm whether multiple rows originate from the same physical
coupon, weld, acquisition site or repeated measurement. All cases sharing a
physical origin must remain in the same bootstrap group. If the public metadata
cannot resolve this dependence, uncertainty will be calculated conservatively at
the subgroup level and the limitation will be stated.

**Required before approval:** document the confirmed grouping key or the exact
conservative fallback.

## 6. Blinded expert review

Two primary specialists and one reserve specialist will be named by the
responsible researcher. Reviewers will receive opaque case identifiers, raw
Nyquist/Bode views and the frozen annotation form. They will not receive KAIRIS
outputs, source subgroup names or the coordinator key before their annotations
are locked.

**Required before approval:** names/roles, conflict declarations, reviewer
training examples, delivery deadline and reserve-activation rule.

## 7. Confirmatory questions and endpoints

The following must be completed without opening KAIRIS results:

1. define the primary external scientific question;
2. identify which expert annotations are primary;
3. identify the pre-specified continuous GSF descriptors, if any;
4. define whether the low/high passivity references support an ordered contrast;
5. define the physically justified ESC reference or declare ESC descriptive;
6. set success thresholds, denominators and handling of abstentions;
7. justify whether 42 cases provide estimation, hypothesis testing or both;
8. define multiplicity handling for any confirmatory subgroup comparison.

Until these items are approved, the cohort is downloaded and technically ready
but the scientific analysis remains locked.

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

- [ ] physical grouping/dependence resolved;
- [ ] two specialists and reserve confirmed;
- [ ] primary and secondary endpoints frozen;
- [ ] success thresholds and statistical contrasts frozen;
- [ ] reviewer materials frozen;
- [ ] exact code commit and configuration identified;
- [ ] OSF registration submitted before KAIRIS execution;
- [ ] registration identifier and timestamp added here;
- [ ] immutable Git tag created.

Only after every applicable item is complete may the status change to
`approved_registered_analysis_locked`.
