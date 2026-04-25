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
    "drive" + "_file_id",
    "drive" + "_file_ids",
    "drive_ref",
    "drive_refs",
    "local_path",
    "manifest_path",
    "semantic_context",
}
PUBLIC_BUNDLE_TYPE = "assetctl_public_request_bundle"
PUBLIC_HANDOFF_TYPE = "assetctl_public_response_handoff"


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
    return errors


def validate_response_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("ok", "schema_version", "response_id", "request_id", "operation_type", "results"):
        if key not in payload:
            errors.append(f"response missing required key: {key}")
    for index, row in enumerate(listify(payload.get("results"))):
        if not isinstance(row, dict):
            continue
        if row.get("private_storage_ref_redacted") is False:
            errors.append(f"public response result {index} contains an unredacted private storage marker")
        leaked_fields = sorted(FORBIDDEN_PUBLIC_RESPONSE_FIELDS.intersection(row.keys()))
        if leaked_fields:
            errors.append(f"public response result {index} contains private fields: {', '.join(leaked_fields)}")
    return errors


def find_forbidden_fields(value: Any, prefix: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key in FORBIDDEN_PUBLIC_RESPONSE_FIELDS:
                found.append(child_path)
            if key in {"private_workspace_root", "private_assetctl", "local_absolute_path", "access_key_secret"}:
                found.append(child_path)
            found.extend(find_forbidden_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_fields(child, f"{prefix}[{index}]"))
    return found


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
    forbidden = find_forbidden_fields(payload)
    if forbidden:
        errors.append("bundle contains private-only fields: " + ", ".join(sorted(set(forbidden))))
    return errors


def validate_public_handoff_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("handoff schema_version must be 1.0")
    if payload.get("handoff_type") != PUBLIC_HANDOFF_TYPE:
        errors.append(f"handoff_type must be {PUBLIC_HANDOFF_TYPE}")
    response = payload.get("response")
    if not isinstance(response, dict):
        errors.append("handoff response must be an object")
    else:
        errors.extend(validate_response_payload(response))
    forbidden = find_forbidden_fields(payload)
    if forbidden:
        errors.append("handoff contains private-only fields: " + ", ".join(sorted(set(forbidden))))
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
        write_json(Path(args.output_path), request)
        output["output_path"] = args.output_path
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
        write_json(Path(args.output_path), bundle)
        output["output_path"] = args.output_path
    return output


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
    bundle.set_defaults(func=command_bundle_request)

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
