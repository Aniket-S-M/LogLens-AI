
import json
from pathlib import Path


DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "cases.json"
)


def test_evaluation_dataset_is_valid():
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    assert len(cases) >= 4

    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))

    valid_categories = {
        "clear_failure",
        "benign",
        "ambiguous",
    }

    valid_statuses = {
        "success",
        "insufficient_evidence",
    }

    for case in cases:
        assert case["category"] in valid_categories
        assert case["expected_status"] in valid_statuses
        assert isinstance(case["logs"], str)
        assert case["logs"].strip()
        assert isinstance(case["expected_keywords"], list)
        assert isinstance(case["expected_evidence"], list)

    assert {
        case["category"] for case in cases
    } == valid_categories
