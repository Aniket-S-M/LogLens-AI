
import json
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


DEFAULT_DATASET = Path("data/incidents.json")
DEFAULT_DB_PATH = Path("data/chroma_db")
DEFAULT_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "historical_incidents"


def load_incidents(path: str | Path = DEFAULT_DATASET) -> list[dict]:
    """Load and validate the historical incident dataset."""
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        incidents = json.load(file)

    if not isinstance(incidents, list):
        raise ValueError("Incident dataset must be a JSON list")

    required_fields = {
        "id", "title", "category", "symptoms",
        "root_cause", "resolution", "source",
    }
    seen_ids = set()

    for incident in incidents:
        if not isinstance(incident, dict):
            raise ValueError("Each incident must be a JSON object")

        missing = required_fields - incident.keys()
        if missing:
            raise ValueError(
                f"Incident is missing fields: {sorted(missing)}"
            )

        if not all(
            isinstance(incident[field], str) and incident[field].strip()
            for field in required_fields
        ):
            raise ValueError("Incident fields must be non-empty strings")

        if incident["id"] in seen_ids:
            raise ValueError(f"Duplicate incident ID: {incident['id']}")

        seen_ids.add(incident["id"])

    return incidents


def incident_document(incident: dict) -> str:
    """Build the text that will be embedded and searched."""
    return (
        f"Title: {incident['title']}\n"
        f"Category: {incident['category']}\n"
        f"Symptoms: {incident['symptoms']}\n"
        f"Root cause: {incident['root_cause']}\n"
        f"Resolution: {incident['resolution']}"
    )


class IncidentRetriever:
    """Persistent local vector search over historical incidents."""

    def __init__(
        self,
        dataset_path: str | Path = DEFAULT_DATASET,
        db_path: str | Path = DEFAULT_DB_PATH,
        model_name: str = DEFAULT_MODEL,
    ):
        self.dataset_path = Path(dataset_path)
        self.db_path = Path(db_path)

        self.model = SentenceTransformer(model_name)
        self.client = chromadb.PersistentClient(
            path=str(self.db_path)
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def index_incidents(self) -> int:
        """Index the dataset, replacing stale entries on re-index."""
        incidents = load_incidents(self.dataset_path)

        existing = self.collection.get()
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        if not incidents:
            return 0

        documents = [incident_document(item) for item in incidents]
        embeddings = self.model.encode(
            documents,
            normalize_embeddings=True,
        ).tolist()

        self.collection.add(
            ids=[item["id"] for item in incidents],
            documents=documents,
            embeddings=embeddings,
            metadatas=[
                {
                    "title": item["title"],
                    "category": item["category"],
                    "symptoms": item["symptoms"],
                    "root_cause": item["root_cause"],
                    "resolution": item["resolution"],
                    "source": item["source"],
                }
                for item in incidents
            ],
        )

        return len(incidents)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Retrieve the closest incidents for a non-empty query."""
        if not query.strip():
            raise ValueError("Search query must not be blank")

        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        if self.collection.count() == 0:
            return []

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self.collection.count()),
            include=["metadatas", "distances"],
        )

        matches = []
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for incident_id, metadata, distance in zip(
            ids, metadatas, distances
        ):
            matches.append({
                "id": incident_id,
                **metadata,
                "distance": float(distance),
            })

        return matches
