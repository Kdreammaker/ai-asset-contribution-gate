#!/usr/bin/env python3
"""Public-safe local vector index for asset metadata.

This tool is intentionally offline by default. It builds a sparse TF-IDF vector
index from caller-provided JSON/JSONL metadata and queries that index without
calling an external embedding service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


EMBEDDING_MODEL = "local-sparse-tfidf-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_records(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return data["records"]
    raise SystemExit("Input metadata must be a JSON array, JSON object with records, or JSONL records.")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(normalize_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(normalize_text(item) for item in value.values())
    return str(value)


def tokenize(text: str) -> List[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    tokens: List[str] = []
    for part in re.split(r"\s+", expanded):
        if not part:
            continue
        tokens.extend(p.lower() for p in re.split(r"[^A-Za-z0-9]+", part) if p)
        if any(ord(ch) > 127 for ch in part):
            clean = re.sub(r"\s+", "", part.lower())
            if clean:
                tokens.append(clean)
                for size in (2, 3, 4):
                    if len(clean) >= size:
                        tokens.extend(clean[i : i + size] for i in range(0, len(clean) - size + 1))
    return [token for token in tokens if len(token) > 1]


def record_uid(record: Dict[str, Any], fallback_index: int) -> str:
    for key in ("asset_uid", "candidate_id", "id", "uid"):
        if record.get(key):
            return str(record[key])
    digest = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"record-{fallback_index:04d}-{digest}"


def record_text(record: Dict[str, Any]) -> str:
    preferred = [
        record.get("asset_name"),
        record.get("name"),
        record.get("title"),
        record.get("asset_type"),
        record.get("source_name"),
        record.get("formats"),
        record.get("usage_groups"),
        record.get("recommended_use"),
        record.get("semantic_tags_en"),
        record.get("semantic_tags_ko"),
        record.get("license_class"),
        record.get("license_action"),
        record.get("risk_level"),
        record.get("notes_for_ai"),
        record.get("description"),
        record.get("search_text"),
    ]
    return normalize_text(preferred if any(item is not None for item in preferred) else record)


def compact_metadata(record: Dict[str, Any], uid: str) -> OrderedDict:
    return OrderedDict(
        [
            ("asset_uid", uid),
            ("asset_name", record.get("asset_name") or record.get("name") or record.get("title") or ""),
            ("asset_type", record.get("asset_type", "")),
            ("source_name", record.get("source_name", "")),
            ("status", record.get("status", "")),
            ("risk_level", record.get("risk_level", "")),
            ("license_class", record.get("license_class", "")),
            ("license_action", record.get("license_action", "")),
            ("usage_groups", record.get("usage_groups", [])),
            ("formats", record.get("formats", [])),
            ("recommended_use", record.get("recommended_use", [])),
            ("semantic_tags_en", record.get("semantic_tags_en", [])),
            ("semantic_tags_ko", record.get("semantic_tags_ko", [])),
        ]
    )


def weighted_vector(counts: Counter[str], idf: Dict[str, float]) -> OrderedDict:
    total = sum(counts.values()) or 1
    weights = []
    for token, count in counts.items():
        weight = (count / total) * idf.get(token, 0.0)
        if weight > 0:
            weights.append((token, weight))
    weights.sort(key=lambda item: (-item[1], item[0]))
    norm = math.sqrt(sum(weight * weight for _, weight in weights)) or 1.0
    return OrderedDict((token, round(weight / norm, 8)) for token, weight in weights[:160])


def command_build(args: argparse.Namespace) -> Dict[str, Any]:
    input_path = Path(args.input_path).resolve()
    output_path = Path(args.output_path).resolve()
    records = read_records(input_path)
    prepared = []
    df: Counter[str] = Counter()
    for index, record in enumerate(records, start=1):
        uid = record_uid(record, index)
        text = record_text(record)
        tokens = tokenize(text)
        if not tokens:
            continue
        df.update(set(tokens))
        prepared.append((uid, record, text, tokens))
    doc_count = len(prepared)
    idf = {token: math.log((1 + doc_count) / (1 + count)) + 1.0 for token, count in df.items()}
    vector_records = []
    for uid, record, text, tokens in prepared:
        vector_records.append(
            OrderedDict(
                [
                    ("asset_uid", uid),
                    ("text_hash", hashlib.sha256(text.encode("utf-8")).hexdigest()),
                    ("vector", weighted_vector(Counter(tokens), idf)),
                    ("metadata", compact_metadata(record, uid)),
                ]
            )
        )
    payload = OrderedDict(
        [
            ("schema_version", 1),
            ("operation_type", "public_asset_vector_index"),
            ("generated_at_utc", utc_now()),
            ("embedding_model", EMBEDDING_MODEL),
            ("external_embedding_service", False),
            ("record_count", len(vector_records)),
            ("vocabulary_count", len(idf)),
            ("idf", OrderedDict(sorted((token, round(value, 8)) for token, value in idf.items()))),
            ("records", vector_records),
        ]
    )
    write_json(output_path, payload)
    return {
        "ok": True,
        "operation_type": "vector_index_build",
        "index_path": str(output_path),
        "record_count": len(vector_records),
        "vocabulary_count": len(idf),
        "embedding_model": EMBEDDING_MODEL,
        "external_embedding_service": False,
    }


def query_vector(query: str, idf: Dict[str, float]) -> OrderedDict:
    counts = Counter(tokenize(query))
    total = sum(counts.values()) or 1
    raw = [(token, (count / total) * idf.get(token, 0.0)) for token, count in counts.items()]
    raw = [(token, weight) for token, weight in raw if weight > 0]
    norm = math.sqrt(sum(weight * weight for _, weight in raw)) or 1.0
    return OrderedDict((token, weight / norm) for token, weight in raw)


def cosine(left: Dict[str, float], right: Dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * float(right.get(token, 0.0)) for token, weight in left.items())


def command_query(args: argparse.Namespace) -> Dict[str, Any]:
    index_path = Path(args.index_path).resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    idf = {str(k): float(v) for k, v in index.get("idf", {}).items()}
    qv = query_vector(args.query, idf)
    candidates = []
    for record in index.get("records", []):
        meta = record.get("metadata") or {}
        if args.asset_type and meta.get("asset_type") != args.asset_type:
            continue
        score = cosine(qv, record.get("vector") or {})
        if score > 0:
            candidates.append((score, record))
    candidates.sort(key=lambda item: (-item[0], item[1].get("metadata", {}).get("source_name", ""), item[1].get("metadata", {}).get("asset_name", "")))
    results = []
    for score, record in candidates[: max(args.limit, 0)]:
        meta = record.get("metadata") or {}
        results.append(
            OrderedDict(
                [
                    ("asset_uid", meta.get("asset_uid", "")),
                    ("asset_name", meta.get("asset_name", "")),
                    ("source_name", meta.get("source_name", "")),
                    ("asset_type", meta.get("asset_type", "")),
                    ("risk_level", meta.get("risk_level", "")),
                    ("license_action", meta.get("license_action", "")),
                    ("vector_score", round(score, 6)),
                ]
            )
        )
    return {
        "ok": True,
        "operation_type": "vector_index_query",
        "query": args.query,
        "index_path": str(index_path),
        "embedding_model": index.get("embedding_model", ""),
        "external_embedding_service": bool(index.get("external_embedding_service", False)),
        "result_count": len(results),
        "results": results,
    }


def command_validate_fixtures(args: argparse.Namespace) -> Dict[str, Any]:
    fixture = Path(args.fixture_path).resolve()
    index_path = Path(args.output_path).resolve()
    build_result = command_build(argparse.Namespace(input_path=str(fixture), output_path=str(index_path)))
    query_result = command_query(argparse.Namespace(index_path=str(index_path), query="dashboard security icon", asset_type="icon", limit=3))
    errors = []
    if not query_result["results"]:
        errors.append("expected at least one vector query result")
    elif query_result["results"][0]["asset_name"] != "shield-check":
        errors.append(f"expected shield-check top result, got {query_result['results'][0]['asset_name']}")
    return {
        "ok": not errors,
        "operation_type": "vector_index_fixture_validation",
        "build": build_result,
        "query": query_result,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public-safe local vector index")
    sub = parser.add_subparsers(dest="operation", required=True)

    build = sub.add_parser("build")
    build.add_argument("--input-path", required=True)
    build.add_argument("--output-path", required=True)
    build.set_defaults(func=command_build)

    query = sub.add_parser("query")
    query.add_argument("--index-path", required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--asset-type", default="")
    query.add_argument("--limit", type=int, default=10)
    query.set_defaults(func=command_query)

    fixtures = sub.add_parser("validate-fixtures")
    fixtures.add_argument("--fixture-path", default=str(Path(__file__).resolve().parent / "fixtures" / "vector-assets.fixture.jsonl"))
    fixtures.add_argument("--output-path", default=str(Path(__file__).resolve().parents[1] / "reports" / "vector-index-fixture.json"))
    fixtures.set_defaults(func=command_validate_fixtures)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
