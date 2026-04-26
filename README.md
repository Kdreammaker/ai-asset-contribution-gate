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

Public installs are fixture-only by default. Cloning this repository does not
grant private backend access, and public requests must not claim their own trust
tier. Private access requires a user-authorized local connector profile,
scoped access-key identifier, or controlled proxy metadata.

## Included

```text
tools/candidate_gate.py
tools/candidate-gate.ps1
tools/bootstrap-workspace.ps1
tools/assetctl-doctor.ps1
tools/user-profile.ps1
tools/vector_index.py
tools/vector-index.ps1
tools/setup-private-connector.ps1
tools/connector_client.py
tools/connector-client.ps1
assetctl-extension.json
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
.\tools\bootstrap-workspace.ps1
.\tools\assetctl-doctor.ps1
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
```

The bootstrap command creates only ignored local runtime folders such as
`reports/` and `.assetctl/`, then runs fixture validation, connector fixture
validation, leak scan, version, and a soft update check. The fixtures are
synthetic and are designed to exercise the safety gate without exposing private
asset metadata.

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
uses GitHub release metadata only when you run it. Connector and private setup
wrappers also accept `-CheckUpdates` for a non-blocking warning before major
connector operations.

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
.\tools\connector-client.ps1 -Operation new-request -CheckUpdates -Query "Korean capital market reform briefing assets: KOSPI KOSDAQ chart modules, finance icons, restrained executive palette" -AssetTypes "palette,icon,deck_component,font" -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation bundle-request -InputPath ".\reports\connector-request.json" -OutputPath ".\reports\connector-request-bundle.json"
```

For a PPT maker or presentation agent, create separate low-limit metadata
bundles for fonts, palettes, and deck components:

```powershell
.\tools\connector-client.ps1 -Operation ppt-metadata-bundles -Topic "Korean business executive KPI presentation" -Limit 3 -OutputDir ".\reports\connector\ppt-metadata"
```

This is a safe request helper, not a design preset. The PPT maker still owns
slide assembly, final design choices, font installation UX, and fallbacks.
See [`docs/PPT_MAKER_PUBLIC_ASSET_HANDOFF_GUIDE.md`](docs/PPT_MAKER_PUBLIC_ASSET_HANDOFF_GUIDE.md).

Search a public-safe metadata fixture or an approved private export metadata
file that the private workspace gives you:

```powershell
.\tools\connector-client.ps1 -Operation search-metadata -InputPath ".\fixtures\connector\public-cli-assets.fixture.jsonl" -Query "calm blue KPI deck"
```

The connector client does not contain real assets, private manifests, private
storage references, approval evidence, or generated private reports. Treat broad
requests such as "all assets", "dump", or empty browsing as unsupported for
external use; ask for a specific design intent instead. Request text must also
avoid private-only field names such as `access_key_secret`, `client_secret`,
`private_workspace_root`, private Drive file identifier fields, `local_path`, or
`trust_tier`.

`bundle-request` validates the public preflight before writing an output file.
Invalid bundles are not written by default; `-AllowInvalidOutput` is only for
clearly marked unsafe-review/debug artifacts that must not be sent.

For another PC or AI that does not have the private repository connected, the
public-only handoff is the safe default: create a request bundle locally, send
that bundle to the private asset backend owner or approved handoff channel, then
validate the returned public-safe handoff JSON:

```powershell
.\tools\connector-client.ps1 -Operation validate-bundle -InputPath ".\reports\connector-request-bundle.json"
.\tools\connector-client.ps1 -Operation validate-handoff -InputPath ".\reports\connector-response-handoff.json"
```

Returned handoffs may be metadata-search successes, deck dry-run successes,
safe rejections, or policy-blocked responses. A valid handoff must still be
public-safe: no private paths, Drive IDs, secrets, generated private reports, or
raw asset payloads.

For the current machine only, when the user has explicitly attached a
`local-maintainer` profile and the private workspace is present, the convenience
runner can dispatch through the ignored local connector config:

```powershell
.\tools\invoke-private-connector.ps1 -Operation search -InputPath ".\reports\connector-request.json"
```

Do not use this local runner as the other-PC default; other PCs should use the
request-bundle handoff unless they have their own user-authorized private
workspace or controlled proxy.

## Private Workspace Setup For AI Agents

When an AI agent installs this public toolkit and needs real asset search or
approved asset export, connect it through a user-authorized profile instead of
copying private data into this repo or exposing raw private workspace paths to
untrusted agents. The profile command shows the connection notice, records a
local audit event outside this repository, and then writes only ignored local
runtime config for this clone.

```powershell
.\tools\user-profile.ps1 -Operation authorize -ConnectorMode external-safe-proxy -ConnectorProxyUrl "<user-authorized-proxy-url>" -AccessKeyId "<key-id-only>" -AcceptNotice
.\tools\user-profile.ps1 -Operation attach
```

For a local maintainer who is allowed to point this clone at a local private
workspace, authorize the explicit path:

```powershell
.\tools\user-profile.ps1 -Operation authorize -ConnectorMode local-maintainer -PrivateWorkspaceRoot "<user-authorized-private-workspace>" -AcceptNotice
.\tools\user-profile.ps1 -Operation attach
```

Bootstrap checks for an existing user-authorized profile and auto-attaches it
unless `-SkipUserProfileAutoAttach` is supplied. A completed attach creates
ignored local config and a short connection guide at:

```text
.assetctl-private-connector.local.json
.assetctl/connection-guide.md
```

The command does not auto-clone a private repository, does not guess private
paths by default, does not store access-key secrets, and keeps the user profile
and audit log outside the repository. `AccessKeyId` is an identifier, not the
secret value.

After setup, use the public
toolkit to create and validate public-safe requests, then use the private
workspace `downloaded-assets\tools\assetctl.ps1` connector commands or the
user-authorized proxy for real metadata search, materialization proposals, and
approved package or output-specific export. Non-internal callers should receive
redacted connector responses and opaque result IDs when that backend mode is
enabled; raw private identifiers remain private-backend material. See
[`docs/PRIVATE_WORKSPACE_CONNECTOR_SETUP.md`](docs/PRIVATE_WORKSPACE_CONNECTOR_SETUP.md).

For a creator AI handoff, start with
[`docs/ASSET_SERVICE_HANDOFF_FOR_CREATOR_AI.md`](docs/ASSET_SERVICE_HANDOFF_FOR_CREATOR_AI.md).

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
