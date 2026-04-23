# Contributing

Thank you for helping improve AI Asset Contribution Safety Gate.

This repository is public so people can inspect, clone, fork, and reuse the
toolkit. Public visibility does not grant direct write access to the upstream
repository. External contributors should work through forks and pull requests
unless they have been explicitly added as collaborators.

## Contribution Flow

1. Fork the repository.
2. Create a focused branch in your fork.
3. Keep changes small and reviewable.
4. Run the smoke checks locally.
5. Open a pull request against `main`.

## Local Checks

From the repository root:

```powershell
python -m py_compile .\tools\candidate_gate.py
python -m json.tool .\schemas\candidate-record.schema.json
python -m json.tool .\schemas\operation-proposal.schema.json
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
.\tools\candidate-gate.ps1 -Operation leak-scan -Path .
```

The GitHub Actions smoke test runs the same core checks on pushes and pull
requests.

## Safety Rules

Do not include:

```text
real private asset payloads
private registry exports
generated report payloads
Drive IDs, folder URLs, or connector state
Slack tokens, channel IDs, or host bridge details
local machine paths
approval records
worklogs or handoff prompts
```

Use synthetic fixtures for tests and examples.

## Candidate Gate Expectations

The gate must remain proposal-first and non-mutating by default.

Expected outcomes:

```text
safe open-source candidate -> review_required
unknown license -> license_review_required
paid license -> license_review_required
commercial restriction -> license_review_required
brand/trademark -> license_review_required
duplicate SHA -> rejected
malformed record -> preflight_failed
unapproved promotion -> blocked
```

## Licensing

By intentionally submitting a contribution for inclusion in this project, you
agree that the contribution is provided under the Apache License, Version 2.0,
unless you explicitly state otherwise in writing.
