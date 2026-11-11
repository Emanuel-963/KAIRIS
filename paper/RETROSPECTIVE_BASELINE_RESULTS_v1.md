# KAIRIS retrospective independent-baseline results — v1

**Execution date:** 11 November 2026

**Role:** retrospective, exploratory supporting analysis

**Corpus:** 198 spectra (72 project synthetic, 54 public experimental, 72
publication-derived synthetic)

**External confirmatory cohort executed:** no

## Methods frozen before execution

The comparison used `config/baseline_comparison_schema_v1.json` without tuning
on the 42-case external cohort. Independent implementations were:

- Lin-KK: `impedance.validation.linKK`, impedance.py 1.7.1, complex fit;
- DRT primary: pyimpspec 5.2.0 TR-NNLS, real mode, automatic lambda
  (`lambda_value=-1.0`);
- DRT sensitivities: imaginary mode with automatic lambda, and real/imaginary
  modes with L-curve selection (`lambda_value=-2.0`).

The same sanitized frequency and complex-impedance vectors were supplied to
KAIRIS and the independent implementations. Failures were retained. No sample
was removed because the methods disagreed.

## Lin-KK comparison

The independent implementation completed 198/198 cases. Binary agreement with
the historical KAIRIS artifacts was 152/198 (76.8%).

| KAIRIS | Independent baseline | n |
|---|---:|---:|
| pass | pass | 149 |
| pass | fail | 45 |
| fail | pass | 1 |
| fail | fail | 3 |

The asymmetric disagreement indicates that the independent implementation was
more conservative under the frozen common reporting thresholds. This result
does not establish which implementation is physically correct. The methods
use different RC-grid/stopping details, so case-level residual structure must
be examined before interpreting disagreement.

## DRT comparison

The primary independent TR-NNLS condition completed 194/198 cases. Four cases
were retained as numerical failures caused by reaching the maximum iteration
count. Exact peak-count agreement with KAIRIS was 48/194 (24.7%). Important
subgroups were:

- simple Randles references: 6/6 exact peak-count agreement;
- public NMC811 cell spectra: 22/54 exact agreement;
- all project-generated synthetic families: 9/72 exact agreement;
- publication-derived synthetic spectra: 17/68 completed cases with exact
  agreement; four primary failures.

Exact count is intentionally a strict descriptive endpoint. It is highly
sensitive to regularization, discretization and peak-separation rules and must
not be interpreted as mechanistic accuracy by itself.

## DRT sensitivity conditions

| Condition | Completed | Failed | Median normalized complex RMSE | Peak count equal to primary |
|---|---:|---:|---:|---:|
| real, automatic lambda (primary) | 194 | 4 | 0.591% | 100.0% |
| real, L-curve | 193 | 5 | 0.519% | 55.2% |
| imaginary, automatic lambda | 192 | 6 | 1.739% | 22.2% |
| imaginary, L-curve | 190 | 8 | 1.032% | 19.8% |

The lower reconstruction RMSE of a sensitivity condition does not make its
peak decomposition automatically more correct. The large changes in peak
count show regularization/observable dependence and support reporting solver
sensitivity explicitly.

## Reproducibility and limitations

The executor writes one atomic JSON record per sample and can resume without
recalculating completed cases. It produces:

- `output/independent_baselines_v1/comparison_summary.json`;
- `output/independent_baselines_v1/comparison_records.csv`;
- `output/independent_baselines_v1/comparison_report.html`;
- full per-case arrays under `output/independent_baselines_v1/records/`.

Generated outputs are ignored by Git because they are reproducible artifacts.
The exact optional environment is frozen in `requirements-validation.lock`.

This execution compared against historical KAIRIS artifacts whose provenance
records identify an earlier dirty development worktree. Therefore these values
are suitable for method development and manuscript planning, not the final
submission table. Before release v1.0, the corpus must be reprocessed from a
clean tagged commit and the comparison rerun without changing the frozen
schema.

## Required next analysis

The next analysis must replace exact-count-only interpretation with one-to-one
peak matching by minimum absolute distance in `log10(tau)`, report unmatched
peaks, compare integrated DRT area and quantify recovery against known
synthetic truth. That analysis should be stratified by circuit family, frequency
coverage and noise condition, with bootstrap confidence intervals.
