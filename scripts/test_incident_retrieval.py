
from loglens.incident_store import IncidentRetriever


retriever = IncidentRetriever()
count = retriever.index_incidents()
print(f"Indexed {count} historical incidents.")

query = "ERROR: Database connection refused"

matches = retriever.search(query, top_k=3)

print(f"\nQuery: {query}")

for match in matches:
    print(f"\n{match['id']} — {match['title']}")
    print(f"Category: {match['category']}")
    print(f"Root cause: {match['root_cause']}")
    print(f"Resolution: {match['resolution']}")
    print(f"Source: {match['source']}")
    print(f"Cosine distance: {match['distance']:.4f}")
