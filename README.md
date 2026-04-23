# assetctl Public Toolkit

Public-safe starter toolkit for candidate-gated asset workspace workflows.

This repository intentionally contains only reusable tooling, schemas,
synthetic fixtures, and generic documentation. It does not contain real asset
files, private registry exports, generated reports, Drive linkage, worklogs,
approval records, connector evidence, or local machine paths.

## Included

```text
tools/candidate_gate.py
tools/candidate-gate.ps1
schemas/candidate-record.schema.json
schemas/operation-proposal.schema.json
fixtures/candidates/*.fixture.json
tools/fixtures/candidates/*.fixture.json
docs/CANDIDATE_CONTRIBUTION_GATE.md
docs/PUBLIC_TOOLKIT_CLI_DESIGN.md
```

## Safety Defaults

```text
safe open-source candidate -> review_required
unknown license -> license_review_required
paid license -> license_review_required
commercial restriction -> license_review_required
brand/trademark -> license_review_required
duplicate SHA -> rejected
malformed record -> preflight_failed
```

The toolkit does not activate registry records. Promotion remains dry-run and
approval-gated unless a private workspace implements its own approved activation
step.

## Quick Check

From this repository root:

```powershell
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
```

The fixtures are synthetic and are designed to exercise the B31-B safety gate
without exposing private asset metadata.

## License

The owner has not selected a public reuse license yet. Until a license is
chosen, treat the repository as source-available only.
