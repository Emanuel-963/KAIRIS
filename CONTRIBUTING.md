# Contributing to KAIRIS

Thank you for helping improve KAIRIS. Contributions that improve scientific
validity, reproducibility, file-format compatibility, accessibility, tests, or
documentation are welcome.

## Before contributing

- Open an issue describing the scientific or engineering problem before a large
  change.
- Do not include confidential spectra, personal data, credentials, or datasets
  whose redistribution terms are unclear.
- Keep scientific claims conservative. A numerical classification must not be
  presented as proof of a unique electrochemical mechanism.
- Changes to frozen scientific thresholds must include a rationale, tests, a
  new benchmark version, and an explicit note that prior validation no longer
  applies unchanged.

## Development workflow

1. Create a branch from `main`.
2. Create a virtual environment and install development dependencies:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

3. Add or update tests for the change.
4. Run:

   ```bash
   python -m pytest -q
   python setup_kairis.py --check
   ```

5. Open a pull request explaining the change, its scientific impact, validation
   performed, and any compatibility implications.

## Reporting problems and requesting support

Use GitHub Issues for reproducible bugs, feature proposals, documentation
questions, and support requests. Include the operating system, Python version,
KAIRIS commit or release, anonymized input format, command used, and relevant
error log. Do not publish sensitive experimental data in an issue.

Security-sensitive reports should follow `SECURITY.md` instead of being posted
publicly.

## Authorship and acknowledgement

Code contribution does not automatically determine scientific-paper authorship.
Paper authorship will follow documented scholarly contributions and the policy
of the target journal. Software contributors remain visible in the Git history
and release notes.
