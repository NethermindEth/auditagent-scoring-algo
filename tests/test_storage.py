"""Tests for storage helpers: severity/category normalization, the truth and
scan JSON shapes we accept, and the evaluation-result round-trip."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scoring_algo.core import storage
from scoring_algo.core.types import CategoryEnum
from tests._helpers import make_evaluated, write_dataset


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("critical", "High"),
        ("High", "High"),
        ("med", "Medium"),
        ("moderate", "Medium"),
        ("low", "Low"),
        ("informational", "Info"),
        ("info", "Info"),
        ("best practices", "Best Practices"),
        ("weird-thing", "Weird-Thing"),
    ],
)
def test_normalize_severity(raw, expected):
    assert storage.normalize_severity(raw) == expected


def test_normalize_severity_non_string_is_na():
    assert storage.normalize_severity(None) == "N/A"
    assert storage.normalize_severity(3) == "N/A"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("reentrancy bug", CategoryEnum.REENTRANCY.value),
        ("missing access control", CategoryEnum.ACCESS_CONTROL.value),
        ("integer overflow", CategoryEnum.INTEGER_OVERFLOW_UNDERFLOW.value),
        ("denial of service", CategoryEnum.DENIAL_OF_SERVICE.value),
        ("unchecked external call", CategoryEnum.UNCHECKED_CALL.value),
        ("front-running", CategoryEnum.FRONT_RUNNING.value),
        ("config issue", CategoryEnum.CONFIG_DEPENDENT.value),
        ("precision loss", CategoryEnum.PRECISION_LOSS.value),
        ("centralization risk", CategoryEnum.CENTRALIZATION_RISK.value),
        ("business logic error", CategoryEnum.BUSINESS_LOGIC.value),
        ("nothing recognizable", None),
    ],
)
def test_map_category_from_vulnerability_type(raw, expected):
    assert storage._map_category_from_vulnerability_type(raw) == expected


def test_ensure_list():
    assert storage._ensure_list(None) == []
    assert storage._ensure_list("x") == ["x"]
    assert storage._ensure_list(["a", None, "b"]) == ["a", "b"]


def test_to_vulnerability_maps_alternate_keys():
    v = storage._to_vulnerability(
        {"title": "T", "description": "D", "severity": "high", "file": "C.sol"}
    )
    assert v.Issue == "T"
    assert v.Severity.value == "High"
    assert v.Contracts == ["C.sol"]
    assert v.Category is CategoryEnum.OTHER  # unrecognized -> default


def test_read_truth_and_scan_from_disk(tmp_path: Path):
    write_dataset(
        tmp_path,
        "repoA",
        truth=[
            {
                "title": "T1",
                "severity": "high",
                "description": "d1",
                "file": "C.sol",
                "category": "Reentrancy",
            }
        ],
        scan=[{"Issue": "S1", "Severity": "Low", "Description": "d", "Contracts": ["C.sol"]}],
    )
    truth = storage.read_truth_data("repoA", tmp_path)
    scan = storage.read_scan_results("repoA", tmp_path, "auditagent")
    assert len(truth) == 1 and truth[0].Issue == "T1"
    assert len(scan) == 1 and scan[0].Issue == "S1"


def test_read_scan_results_findings_object_shape(tmp_path: Path):
    """The baseline exporter uses ``{project, findings: [...]}`` with lowercase keys
    and a ``vulnerability_type`` that maps into our Category enum."""
    (tmp_path / "baseline").mkdir(parents=True)
    (tmp_path / "baseline" / "repoB_results.json").write_text(
        json.dumps(
            {
                "project": "repoB",
                "findings": [
                    {
                        "title": "F1",
                        "severity": "high",
                        "description": "d",
                        "file": "C.sol",
                        "vulnerability_type": "reentrancy",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scan = storage.read_scan_results("repoB", tmp_path, "baseline")
    assert len(scan) == 1
    assert scan[0].Issue == "F1"
    assert scan[0].Severity.value == "High"
    assert scan[0].Category is CategoryEnum.REENTRANCY  # from vulnerability_type


def test_read_scan_results_rejects_unknown_shape(tmp_path: Path):
    (tmp_path / "auditagent").mkdir(parents=True)
    (tmp_path / "auditagent" / "repoX_results.json").write_text(
        json.dumps({"unexpected": True}), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        storage.read_scan_results("repoX", tmp_path, "auditagent")


def test_read_truth_data_rejects_unknown_shape(tmp_path: Path):
    (tmp_path / "source_of_truth").mkdir(parents=True)
    (tmp_path / "source_of_truth" / "repoX.json").write_text(
        json.dumps("not a supported shape"), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        storage.read_truth_data("repoX", tmp_path)


def test_read_empty_arrays_return_empty(tmp_path: Path):
    write_dataset(tmp_path, "repoEmpty", truth=[], scan=[])
    assert storage.read_truth_data("repoEmpty", tmp_path) == []
    assert storage.read_scan_results("repoEmpty", tmp_path, "auditagent") == []


def test_store_evaluation_result_roundtrip(tmp_path: Path):
    out = tmp_path / "bench"
    storage.store_evaluation_result([make_evaluated(is_match=True, index=0)], "repoA", out)
    path = storage.get_evaluation_path("repoA", out)
    data = json.loads(path.read_text())
    assert isinstance(data, list) and data[0]["is_match"] is True
