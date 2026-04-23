# Security Policy

## Scope

This repository contains public-safe tooling for reviewing AI asset contribution
candidates before a private asset registry accepts them.

Security-sensitive issues include:

- private asset registry data exposed in public files
- real asset payloads, generated reports, approval records, or connector state
  committed to the repository
- local machine paths, Drive identifiers, Slack tokens, or host bridge details
  appearing in public content
- candidate promotion paths that can activate assets without explicit approval
- unsafe license/source handling that lets unknown, paid, commercially
  restricted, or brand-controlled assets become active automatically

## Reporting

Please report security concerns privately through GitHub's security reporting
features when available. If private reporting is not available, open a minimal
issue that describes the affected area without including secrets, private paths,
tokens, real asset payloads, or private registry records.

## Safe Handling

Do not post secrets, private registry excerpts, raw asset files, generated
report payloads, or connector evidence in public issues, pull requests, or
discussion threads. Use synthetic examples whenever possible.

## Validation

Before publishing changes, run:

```powershell
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
.\tools\candidate-gate.ps1 -Operation leak-scan -Path .
```

The GitHub Actions smoke test runs the same core checks on pushes and pull
requests.
