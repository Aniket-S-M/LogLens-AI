
import json
from pathlib import Path

from loglens.incident_store import IncidentRetriever


ROOT = Path(__file__).resolve().parents[1]
QUERIES_PATH = ROOT / "evaluation" / "incident_queries.json"
RESULTS_PATH = ROOT / "evaluation" / "incident_retrieval_results.json"


def main():
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))

    retriever = IncidentRetriever(
        dataset_path=ROOT / "data" / "incidents.json",
        db_path=ROOT / "data" / "chroma_db",
    )
    retriever.index_incidents()

    results = []

    recall_at_1 = []
    recall_at_3 = []
    reciprocal_ranks = []

    for case in queries:
        expected = set(case["expected_ids"])
        matches = retriever.search(case["query"], top_k=3)
        ranked_ids = [match["id"] for match in matches]

        hit_at_1 = bool(expected.intersection(ranked_ids[:1]))
        hit_at_3 = bool(expected.intersection(ranked_ids[:3]))

        rank = next(
            (
                index
                for index, incident_id in enumerate(ranked_ids, start=1)
                if incident_id in expected
            ),
            None,
        )

        reciprocal_rank = 1 / rank if rank is not None else 0.0

        recall_at_1.append(float(hit_at_1))
        recall_at_3.append(float(hit_at_3))
        reciprocal_ranks.append(reciprocal_rank)

        results.append({
            "id": case["id"],
            "query": case["query"],
            "expected_ids": sorted(expected),
            "ranked_ids": ranked_ids,
            "hit_at_1": hit_at_1,
            "hit_at_3": hit_at_3,
            "reciprocal_rank": reciprocal_rank,
            "correct_rank": rank,
        })

        print(f"\n{case['id']}: {case['query']}")
        print(f"Expected: {sorted(expected)}")
        print(f"Retrieved: {ranked_ids}")
        print(f"Correct rank: {rank}")

    count = len(results)
    if count == 0:
        raise ValueError("No evaluation queries found")

    summary = {
        "total_queries": count,
        "recall_at_1": sum(recall_at_1) / count,
        "recall_at_3": sum(recall_at_3) / count,
        "mrr": sum(reciprocal_ranks) / count,
        "results": results,
    }

    RESULTS_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n--- Retrieval Evaluation ---")
    print(f"Queries: {count}")
    print(f"Recall@1: {summary['recall_at_1']:.1%}")
    print(f"Recall@3: {summary['recall_at_3']:.1%}")
    print(f"MRR:      {summary['mrr']:.3f}")
    print(f"Saved: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
