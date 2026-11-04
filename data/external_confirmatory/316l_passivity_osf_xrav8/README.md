# KAIRIS external confirmatory cohort: 316L passivity

## Status

**Selected and downloaded on 4 November 2026; not analysed by KAIRIS.**

Do not run the scientific pipeline on this cohort until the external validation
addendum has been approved, registered and tagged. Preparing the blinded file
layout is allowed because it is a deterministic representation conversion and
does not calculate KAIRIS endpoints.

## Source

- title: *Optimizing Unsupervised Clustering of Electrochemical Impedance
  Spectra via Normalization and Dimensionality Reduction*;
- creators: Sanja Martinez and collaborators;
- repository DOI: <https://doi.org/10.17605/OSF.IO/XRAV8>;
- dataset DOI: <https://doi.org/10.17632/r9snmwyzkv.1>;
- article DOI: <https://doi.org/10.1038/s41598-026-35621-3>;
- license: CC BY 4.0;
- independent institution: University of Zagreb, Faculty of Chemical
  Engineering and Technology;
- system: welded 316L stainless steel in aerated 0.1 M NaCl;
- design: 42 spectra, 36 frequencies, eight surface/region groups and two
  passivity reference groups.

Only the two source input tables were downloaded. Published clustering results,
figures and workflows were deliberately not copied into the KAIRIS cohort.

## Layout

- `raw/input_data.csv`: canonical source selected for conversion;
- `raw/input_data_merged.csv`: second source input preserved for provenance;
- `source_metadata.json`: immutable source, checksum and selection record;
- `prepared_blind/`: long-form EIS files with opaque case identifiers;
- `coordinator/blinding_key.csv`: local case-to-source mapping.

The coordinator key is ignored by Git and must not be given to expert reviewers.
The public source itself contains its group names, so the reviewer pack must be
generated from `prepared_blind/`, never from `raw/`.

## Deterministic preparation

The source stores rows of `log10(|Z|)` and positive capacitive phase-angle
magnitudes. Preparation uses:

```text
|Z| = 10**log10(|Z|)
Re(Z) = |Z| cos(phase)
-Im(Z) = |Z| sin(phase)
```

Run only the representation conversion:

```bash
python scripts/prepare_external_316l_dataset.py
```

This command verifies the canonical source SHA-256 before writing anything. It
does not import or execute the KAIRIS agents.
