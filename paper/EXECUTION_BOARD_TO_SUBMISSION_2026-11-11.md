# KAIRIS execution board — 11 November 2026 to submission

**Scientific article deadline:** 16 February 2027  
**JOSS package deadline:** ready by 16 February 2027; submit when eligible  
**Rule:** external KAIRIS processing remains locked until all registration gates
pass. Work below is parallelized specifically to avoid waiting idly for reviewer
administration.

## Current state

- external scientific addendum: complete and frozen;
- analysis code/config identity: complete;
- 42-case blind preparation: complete;
- reviewer pack: generated and hash-manifested;
- panel administration: two acceptances reported; conflict declarations pending;
- OSF registration: draft/bundle preparation in progress;
- external KAIRIS results: none;
- manuscript: Introduction and Methods underway;
- retrospective corpus: 198/198 completed, development evidence only.

## Workstreams and dependencies

| Stream | Can run now? | Blocks external run? | Deliverable |
|---|---|---|---|
| Reviewer acceptances/conflicts | yes | yes | private complete sign-off record |
| OSF draft and attachment bundle | yes | yes | reviewed registration draft and immutable ZIP |
| Blinded review of raw cases | yes, after distribution | no for software run; yes for P2 | two locked forms |
| Lin–KK reference comparison | yes | no | baseline report and reproducible script |
| Independent DRT comparison | yes | no | solver comparison and sensitivity table |
| GSF/ESC ablations | yes on retrospective data | no | incremental-information report |
| Robustness/sensitivity | yes on synthetic/retrospective data | no | noise/truncation/density figures |
| Manuscript Introduction/Methods | yes | no | submission-ready text without invented results |
| External KAIRIS execution | no | — | 42 locked JSON/HTML records |
| Confirmatory P1/P2 analysis | no | — | registered statistical report |
| Independent reproduction | partially | no | Windows/Linux/macOS evidence |

## Sprint 1 — 11 to 18 November 2026

1. finalize OSF Secondary Data Preregistration text;
2. build and independently inspect the OSF attachment ZIP;
3. obtain conflict declarations from the two accepted panel members;
4. obtain the third role acceptance or record reserve activation planning;
5. distribute separate blind review packages after administrative completeness;
6. select the established Lin–KK baseline and freeze its version;
7. select the independent DRT solver and freeze its version;
8. continue Methods and prepare empty result-table schemas.

**Exit criterion:** OSF draft ready for final human review, all required private
panel records complete, baseline tools selected, no external KAIRIS results
opened.

## Sprint 2 — 19 November to 10 December 2026

1. submit OSF registration, public or embargoed as decided;
2. record identifier, timestamp, visibility and attached bundle SHA-256;
3. unlock only after the readiness checker passes;
4. execute the 42 cases once in a fresh directory without LLM;
5. run P1 integrity evaluation;
6. continue independent human review without revealing KAIRIS outputs;
7. execute Lin–KK/DRT baselines on permitted retrospective and external inputs
   according to the registered plan;
8. execute frozen ablations and sensitivity analyses.

**Exit criterion:** external run immutable, P1 known, blinded human forms still
independent, all deviations logged.

## Sprint 3 — 11 December 2026 to 10 January 2027

1. lock and hash Reviewer A/B forms;
2. calculate pre-adjudication agreement;
3. adjudicate only after agreement is preserved;
4. execute P2 and secondary registered analyses;
5. classify disagreements and abstentions;
6. produce final tables and figures directly from artifacts;
7. draft Results and Discussion;
8. run independent reproduction on at least one non-development machine.

**Exit criterion:** all registered analyses complete, denominators explicit,
tables/figures reproducible, no result selected post hoc.

## Sprint 4 — 11 to 31 January 2027

1. complete Windows, Linux and macOS reproduction;
2. document 4 GB and 8 GB operation;
3. resolve P0 defects only, with deviation records where applicable;
4. freeze KAIRIS v1.0 release candidate;
5. complete manuscript and supplement;
6. prepare Zenodo archive, DOI metadata and `CITATION.cff`;
7. prepare JOSS paper and review checklist.

**Exit criterion:** release candidate reproducible, manuscript internally
complete, archive draft ready.

## Sprint 5 — 1 to 16 February 2027

1. final author review and declarations;
2. verify journal guide and submission files;
3. regenerate every table/figure from the release candidate;
4. create release `v1.0.0` and archival DOI;
5. perform clean-room reproduction of the article commands;
6. submit the scientific article by 16 February;
7. preserve the JOSS-ready package until the eligibility date.

## Work that remains outside the critical path

- fine-tuning LLM weights;
- cosmetic dashboard expansion;
- new modules beyond Lin–KK, DRT, GSF and ESC;
- unregistered new external cohorts;
- speculative mechanism labels;
- merging experimental standalone science into frozen confirmatory endpoints.

## Weekly control questions

1. Did any work inspect external KAIRIS outcomes before registration?
2. Does every reported result identify its code commit and data role?
3. Are reviewer identities and declarations still private?
4. Are retrospective, confirmatory and exploratory claims separated?
5. Is any new feature displacing a P0 validation or manuscript task?
6. Can the current table/figure be regenerated by one documented command?

