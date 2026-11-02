# Security policy

## Supported versions

Until the first stable release, security fixes are applied to the current
`main` branch. After KAIRIS 1.0, supported release lines will be listed here.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that may expose credentials,
local files, unpublished spectra, or arbitrary code execution. Use GitHub's
private vulnerability reporting feature when it is enabled for this repository.
If that feature is unavailable, contact the repository owner privately through
their GitHub profile and provide only the minimum information needed to arrange
a secure exchange.

KAIRIS should be run on trusted local input files. The local web panel and
Ollama endpoint must not be exposed directly to an untrusted public network.
