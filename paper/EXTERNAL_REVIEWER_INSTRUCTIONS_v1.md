# KAIRIS external blinded review — frozen instructions v1

**Public identifiers:** Reviewer A, Reviewer B and Reviewer R only. Personal
identifiers and declarations must remain in the coordinator's private records.

## Material supplied

Reviewers receive an opaque case identifier, a CSV with frequency, real and
imaginary impedance, and a figure containing raw Nyquist and Bode views. Source
condition, subgroup, publication labels and every KAIRIS output remain hidden.

Reviewer A and Reviewer B complete the full cohort independently. They must not
discuss cases or inspect KAIRIS results before both first-round files are locked
and hashed. Reviewer R follows the replacement/adjudication rule in
`REVIEWER_ROLES_AND_CONFLICTS_v1.md`.

## Frozen fields and allowed values

| Field | Allowed values | Decision rule |
|---|---|---|
| `spectrum_quality` | `acceptable`, `questionable`, `unusable` | judge whether the measured spectrum supports cautious interpretation; do not infer source condition |
| `dominant_response` | `kinetic`, `diffusive`, `pseudocapacitive`, `mixed`, `inductive`, `undetermined` | select one only when the raw spectrum supports it; use `undetermined` rather than forcing a label |
| `estimated_process_count` | `0`–`5`, `undetermined` | apparent resolvable processes, not a claim that an equivalent circuit is unique |
| `intercalation_pseudocapacitive` | `yes`, `no`, `uncertain` | compatibility of the observed response, not proof of material chemistry |
| `confidence_1_to_5` | integer `1`–`5` | 1 = very low; 5 = very high |
| `exclude_from_analysis` | `yes`, `no` | use `yes` only for unusable/corrupt measurement, never for an unusual result |
| `exclusion_reason` | free text | mandatory when exclusion is proposed |
| `reviewer_comment` | free text | optional concise rationale |

The review form must preserve the original `case_id` values and contain one row
per case. Missing answers are not silently imputed. An administrative query may
ask only whether an accidental omission should be filled; it may not suggest a
scientific answer.

## Locking and adjudication

1. The coordinator validates only schema and completeness.
2. Each returned file receives a SHA-256 hash and is made read-only.
3. Inter-reviewer agreement is calculated before any discussion.
4. Disagreements remain in the primary record. Reviewer R may adjudicate them
   only afterward and without seeing KAIRIS outputs.
5. The source key is opened only after the registered analysis permits it.

The primary human reference for dominant response is exact pre-adjudication
agreement between A and B. A disagreement or `undetermined` answer is a human
abstention, not a KAIRIS error. Adjudicated results are secondary.
