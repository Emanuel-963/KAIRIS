# Journal selection for the KAIRIS scientific article

**Decision date:** 4 November 2026

## Primary target: Electrochimica Acta

*Electrochimica Acta* is the recommended primary venue. KAIRIS is not merely a
software package or a collection of performance results: it proposes a
reproducible, multiperspective protocol for acquiring evidence from EIS while
separating mathematical validation, relaxation structure, global spectral
descriptors, ESC geometry and deterministic interpretation. That contribution
fits the journal only if the article demonstrates new electrochemical insight,
external validation and explicit domains of validity.

The manuscript should therefore lead with the scientific protocol and its
validation, not with the web dashboard or Ollama integration. Software
engineering evidence belongs in reproducibility sections and supplementary
material.

Official scope:
<https://www.sciencedirect.com/journal/electrochimica-acta/about/aims-and-scope>

Official author guidance and LaTeX instructions:
<https://www.elsevier.com/en-gb/researcher/author/policies-and-guidelines/latex-instructions>

## Alternative: Journal of Electroanalytical Chemistry

The *Journal of Electroanalytical Chemistry* is the first alternative if the
final contribution is more analytical/methodological than mechanistic. Its scope
welcomes theoretical and applied electrochemistry but still requires novelty,
quality and adequate interpretation. It is not a fallback for an incompletely
validated protocol.

Official journal page:
<https://www.sciencedirect.com/journal/journal-of-electroanalytical-chemistry>

## Template decision

The working manuscript uses Elsevier's official CAS single-column template,
version 2.4, obtained from CTAN. The original file is retained unchanged as
`elsevier-cas-sc-template-original.tex`; `main.tex` is the KAIRIS working copy.
The class and template are distributed under the LaTeX Project Public License.

Before submission, the current *Guide for Authors* must be checked again. Elsevier
normally accepts a manuscript PDF for initial submission, but journal-specific
requirements and reference style may change.

## Editorial positioning

Working article type: full research article.

Working scientific claim:

> KAIRIS is a reproducible multiperspective EIS protocol that integrates
> spectral admissibility, DRT, GSF and ESC, quantifies agreement and
> disagreement between distinct observables, and abstains when evidence is
> insufficient.

Claims of automatic causal identification of electrochemical mechanisms remain
out of scope unless supported by independent physical evidence.
