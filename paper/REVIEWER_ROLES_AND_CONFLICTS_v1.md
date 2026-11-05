# KAIRIS blinded-review panel: roles and declarations — draft v1

**Status:** public, de-identified role specification; identities, qualifications
and declarations are kept in the coordinator's private records

**Applies to:** the 42-case external 316L/0.1 M NaCl confirmatory cohort and any
retrospective cohort explicitly assigned to the same review round

## Scientific-design principle

Both primary specialists evaluate the same cases and complete the same full
annotation form independently. Responsibilities are not divided by KAIRIS
module. This overlap is required to estimate inter-reviewer agreement and to
preserve a human reference that is independent of DRT, GSF, ESC and the KAIRIS
orchestrator outputs.

The dataset is externally sourced. No claim of institutional independence is
made solely from the source of the cohort. Blinding, file separation, timing and
immutable hashes provide operational independence of the first-round
annotations. Relationships and conflicts are evaluated from private declarations.

## Panel assignments

### Primary specialist A — Reviewer A

Responsibilities:

1. complete every field of the frozen form for all eligible cases;
2. evaluate spectral quality, dominant response, apparent process count,
   compatibility with intercalation pseudocapacitance, confidence and any
   proposed exclusion;
3. work without access to source labels, KAIRIS outputs or the other reviewer's
   decisions;
4. record uncertainty as `indeterminate` rather than infer a forced mechanism;
5. return the completed file to the coordinator by the frozen deadline;
6. participate in post-agreement discussion only after both primary files have
   been hashed and locked.

### Primary specialist B — Reviewer B

Responsibilities are identical to those of specialist A. Neither primary
specialist has interpretive priority. Reviewer identifiers A and B are retained
in the analysis so that disagreement is auditable, but comparative performance
rankings between reviewers are outside the study objectives.

### Reserve specialist and adjudicator — Reviewer R

Two mutually exclusive operational roles are possible in a review round:

1. **replacement reviewer:** annotate the full cohort independently and blindly
   if one primary reviewer triggers the reserve-activation rule; or
2. **adjudicator:** review only unresolved disagreements after the original
   agreement statistics have been calculated, without access to KAIRIS outputs.

If Reviewer R replaces a primary reviewer, that person must not also be presented as an
independent third adjudicator for that same round. Any subsequent adjudication
would require a different, pre-declared person or the cases would remain
unresolved and be reported as such.

## Coordinator role

The responsible researcher acts as data coordinator, not as a blinded reviewer
or adjudicator. The coordinator:

- generates the blinded package and retains the identification key;
- distributes identical instructions and frozen training material;
- answers only administrative or schema questions during independent review;
- receives files, performs completeness checks and records SHA-256 hashes;
- calculates agreement before any discussion or adjudication;
- records protocol deviations without changing annotations;
- opens the key only at the stage authorized by the registered protocol.

The coordinator must not suggest classifications, disclose KAIRIS results or
silently correct a reviewer's scientific response.

## Reserve-activation rule

The reserve is activated as a replacement if a primary specialist:

- declines or withdraws;
- misses the frozen delivery deadline;
- returns a technically unreadable file that cannot be recovered; or
- leaves more than 10% of required fields missing after one neutral
  administrative completeness query.

Activation, reason, date and affected review round must be logged. A late primary
form received after reserve activation is preserved but is not substituted into
the confirmatory analysis based on which result is more favorable.

## Required declarations before package delivery

Each panel member must provide:

- full name and institutional affiliation;
- highest completed degree and relevant EIS experience;
- ORCID, if available;
- written acceptance of the assigned role and deadline;
- relationships with the authors, project or software;
- financial, intellectual, supervisory or collaborative conflicts;
- confirmation that the first-round annotations will be completed without
  consultation with another panel member or inspection of KAIRIS results.

Supervisory or collaborative relationships are disclosed, not treated as an
automatic reason for exclusion. They must be stated accurately in the article's
methods and limitations.

## Private sign-off record

The coordinator maintains an untracked private record mapping Reviewer A,
Reviewer B and Reviewer R to their identities and storing affiliation, ORCID,
role acceptance, conflict declaration and accepted deadline. The public
repository must contain neither that mapping nor the individual declarations.
