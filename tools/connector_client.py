from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
CONNECTOR_SCHEMA_DIR = Path("schemas") / "connector"
CONNECTOR_FIXTURE_DIR = Path("fixtures") / "connector"
FORBIDDEN_PUBLIC_RESPONSE_FIELDS = {
    "asset_uid",
    "asset_uids",
    "drive" + "_file_id",
    "drive" + "_file_ids",
    "drive_link",
    "drive_links",
    "drive_ref",
    "drive_refs",
    "drive_url",
    "drive_urls",
    "local_path",
    "local_paths",
    "local_absolute_path",
    "local_absolute_paths",
    "manifest_path",
    "private_report_path",
    "private_report_paths",
    "private_storage_ref",
    "private_storage_refs",
    "semantic_context",
}
FORBIDDEN_PUBLIC_FIELD_NAMES = FORBIDDEN_PUBLIC_RESPONSE_FIELDS.union(
    {
        "access_key_secret",
        "access_token",
        "api_key",
        "authorization",
        "bearer_token",
        "client_secret",
        "drive_id",
        "drive_ids",
        "generated_private_report",
        "generated_private_reports",
        "github_token",
        "password",
        "private_assetctl",
        "private_workspace_root",
        "raw_asset",
        "raw_assets",
        "secret",
        "slack" + "_token",
        "storage_ref",
        "storage_refs",
        "token",
    }
)
PRIVATE_ONLY_QUERY_FIELD_NAMES = {
    "access_key_secret",
    "access_token",
    "bearer_token",
    "client_secret",
    "drive" + "_file" + "_id",
    "drive" + "_file" + "_ids",
    "drive" + "_id",
    "drive" + "_ids",
    "drive" + "_ref",
    "drive" + "_refs",
    "drive" + "_url",
    "drive" + "_urls",
    "generated_private_report",
    "generated_private_reports",
    "local_absolute_path",
    "local_absolute_paths",
    "local_path",
    "local_paths",
    "manifest_path",
    "private_assetctl",
    "private_report_path",
    "private_report_paths",
    "private_storage_ref",
    "private_storage_refs",
    "private_workspace_root",
    "raw_asset",
    "raw_assets",
    "semantic_context",
    "storage_ref",
    "storage_refs",
    "trust_tier",
}
PUBLIC_BUNDLE_TYPE = "assetctl_public_request_bundle"
PUBLIC_HANDOFF_TYPE = "assetctl_public_response_handoff"
BROAD_ENUMERATION_TERMS = {
    "*",
    "all",
    "any",
    "browse",
    "catalog",
    "crawl",
    "dump",
    "everything",
    "exhaustive",
    "full",
    "inventory",
    "library",
    "list",
    "raw",
    "registry",
    "show",
    "systematic",
}
BROAD_ENUMERATION_PHRASES = (
    "all assets",
    "all icons",
    "all files",
    "all records",
    "all registry",
    "browse all",
    "browse assets",
    "browse catalog",
    "browse everything",
    "browse icons",
    "browse library",
    "complete catalog",
    "complete inventory",
    "dump assets",
    "dump catalog",
    "dump registry",
    "entire catalog",
    "entire library",
    "entire registry",
    "export all",
    "full asset list",
    "full catalog",
    "full inventory",
    "full registry",
    "list all",
    "raw registry",
    "show all",
    "systematic enumeration",
)
DRIVE_URL_RE = re.compile(r"https?://(?:drive|docs)\.google\.com/", re.IGNORECASE)
DRIVE_ID_CONTEXT_RE = re.compile(
    r"(drive[\s_-]*(?:file[\s_-]*)?id|docs[\s_-]*(?:file[\s_-]*)?id)\s*[:=]?\s*[A-Za-z0-9_-]{20,}",
    re.IGNORECASE,
)
LOCAL_PATH_RE = re.compile(
    r"(^|\s)([A-Za-z]:[\\/]+|\\\\[^\\/]+[\\/][^\\/]+|/(?:Users|home|mnt|var|private|Volumes)/|file://)",
    re.IGNORECASE,
)
PRIVATE_REPORT_VALUE_RE = re.compile(
    r"(^|[\\/])(?:downloaded-assets[\\/])?registry[\\/]reports[\\/]",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|ya29\.[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})",
    re.IGNORECASE,
)
PPT_METADATA_REQUESTS = (
    {
        "name": "fonts",
        "asset_types": "font",
        "query_template": "{topic} readable presentation fonts for business deck",
    },
    {
        "name": "palettes",
        "asset_types": "palette",
        "query_template": "{topic} color palette for executive presentation",
    },
    {
        "name": "layouts",
        "asset_types": "deck_component",
        "query_template": "{topic} slide layout deck component for presentation",
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()[:16]}"


def tokenize(text: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    tokens: list[str] = []
    for part in re.split(r"\s+", expanded):
        if not part:
            continue
        tokens.extend(p.lower() for p in re.split(r"[^A-Za-z0-9]+", part) if len(p) > 1)
        if any(ord(ch) > 127 for ch in part):
            clean = re.sub(r"\s+", "", part.lower())
            if clean:
                tokens.append(clean)
                for size in (2, 3, 4):
                    if len(clean) >= size:
                        tokens.extend(clean[i : i + size] for i in range(0, len(clean) - size + 1))
    return list(dict.fromkeys(tokens))


def private_query_field_pattern(field_name: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in field_name.split("_")]
    separator = r"[\s_-]*"
    return re.compile(r"(?<![A-Za-z0-9])" + separator.join(parts) + r"(?![A-Za-z0-9])", re.IGNORECASE)


PRIVATE_QUERY_FIELD_PATTERNS = {
    field_name: private_query_field_pattern(field_name) for field_name in PRIVATE_ONLY_QUERY_FIELD_NAMES
}


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def relative_or_name(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.name


def required_keys_for_fixture(name: str) -> list[str]:
    mapping = {
        "asset-request.example.json": ["schema_version", "request_id", "request_type"],
        "asset-response.example.json": ["schema_version", "response_id", "request_id", "results"],
        "connector-capabilities.example.json": ["schema_version", "connector_id", "runtime_type", "commands"],
        "private-export-manifest.example.json": ["schema_version", "manifest_id", "approval", "items"],
        "deck-generation-request.example.json": ["schema_version", "request_id", "deck"],
        "deck-generation-response.example.json": ["schema_version", "response_id", "status"],
        "public-request-bundle.example.json": ["schema_version", "bundle_type", "bundle_id", "request"],
        "public-handoff-search.example.json": ["schema_version", "handoff_type", "bundle_id", "request_id", "response"],
        "public-handoff-deck-dry-run.example.json": ["schema_version", "handoff_type", "bundle_id", "request_id", "response"],
        "public-handoff-rejection.example.json": ["schema_version", "handoff_type", "bundle_id", "request_id", "errors"],
        "public-handoff-policy-blocked.example.json": ["schema_version", "handoff_type", "bundle_id", "request_id", "response", "errors"],
        "ppt-maker-discovery-response.example.json": ["contract", "response_id", "created_at", "status", "request", "candidate_groups", "public_safety"],
        "ppt-maker-package-response.example.json": ["contract", "response_id", "created_at", "status", "request", "approval", "selected_items", "public_safety"],
    }
    return mapping.get(name, [])


def validate_request_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "request_id", "request_type"):
        if not payload.get(key):
            errors.append(f"request missing required key: {key}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("request schema_version must be 1.0")
    delivery = payload.get("delivery") or {}
    if delivery.get("include_private_storage_refs") is True:
        errors.append("public requests must not ask for private storage references")
    caller = payload.get("caller") or {}
    if payload.get("trust_tier") or (isinstance(caller, dict) and caller.get("trust_tier")):
        errors.append("public requests must not claim trust_tier; the private backend assigns it")
    errors.extend(validate_public_preflight(payload, artifact_label="request"))
    return errors


def validate_response_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if is_b44_response(payload):
        return validate_b44_response_payload(payload)
    for key in ("ok", "schema_version", "response_id", "request_id", "operation_type"):
        if key not in payload:
            errors.append(f"response missing required key: {key}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("response schema_version must be 1.0")
    operation_type = str(payload.get("operation_type") or "")
    response_ok = payload.get("ok")
    is_deck_dry_run = "deck" in operation_type or "ppt" in operation_type or "dry_run" in operation_type
    if response_ok is True and is_deck_dry_run:
        for key in ("status", "pptx_created"):
            if key not in payload:
                errors.append(f"deck dry-run response missing required key: {key}")
    elif response_ok is True:
        if "results" not in payload:
            errors.append("success response missing required key: results")
    elif response_ok is False:
        if not payload.get("errors") and not payload.get("status") and not payload.get("policy_decision"):
            errors.append("rejection response must include errors, status, or policy_decision")
    for index, row in enumerate(listify(payload.get("results"))):
        if not isinstance(row, dict):
            continue
        if row.get("private_storage_ref_redacted") is False:
            errors.append(f"public response result {index} contains an unredacted private storage marker")
        leaked_fields = sorted(FORBIDDEN_PUBLIC_RESPONSE_FIELDS.intersection(row.keys()))
        if leaked_fields:
            errors.append(f"public response result {index} contains private fields: {', '.join(leaked_fields)}")
    return errors


def is_b44_response(payload: dict[str, Any]) -> bool:
    contract = payload.get("contract")
    return isinstance(contract, dict) and contract.get("name") == "b44.ppt_maker_asset_handoff"


def validate_b44_response_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("contract", "response_id", "created_at", "status", "public_safety"):
        if key not in payload:
            errors.append(f"B44 response missing required key: {key}")
    contract = payload.get("contract") or {}
    if contract.get("version") != "1.0":
        errors.append("B44 contract version must be 1.0")
    if contract.get("compatibility") != "additive_to_b43_1":
        errors.append("B44 compatibility must be additive_to_b43_1")
    public_safety = payload.get("public_safety") or {}
    expected_safety = {
        "private_refs_redacted": True,
        "contains_raw_assets": False,
        "contains_drive_ids": False,
        "contains_private_paths": False,
    }
    for key, expected in expected_safety.items():
        if public_safety.get(key) is not expected:
            errors.append(f"B44 public_safety.{key} must be {expected}")
    if "candidate_groups" in payload:
        if "request" not in payload:
            errors.append("B44 discovery response missing request")
        for group_index, group in enumerate(listify(payload.get("candidate_groups"))):
            if not isinstance(group, dict):
                errors.append(f"B44 candidate group {group_index} must be an object")
                continue
            if not group.get("asset_type"):
                errors.append(f"B44 candidate group {group_index} missing asset_type")
            for candidate_index, candidate in enumerate(listify(group.get("candidates"))):
                if not isinstance(candidate, dict):
                    errors.append(f"B44 candidate {group_index}.{candidate_index} must be an object")
                    continue
                for key in ("result_id", "stable_asset_key", "asset_type", "display_name", "availability_status", "materialization_status", "license_action"):
                    if key not in candidate:
                        errors.append(f"B44 candidate {group_index}.{candidate_index} missing {key}")
    if "selected_items" in payload:
        for key in ("request", "approval", "materialization_status", "package_manifest_available"):
            if key not in payload:
                errors.append(f"B44 package response missing {key}")
        for item_index, item in enumerate(listify(payload.get("selected_items"))):
            if not isinstance(item, dict):
                errors.append(f"B44 package selected item {item_index} must be an object")
                continue
            for key in ("result_id", "stable_asset_key", "asset_type", "display_name", "license_action", "fallback_policy", "recommended_next_action"):
                if key not in item:
                    errors.append(f"B44 package selected item {item_index} missing {key}")
    errors.extend(validate_public_data_boundary(payload, "B44 response"))
    return errors


def find_forbidden_fields(value: Any, prefix: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if str(key) in FORBIDDEN_PUBLIC_FIELD_NAMES:
                found.append(child_path)
            found.extend(find_forbidden_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_fields(child, f"{prefix}[{index}]"))
    return found


def find_forbidden_values(value: Any, prefix: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(find_forbidden_values(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_values(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        if DRIVE_URL_RE.search(value):
            found.append(f"{prefix} contains a Google Drive/Docs URL")
        if DRIVE_ID_CONTEXT_RE.search(value):
            found.append(f"{prefix} contains a Google Drive/Docs ID")
        if LOCAL_PATH_RE.search(value.strip()):
            found.append(f"{prefix} contains a local absolute path")
        if PRIVATE_REPORT_VALUE_RE.search(value.strip()):
            found.append(f"{prefix} contains a generated private report reference")
        if SECRET_VALUE_RE.search(value):
            found.append(f"{prefix} contains a secret-like value")
    return found


def find_private_query_field_mentions(query: str) -> list[str]:
    found: list[str] = []
    for field_name, pattern in PRIVATE_QUERY_FIELD_PATTERNS.items():
        if pattern.search(query):
            found.append(field_name)
    return sorted(set(found))


def validate_public_data_boundary(value: Any, artifact_label: str) -> list[str]:
    errors: list[str] = []
    forbidden = find_forbidden_fields(value)
    if forbidden:
        errors.append(f"{artifact_label} contains private-only fields: " + ", ".join(sorted(set(forbidden))))
    forbidden_values = find_forbidden_values(value)
    if forbidden_values:
        errors.append(f"{artifact_label} contains private-only values: " + ", ".join(sorted(set(forbidden_values))))
    return errors


def validate_public_preflight(payload: dict[str, Any], artifact_label: str) -> list[str]:
    errors: list[str] = []
    query = str(payload.get("query") or payload.get("intent") or "").strip()
    request_type = str(payload.get("request_type") or "")
    if not query:
        errors.append(f"{artifact_label} query/intent must not be empty")
    normalized = re.sub(r"\s+", " ", query.lower()).strip()
    query_tokens = set(tokenize(normalized))
    if normalized in {"*", "all", "any", "browse", "dump", "everything"}:
        errors.append(f"{artifact_label} query is too broad for public preflight")
    if any(phrase in normalized for phrase in BROAD_ENUMERATION_PHRASES):
        errors.append(f"{artifact_label} query asks for broad enumeration")
    if request_type in {"asset_search", "manifest_export", "deck_generation_dry_run", "asset_resolve"}:
        strong_terms = query_tokens.intersection(BROAD_ENUMERATION_TERMS)
        specific_terms = query_tokens.difference(BROAD_ENUMERATION_TERMS)
        if strong_terms and len(specific_terms) == 0:
            errors.append(f"{artifact_label} query has only enumeration terms")
    private_query_fields = find_private_query_field_mentions(query)
    if private_query_fields:
        errors.append(
            f"{artifact_label} query mentions private-only field names: "
            + ", ".join(private_query_fields)
        )
    errors.extend(validate_public_data_boundary(payload, artifact_label))
    return errors


def validate_public_bundle_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("bundle schema_version must be 1.0")
    if payload.get("bundle_type") != PUBLIC_BUNDLE_TYPE:
        errors.append(f"bundle_type must be {PUBLIC_BUNDLE_TYPE}")
    request = payload.get("request")
    if not isinstance(request, dict):
        errors.append("bundle request must be an object")
    else:
        errors.extend(validate_request_payload(request))
    errors.extend(validate_public_data_boundary(payload, "bundle"))
    return errors


def validate_public_handoff_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("handoff schema_version must be 1.0")
    if payload.get("handoff_type") != PUBLIC_HANDOFF_TYPE:
        errors.append(f"handoff_type must be {PUBLIC_HANDOFF_TYPE}")
    response = payload.get("response")
    handoff_ok = payload.get("ok")
    handoff_errors = payload.get("errors")
    if response is None:
        if handoff_ok is not False or not handoff_errors:
            errors.append("handoff response may be null only for a rejection with errors")
    elif not isinstance(response, dict):
        errors.append("handoff response must be an object or null rejection")
    else:
        errors.extend(validate_response_payload(response))
    if handoff_ok is False and not handoff_errors and not (isinstance(response, dict) and response.get("errors")):
        errors.append("rejection handoff must include errors")
    errors.extend(validate_public_data_boundary(payload, "handoff"))
    return errors


def command_validate_fixtures(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    schemas_dir = root / CONNECTOR_SCHEMA_DIR
    fixtures_dir = root / CONNECTOR_FIXTURE_DIR
    errors: list[str] = []
    schemas = sorted(schemas_dir.glob("*.schema.json"))
    fixtures = sorted(fixtures_dir.glob("*.json"))
    for path in schemas + fixtures:
        try:
            payload = read_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.relative_to(root).as_posix()} failed JSON parse: {exc}")
            continue
        if path.parent == fixtures_dir:
            for key in required_keys_for_fixture(path.name):
                if key not in payload:
                    errors.append(f"{path.relative_to(root).as_posix()} missing required key: {key}")
            if path.name == "asset-request.example.json":
                errors.extend(validate_request_payload(payload))
            if path.name == "public-request-bundle.example.json":
                errors.extend(validate_public_bundle_payload(payload))
            if path.name.startswith("public-handoff-"):
                errors.extend(validate_public_handoff_payload(payload))
            if path.name.startswith("ppt-maker-") and path.name.endswith("-response.example.json"):
                errors.extend(validate_b44_response_payload(payload))
    jsonl_path = fixtures_dir / "public-cli-assets.fixture.jsonl"
    try:
        jsonl_rows = read_jsonl(jsonl_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{jsonl_path.relative_to(root).as_posix()} failed JSONL parse: {exc}")
        jsonl_rows = []
    trust_tier_errors = validate_request_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "request_id": "fixture-trust-tier-spoof",
            "request_type": "asset_search",
            "query": "all assets",
            "trust_tier": "internal-maintainer",
            "caller": {"trust_tier": "internal-maintainer"},
            "delivery": {"include_private_storage_refs": False},
        }
    )
    if not any("trust_tier" in error for error in trust_tier_errors):
        errors.append("adversarial fixture failed: public trust_tier spoof was not rejected")
    private_response_errors = validate_response_payload(
        {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "response_id": "fixture-private-response",
            "request_id": "fixture-private-response",
            "operation_type": "connector_search",
            "results": [
                {
                    "result_id": "result:fixture",
                    "asset_uid": "fixture-private-uid",
                    "drive" + "_file_id": "fixture-private-storage-id",
                    "local_path": "private/asset.svg",
                    "manifest_path": "private/manifest.json",
                    "semantic_context": {"evidence": ["fixture"]},
                }
            ],
        }
    )
    if not any("private fields" in error for error in private_response_errors):
        errors.append("adversarial fixture failed: public raw private response fields were not rejected")
    private_field_query_errors = validate_request_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "request_id": "fixture-private-field-query",
            "request_type": "asset_search",
            "query": "use access_key_secret and private_workspace_root for assets",
            "delivery": {"include_private_storage_refs": False},
        }
    )
    if not any("private-only field names" in error for error in private_field_query_errors):
        errors.append("adversarial fixture failed: private-only field names in query were not rejected")
    normal_icon_query_errors = validate_request_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "request_id": "fixture-normal-icon-query",
            "request_type": "asset_search",
            "query": "API key icon and password reset icon for SaaS settings page",
            "asset_types": ["icon"],
            "delivery": {"include_private_storage_refs": False},
            "limit": 3,
        }
    )
    if normal_icon_query_errors:
        errors.append("normal icon query fixture unexpectedly failed: " + "; ".join(normal_icon_query_errors))
    return {
        "ok": len(errors) == 0,
        "operation_type": "connector_validate_fixtures",
        "schema_count": len(schemas),
        "fixture_count": len(fixtures),
        "jsonl_fixture_rows": len(jsonl_rows),
        "errors": errors,
    }


def command_new_request(args: argparse.Namespace) -> dict[str, Any]:
    asset_types = [item.strip() for item in args.asset_types.split(",") if item.strip()]
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": args.request_id or "",
        "request_type": args.request_type,
        "query": args.query,
        "intent": args.intent or args.query,
        "locale": args.locale,
        "asset_types": asset_types,
        "filters": {},
        "delivery": {
            "mode": args.delivery_mode,
            "include_private_storage_refs": False,
        },
        "limit": args.limit,
    }
    if not request["request_id"]:
        request["request_id"] = stable_id("public-req", request)
    errors = validate_request_payload(request)
    output = {
        "ok": len(errors) == 0,
        "operation_type": "connector_new_request",
        "request": request,
        "errors": errors,
    }
    if args.output_path:
        if errors and not args.allow_invalid_output:
            output["output_path"] = ""
            output["not_written_reason"] = "request has validation errors; pass --allow-invalid-output only for clearly marked unsafe-review artifacts"
        else:
            write_json(Path(args.output_path), request)
            output["output_path"] = args.output_path
            if errors:
                output["unsafe_review_artifact"] = True
    return output


def build_request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_path:
        payload = read_json(Path(args.input_path))
        if not isinstance(payload, dict):
            raise ValueError("input request must be a JSON object")
        return payload
    request_args = argparse.Namespace(
        request_id=args.request_id,
        request_type=args.request_type,
        query=args.query,
        intent=args.intent,
        locale=args.locale,
        asset_types=args.asset_types,
        delivery_mode=args.delivery_mode,
        limit=args.limit,
        output_path="",
        allow_invalid_output=False,
    )
    return command_new_request(request_args)["request"]


def command_bundle_request(args: argparse.Namespace) -> dict[str, Any]:
    request = build_request_from_args(args)
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "bundle_type": PUBLIC_BUNDLE_TYPE,
        "bundle_id": stable_id("public-bundle", request),
        "generated_at_utc": utc_now(),
        "source": {
            "toolkit": "ai-asset-contribution-gate",
            "local_source_path": relative_or_name(args.input_path),
        },
        "request": request,
        "safety": {
            "public_only_local_bundle": True,
            "private_repo_connected": False,
            "contains_private_paths": False,
            "contains_drive_ids": False,
            "contains_access_key_secret": False,
            "contains_raw_assets": False,
        },
        "handoff": {
            "expected_private_operation": "connector-search",
            "expected_public_response_type": PUBLIC_HANDOFF_TYPE,
            "notes": [
                "Send this bundle to the private asset backend owner or approved handoff channel.",
                "Do not add private paths, Drive IDs, raw assets, or secrets to this bundle.",
            ],
        },
    }
    errors = validate_public_bundle_payload(bundle)
    output = {
        "ok": len(errors) == 0,
        "operation_type": "connector_bundle_request",
        "bundle_id": bundle["bundle_id"],
        "request_id": request.get("request_id", ""),
        "bundle": bundle,
        "errors": errors,
    }
    if args.output_path:
        if errors and not args.allow_invalid_output:
            output["output_path"] = ""
            output["not_written_reason"] = "bundle has validation errors; pass --allow-invalid-output only for clearly marked unsafe-review artifacts"
        else:
            write_json(Path(args.output_path), bundle)
            output["output_path"] = args.output_path
            if errors:
                output["unsafe_review_artifact"] = True
    return output


def build_public_request(
    *,
    request_type: str,
    query: str,
    intent: str,
    locale: str,
    asset_types: str,
    delivery_mode: str,
    limit: int,
) -> tuple[dict[str, Any], list[str]]:
    request_args = argparse.Namespace(
        request_id="",
        request_type=request_type,
        query=query,
        intent=intent,
        locale=locale,
        asset_types=asset_types,
        delivery_mode=delivery_mode,
        limit=limit,
        output_path="",
        allow_invalid_output=False,
    )
    output = command_new_request(request_args)
    return output["request"], list(output.get("errors") or [])


def build_public_bundle(request: dict[str, Any], local_source_path: str) -> tuple[dict[str, Any], list[str]]:
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "bundle_type": PUBLIC_BUNDLE_TYPE,
        "bundle_id": stable_id("public-bundle", request),
        "generated_at_utc": utc_now(),
        "source": {
            "toolkit": "ai-asset-contribution-gate",
            "local_source_path": local_source_path,
        },
        "request": request,
        "safety": {
            "public_only_local_bundle": True,
            "private_repo_connected": False,
            "contains_private_paths": False,
            "contains_drive_ids": False,
            "contains_access_key_secret": False,
            "contains_raw_assets": False,
        },
        "handoff": {
            "expected_private_operation": "connector-search",
            "expected_public_response_type": PUBLIC_HANDOFF_TYPE,
            "notes": [
                "Send this bundle to the private asset backend owner or approved handoff channel.",
                "Do not add private paths, Drive IDs, raw assets, or secrets to this bundle.",
            ],
        },
    }
    return bundle, validate_public_bundle_payload(bundle)


def command_ppt_metadata_bundles(args: argparse.Namespace) -> dict[str, Any]:
    topic = args.topic.strip()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    outputs: list[dict[str, Any]] = []
    for spec in PPT_METADATA_REQUESTS:
        query = spec["query_template"].format(topic=topic)
        request, request_errors = build_public_request(
            request_type="asset_search",
            query=query,
            intent=query,
            locale=args.locale,
            asset_types=spec["asset_types"],
            delivery_mode="metadata_only",
            limit=args.limit,
        )
        request_path = output_dir / f"{args.prefix}-{spec['name']}-request.json"
        bundle_path = output_dir / f"{args.prefix}-{spec['name']}-bundle.json"
        bundle, bundle_errors = build_public_bundle(request, request_path.name)
        if request_errors:
            errors.extend(f"{spec['name']} request: {error}" for error in request_errors)
        if bundle_errors:
            errors.extend(f"{spec['name']} bundle: {error}" for error in bundle_errors)
        if not request_errors and not bundle_errors:
            write_json(request_path, request)
            write_json(bundle_path, bundle)
        outputs.append(
            {
                "name": spec["name"],
                "asset_types": [spec["asset_types"]],
                "query": query,
                "request_id": request.get("request_id"),
                "bundle_id": bundle.get("bundle_id"),
                "request_path": request_path.as_posix(),
                "bundle_path": bundle_path.as_posix(),
                "written": not request_errors and not bundle_errors,
                "errors": request_errors + bundle_errors,
            }
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "operation_type": "ppt_metadata_bundle_set",
        "generated_at_utc": utc_now(),
        "topic": topic,
        "limit": args.limit,
        "delivery_mode": "metadata_only",
        "private_repo_connected": False,
        "not_a_design_preset": True,
        "ppt_maker_responsibility": [
            "validate returned handoffs",
            "assemble the presentation",
            "choose the final design direction",
            "handle font install UX with user approval",
        ],
        "requests": outputs,
    }
    manifest_path = output_dir / f"{args.prefix}-manifest.json"
    if not errors:
        write_json(manifest_path, manifest)
    return {
        "ok": len(errors) == 0,
        "operation_type": "connector_ppt_metadata_bundles",
        "topic": topic,
        "limit": args.limit,
        "output_dir": output_dir.as_posix(),
        "manifest_path": manifest_path.as_posix() if not errors else "",
        "requests": outputs,
        "errors": errors,
    }


def command_validate_request(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(Path(args.input_path))
    errors = validate_request_payload(payload)
    return {
        "ok": len(errors) == 0,
        "operation_type": "connector_validate_request",
        "request_id": payload.get("request_id", ""),
        "errors": errors,
    }


def command_validate_bundle(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(Path(args.input_path))
    errors = validate_public_bundle_payload(payload)
    return {
        "ok": len(errors) == 0,
        "operation_type": "connector_validate_bundle",
        "bundle_id": payload.get("bundle_id", ""),
        "request_id": (payload.get("request") or {}).get("request_id", "") if isinstance(payload.get("request"), dict) else "",
        "errors": errors,
    }


def score_row(row: dict[str, Any], query_tokens: list[str]) -> tuple[int, list[str]]:
    text = " ".join(
        str(row.get(key, ""))
        for key in ("export_item_id", "asset_type", "name", "search_text", "relative_path")
    ).lower()
    row_tokens = set(tokenize(text))
    score = 0
    reasons: list[str] = []
    for token in query_tokens:
        if token in row_tokens:
            score += 30
            reasons.append(f"token:{token}")
        elif token in text:
            score += 10
            reasons.append(f"partial:{token}")
    if row.get("risk_level") == "low":
        score += 5
        reasons.append("policy:risk-low")
    if row.get("license_action") in ("", "none"):
        score += 3
        reasons.append("policy:license-action-none")
    return score, reasons


def command_search_metadata(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(Path(args.input_path))
    query_tokens = tokenize(args.query)
    results: list[dict[str, Any]] = []
    for row in rows:
        if args.asset_type and row.get("asset_type") != args.asset_type:
            continue
        score, reasons = score_row(row, query_tokens)
        if score <= 0:
            continue
        result = dict(row)
        result["score"] = score
        result["match_reasons"] = reasons
        result["private_storage_ref_redacted"] = True
        results.append(result)
    results.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("name", ""))))
    results = results[: max(args.limit, 0)]
    return {
        "ok": True,
        "operation_type": "connector_search_metadata",
        "query": args.query,
        "result_count": len(results),
        "results": results,
    }


def command_validate_response(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(Path(args.input_path))
    errors = validate_response_payload(payload)
    return {
        "ok": len(errors) == 0,
        "operation_type": "connector_validate_response",
        "request_id": payload.get("request_id", ""),
        "errors": errors,
    }


def command_validate_handoff(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(Path(args.input_path))
    errors = validate_public_handoff_payload(payload)
    return {
        "ok": len(errors) == 0,
        "operation_type": "connector_validate_handoff",
        "bundle_id": payload.get("bundle_id", ""),
        "request_id": payload.get("request_id", ""),
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public-safe connector request and fixture helper.")
    sub = parser.add_subparsers(dest="operation", required=True)

    validate_fixtures = sub.add_parser("validate-fixtures")
    validate_fixtures.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    validate_fixtures.set_defaults(func=command_validate_fixtures)

    new_request = sub.add_parser("new-request")
    new_request.add_argument("--request-type", default="asset_search", choices=["asset_search", "asset_resolve", "manifest_export", "deck_generation_dry_run"])
    new_request.add_argument("--request-id", default="")
    new_request.add_argument("--query", required=True)
    new_request.add_argument("--intent", default="")
    new_request.add_argument("--locale", default="auto")
    new_request.add_argument("--asset-types", default="")
    new_request.add_argument("--delivery-mode", default="metadata_only", choices=["metadata_only", "manifest_only", "materialization_proposal"])
    new_request.add_argument("--limit", type=int, default=10)
    new_request.add_argument("--output-path", default="")
    new_request.add_argument("--allow-invalid-output", action="store_true")
    new_request.set_defaults(func=command_new_request)

    bundle = sub.add_parser("bundle-request")
    bundle.add_argument("--input-path", default="")
    bundle.add_argument("--request-type", default="asset_search", choices=["asset_search", "asset_resolve", "manifest_export", "deck_generation_dry_run"])
    bundle.add_argument("--request-id", default="")
    bundle.add_argument("--query", default="")
    bundle.add_argument("--intent", default="")
    bundle.add_argument("--locale", default="auto")
    bundle.add_argument("--asset-types", default="")
    bundle.add_argument("--delivery-mode", default="metadata_only", choices=["metadata_only", "manifest_only", "materialization_proposal"])
    bundle.add_argument("--limit", type=int, default=10)
    bundle.add_argument("--output-path", default="")
    bundle.add_argument("--allow-invalid-output", action="store_true")
    bundle.set_defaults(func=command_bundle_request)

    ppt = sub.add_parser("ppt-metadata-bundles")
    ppt.add_argument("--topic", required=True)
    ppt.add_argument("--locale", default="auto")
    ppt.add_argument("--limit", type=int, default=3)
    ppt.add_argument("--output-dir", default=str(Path("reports") / "connector" / "ppt-metadata"))
    ppt.add_argument("--prefix", default="ppt-assets")
    ppt.set_defaults(func=command_ppt_metadata_bundles)

    validate_request = sub.add_parser("validate-request")
    validate_request.add_argument("--input-path", required=True)
    validate_request.set_defaults(func=command_validate_request)

    validate_bundle = sub.add_parser("validate-bundle")
    validate_bundle.add_argument("--input-path", required=True)
    validate_bundle.set_defaults(func=command_validate_bundle)

    validate_response = sub.add_parser("validate-response")
    validate_response.add_argument("--input-path", required=True)
    validate_response.set_defaults(func=command_validate_response)

    validate_handoff = sub.add_parser("validate-handoff")
    validate_handoff.add_argument("--input-path", required=True)
    validate_handoff.set_defaults(func=command_validate_handoff)

    search = sub.add_parser("search-metadata")
    search.add_argument("--input-path", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--asset-type", default="")
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(func=command_search_metadata)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
