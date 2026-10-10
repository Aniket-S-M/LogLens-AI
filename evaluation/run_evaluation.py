
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from loglens.api import number_log_lines
from loglens.llm_client import analyze_logs, OllamaClientError

DATASET_PATH = PROJECT_ROOT / "evaluation" / "cases.json"
RESULTS_PATH = PROJECT_ROOT / "evaluation" / "results.json"


def main():
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    results = []

    for case in cases:
        print(f"\nEvaluating: {case['id']}")
        started = time.perf_counter()

        try:
            numbered_logs = number_log_lines(case["logs"])
            report, metrics = analyze_logs(numbered_logs)

            actual_status = report.status

            # Collect diagnosis text for keyword matching.
            diagnosis_text = " ".join(
                " ".join([
                    diagnosis.title,
                    diagnosis.summary,
                    diagnosis.likely_cause,
                    *diagnosis.recommended_actions,
                ])
                for diagnosis in report.diagnoses
            ).lower()

            expected_keywords = [
                keyword.lower()
                for keyword in case["expected_keywords"]
            ]

            matched_keywords = [
                keyword
                for keyword in expected_keywords
                if keyword in diagnosis_text
            ]

            # Compare expected excerpts against verified citations.
            expected_evidence = case["expected_evidence"]

            cited_excerpts = [
                item.excerpt.lower()
                for diagnosis in report.diagnoses
                for item in diagnosis.evidence
            ]

            matched_evidence = [
                excerpt
                for excerpt in expected_evidence
                if any(
                    excerpt.lower() in cited
                    for cited in cited_excerpts
                )
            ]

            keyword_coverage = (
                len(matched_keywords) / len(expected_keywords)
                if expected_keywords else None
            )

            evidence_coverage = (
                len(matched_evidence) / len(expected_evidence)
                if expected_evidence else None
            )

            result = {
                "id": case["id"],
                "category": case["category"],
                "expected_status": case["expected_status"],
                "actual_status": actual_status,
                "status_match": (
                    actual_status == case["expected_status"]
                ),
                "diagnosis_count": len(report.diagnoses),
                "matched_keywords": matched_keywords,
                "keyword_coverage": keyword_coverage,
                "matched_evidence": matched_evidence,
                "evidence_coverage": evidence_coverage,
                "latency_ms": metrics["latency_ms"],
                "evidence_valid": True,
                "error": None,
            }

            print(f"Expected: {case['expected_status']}")
            print(f"Actual:   {actual_status}")
            print(f"Status match: {result['status_match']}")

            if keyword_coverage is not None:
                print(f"Keyword coverage: {keyword_coverage:.0%}")

            if evidence_coverage is not None:
                print(f"Evidence coverage: {evidence_coverage:.0%}")

            print(f"Latency: {metrics['latency_ms']:.2f} ms")

        except (OllamaClientError, ValueError) as exc:
            result = {
                "id": case["id"],
                "category": case["category"],
                "expected_status": case["expected_status"],
                "actual_status": "error",
                "status_match": False,
                "diagnosis_count": 0,
                "matched_keywords": [],
                "keyword_coverage": None,
                "matched_evidence": [],
                "evidence_coverage": None,
                "latency_ms": round(
                    (time.perf_counter() - started) * 1000, 2
                ),
                "evidence_valid": False,
                "error": str(exc),
            }

            print(f"ERROR: {exc}")

        results.append(result)

    completed = [
        item for item in results
        if item["actual_status"] != "error"
    ]

    status_matches = sum(
        item["status_match"] for item in results
    )

    keyword_scores = [
        item["keyword_coverage"]
        for item in completed
        if item["keyword_coverage"] is not None
    ]

    evidence_scores = [
        item["evidence_coverage"]
        for item in completed
        if item["evidence_coverage"] is not None
    ]

    summary = {
        "total_cases": len(results),
        "completed_cases": len(completed),
        "failed_cases": len(results) - len(completed),
        "status_matches": status_matches,
        "status_match_rate": (
            status_matches / len(results) if results else 0.0
        ),
        "average_keyword_coverage": (
            sum(keyword_scores) / len(keyword_scores)
            if keyword_scores else None
        ),
        "average_evidence_coverage": (
            sum(evidence_scores) / len(evidence_scores)
            if evidence_scores else None
        ),
        "average_latency_ms": (
            sum(item["latency_ms"] for item in completed)
            / len(completed)
            if completed else None
        ),
        "results": results,
    }

    RESULTS_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n--- EVALUATION SUMMARY ---")
    print(json.dumps(
        {
            key: value
            for key, value in summary.items()
            if key != "results"
        },
        indent=2,
    ))

    print(f"\nDetailed results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
