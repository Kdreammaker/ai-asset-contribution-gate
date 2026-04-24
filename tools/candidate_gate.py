#!/usr/bin/env python3
"""B31-B candidate contribution and license safety gate.

The tool writes candidate records and review reports only. It never mutates the
active registry, source policy, license policy, Drive state, or raw asset
storage.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TOOL_NAME = "ai-asset-contribution-gate"
TOOL_VERSION = "v0.3.0"
DEFAULT_REPOSITORY = "Kdreammaker/ai-asset-contribution-gate"

ALLOWED_FORMATS = {
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".pptx",
    ".potx",
    ".odp",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".json",
    ".md",
    ".csv",
}

LICENSE_OPEN_TERMS = {
    "mit",
    "apache-2.0",
    "apache 2.0",
    "bsd",
    "cc0",
    "public domain",
    "mpl-2.0",
    "isc",
    "open-source",
    "open source",
}
LICENSE_FONT_TERMS = {"ofl", "sil ofl", "open-font", "open font"}
LICENSE_UNKNOWN_TERMS = {"", "unknown", "unclear", "unspecified", "none", "n/a"}
LICENSE_PAID_TERMS = {
    "paid",
    "premium",
    "marketplace",
    "commercial license",
    "royalty-free",
    "stock",
}
LICENSE_RESTRICTED_TERMS = {
    "restricted",
    "editorial only",
    "non-commercial",
    "personal use",
    "no commercial use",
    "commercially restricted",
}
LICENSE_BRAND_TERMS = {"brand-guidelines", "brand guidelines", "trademark", "logo"}

BRAND_TERMS = {
    "logo",
    "brand",
    "trademark",
    "google",
    "microsoft",
    "apple",
    "amazon",
    "facebook",
    "meta",
    "slack",
    "github",
    "twitter",
    "x-logo",
    "youtube",
    "linkedin",
    "netflix",
    "adobe",
}

PAID_SOURCE_TERMS = {
    "envato",
    "creative market",
    "creativemarket",
    "shutterstock",
    "istock",
    "getty",
    "adobe stock",
    "depositphotos",
    "freepik premium",
    "paid",
    "premium",
}

PROHIBITED_USAGE_TERMS = {
    "nft",
    "ai-training",
    "ai training",
    "resale",
    "redistribution-asset-pack",
    "asset pack",
    "logo",
    "trademark",
}

STATUS_TO_DIR = {
    "submitted": "pending",
    "preflight_failed": "preflight-failed",
    "review_required": "review-required",
    "license_review_required": "license-review-required",
    "approved": "approved",
    "rejected": "rejected",
    "promoted": "promoted",
    "superseded": "superseded",
}

DEFAULT_SOURCE_POLICY = {
    "sources": {
        "Tabler Icons": {
            "license_class": "open-source",
            "license_action": "none",
            "risk_level": "low",
            "brand_guidelines_required": False,
        }
    }
}

DEFAULT_LICENSE_POLICY = {
    "license_classes": {
        "open-source": {"default_risk_level": "low", "default_action": "none"},
        "open-font": {"default_risk_level": "low", "default_action": "check-license-file"},
        "free-with-restrictions": {"default_risk_level": "medium", "default_action": "check-source-policy"},
        "brand-guidelines": {"default_risk_level": "restricted", "default_action": "check-brand-guidelines"},
        "unknown": {"default_risk_level": "unknown", "default_action": "avoid"},
    }
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(parts: Iterable[str]) -> str:
    text = "|".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z._-]+", "-", value.strip()).strip("-").lower()
    return slug or "candidate"


def bool_or_none(value: str) -> Optional[bool]:
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def normalize_license(value: str) -> Tuple[str, str]:
    text = str(value or "").strip().lower()
    if text in LICENSE_UNKNOWN_TERMS:
        return ("unknown", "unknown license")
    if any(term in text for term in LICENSE_PAID_TERMS):
        return ("paid-license", "paid or marketplace license")
    if any(term in text for term in LICENSE_RESTRICTED_TERMS):
        return ("commercially-restricted", "commercial use restriction")
    if any(term in text for term in LICENSE_BRAND_TERMS):
        return ("brand-guidelines", "brand or trademark license")
    if text in LICENSE_FONT_TERMS or any(term in text for term in LICENSE_FONT_TERMS):
        return ("open-font", "open font license")
    if text in LICENSE_OPEN_TERMS or any(term in text for term in LICENSE_OPEN_TERMS):
        return ("open-source", "open source license")
    return ("unknown", "unrecognized declared license")


def load_registry_sha_index(registry_path: Path) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    if not registry_path.exists():
        return index
    with registry_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            sha = str(record.get("sha256") or "")
            if sha and sha not in index:
                index[sha] = {
                    "asset_uid": str(record.get("asset_uid") or ""),
                    "asset_name": str(record.get("asset_name") or ""),
                    "status": str(record.get("status") or ""),
                    "source_name": str(record.get("source_name") or ""),
                }
    return index


def lookup_source_policy(source_policy: Dict[str, Any], source_name: str) -> Optional[Dict[str, Any]]:
    sources = source_policy.get("sources") or {}
    if source_name in sources:
        return dict(sources[source_name])
    for name, rule in sources.items():
        prefix = str(rule.get("match_prefix") or "")
        if prefix and source_name.startswith(prefix):
            result = dict(rule)
            result["_matched_source_name"] = name
            return result
    return None


def check(name: str, status: str, reason: str = "", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {"name": name, "status": status}
    if reason:
        result["reason"] = reason
    if details:
        result["details"] = details
    return result


def candidate_text(candidate: Dict[str, Any]) -> str:
    fields = [
        candidate.get("candidate_id"),
        candidate.get("source_url"),
        candidate.get("source_name"),
        candidate.get("declared_license"),
        candidate.get("asset_type"),
        candidate.get("intended_use"),
        candidate.get("user_notes"),
    ]
    for file_item in candidate.get("files") or []:
        fields.extend([file_item.get("name"), file_item.get("path"), file_item.get("format")])
    return " ".join(str(item or "") for item in fields).lower()


def preflight_candidate(
    candidate: Dict[str, Any],
    assets_root: Path,
    synthetic_sha_index: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    source_policy_path = assets_root / "registry" / "source-policy.json"
    license_policy_path = assets_root / "registry" / "license-policy.json"
    source_policy = read_json(source_policy_path) if source_policy_path.exists() else DEFAULT_SOURCE_POLICY
    license_policy = read_json(license_policy_path) if license_policy_path.exists() else DEFAULT_LICENSE_POLICY
    registry_sha_index = load_registry_sha_index(assets_root / "registry" / "asset-registry.jsonl")
    if synthetic_sha_index:
        registry_sha_index.update(synthetic_sha_index)

    checks: List[Dict[str, Any]] = []
    hard_fail = False
    license_review = False
    duplicate = False

    required = ["candidate_id", "candidate_type", "submitted_by_role", "asset_type"]
    missing_required = [field for field in required if not str(candidate.get(field) or "").strip()]
    files = list(candidate.get("files") or [])
    if missing_required or not files:
        hard_fail = True
        checks.append(check("metadata_completeness", "fail", "missing required candidate fields", {"missing": missing_required}))
    else:
        checks.append(check("metadata_completeness", "pass", "required candidate fields are present"))

    source_url = str(candidate.get("source_url") or "").strip()
    if source_url:
        checks.append(check("source_url_presence", "pass", "source URL declared"))
    else:
        license_review = True
        checks.append(check("source_url_presence", "review", "source URL is required before promotion"))

    declared_license = str(candidate.get("declared_license") or candidate.get("declared_license_class") or "")
    license_class, license_reason = normalize_license(declared_license)
    candidate["declared_license_class"] = license_class
    if license_class in {"unknown", "paid-license", "commercially-restricted", "brand-guidelines"}:
        license_review = True
        checks.append(check("license_policy_lookup", "review", license_reason, {"declared_license_class": license_class}))
    else:
        known_class = license_class in (license_policy.get("license_classes") or {})
        checks.append(check("license_policy_lookup", "pass" if known_class else "warn", license_reason, {"declared_license_class": license_class}))

    commercial_allowed = candidate.get("declared_commercial_use_allowed")
    if commercial_allowed is True:
        checks.append(check("commercial_use_declaration", "pass", "commercial use declared allowed"))
    elif commercial_allowed is False:
        license_review = True
        checks.append(check("commercial_use_declaration", "review", "commercial use is declared restricted"))
    else:
        license_review = True
        checks.append(check("commercial_use_declaration", "review", "commercial use declaration is missing"))

    source_name = str(candidate.get("source_name") or "").strip()
    source_rule = lookup_source_policy(source_policy, source_name)
    if source_rule:
        source_risk = str(source_rule.get("risk_level") or "")
        source_license = str(source_rule.get("license_class") or "")
        source_brand = bool(source_rule.get("brand_guidelines_required"))
        if source_brand or source_license == "brand-guidelines" or source_risk in {"restricted", "unknown"}:
            license_review = True
            checks.append(check("known_source_policy_lookup", "review", "known source requires extra review", {"risk_level": source_risk, "license_class": source_license}))
        else:
            checks.append(check("known_source_policy_lookup", "pass", "source policy matched", {"risk_level": source_risk, "license_class": source_license}))
    else:
        license_review = True
        checks.append(check("known_source_policy_lookup", "review", "source is not in source-policy.json"))

    file_failures = []
    duplicate_hits = []
    for file_item in files:
        sha = str(file_item.get("sha256") or "").strip().lower()
        fmt = str(file_item.get("format") or Path(str(file_item.get("name") or file_item.get("path") or "")).suffix).lower()
        if not sha:
            file_failures.append({"file": file_item.get("name") or file_item.get("path") or "", "reason": "missing sha256"})
        if fmt and not fmt.startswith("."):
            fmt = f".{fmt}"
        if fmt not in ALLOWED_FORMATS:
            file_failures.append({"file": file_item.get("name") or file_item.get("path") or "", "reason": f"unsupported format {fmt or '(missing)'}"})
        if sha and sha in registry_sha_index:
            duplicate = True
            duplicate_hits.append({"sha256": sha, "duplicate_of": registry_sha_index[sha]})
    if file_failures:
        hard_fail = True
        checks.append(check("file_hash_and_allowed_format", "fail", "file hash or format check failed", {"failures": file_failures}))
    else:
        checks.append(check("file_hash_and_allowed_format", "pass", "file hashes and formats are present"))
    if duplicate_hits:
        checks.append(check("duplicate_sha_check", "fail", "candidate duplicates an existing registry SHA", {"duplicates": duplicate_hits}))
    else:
        checks.append(check("duplicate_sha_check", "pass", "no duplicate SHA found"))

    text = candidate_text(candidate)
    brand_hits = sorted(term for term in BRAND_TERMS if re.search(rf"(^|[^a-z0-9]){re.escape(term)}([^a-z0-9]|$)", text))
    if brand_hits:
        license_review = True
        checks.append(check("brand_trademark_keyword_scan", "review", "brand or trademark-like terms found", {"hits": brand_hits}))
    else:
        checks.append(check("brand_trademark_keyword_scan", "pass", "no brand/trademark keyword hits"))

    paid_hits = sorted(term for term in PAID_SOURCE_TERMS if term in text)
    if paid_hits:
        license_review = True
        checks.append(check("paid_marketplace_source_scan", "review", "paid or marketplace source terms found", {"hits": paid_hits}))
    else:
        checks.append(check("paid_marketplace_source_scan", "pass", "no paid marketplace terms found"))

    prohibited_hits = sorted(term for term in PROHIBITED_USAGE_TERMS if term in text)
    if prohibited_hits:
        license_review = True
        checks.append(check("prohibited_usage_scan", "review", "prohibited or restricted usage terms found", {"hits": prohibited_hits}))
    else:
        checks.append(check("prohibited_usage_scan", "pass", "no prohibited usage terms found"))

    if hard_fail:
        status = "preflight_failed"
    elif duplicate:
        status = "rejected"
    elif license_review:
        status = "license_review_required"
    else:
        status = "review_required"

    candidate["status"] = status
    candidate["preflight"] = {
        "status": status,
        "checked_at_utc": utc_now(),
        "checks": checks,
    }
    candidate.setdefault("approval", {"status": "not_requested"})
    return candidate


def build_candidate_from_args(args: argparse.Namespace, assets_root: Path) -> Dict[str, Any]:
    file_path = Path(args.file).resolve() if args.file else None
    files: List[Dict[str, Any]] = []
    if file_path:
        if not file_path.exists():
            raise SystemExit(f"Candidate file does not exist: {file_path}")
        files.append(
            {
                "path": str(file_path),
                "name": file_path.name,
                "sha256": sha256_file(file_path),
                "size_bytes": file_path.stat().st_size,
                "format": file_path.suffix.lower(),
            }
        )
    if args.metadata:
        metadata = read_json(Path(args.metadata))
        for item in metadata.get("files") or []:
            files.append(dict(item))

    seed = [
        args.candidate_id,
        args.candidate_type,
        args.source_url,
        args.source_name,
        args.declared_license,
        args.asset_type,
        files[0]["sha256"] if files else utc_now(),
    ]
    candidate_id = args.candidate_id or f"cand-{stable_id(seed)}"
    return {
        "candidate_id": candidate_id,
        "candidate_type": args.candidate_type,
        "submitted_by_role": args.submitted_by_role,
        "submitted_at_utc": utc_now(),
        "status": "submitted",
        "source_url": args.source_url or "",
        "source_name": args.source_name or "",
        "declared_license": args.declared_license or "",
        "declared_commercial_use_allowed": bool_or_none(args.declared_commercial_use_allowed),
        "declared_attribution_required": bool_or_none(args.declared_attribution_required),
        "asset_type": args.asset_type or "unknown",
        "intended_use": args.intended_use or "",
        "files": files,
        "user_notes": args.notes or "",
        "preflight": {"status": "submitted", "checks": []},
        "approval": {"status": "not_requested", "reviewed_by_role": None, "reviewed_at_utc": None, "notes": ""},
    }


def candidate_output_path(assets_root: Path, candidate: Dict[str, Any]) -> Path:
    status = str(candidate.get("status") or "submitted")
    status_dir = STATUS_TO_DIR.get(status, "pending")
    candidate_id = slugify(str(candidate.get("candidate_id") or "candidate"))
    return assets_root / "candidates" / status_dir / f"{candidate_id}.candidate.json"


def write_candidate_reports(assets_root: Path, reviewed: List[Dict[str, Any]]) -> Dict[str, str]:
    reports_root = assets_root / "registry" / "reports"
    preflight_report = {
        "ok": True,
        "operation_type": "candidate_preflight",
        "generated_at_utc": utc_now(),
        "candidate_count": len(reviewed),
        "summary": summarize_candidates(reviewed),
        "candidates": reviewed,
    }
    license_report = {
        "ok": True,
        "operation_type": "candidate_license_review",
        "generated_at_utc": utc_now(),
        "candidate_count": len([item for item in reviewed if item.get("status") == "license_review_required"]),
        "candidates": [item for item in reviewed if item.get("status") == "license_review_required"],
    }
    duplicate_report = {
        "ok": True,
        "operation_type": "candidate_duplicate_review",
        "generated_at_utc": utc_now(),
        "candidate_count": len([item for item in reviewed if item.get("status") == "rejected"]),
        "candidates": [item for item in reviewed if item.get("status") == "rejected"],
    }
    paths = {
        "preflight_report": str(reports_root / "candidate-preflight-report.json"),
        "license_review_report": str(reports_root / "candidate-license-review-report.json"),
        "duplicate_report": str(reports_root / "candidate-duplicate-report.json"),
    }
    write_json(Path(paths["preflight_report"]), preflight_report)
    write_json(Path(paths["license_review_report"]), license_report)
    write_json(Path(paths["duplicate_report"]), duplicate_report)
    return paths


def summarize_candidates(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for item in candidates:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"status_counts": counts}


def command_add(args: argparse.Namespace) -> Dict[str, Any]:
    assets_root = Path(args.assets_root).resolve()
    candidate = build_candidate_from_args(args, assets_root)
    reviewed = preflight_candidate(candidate, assets_root)
    output_path = Path(args.output_path).resolve() if args.output_path else candidate_output_path(assets_root, reviewed)
    write_json(output_path, reviewed)
    report_paths = write_candidate_reports(assets_root, [reviewed])
    return {
        "ok": True,
        "operation_type": "candidate_add",
        "candidate": reviewed,
        "candidate_path": str(output_path),
        "reports": report_paths,
        "active_registry_mutated": False,
    }


def command_review(args: argparse.Namespace) -> Dict[str, Any]:
    assets_root = Path(args.assets_root).resolve()
    input_paths: List[Path] = []
    if args.input_path:
        input_paths.append(Path(args.input_path).resolve())
    else:
        candidate_root = assets_root / "candidates"
        input_paths.extend(candidate_root.glob("**/*.candidate.json"))
    reviewed: List[Dict[str, Any]] = []
    for path in input_paths:
        candidate = read_json(path)
        reviewed_candidate = preflight_candidate(candidate, assets_root)
        reviewed.append(reviewed_candidate)
        if args.apply:
            write_json(candidate_output_path(assets_root, reviewed_candidate), reviewed_candidate)
    report_paths = write_candidate_reports(assets_root, reviewed)
    return {
        "ok": True,
        "operation_type": "candidate_review",
        "candidate_count": len(reviewed),
        "summary": summarize_candidates(reviewed),
        "reports": report_paths,
        "active_registry_mutated": False,
    }


def command_promote(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.input_path:
        raise SystemExit("candidate promote requires --input-path")
    assets_root = Path(args.assets_root).resolve()
    candidate = read_json(Path(args.input_path).resolve())
    errors: List[str] = []
    warnings: List[str] = []
    role = str(args.actor_role or "user").lower()
    approval = candidate.get("approval") or {}
    preflight = candidate.get("preflight") or {}
    if candidate.get("status") != "approved":
        errors.append("candidate status must be approved before promotion")
    if approval.get("status") != "approved":
        errors.append("candidate approval.status must be approved before promotion")
    if role not in {"admin", "master"}:
        errors.append("candidate promotion requires admin/master actor role")
    if preflight.get("status") not in {"review_required", "approved"}:
        errors.append("candidate preflight status must be review_required or approved before promotion")
    if not args.approve:
        warnings.append("dry-run only; pass --approve after explicit approval to mark ready for private activation")

    report = {
        "ok": len(errors) == 0,
        "operation_type": "candidate_promotion_dry_run",
        "generated_at_utc": utc_now(),
        "candidate_id": candidate.get("candidate_id"),
        "actor_role": role,
        "approve_requested": bool(args.approve),
        "active_registry_mutated": False,
        "would_write_active_registry": False,
        "ready_for_private_registry_activation": bool(args.approve and not errors),
        "warnings": warnings,
        "errors": errors,
        "candidate": candidate,
    }
    output_path = Path(args.output_path).resolve() if args.output_path else assets_root / "registry" / "reports" / "candidate-promotion-dry-run-report.json"
    write_json(output_path, report)
    return report


def fixture_expected_status(path: Path, record: Dict[str, Any]) -> str:
    expected = record.get("expected_preflight_status")
    if expected:
        return str(expected)
    stem = path.stem
    if "safe-open-source" in stem:
        return "review_required"
    if "duplicate" in stem:
        return "rejected"
    if "malformed" in stem:
        return "preflight_failed"
    return "license_review_required"


def command_validate_fixtures(args: argparse.Namespace) -> Dict[str, Any]:
    assets_root = Path(args.assets_root).resolve()
    fixture_root = Path(args.fixture_root).resolve() if args.fixture_root else assets_root / "tools" / "fixtures" / "candidates"
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    for path in sorted(fixture_root.glob("*.fixture.json")):
        record = read_json(path)
        synthetic_index = {}
        if record.pop("test_registry_duplicate_sha", False):
            for file_item in record.get("files") or []:
                synthetic_index[str(file_item.get("sha256") or "")] = {
                    "asset_uid": "fixture:existing-active-asset",
                    "asset_name": "Synthetic existing active asset",
                    "status": "active",
                    "source_name": "Synthetic Fixture Source",
                }
        reviewed = preflight_candidate(record, assets_root, synthetic_index)
        expected = fixture_expected_status(path, record)
        ok = reviewed.get("status") == expected
        if not ok:
            errors.append(f"{path.name}: expected {expected}, got {reviewed.get('status')}")
        result = {
            "fixture": str(path),
            "expected_status": expected,
            "actual_status": reviewed.get("status"),
            "ok": ok,
        }
        if "expected_promotion_ok" in record:
            promotion_report = simulate_promotion(record, actor_role="user", approve=True)
            promotion_expected = bool(record.get("expected_promotion_ok"))
            promotion_ok = bool(promotion_report.get("ok")) == promotion_expected
            if not promotion_ok:
                errors.append(f"{path.name}: expected promotion ok={promotion_expected}, got {promotion_report.get('ok')}")
            result["promotion_expected_ok"] = promotion_expected
            result["promotion_actual_ok"] = bool(promotion_report.get("ok"))
            result["promotion_errors"] = promotion_report.get("errors", [])
            result["ok"] = bool(result["ok"] and promotion_ok)
        results.append(result)
    report = {
        "ok": len(errors) == 0,
        "operation_type": "candidate_fixture_validation",
        "generated_at_utc": utc_now(),
        "fixture_count": len(results),
        "results": results,
        "errors": errors,
    }
    output_path = Path(args.output_path).resolve() if args.output_path else assets_root / "registry" / "reports" / "candidate-fixture-validation-report.json"
    write_json(output_path, report)
    return report


def simulate_promotion(candidate: Dict[str, Any], actor_role: str, approve: bool) -> Dict[str, Any]:
    errors: List[str] = []
    role = str(actor_role or "user").lower()
    approval = candidate.get("approval") or {}
    preflight = candidate.get("preflight") or {}
    if candidate.get("status") != "approved":
        errors.append("candidate status must be approved before promotion")
    if approval.get("status") != "approved":
        errors.append("candidate approval.status must be approved before promotion")
    if role not in {"admin", "master"}:
        errors.append("candidate promotion requires admin/master actor role")
    if preflight.get("status") not in {"review_required", "approved"}:
        errors.append("candidate preflight status must be review_required or approved before promotion")
    return {
        "ok": len(errors) == 0,
        "approve_requested": approve,
        "actor_role": role,
        "errors": errors,
    }


def command_leak_scan(args: argparse.Namespace) -> Dict[str, Any]:
    target = Path(args.path).resolve()
    skipped_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "candidates",
        "registry",
        "reports",
    }
    skipped_files = {
        ".assetctl-private-connector.local.json",
    }
    patterns = {
        "local_absolute_path": re.compile(r"([A-Za-z]:\\Users\\|/Users/|\\\\[^\\]+\\[^\\]+)"),
        "drive_url": re.compile(r"https://drive\.google\.com/|drive_file_id|drive_folder_id", re.I),
        "slack_secret_or_id": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+|\bslack\s+(?:bot\s+)?token\b|\bSLACK_(?:BOT_)?TOKEN\b", re.I),
        "slack_channel_reference": re.compile(r"\b(?:slack_channel_id|slack-channel-id|channel_id|channel-id)\b|<#C[A-Z0-9]{8,}", re.I),
        "host_bridge_path": re.compile(r"host-main|setting auto system|Send_Workspace_Slack_Message", re.I),
    }
    findings: List[Dict[str, Any]] = []
    files: Iterable[Path]
    if target.is_file():
        files = [target]
    else:
        files = [
            item
            for item in target.rglob("*")
            if item.is_file()
            and item.name.lower() not in skipped_files
            and item.suffix.lower() in {".md", ".json", ".jsonl", ".ps1", ".py", ".yml", ".yaml", ".txt"}
            and not any(part.lower() in skipped_dirs for part in item.relative_to(target).parts[:-1])
        ]
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if file_path.name == Path(__file__).name and "re.compile(" in line:
                continue
            for name, pattern in patterns.items():
                if pattern.search(line):
                    findings.append({"file": str(file_path), "line": line_number, "check": name})
    report = {
        "ok": len(findings) == 0,
        "operation_type": "public_safe_leak_scan",
        "generated_at_utc": utc_now(),
        "target": str(target),
        "finding_count": len(findings),
        "findings": findings,
    }
    if args.output_path:
        write_json(Path(args.output_path).resolve(), report)
    return report


def normalize_version(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("refs/tags/"):
        text = text[len("refs/tags/"):]
    return text


def command_version(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "ok": True,
        "operation_type": "version",
        "tool_name": TOOL_NAME,
        "version": TOOL_VERSION,
        "repository": DEFAULT_REPOSITORY,
    }


def command_update_check(args: argparse.Namespace) -> Dict[str, Any]:
    current_version = normalize_version(args.current_version or TOOL_VERSION)
    repository = args.repository or DEFAULT_REPOSITORY
    url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = urllib.request.Request(url, headers={"User-Agent": f"{TOOL_NAME}/{TOOL_VERSION}"})
    try:
        with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "operation_type": "update_check",
            "tool_name": TOOL_NAME,
            "current_version": current_version,
            "repository": repository,
            "latest_version": "",
            "update_available": False,
            "errors": [str(exc)],
        }

    latest_version = normalize_version(payload.get("tag_name", ""))
    latest_url = payload.get("html_url", "")
    update_available = bool(latest_version and latest_version != current_version)
    return {
        "ok": True,
        "operation_type": "update_check",
        "tool_name": TOOL_NAME,
        "current_version": current_version,
        "repository": repository,
        "latest_version": latest_version,
        "latest_url": latest_url,
        "update_available": update_available,
        "message": (
            f"Update available: {current_version} -> {latest_version}"
            if update_available
            else f"Current version is up to date: {current_version}"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="B31-B candidate safety gate")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--assets-root", default=str(Path(__file__).resolve().parents[1]))
        sub.add_argument("--output-path", default="")

    add_parser = subparsers.add_parser("add")
    add_common(add_parser)
    add_parser.add_argument("--file", default="")
    add_parser.add_argument("--metadata", default="")
    add_parser.add_argument("--candidate-id", default="")
    add_parser.add_argument("--candidate-type", default="asset_candidate")
    add_parser.add_argument("--submitted-by-role", default="user")
    add_parser.add_argument("--source-url", default="")
    add_parser.add_argument("--source-name", default="")
    add_parser.add_argument("--declared-license", default="")
    add_parser.add_argument("--declared-commercial-use-allowed", default="")
    add_parser.add_argument("--declared-attribution-required", default="")
    add_parser.add_argument("--asset-type", default="unknown")
    add_parser.add_argument("--intended-use", default="")
    add_parser.add_argument("--notes", default="")
    add_parser.set_defaults(func=command_add)

    review_parser = subparsers.add_parser("review")
    add_common(review_parser)
    review_parser.add_argument("--input-path", default="")
    review_parser.add_argument("--apply", action="store_true")
    review_parser.set_defaults(func=command_review)

    promote_parser = subparsers.add_parser("promote")
    add_common(promote_parser)
    promote_parser.add_argument("--input-path", default="")
    promote_parser.add_argument("--actor-role", default="user")
    promote_parser.add_argument("--approve", action="store_true")
    promote_parser.set_defaults(func=command_promote)

    fixture_parser = subparsers.add_parser("validate-fixtures")
    add_common(fixture_parser)
    fixture_parser.add_argument("--fixture-root", default="")
    fixture_parser.set_defaults(func=command_validate_fixtures)

    leak_parser = subparsers.add_parser("leak-scan")
    leak_parser.add_argument("--path", required=True)
    leak_parser.add_argument("--output-path", default="")
    leak_parser.set_defaults(func=command_leak_scan)

    version_parser = subparsers.add_parser("version")
    version_parser.set_defaults(func=command_version)

    update_parser = subparsers.add_parser("update-check")
    update_parser.add_argument("--current-version", default=TOOL_VERSION)
    update_parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    update_parser.add_argument("--timeout-seconds", type=int, default=10)
    update_parser.set_defaults(func=command_update_check)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
