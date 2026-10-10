
import json

import pytest

from loglens.incident_store import (
    IncidentRetriever,
    load_incidents,
)


def write_dataset(tmp_path, incidents):
    path = tmp_path / "incidents.json"
    path.write_text(
        json.dumps(incidents),
        encoding="utf-8",
    )
    return path


def sample_incident():
    return {
        "id": "INC-001",
        "title": "Database connection refused",
        "category": "database",
        "symptoms": (
            "Database connection failed. Connection refused."
        ),
        "root_cause": (
            "The database service was unavailable."
        ),
        "resolution": (
            "Verify database health and configured host and port."
        ),
        "source": "Synthetic incident for testing",
    }


def test_load_incidents_validates_dataset(tmp_path):
    path = write_dataset(tmp_path, [sample_incident()])

    incidents = load_incidents(path)

    assert len(incidents) == 1
    assert incidents[0]["id"] == "INC-001"


def test_load_incidents_rejects_missing_fields(tmp_path):
    path = write_dataset(
        tmp_path,
        [{"id": "INC-001", "title": "Incomplete"}],
    )

    with pytest.raises(ValueError, match="missing fields"):
        load_incidents(path)


def test_load_incidents_rejects_duplicate_ids(tmp_path):
    incident = sample_incident()
    path = write_dataset(tmp_path, [incident, incident])

    with pytest.raises(ValueError, match="Duplicate incident ID"):
        load_incidents(path)


def test_search_returns_relevant_incident(tmp_path):
    dataset = write_dataset(
        tmp_path,
        [sample_incident()],
    )

    retriever = IncidentRetriever(
        dataset_path=dataset,
        db_path=tmp_path / "chroma",
    )
    retriever.index_incidents()

    results = retriever.search(
        "ERROR database connection refused",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0]["id"] == "INC-001"
    assert results[0]["category"] == "database"
    assert "Verify database health" in results[0]["resolution"]


def test_indexing_is_repeatable(tmp_path):
    dataset = write_dataset(
        tmp_path,
        [sample_incident()],
    )

    retriever = IncidentRetriever(
        dataset_path=dataset,
        db_path=tmp_path / "chroma",
    )

    assert retriever.index_incidents() == 1
    assert retriever.index_incidents() == 1
    assert retriever.collection.count() == 1
