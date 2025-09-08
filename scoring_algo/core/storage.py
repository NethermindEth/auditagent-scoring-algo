from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .types import CategoryEnum, EvaluatedFinding, Vulnerability


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_scan_path(repository: str, data_root: Path, scan_source: str) -> Path:
    return data_root / scan_source / f"{repository}_results.json"


def get_evaluation_path(repository: str, output_root: Path) -> Path:
    return output_root / f"{repository}_results.json"


def get_truth_path(repository: str, data_root: Path) -> Path:
    return data_root / "source_of_truth" / f"{repository}.json"


def normalize_severity(value: Any) -> str:
    if not isinstance(value, str):
        return "N/A"
    v = value.strip().lower()
    mapping = {
        "critical": "High",
        "high": "High",
        "med": "Medium",
        "medium": "Medium",
        "moderate": "Medium",
        "low": "Low",
        "informational": "Info",
        "info": "Info",
        "best practices": "Best Practices",
        "best_practices": "Best Practices",
    }
    return mapping.get(v, value.title())


def _ensure_list(obj: Any) -> List[str]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return [str(x) for x in obj if x is not None]
    return [str(obj)]


def _map_category_from_vulnerability_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    if "reentrancy" in v:
        return CategoryEnum.REENTRANCY.value
    if "access control" in v or "authentication" in v:
        return CategoryEnum.ACCESS_CONTROL.value
    if "overflow" in v or "underflow" in v or "integer" in v:
        return CategoryEnum.INTEGER_OVERFLOW_UNDERFLOW.value
    if "denial of service" in v or "denial-of-service" in v or "dos" in v:
        return CategoryEnum.DENIAL_OF_SERVICE.value
    if "unchecked" in v and "call" in v:
        return CategoryEnum.UNCHECKED_CALL.value
    if "front" in v and "run" in v:
        return CategoryEnum.FRONT_RUNNING.value
    if "config" in v:
        return CategoryEnum.CONFIG_DEPENDENT.value
    if "precision" in v or "round" in v:
        return CategoryEnum.PRECISION_LOSS.value
    if "centralization" in v:
        return CategoryEnum.CENTRALIZATION_RISK.value
    if (
        "logic" in v
        or "validation" in v
        or "business" in v
        or "state corruption" in v
        or "storage collision" in v
    ):
        return CategoryEnum.BUSINESS_LOGIC.value
    return None


def _to_vulnerability(item: Dict[str, Any]) -> Vulnerability:
    # Map diverse shapes to our Vulnerability model (Pydantic)
    issue = item.get("Issue") or item.get("title") or item.get("Title") or item.get("issue") or ""
    description = item.get("Description") or item.get("description")
    severity = normalize_severity(item.get("Severity") or item.get("severity"))
    contracts = item.get("Contracts") or item.get("file") or []
    category_raw = item.get("Category") or item.get("category")

    params: Dict[str, Any] = {
        "Issue": str(issue),
        "Severity": severity,
        "Description": str(description),
        "Contracts": _ensure_list(contracts),
    }

    # Only set Category if it's recognized; otherwise let the default (Other) apply
    if isinstance(category_raw, str):
        normalized = category_raw.strip()
        if normalized in {e.value for e in CategoryEnum}:
            params["Category"] = normalized

    return Vulnerability(**params)


def read_truth_data(repository: str, data_root: Path) -> List[Vulnerability]:
    path = get_truth_path(repository, data_root)
    data = json.loads(path.read_text(encoding="utf-8"))
    # Support two shapes:
    # 1) Array of items already matching our schema
    # 2) Object with { project_id, vulnerabilities: [...] } (current source_of_truth)
    items: List[Dict[str, Any]]
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("vulnerabilities"), list):
        # Map to our structure
        items = []
        for v in data["vulnerabilities"]:
            mapped = {
                "Issue": v.get("title"),
                "Category": v.get("category"),
                "Severity": v.get("severity"),
                "Description": v.get("description"),
                "Contracts": [v.get("file")],
            }
            items.append(mapped)
    else:
        raise ValueError(f"Unsupported truth data format in {path}")

    # Clean and normalize
    for item in items:
        item.pop("Submitted", None)
        item.pop("Link", None)

    return [_to_vulnerability(item) for item in items]


def read_scan_results(repository: str, data_root: Path, scan_source: str) -> List[Vulnerability]:
    path = get_scan_path(repository, data_root, scan_source)
    data = json.loads(path.read_text(encoding="utf-8"))
    items: List[Dict[str, Any]]
    if isinstance(data, list):
        # e.g., auditagent exporting a plain array of finding objects
        items = data
    elif isinstance(data, dict):
        # e.g., hound shape { project, findings: [...] }
        if isinstance(data.get("findings"), list):
            items = []
            for f in data["findings"]:
                mapped = {
                    "Issue": f.get("title") or f.get("Issue"),
                    "Severity": f.get("severity") or f.get("Severity"),
                    "Description": f.get("description") or f.get("Description"),
                    "file": f.get("file"),
                    "Category": _map_category_from_vulnerability_type(f.get("vulnerability_type")),
                }
                items.append(mapped)
        else:
            raise ValueError(f"Unsupported scan results format in {path}")
    else:
        raise ValueError(f"Unsupported scan results format in {path}")

    return [_to_vulnerability(it) for it in items]


def store_evaluation_result(
    results: List[EvaluatedFinding], repository: str, output_root: Path
) -> None:
    path = get_evaluation_path(repository, output_root)
    ensure_dir(path.parent)
    payload = [r.model_dump(mode="json") for r in results]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def store_debug_prompt(prompt: str, repository: str, output_root: Path) -> None:
    ensure_dir(output_root)
    (output_root / f"{repository}_prompt.txt").write_text(prompt, encoding="utf-8")
