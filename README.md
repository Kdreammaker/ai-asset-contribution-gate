# AI Asset Contribution Safety Gate

[![Smoke Test](https://github.com/Kdreammaker/ai-asset-contribution-gate/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/Kdreammaker/ai-asset-contribution-gate/actions/workflows/smoke-test.yml)

Public-safe starter toolkit and connector client for AI agents that need a
governed asset service. It can review user-submitted asset candidates before
they enter a private registry, and it can create public-safe requests for a
private asset backend that serves metadata, recommendations, and approved
export packages to any system that needs governed design assets. Website and
presentation builders are common examples, not the boundary of the service.

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
tools/setup-private-connector.ps1
tools/connector_client.py
tools/connector-client.ps1
schemas/candidate-record.schema.json
schemas/operation-proposal.schema.json
schemas/connector/*.schema.json
tools/fixtures/candidates/*.fixture.json
tools/fixtures/vector-assets.fixture.jsonl
fixtures/connector/*.json
fixtures/connector/public-cli-assets.fixture.jsonl
docs/CANDIDATE_CONTRIBUTION_GATE.md
docs/PUBLIC_TOOLKIT_CLI_DESIGN.md
docs/PRIVATE_WORKSPACE_CONNECTOR_SETUP.md
docs/ASSET_SERVICE_HANDOFF_FOR_CREATOR_AI.md
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

## Private Connector Client Contract

Build and validate public-safe requests for a private asset backend:

```powershell
.\tools\connector-client.ps1 -Operation validate-fixtures
.\tools\connector-client.ps1 -Operation new-request -Query "Korean capital market reform briefing assets: KOSPI KOSDAQ chart modules, finance icons, restrained executive palette" -AssetTypes "palette,icon,deck_component,font" -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\connector-request.json"
```

Search a public-safe metadata fixture or an approved private export metadata
file that the private workspace gives you:

```powershell
.\tools\connector-client.ps1 -Operation search-metadata -InputPath ".\fixtures\connector\public-cli-assets.fixture.jsonl" -Query "calm blue KPI deck"
```

The connector client does not contain real assets, private manifests, private
storage references, approval evidence, or generated private reports.

## Private Workspace Setup For AI Agents

When an AI agent installs this public toolkit and needs real asset search or
approved asset export, connect it to the private workspace instead of copying
private data into this repo:

```powershell
.\tools\setup-private-connector.ps1 -PrivateWorkspaceRoot "<path-to-private-workspace>"
```

This creates ignored local config at:

```text
.assetctl-private-connector.local.json
```

After setup, use the public toolkit to create and validate public-safe requests,
then use the private workspace `downloaded-assets\tools\assetctl.ps1` connector
commands for real metadata search, materialization proposals, and approved
package or output-specific export. See
[`docs/PRIVATE_WORKSPACE_CONNECTOR_SETUP.md`](docs/PRIVATE_WORKSPACE_CONNECTOR_SETUP.md).

For a creator AI handoff, start with
[`docs/ASSET_SERVICE_HANDOFF_FOR_CREATOR_AI.md`](docs/ASSET_SERVICE_HANDOFF_FOR_CREATOR_AI.md).

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
