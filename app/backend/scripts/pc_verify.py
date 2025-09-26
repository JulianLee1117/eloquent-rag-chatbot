from pinecone.grpc import PineconeGRPC as Pinecone
import json
import math
from statistics import mean
from app.core.config import settings

API_KEY = settings.pinecone_api_key
HOST    = str(settings.pinecone_host)
INDEX   = settings.pinecone_index
NS      = ""  # default namespace

# Tweak these to control output
SEARCH              = None    # e.g., "protein" to filter by content; or None for all
SHOW_FULL           = False   # True to print full content; False to truncate
PREVIEW_LEN         = 200     # chars when SHOW_FULL is False
N_IDS               = 200     # how many IDs to sample per namespace
FETCH_BATCH         = 100     # fetch batch size
LOOP_ALL_NAMESPACES = True    # scan every namespace with vectors
VALUES_PREVIEW_N    = 8       # how many embedding floats to preview

pc = Pinecone(api_key=API_KEY)
index = pc.Index(host=HOST)  # data-plane client

print("=== describe_index_stats ===")
stats = index.describe_index_stats()
print(stats)

def preview(text: str | None, n: int = PREVIEW_LEN) -> str | None:
    if not text:
        return text
    if SHOW_FULL or len(text) <= n:
        return text
    return text[:n] + "..."

def preview_values(values: list[float] | None, n: int = VALUES_PREVIEW_N) -> str:
    if not values:
        return "(none)"
    head = values[:n]
    return "[" + ", ".join(f"{v:.4f}" for v in head) + (" ...]" if len(values) > n else "]")

def emb_stats(values: list[float] | None) -> dict | None:
    if not values:
        return None
    return {
        "dim": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
        "l2": math.sqrt(sum(v * v for v in values)),
    }

def guess_content(meta: dict) -> str | None:
    candidates = [
        "chunk_text", "page_content", "text", "content", "body", "raw_text", "chunk"
    ]
    for key in candidates:
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            return val
    # Fallback: any long string value in metadata
    for key, val in meta.items():
        if isinstance(val, str) and len(val) > 30:
            return val
    return None

namespaces = [NS]
if LOOP_ALL_NAMESPACES and isinstance(stats, dict):
    ns_map = (stats or {}).get("namespaces", {}) or {}
    if ns_map:
        namespaces = [n for n, v in ns_map.items() if (v or {}).get("vector_count", 0) > 0]

for curr_ns in namespaces:
    print(f"\n=== namespace: '{curr_ns}' ===")
    ids: list[str] = []
    for page in index.list(namespace=curr_ns):
        ids.extend(page)
        if len(ids) >= N_IDS:
            ids = ids[:N_IDS]
            break
    if not ids:
        print("(no vectors in this namespace)")
        continue
    print(f"sample ids: {ids[:10]}")

    print("--- fetch and list full metadata + embeddings per vector ---")
    for i in range(0, len(ids), FETCH_BATCH):
        batch_ids = ids[i:i + FETCH_BATCH]
        recs = index.fetch(ids=batch_ids, namespace=curr_ns)
        for rid, vec in recs.vectors.items():
            meta = getattr(vec, "metadata", {}) or {}
            values = getattr(vec, "values", None)

            content = guess_content(meta)
            if SEARCH and content and SEARCH.lower() not in content.lower():
                continue

            print(f"\nID: {rid}")
            print("metadata (json):")
            try:
                print(json.dumps(meta, indent=2, ensure_ascii=False))
            except Exception:
                # If non-serializable values exist
                print(str(meta))

            print("content (guess):")
            print(preview(content))

            stats_obj = emb_stats(values)
            print("embedding preview:", preview_values(values))
            if stats_obj:
                print(
                    "embedding stats: "
                    f"dim={stats_obj['dim']}, "
                    f"min={stats_obj['min']:.4f}, "
                    f"max={stats_obj['max']:.4f}, "
                    f"mean={stats_obj['mean']:.4f}, "
                    f"l2={stats_obj['l2']:.4f}"
                )
            else:
                print("embedding stats: (no values returned)")