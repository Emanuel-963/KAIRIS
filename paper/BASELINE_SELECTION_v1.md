# KAIRIS independent baseline selection — draft v1

**Decision date:** 11 November 2026  
**Scope:** supporting comparisons; no change to registered P1/P2 definitions  
**Installation status:** installed and smoke-tested in isolated environment
**External 42-case outputs inspected:** no

## 1. Purpose

The article requires independent reference implementations for Lin–KK and DRT.
These comparisons test implementation dependence, numerical sensitivity and
domains of disagreement. They are not a vote between algorithms and do not
authorize replacement of the frozen KAIRIS confirmatory output by whichever
baseline appears more favorable.

The baseline environment must be separate from the production requirements so
that KAIRIS remains lightweight and usable without these optional packages.

## 2. Lin–KK baseline candidate

**Package:** `impedance` / impedance.py  
**Candidate version:** `1.7.1`  
**Method:** `impedance.validation.linKK`  
**Project:** <https://github.com/ECSHackWeek/impedance.py>  
**Documentation:**
<https://impedancepy.readthedocs.io/en/latest/examples/validation_example.html>

Rationale:

- independent open-source implementation;
- implements the Schönleber Lin–KK construction;
- exposes fitted impedance, residuals, number of RC elements and μ;
- widely documented and scriptable;
- compatible with a lightweight batch comparison.

Frozen comparison inputs:

- identical frequency and complex-impedance vectors after KAIRIS import;
- no filtering based on KAIRIS pass/fail;
- cutoff `c=0.85`;
- maximum RC count matched to the KAIRIS configuration where the API permits;
- capacitance option recorded explicitly;
- version and effective call parameters retained per run.

Planned outputs:

- Lin–KK fitted spectrum;
- normalized complex RMSE recomputed by one common comparison function;
- pointwise normalized residue and failure fraction under the frozen KAIRIS
  reporting thresholds;
- fitted RC count and μ;
- binary agreement table plus four discrepancy cells;
- case-level residual plots for every disagreement, without post hoc removal.

Exact numerical identity is not required because weighting, stopping and model
details can differ. The comparison reports both implementations rather than
declaring one automatically correct.

## 3. DRT baseline candidate

**Package:** `pyimpspec`  
**Candidate version:** `5.2.0`  
**Method:** TR-NNLS (`calculate_drt_tr_nnls`)  
**Project:** <https://github.com/vyrjana/pyimpspec>  
**Documentation:** <https://vyrjana.github.io/pyimpspec/guide_drt.html>

Rationale:

- actively documented release supporting Python 3.12;
- independent TR-NNLS implementation;
- exposes time constants, gamma, reconstructed impedance, residuals and λ;
- supports automatic regularization selection;
- traces the implementation to the published Kulikovsky TR-NNLS method.

The package is GPL-3.0-or-later. It will be an optional validation dependency,
not copied into or redistributed as KAIRIS source. The validation environment,
package version and license attribution must be recorded.

Frozen comparison inputs:

- identical imported frequency and complex-impedance vectors;
- no exclusion based on KAIRIS DRT convergence or peak morphology;
- real and imaginary modes evaluated according to a predeclared comparison
  matrix, with the primary candidate mode chosen before external outputs;
- automatic λ and at least one shared fixed-λ sensitivity condition;
- raw baseline grid preserved; interpolation to a common log-τ grid used only
  for explicitly labelled curve-distance metrics.

Planned outputs:

- reconstructed-impedance error;
- selected λ and method mode;
- number and location of peaks using one common 5% relative prominence rule;
- one-to-one peak matching by minimum absolute error in `log10(tau)`;
- integrated DRT area under a documented log-time convention;
- curve distance after interpolation to a common grid;
- failed/nonconverged cases retained and counted.

Known-parameter synthetic families provide the interpretable recovery reference.
For experimental spectra without ground truth, differences between DRT solvers
are sensitivity results, not proof that either peak set is physically true.

## 4. Why pyDRTtools is not the first batch candidate

`pyDRTtools` remains scientifically relevant and may be used as a secondary
sensitivity implementation. It provides Tikhonov/RBF methods, Bayesian Hilbert
transform tools and uncertainty options. It was not selected as the first batch
candidate because its primary workflow and dependency set are GUI-oriented,
which increases automation and cross-platform burden for the February deadline.

This is an engineering prioritization, not a judgment that pyDRTtools is
scientifically inferior.

## 5. Dataset roles

| Dataset | Use in baseline work |
|---|---|
| simple synthetic references | parameter-recovery comparison |
| broader 198-case corpus | retrospective agreement and failure characterization |
| 42-case external cohort | only after OSF registration/unlock; supporting registered comparison |

No baseline package may be tuned on the external cohort. Any dependency failure
on Windows, Linux or macOS is reported as a portability result.

## 6. Environment and reproducibility

Candidate pins are isolated in `requirements-validation.txt`. Before final
freeze, the project must record:

1. installed package versions and transitive lock;
2. Python version and operating system;
3. license metadata;
4. exact command and configuration;
5. clean Git commit;
6. whether each baseline succeeded, failed or abstained per case.

Installation or downloads remain explicit and user-confirmed. The packages are
not required for normal KAIRIS execution.

## 7. Operational freeze and smoke-test result

The candidate selection became operational on 11 November 2026 after:

- installation of `impedance==1.7.1` and `pyimpspec==5.2.0` in isolated
  Python 3.12.14 on Windows;
- a smoke test on all six synthetic `randles_rc` fixtures;
- inspection of impedance and time-constant sign conventions;
- freezing `config/baseline_comparison_schema_v1.json`;
- selection of TR-NNLS `mode="real", lambda_value=-1.0` as the primary DRT
  comparison before any external output was generated;
- retention of imaginary-mode and L-curve (`lambda_value=-2.0`) conditions as
  declared sensitivity analyses.

All four DRT conditions recovered one peak in each of the six simple Randles
fixtures. Primary-mode normalized complex reconstruction RMSE ranged from
0.223% to 0.959%. The independent Lin-KK implementation did not meet the
KAIRIS pass thresholds on these noisy fixtures (RMSE 15.20%–32.69%). This
difference is retained as an implementation-disagreement result; thresholds
or stopping rules were not retuned to force agreement.

`impedance.py 1.7.1` omits `numpy` from the evaluation namespace used by its
generated Lin-KK circuit expression. The adapter supplies that namespace entry
without changing the package equations and records the compatibility action in
each output.

The exact transitive environment is in `requirements-validation.lock`. The
input pin file SHA-256 is
`c35b015597554f22c81282c6bf4e58ac4763db3b8330a3fba4a543b42a592081`.
Generated smoke evidence remains under ignored `output/`; it contains no
external-confirmatory result.

These are now validated *comparison implementations*, not proof of mechanistic
ground truth. The 42-case external cohort remains locked.

