# AI Asset Contribution Safety Gate

[![Smoke Test](https://github.com/Kdreammaker/ai-asset-contribution-gate/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/Kdreammaker/ai-asset-contribution-gate/actions/workflows/smoke-test.yml)

Public-safe starter toolkit for reviewing user-submitted AI asset candidates
before they can enter a private asset registry.

This repository intentionally contains only reusable tooling, schemas,
synthetic fixtures, and generic documentation. It does not contain real asset
files, private registry exports, generated reports, Drive linkage, worklogs,
approval records, connector evidence, or local machine paths.

## Included

```text
tools/candidate_gate.py
tools/candidate-gate.ps1
tools/vector_index.py
tools/vector-index.ps1
schemas/candidate-record.schema.json
schemas/operation-proposal.schema.json
tools/fixtures/candidates/*.fixture.json
tools/fixtures/vector-assets.fixture.jsonl
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

## Version And Updates

Show the local gate version:

```powershell
.\tools\candidate-gate.ps1 -Operation version
```

Check whether a newer public release is available:

```powershell
.\tools\candidate-gate.ps1 -Operation update-check
```

Normal commands remain offline by default. The update check is explicit and
uses GitHub release metadata only when you run it.

## Local Vector Index

Build a local sparse vector index from your own public-safe asset metadata:

```powershell
.\tools\vector-index.ps1 -Operation build -InputPath ".\my-assets.jsonl" -OutputPath ".\reports\my-vector-index.json"
```

Query it:

```powershell
.\tools\vector-index.ps1 -Operation query -IndexPath ".\reports\my-vector-index.json" -Query "dashboard security icon" -AssetType icon
```

This is not an external Vector DB and does not call an embedding API. It is a
small offline TF-IDF vector layer that complements registry policy checks and
graph/relationship exploration in private workspaces.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
