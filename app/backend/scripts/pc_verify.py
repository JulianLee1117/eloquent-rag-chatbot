from pinecone.grpc import PineconeGRPC as Pinecone
from app.core.config import settings

API_KEY = settings.pinecone_api_key
HOST    = str(settings.pinecone_host)
INDEX   = settings.pinecone_index
NS      = "__default__"               # or your namespace

pc = Pinecone(api_key=API_KEY)

# Data-plane client (use host directly in production)
index = pc.Index(host=HOST)

print("=== describe_index_stats ===")
stats = index.describe_index_stats()
print(stats)  # includes "dimension" and counts per namespace

print("\n=== sample IDs (first ~50, prefix 'faq::' if you used that) ===")
# List IDs to see naming pattern (use a prefix if you expect one)
for batch in index.list(namespace=NS):
    print(batch[:10])  # first 10 per page
    break

# === sample IDs (first ~50) ===
NS = ""  # default namespace is empty string in your index
first_ids = []
for batch in index.list(namespace=NS):  # list IDs is paginated generator
    print(batch[:10])                   # preview IDs
    first_ids.extend(batch[:5])
    break

if first_ids:
    print("\n=== fetch metadata for first few IDs ===")
    recs = index.fetch(ids=first_ids, namespace=NS)
    # FetchResponse.vectors is a dict: {id: Vector(id, values, metadata)}
    for rid, vec in recs.vectors.items():
        meta = getattr(vec, "metadata", {}) or {}
        print(rid, {k: meta.get(k) for k in ["category","heading","source","chunk_index","chunk_text"]})
